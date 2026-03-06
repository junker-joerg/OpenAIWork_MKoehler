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
                price = int(max(12, base * volatility * bonus))
                city_prices[good] = price
            city.prices = city_prices

        if not initial:
            self.state.status_msg = "Neuer Handelstag: Marktpreise wurden aktualisiert."

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
        self.state.day += 1
        self.generate_market()
        self.state.debt = int(self.state.debt * 1.02)
        self.state.status_msg = f"Reise nach {self.state.location.name} abgeschlossen."

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
        self.generate_market()
        self.state.status_msg = "Du ruhst einen Tag und studierst den Markt."

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
        if h < 32 or w < 100:
            self.stdscr.addstr(0, 0, "Bitte Fenster auf mindestens 100x32 vergrößern.")
            self.stdscr.refresh()
            return

        self.draw_box(0, 0, 6, w, "NEON TRADE TYCOON", 2)
        self.draw_box(6, 0, 17, w // 2, "Markt", 1)
        self.draw_box(6, w // 2, 17, w - (w // 2), "Städte", 1)
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

        commands = "[↑/↓] Ware  [W/S] Stadt  [B] Kaufen  [V] Verkaufen  [T] Reisen  [R] Tanken  [D] Schulden zahlen  [N] Nächster Tag  [Q] Ende"
        self.stdscr.addstr(24, 2, textwrap.shorten(commands, width=w - 5, placeholder="…"), curses.A_BOLD)
        self.stdscr.addstr(26, 2, st.status_msg[: w - 5], curses.color_pair(5))

        wealth = st.money + sum(st.cargo[g] * st.location.prices[g] for g in GOODS) - st.debt
        rating = (
            "Legende" if wealth > 5000 else "Aufsteiger" if wealth > 2500 else "Händler" if wealth > 1200 else "Anfänger"
        )
        self.stdscr.addstr(28, 2, f"Nettovermögen: {wealth} Gold  |  Rang: {rating}")

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

        running = True
        while running:
            self.draw()
            key = self.stdscr.getch()
            running = self.handle_input(key)


def main() -> None:
    curses.wrapper(lambda stdscr: TradeGame(stdscr).run())


if __name__ == "__main__":
    main()
