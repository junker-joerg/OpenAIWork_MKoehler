#!/usr/bin/env python3
"""Neon Trade Tycoon - kleine Wirtschaftssimulation im Terminal."""

from __future__ import annotations

import curses
import random
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List


GOODS = [
    "Getreide",
    "Eisen",
    "Gewürze",
    "Tuch",
    "Werkzeuge",
    "Luxusgüter",
]

CITY_NAMES = ["Aurelia", "Dornhafen", "Eiswacht", "Kupferfurt", "Neonheim"]

BASE_PRICES = {
    "Getreide": 32,
    "Eisen": 75,
    "Gewürze": 140,
    "Tuch": 95,
    "Werkzeuge": 120,
    "Luxusgüter": 220,
}


@dataclass
class City:
    name: str
    prices: Dict[str, int] = field(default_factory=dict)
    # optional map position (computed in draw if not set)
    map_x: int = 0
    map_y: int = 0


@dataclass
class Event:
    desc: str
    days: int
    city_name: str | None = None
    good: str | None = None
    multiplier: float = 1.0


@dataclass
class GameState:
    money: int = 1000
    debt: int = 400
    day: int = 1
    cargo_capacity: int = 20
    fuel: int = 8
    max_fuel: int = 8
    location_index: int = 0
    selected_good_index: int = 0
    selected_city_index: int = 1
    status_msg: str = "Willkommen, Händler!"
    cargo: Dict[str, int] = field(default_factory=lambda: {good: 0 for good in GOODS})
    cities: List[City] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    active_effects: List[Event] = field(default_factory=list)
    # relative starfield for the map: tuples (x_rel, y_rel, char, color_pair)
    map_stars: List[tuple] = field(default_factory=list)

    @property
    def location(self) -> City:
        return self.cities[self.location_index]

    @property
    def cargo_used(self) -> int:
        return sum(self.cargo.values())

    @property
    def cargo_free(self) -> int:
        return self.cargo_capacity - self.cargo_used


