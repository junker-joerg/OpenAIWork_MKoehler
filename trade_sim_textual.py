from __future__ import annotations

import random
import asyncio
import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static, Header, Footer, Button
from textual.reactive import reactive
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from textual.events import Key

GOODS = ["Getreide", "Eisen", "Gewürze", "Tuch", "Werkzeuge", "Luxusgüter"]
CITY_NAMES = ["Aurelia", "Dornhafen", "Eiswacht", "Kupferfurt", "Neonheim"]
BASE_PRICES = {g: v for g, v in zip(GOODS, [32, 75, 140, 95, 120, 220])}


@dataclass
class City:
    name: str
    prices: Dict[str, int] = field(default_factory=dict)
    pos: Tuple[int, int] = (0, 0)  # map coordinates
    supply: Dict[str, int] = field(default_factory=dict)


@dataclass
class GameState:
    money: int = 1000
    debt: int = 400
    day: int = 1
    fuel: int = 8
    max_fuel: int = 8
    location_index: int = 0
    cargo_capacity: int = 20
    selected_good_index: int = 0
    selected_city_index: int = 1
    cargo: Dict[str, int] = field(default_factory=lambda: {g: 0 for g in GOODS})
    cities: List[City] = field(default_factory=lambda: [City(name=n) for n in CITY_NAMES])
    events: List[str] = field(default_factory=list)
    active_effects: List[dict] = field(default_factory=list)
    map_stars: List[Tuple[int, int, str]] = field(default_factory=list)
    contracts: List[dict] = field(default_factory=list)

    def location(self) -> City:
        return self.cities[self.location_index]


class MarketWidget(Static):
    def render(self) -> Panel:
        st: GameState = self.app.state
        table = Table.grid()
        table.add_column(justify="left", ratio=2)
        table.add_column(justify="right")
        table.add_column(justify="right")
        table.add_column(justify="right")
        table.add_row("Ware", "Preis", "Vorrat", "Im Laderaum")
        city = st.cities[st.location_index]
        for i, g in enumerate(GOODS):
            price = city.prices.get(g, BASE_PRICES[g])
            supply = city.supply.get(g, 0)
            cargo = st.cargo.get(g, 0)
            sel = "▶" if i == st.selected_good_index else " "
            table.add_row(f"{sel} {g}", f"{price} G", f"{supply}", f"{cargo}")
        footer = f"Laderaum: {sum(st.cargo.values())}/{st.cargo_capacity} | Stadt: {city.name}"
        return Panel(table, title="Markt", subtitle=footer)


class EventWidget(Static):
    def render(self) -> Panel:
        st: GameState = self.app.state
        lines = st.events[-6:][::-1]
        content = "\n".join(lines) if lines else "Keine Ereignisse"
        return Panel(Align.left(content), title=f"Tag {st.day} - Ereignisse")


class MapWidget(Static):
    def render(self) -> Panel:
        st: GameState = self.app.state
        w, h = 38, 12
        grid = [[" " for _ in range(w)] for _ in range(h)]
        # static starfield from state
        for (x, y, ch) in st.map_stars:
            if 0 <= x < w and 0 <= y < h:
                grid[y][x] = ch
        # cities
        for i, c in enumerate(st.cities):
            x = int((i / max(1, len(st.cities) - 1)) * (w - 6)) + 2
            y = 2 + (i % 3) * 3
            c.pos = (x, y)
            grid[y][x] = "✦" if i == st.location_index else "✩"
        lines = ["".join(row) for row in grid]
        return Panel("\n".join(lines), title="Sternenkarte")


class Controls(Static):
    pass