class TradeGame:
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self.rng = random.Random()
        self.state = GameState(cities=[City(name=n) for n in CITY_NAMES])
        self.generate_market(initial=True)
        # Erzeuge initiale Sternenfelder / Nebel (relative Koordinaten)
        self.generate_starfield()

    def generate_starfield(self) -> None:
        # create a pool of relative stars within a canonical map size
        stars: List[tuple] = []
        w_rel = 48
        h_rel = 9
        for _ in range(80):
            x = self.rng.randint(0, w_rel - 1)
            y = self.rng.randint(0, h_rel - 1)
            ch = self.rng.choice(['.', '·', '*'])
            color = self.rng.choice([6, 5, 4])
            stars.append((x, y, ch, color))
        # add a few nebula 'clouds'
        for _ in range(6):
            x = self.rng.randint(0, w_rel - 6)
            y = self.rng.randint(0, h_rel - 3)
            # nebula uses different chars and color
            for dx in range(5):
                for dy in range(2):
                    if self.rng.random() < 0.45:
                        stars.append((x + dx, y + dy, self.rng.choice(['≈', '¤', '~']), 7))
        self.state.map_stars = stars

    def _bresenham(self, x0: int, y0: int, x1: int, y1: int) -> List[tuple]:
        # return list of points between two coordinates (inclusive)
        points: List[tuple] = []
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            points.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return points

    def generate_market(self, initial: bool = False) -> None:
        for city in self.state.cities:
            city_prices: Dict[str, int] = {}
            for good in GOODS:
                base = BASE_PRICES[good]
                volatility = self.rng.uniform(0.65, 1.45)
                bonus = 1.0
                if city.name == "Eiswacht" and good in {"Eisen", "Werkzeuge"}:
                    bonus = 0.8
                elif city.name == "Dornhafen" and good in {"Getreide", "Tuch"}:
                    bonus = 0.82
                elif city.name == "Aurelia" and good in {"Luxusgüter", "Gewürze"}:
                    bonus = 0.78
                # apply active effects multipliers (product)
                mult = 1.0
                for eff in self.state.active_effects:
                    if (eff.city_name is None or eff.city_name == city.name) and (
                        eff.good is None or eff.good == good
                    ):
                        mult *= eff.multiplier

                price = int(max(8, base * volatility * bonus * mult))
                city_prices[good] = price
            city.prices = city_prices

        if not initial:
            self.state.status_msg = "Neuer Handelstag: Marktpreise wurden aktualisiert."
        # Geringe Chance für wirtschaftliche Ereignisse
        if self.rng.random() < 0.25:
            self.generate_economic_event()

    def buy_selected(self) -> None:
        good = GOODS[self.state.selected_good_index]
        price = self.state.location.prices[good]

        if self.state.cargo_free <= 0:
            self.state.status_msg = "Laderaum ist voll."
            return
        if self.state.money < price:
            self.state.status_msg = "Nicht genug Gold zum Kaufen."
            return

        self.state.money -= price
        self.state.cargo[good] += 1
        self.state.status_msg = f"Gekauft: 1x {good} für {price} Gold."

    def sell_selected(self) -> None:
        good = GOODS[self.state.selected_good_index]
        amount = self.state.cargo[good]
        if amount <= 0:
            self.state.status_msg = f"Kein {good} zum Verkaufen vorhanden."
            return

        price = self.state.location.prices[good]
        self.state.cargo[good] -= 1
        self.state.money += price
        self.state.status_msg = f"Verkauft: 1x {good} für {price} Gold."

    def travel(self) -> None:
        target = self.state.selected_city_index
        if target == self.state.location_index:
            self.state.status_msg = "Du bist bereits in dieser Stadt."
            return
        if self.state.fuel <= 0:
            self.state.status_msg = "Kein Treibstoff! Drücke [R] zum Tanken (150 Gold)."
            return

        self.state.location_index = target
        self.state.fuel -= 1
        # ein Tag vergeht bei der Reise
        self.state.day += 1
        # Zins für Schulden
        self.state.debt = int(self.state.debt * 1.02)
        # Altere aktive Effekte um einen Tag
        self.age_effects(1)
        # Markt neu berechnen nach Ankunft
        self.generate_market()
        self.state.status_msg = f"Reise nach {self.state.location.name} abgeschlossen."
        # Reiseereignis mit Wahrscheinlichkeit, kann zusätzliche Tage verursachen
        if self.rng.random() < 0.35:
            extra = self.generate_travel_event()
            if extra and extra > 0:
                for _ in range(extra):
                    self.state.day += 1
                    self.age_effects(1)
                    self.state.debt = int(self.state.debt * 1.02)
                    self.generate_market()

    def refuel(self) -> None:
        cost = 150
        if self.state.money < cost:
            self.state.status_msg = "Nicht genug Gold zum Tanken."
            return
        if self.state.fuel >= self.state.max_fuel:
            self.state.status_msg = "Tank ist bereits voll."
            return
        self.state.money -= cost
        self.state.fuel = self.state.max_fuel
        self.state.status_msg = "Tank aufgefüllt."

    def repay_debt(self) -> None:
        if self.state.debt <= 0:
            self.state.status_msg = "Keine Schulden mehr. Stark!"
            return
        payment = min(200, self.state.money, self.state.debt)
        if payment <= 0:
            self.state.status_msg = "Du hast kein Gold für die Tilgung."
            return
        self.state.money -= payment
        self.state.debt -= payment
        self.state.status_msg = f"{payment} Gold Schulden zurückgezahlt."

    def next_day(self) -> None:
        self.state.day += 1
        self.state.debt = int(self.state.debt * 1.02)
        self.age_effects(1)
        self.generate_market()
        self.state.status_msg = "Du ruhst einen Tag und studierst den Markt."

    def push_event(self, text: str) -> None:
        self.state.events.append(text)
        # begrenze Loglänge
        if len(self.state.events) > 8:
            self.state.events.pop(0)

    def generate_economic_event(self) -> None:
        city = self.rng.choice(self.state.cities)
        good = self.rng.choice(GOODS)
        kind = self.rng.choice(["Boom", "Knappheit", "Überschuss"])
        dur = int(self.rng.uniform(2, 5))
        if kind == "Boom":
            mult = self.rng.uniform(1.35, 1.8)
            msg = f"Wirtschaftsboom in {city.name}: {good}-Preis erhöht für {dur} Tage."
        elif kind == "Knappheit":
            mult = self.rng.uniform(1.2, 1.45)
            msg = f"Knappheit in {city.name}: {good} wird teurer für {dur} Tage."
        else:
            mult = self.rng.uniform(0.5, 0.85)
            msg = f"Überschuss in {city.name}: {good} wird billiger für {dur} Tage."
        ev = Event(desc=msg, days=dur, city_name=city.name, good=good, multiplier=mult)
        self.state.active_effects.append(ev)
        self.push_event(msg)

    def generate_travel_event(self) -> None:
        target_city = self.state.location
        roll = self.rng.random()
        extra_days = 0
        if roll < 0.18:
            # Piratenangriff: Verlust oder Zahlung
            loss = min(self.state.money, int(self.rng.uniform(50, 200)))
            self.state.money -= loss
            msg = f"Piratenüberfall nahe {target_city.name}: Verluste {loss} Gold."
        elif roll < 0.33:
            # Treibstoffleck
            leak = min(self.state.fuel, 1)
            self.state.fuel = max(0, self.state.fuel - leak)
            msg = f"Treibstoffleck: -{leak} Treibstoff während der Ankunft in {target_city.name}."
        elif roll < 0.53:
            # Finden von Wrack mit kleinen Gewinnen
            found = int(self.rng.uniform(20, 160))
            self.state.money += found
            msg = f"Du entdeckst ein Handelsschiff: +{found} Gold in der Nähe von {target_city.name}."
        else:
            # Mechanisches Problem: verlorener Tag, kleine Schuld
            extra_cost = int(self.rng.uniform(20, 100))
            self.state.debt += extra_cost
            extra_days = 1
            msg = f"Maschinenprobleme bei Ankunft in {target_city.name}: +1 Tag, +{extra_cost} Gold Schulden."
        self.push_event(msg)
        return extra_days

    def draw_box(self, y: int, x: int, h: int, w: int, title: str, color_pair: int = 1) -> None:
        self.stdscr.attron(curses.color_pair(color_pair))
        self.stdscr.addstr(y, x, "┌" + "─" * (w - 2) + "┐")
        for row in range(y + 1, y + h - 1):
            self.stdscr.addstr(row, x, "│" + " " * (w - 2) + "│")
        self.stdscr.addstr(y + h - 1, x, "└" + "─" * (w - 2) + "┘")
        label = f" {title} "
        if len(label) < w - 2:
            self.stdscr.addstr(y, x + 2, label)
        self.stdscr.attroff(curses.color_pair(color_pair))

    def draw(self) -> None:
        self.stdscr.clear()
        h, w = self.stdscr.getmaxyx()
        st = self.state
        if h < 32 or w < 100:
            self.stdscr.addstr(0, 0, "Bitte Fenster auf mindestens 100x32 vergrößern.")
            self.stdscr.refresh()
            return

        self.draw_box(0, 0, 6, w, "NEON TRADE TYCOON", 2)
        self.draw_box(6, 0, 17, w // 2, "Markt", 1)
        self.draw_box(6, w // 2, 17, w - (w // 2), "Städte", 1)
        # verbesserte Karte: Verteile Städte frei im Panel und zeichne Linien
        map_x0 = (w // 2) + 3
        map_y0 = 9
        map_w = (w - (w // 2)) - 10
        map_h = 11
        # berechne Positionen (gleichmäßig, aber mit leichter Y-Varianz)
        n = len(st.cities)
        positions = []
        for i, city in enumerate(st.cities):
            px = map_x0 + 2 + int((map_w - 6) * (i / max(1, n - 1)))
            # sinusförmige Variation für schöne Verteilung
            offset = int((map_h - 3) / 2 * (1 + self.rng.uniform(-0.3, 0.3)))
            py = map_y0 + 1 + (map_h // 2) + ( -1 if i % 2 == 0 else 1 ) * (i % 3)
            positions.append((px, py))
            city.map_x = px
            city.map_y = py

        # zeichne Sternenfeld (relativ)
        for sx, sy, ch, col in st.map_stars:
            tx = map_x0 + sx
            ty = map_y0 + sy
            # ein wenig zufälliges Flackern
            char = ch
            if ch == '.':
                char = '*' if (self.rng.random() < 0.06) else '.'
            try:
                if 0 < ty < h and 0 < tx < w:
                    if col >= 6:
                        self.stdscr.addstr(ty, tx, char, curses.color_pair(col))
                    else:
                        self.stdscr.addstr(ty, tx, char)
            except curses.error:
                pass

        # zeichne Linien zwischen benachbarten Städten (Routen)
        for i in range(len(positions) - 1):
            x1, y1 = positions[i]
            x2, y2 = positions[i + 1]
            pts = self._bresenham(x1, y1, x2, y2)
            for (px, py) in pts[1:-1]:
                try:
                    # Punkte als kleine Sternpunkte für spaciges Feeling
                    self.stdscr.addstr(py, px, '·', curses.color_pair(6))
                except curses.error:
                    pass

        # zeichne Städte (mit spacigen Symbolen)
        for i, city in enumerate(st.cities):
            cx, cy = city.map_x, city.map_y
            marker = "✦" if i == st.location_index else "✩"
            try:
                self.stdscr.addstr(cy, cx, marker, curses.color_pair(4))
                self.stdscr.addstr(cy + 1, max(map_x0, cx - 2), city.name[:8])
            except curses.error:
                pass
        self.draw_box(23, 0, 9, w, "Konsole", 3)

        st = self.state
        stats = (
            f"Tag: {st.day:>3}   Ort: {st.location.name:<10}   Gold: {st.money:>6}   "
            f"Schulden: {st.debt:>5}   Treibstoff: {st.fuel}/{st.max_fuel}   "
            f"Laderaum: {st.cargo_used}/{st.cargo_capacity}"
        )
        self.stdscr.addstr(2, 3, stats, curses.A_BOLD)

        # Markttabelle
        self.stdscr.addstr(7, 2, "Ware", curses.A_UNDERLINE)
        self.stdscr.addstr(7, 22, "Preis", curses.A_UNDERLINE)
        self.stdscr.addstr(7, 34, "Im Laderaum", curses.A_UNDERLINE)

        for i, good in enumerate(GOODS):
            y = 9 + i * 2
            price = st.location.prices[good]
            cargo = st.cargo[good]
            selected = i == st.selected_good_index
            attr = curses.A_BOLD | curses.color_pair(4) if selected else curses.A_NORMAL
            marker = "▶" if selected else " "
            self.stdscr.addstr(y, 2, f"{marker} {good:<14}", attr)
            self.stdscr.addstr(y, 22, f"{price:>5} G")
            self.stdscr.addstr(y, 36, f"{cargo:>3}")

        # Städte
        self.stdscr.addstr(7, (w // 2) + 2, "Wähle Zielstadt", curses.A_UNDERLINE)
        for i, city in enumerate(st.cities):
            y = 9 + i * 2
            selected = i == st.selected_city_index
            current = i == st.location_index
            attr = curses.A_BOLD | curses.color_pair(4) if selected else curses.A_NORMAL
            label = city.name
            if current:
                label += "  (Hier)"
            self.stdscr.addstr(y, (w // 2) + 3, ("▶ " if selected else "  ") + label, attr)

        # Konsole: Events + Befehle
        commands = "[↑/↓] Ware  [W/S] Stadt  [B] Kaufen  [V] Verkaufen  [T] Reisen  [R] Tanken  [D] Schulden zahlen  [N] Nächster Tag  [Q] Ende"
        # Zeige letzte Events
        self.stdscr.addstr(23, 2, "Ereignisse:", curses.A_UNDERLINE)
        ev_y = 24
        # aktive Effekte zuerst
        for eff in st.active_effects[-5:]:
            label = f"[{eff.days}d] {eff.desc}"
            self.stdscr.addstr(ev_y, 4, textwrap.shorten(label, width=w - 10))
            ev_y += 1
        for e in st.events[-5:]:
            try:
                self.stdscr.addstr(ev_y, 4, textwrap.shorten(e, width=w - 10))
            except curses.error:
                pass
            ev_y += 1
        # Status und Befehle weiter unten
        try:
            self.stdscr.addstr(ev_y + 0, 2, textwrap.shorten(commands, width=w - 5, placeholder="…"), curses.A_BOLD)
            self.stdscr.addstr(ev_y + 2, 2, st.status_msg[: w - 5], curses.color_pair(5))
        except curses.error:
            pass

        wealth = st.money + sum(st.cargo[g] * st.location.prices[g] for g in GOODS) - st.debt
        rating = (
            "Legende" if wealth > 5000 else "Aufsteiger" if wealth > 2500 else "Händler" if wealth > 1200 else "Anfänger"
        )
        self.stdscr.addstr(h - 3, 2, f"Nettovermögen: {wealth} Gold  |  Rang: {rating}")

        self.stdscr.refresh()

    def handle_input(self, key: int) -> bool:
        if key in (ord("q"), ord("Q")):
            return False
        if key == curses.KEY_UP:
            self.state.selected_good_index = (self.state.selected_good_index - 1) % len(GOODS)
        elif key == curses.KEY_DOWN:
            self.state.selected_good_index = (self.state.selected_good_index + 1) % len(GOODS)
        elif key in (ord("w"), ord("W")):
            self.state.selected_city_index = (self.state.selected_city_index - 1) % len(self.state.cities)
        elif key in (ord("s"), ord("S")):
            self.state.selected_city_index = (self.state.selected_city_index + 1) % len(self.state.cities)
        elif key in (ord("b"), ord("B")):
            self.buy_selected()
        elif key in (ord("v"), ord("V")):
            self.sell_selected()
        elif key in (ord("t"), ord("T")):
            self.travel()
        elif key in (ord("r"), ord("R")):
            self.refuel()
        elif key in (ord("d"), ord("D")):
            self.repay_debt()
        elif key in (ord("n"), ord("N")):
            self.next_day()
        return True

    def run(self) -> None:
        curses.curs_set(0)
        self.stdscr.nodelay(False)
        self.stdscr.keypad(True)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_MAGENTA, -1)
        curses.init_pair(3, curses.COLOR_BLUE, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, curses.COLOR_GREEN, -1)
        # additional color pairs for starfield/nebula
        try:
            curses.init_pair(6, curses.COLOR_WHITE, -1)
            curses.init_pair(7, curses.COLOR_MAGENTA, -1)
            curses.init_pair(8, curses.COLOR_CYAN, -1)
        except Exception:
            pass

        running = True
        while running:
            self.draw()
            key = self.stdscr.getch()
            running = self.handle_input(key)


def main() -> None:
    curses.wrapper(lambda stdscr: TradeGame(stdscr).run())


if __name__ == "__main__":
    main()