class TextualTradeApp(App):
    CSS_PATH = None
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("b", "buy", "Buy"),
        ("v", "sell", "Sell"),
        ("t", "travel", "Travel"),
        ("up", "select_up", "SelectUp"),
        ("down", "select_down", "SelectDown"),
        ("left", "select_left", "SelectLeft"),
        ("right", "select_right", "SelectRight"),
        ("c", "contract", "Contract"),
    ]

    state: GameState = reactive(GameState())

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical():
                yield MarketWidget(id="market")
                yield EventWidget(id="events")
            yield MapWidget(id="map")
        yield Footer()

    async def on_mount(self) -> None:
        # initialize market prices
        for city in self.state.cities:
            city.prices = {g: int(BASE_PRICES[g] * random.uniform(0.7, 1.4)) for g in GOODS}
            city.supply = {g: random.randint(8, 48) for g in GOODS}
        # start periodic refresh
        # prepare a static starfield for the map (no animation)
        w_rel, h_rel = 36, 10
        stars = []
        for _ in range(90):
            stars.append((random.randrange(w_rel), random.randrange(h_rel), random.choice(['.', '*', '·'])))
        self.state.map_stars = stars

        self.set_interval(1.2, self.refresh_screen)
        # optional demo mode for automated testing
        if os.environ.get("TEXTUAL_DEMO") == "1":
            asyncio.create_task(self._demo_sequence())

    async def _demo_sequence(self) -> None:
        # wait a moment for UI to initialize
        await asyncio.sleep(0.4)
        # perform a few actions
        self.action_buy()
        await asyncio.sleep(0.2)
        self.action_travel()
        await asyncio.sleep(0.2)
        self.action_buy()
        await asyncio.sleep(0.2)
        self.action_sell()
        await asyncio.sleep(0.2)
        self.action_travel()
        await asyncio.sleep(0.2)
        # print a short summary to stdout so the wrapper can capture it
        print("--- DEMO SUMMARY ---")
        print(f"Tag: {self.state.day}, Ort: {self.state.cities[self.state.location_index].name}")
        print("Letzte Ereignisse:")
        for e in self.state.events[-10:]:
            print(e)
        # exit the app
        await asyncio.sleep(0.2)
        self.exit()

    async def refresh_screen(self) -> None:
        # advance simulation by one day: age effects, update market, maybe new event
        self.state.day += 1
        # age active effects
        for eff in list(self.state.active_effects):
            eff['days'] -= 1
            if eff['days'] <= 0:
                self.state.active_effects.remove(eff)

        # recompute prices with small volatility + active effects
        for city in self.state.cities:
            for g in GOODS:
                base = BASE_PRICES[g]
                volatility = random.uniform(0.9, 1.12)
                mult = 1.0
                for eff in self.state.active_effects:
                    if (eff.get('city') is None or eff.get('city') == city.name) and (eff.get('good') is None or eff.get('good') == g):
                        mult *= eff.get('mult', 1.0)
                city.prices[g] = max(5, int(base * volatility * mult))

        # occasional new economic event
        if random.random() < 0.25:
            c = random.choice(self.state.cities)
            g = random.choice(GOODS)
            kind = random.choice(['Boom', 'Knappheit', 'Überschuss'])
            dur = random.randint(2, 5)
            if kind == 'Boom':
                mult = random.uniform(1.3, 1.8)
            elif kind == 'Knappheit':
                mult = random.uniform(1.2, 1.45)
            else:
                mult = random.uniform(0.5, 0.85)
            ev = {'desc': f"{kind} in {c.name} für {g} ({dur}d)", 'days': dur, 'city': c.name, 'good': g, 'mult': mult}
            self.state.active_effects.append(ev)
            self.state.events.append(ev['desc'])
            if len(self.state.events) > 80:
                self.state.events.pop(0)
        # refresh widgets (refresh() is synchronous)
        self.query_one(MarketWidget).refresh()
        self.query_one(MapWidget).refresh()
        self.query_one(EventWidget).refresh()

    def on_key(self, event: Key) -> None:
        # Log raw key names to help debugging bindings
        keyname = getattr(event, "key", None)
        self.state.events.append(f"(key) {keyname}")
        # keep log short
        if len(self.state.events) > 80:
            self.state.events.pop(0)
        # refresh event widget quickly
        try:
            self.query_one(EventWidget).refresh()
        except Exception:
            pass

    def action_buy(self) -> None:
        city = self.state.cities[self.state.location_index]
        good = GOODS[self.state.selected_good_index]
        price = city.prices.get(good, BASE_PRICES[good])
        if city.supply.get(good, 0) <= 0:
            self.state.events.append(f"Kein {good} auf dem Markt in {city.name} verfügbar.")
            return
        if self.state.money < price:
            self.state.events.append("Nicht genug Gold.")
            return
        if sum(self.state.cargo.values()) >= self.state.cargo_capacity:
            self.state.events.append("Laderaum voll.")
            return
        # buy one unit
        city.supply[good] -= 1
        self.state.money -= price
        self.state.cargo[good] += 1
        self.state.events.append(f"Gekauft: 1x {good} für {price} G")

    def action_sell(self) -> None:
        good = GOODS[self.state.selected_good_index]
        amount = self.state.cargo.get(good, 0)
        city = self.state.cities[self.state.location_index]
        if amount <= 0:
            self.state.events.append(f"Kein {good} im Laderaum zum Verkaufen.")
            return
        price = city.prices.get(good, BASE_PRICES[good])
        self.state.cargo[good] -= 1
        self.state.money += price
        # selling increases local supply
        city.supply[good] = city.supply.get(good, 0) + 1
        self.state.events.append(f"Verkauft: 1x {good} für {price} G")

    def action_travel(self) -> None:
        # simple next city travel
        self.state.location_index = (self.state.location_index + 1) % len(self.state.cities)
        self.state.fuel = max(0, self.state.fuel - 1)
        dest = self.state.cities[self.state.location_index].name
        self.state.events.append(f"Reise nach {dest}")
        # check for contract deliveries upon arrival
        delivered = []
        for c in list(self.state.contracts):
            if c.get('to') == dest:
                # deliver: remove goods from cargo and give reward
                good = c.get('good')
                qty = c.get('qty', 0)
                carried = min(qty, self.state.cargo.get(good, 0))
                if carried > 0:
                    self.state.cargo[good] -= carried
                    self.state.money += c.get('reward', 0)
                    self.state.events.append(f"Vertrag erfüllt: {carried}x {good} = +{c.get('reward',0)} G")
                else:
                    self.state.events.append(f"Vertrag verfehlt: {good} nicht an Bord.")
                self.state.contracts.remove(c)
                delivered.append(c)

    def action_select_up(self) -> None:
        self.state.selected_good_index = (self.state.selected_good_index - 1) % len(GOODS)

    def action_select_down(self) -> None:
        self.state.selected_good_index = (self.state.selected_good_index + 1) % len(GOODS)

    def action_select_left(self) -> None:
        self.state.selected_city_index = (self.state.selected_city_index - 1) % len(self.state.cities)

    def action_select_right(self) -> None:
        self.state.selected_city_index = (self.state.selected_city_index + 1) % len(self.state.cities)

    def action_contract(self) -> None:
        # create a simple freight contract from current city to selected city
        if self.state.selected_city_index == self.state.location_index:
            self.state.events.append("Zielstadt gleich aktuelle Stadt - kein Vertrag möglich.")
            return
        good = GOODS[self.state.selected_good_index]
        src = self.state.cities[self.state.location_index]
        if src.supply.get(good, 0) <= 0:
            self.state.events.append("Nicht genug Ware für Vertrag.")
            return
        qty = min(5, src.supply.get(good, 0), self.state.cargo_capacity - sum(self.state.cargo.values()))
        if qty <= 0:
            self.state.events.append("Kein Laderaum verfügbar für Vertrag.")
            return
        # reserve supply and load cargo
        src.supply[good] -= qty
        self.state.cargo[good] += qty
        reward = int((src.prices.get(good, BASE_PRICES[good]) * 1.4) * qty)
        contract = {"from": src.name, "to": self.state.cities[self.state.selected_city_index].name, "good": good, "qty": qty, "reward": reward}
        self.state.contracts.append(contract)
        self.state.events.append(f"Vertrag angenommen: {qty}x {good} → {contract['to']} für {reward} G")
        # travel may trigger travel-events
        if random.random() < 0.35:
            roll = random.random()
            if roll < 0.18:
                loss = min(self.state.money, random.randint(50, 200))
                self.state.money -= loss
                self.state.events.append(f"Piratenüberfall: -{loss} G")
            elif roll < 0.33:
                leak = min(self.state.fuel, 1)
                self.state.fuel = max(0, self.state.fuel - leak)
                self.state.events.append(f"Treibstoffleck: -{leak} Treibstoff")
            elif roll < 0.53:
                found = random.randint(20, 160)
                self.state.money += found
                self.state.events.append(f"Gefundenes Handelsschiff: +{found} G")
            else:
                extra_cost = random.randint(20, 100)
                self.state.debt += extra_cost
                self.state.day += 1
                self.state.events.append(f"Maschinenprobleme: +1 Tag, +{extra_cost} Schulden")


if __name__ == "__main__":
    TextualTradeApp().run()
