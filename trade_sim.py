#!/usr/bin/env python3
"""Terminal-Handelssimulation ohne curses/Textual.

Läuft nur mit Python-Standardbibliothek in praktisch jeder Umgebung.
"""

from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass, field
from typing import Dict, List

GOODS = ["Getreide", "Eisen", "Gewürze", "Tuch", "Werkzeuge", "Luxusgüter"]
CITY_NAMES = ["Aurelia", "Dornhafen", "Eiswacht", "Kupferfurt", "Neonheim"]
BASE_PRICES = {
    "Getreide": 32,
    "Eisen": 75,
    "Gewürze": 140,
    "Tuch": 95,
    "Werkzeuge": 120,
    "Luxusgüter": 220,
}


class KeyReader:
    """Liest einzelne Tasten ohne curses.

    - Windows: msvcrt
    - POSIX: termios/tty
    - Fallback: input()
    """

    def __init__(self) -> None:
        self.is_tty = sys.stdin.isatty() and sys.stdout.isatty()

    def read(self) -> str:
        if not self.is_tty:
            return self._line_input()

        if os.name == "nt":
            return self._read_windows()
        return self._read_posix()

    def _line_input(self) -> str:
        try:
            return input("Befehl > ").strip().lower()[:1]
        except EOFError:
            return "q"

    @staticmethod
    def _read_windows() -> str:
        import msvcrt  # type: ignore

        ch = msvcrt.getwch()
        if ch in {"\x00", "\xe0"}:  # Spezialtaste
            nxt = msvcrt.getwch()
            return {"H": "k", "P": "j"}.get(nxt, "")
        return ch.lower()

    @staticmethod
    def _read_posix() -> str:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                if seq == "[A":
                    return "k"
                if seq == "[B":
                    return "j"
                return ""
            return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


@dataclass
class City:
    name: str
    prices: Dict[str, int] = field(default_factory=dict)


@dataclass
class GameState:
    money: int = 1200
    debt: int = 500
    day: int = 1
    cargo_capacity: int = 24
    fuel: int = 8
    max_fuel: int = 8
    location_index: int = 0
    selected_good_index: int = 0
    selected_city_index: int = 1
    status: str = "Willkommen im Markt!"
    cargo: Dict[str, int] = field(default_factory=lambda: {g: 0 for g in GOODS})
    cities: List[City] = field(default_factory=list)

    @property
    def location(self) -> City:
        return self.cities[self.location_index]

    @property
    def cargo_used(self) -> int:
        return sum(self.cargo.values())

    @property
    def net_worth(self) -> int:
        cargo_value = sum(self.cargo[g] * self.location.prices[g] for g in GOODS)
        return self.money + cargo_value - self.debt


class TradeSim:
    def __init__(self) -> None:
        self.rng = random.Random()
        self.state = GameState(cities=[City(name=n) for n in CITY_NAMES])
        self.key_reader = KeyReader()
        self.generate_market(initial=True)

    def generate_market(self, initial: bool = False) -> None:
        for city in self.state.cities:
            prices: Dict[str, int] = {}
            for good in GOODS:
                base = BASE_PRICES[good]
                volatility = self.rng.uniform(0.6, 1.5)
                bonus = 1.0
                if city.name == "Eiswacht" and good in {"Eisen", "Werkzeuge"}:
                    bonus = 0.82
                elif city.name == "Dornhafen" and good in {"Getreide", "Tuch"}:
                    bonus = 0.84
                elif city.name == "Aurelia" and good in {"Luxusgüter", "Gewürze"}:
                    bonus = 0.79
                prices[good] = int(max(10, base * volatility * bonus))
            city.prices = prices

        if not initial:
            self.state.status = "Neuer Tag: Marktpreise haben sich geändert."

    @staticmethod
    def clear_screen() -> None:
        print("\033[2J\033[H", end="")

    @staticmethod
    def color(text: str, code: str) -> str:
        if not sys.stdout.isatty():
            return text
        return f"\033[{code}m{text}\033[0m"

    def boxed(self, title: str, lines: List[str], width: int = 84, color_code: str = "36") -> List[str]:
        top = f"┌{'─' * (width - 2)}┐"
        head = f"│ {title[: width - 4]:<{width - 4}} │"
        sep = f"├{'─' * (width - 2)}┤"
        out = [self.color(top, color_code), self.color(head, color_code), self.color(sep, color_code)]
        for line in lines:
            out.append(f"│ {line[: width - 4]:<{width - 4}} │")
        out.append(self.color(f"└{'─' * (width - 2)}┘", color_code))
        return out

    def render(self) -> None:
        self.clear_screen()
        st = self.state

        header = [
            f"Tag {st.day} | Ort: {st.location.name} | Gold: {st.money} | Schulden: {st.debt} | Treibstoff: {st.fuel}/{st.max_fuel} | Laderaum: {st.cargo_used}/{st.cargo_capacity}",
            f"Nettovermögen: {st.net_worth} | Rang: {self.rank(st.net_worth)}",
        ]

        market_lines = ["Ware                Preis     Lager"]
        for i, good in enumerate(GOODS):
            marker = "▶" if i == st.selected_good_index else " "
            market_lines.append(f"{marker} {good:<16} {st.location.prices[good]:>5} G   {st.cargo[good]:>3}")

        city_lines = ["Reiseziel wählen"]
        for i, city in enumerate(st.cities):
            marker = "▶" if i == st.selected_city_index else " "
            here = " (Hier)" if i == st.location_index else ""
            city_lines.append(f"{marker} {city.name}{here}")

        help_lines = [
            "k/j oder Pfeil hoch/runter = Ware wählen | w/s = Stadt wählen",
            "b = kaufen | v = verkaufen | t = reisen | r = tanken",
            "d = Schulden zahlen | n = nächster Tag | q = beenden",
            f"Status: {st.status}",
        ]

        for block in (
            self.boxed("NEON TRADE TYCOON (ohne curses)", header, color_code="35"),
            self.boxed("MARKT", market_lines, color_code="36"),
            self.boxed("STÄDTE", city_lines, color_code="34"),
            self.boxed("KOMMANDOS", help_lines, color_code="32"),
        ):
            print("\n".join(block))

        if self.key_reader.is_tty:
            print("Taste drücken...", end=" ", flush=True)

    @staticmethod
    def rank(wealth: int) -> str:
        if wealth > 7000:
            return "Magnat"
        if wealth > 4000:
            return "Aufsteiger"
        if wealth > 1800:
            return "Händler"
        return "Anfänger"

    def buy(self) -> None:
        st = self.state
        good = GOODS[st.selected_good_index]
        price = st.location.prices[good]
        if st.cargo_used >= st.cargo_capacity:
            st.status = "Laderaum voll."
            return
        if st.money < price:
            st.status = "Zu wenig Gold."
            return
        st.money -= price
        st.cargo[good] += 1
        st.status = f"Gekauft: 1x {good} für {price} G."

    def sell(self) -> None:
        st = self.state
        good = GOODS[st.selected_good_index]
        if st.cargo[good] <= 0:
            st.status = f"Kein {good} im Laderaum."
            return
        price = st.location.prices[good]
        st.cargo[good] -= 1
        st.money += price
        st.status = f"Verkauft: 1x {good} für {price} G."

    def travel(self) -> None:
        st = self.state
        target = st.selected_city_index
        if target == st.location_index:
            st.status = "Du bist bereits dort."
            return
        if st.fuel <= 0:
            st.status = "Kein Treibstoff. Tanke mit r."
            return
        st.location_index = target
        st.fuel -= 1
        self.advance_day("Reise abgeschlossen.")

    def refuel(self) -> None:
        st = self.state
        cost = 160
        if st.fuel >= st.max_fuel:
            st.status = "Tank ist schon voll."
            return
        if st.money < cost:
            st.status = "Nicht genug Gold zum Tanken."
            return
        st.money -= cost
        st.fuel = st.max_fuel
        st.status = "Tank aufgefüllt."

    def repay_debt(self) -> None:
        st = self.state
        if st.debt <= 0:
            st.status = "Du bist schuldenfrei."
            return
        amount = min(250, st.money, st.debt)
        if amount <= 0:
            st.status = "Kein Gold für Tilgung."
            return
        st.money -= amount
        st.debt -= amount
        st.status = f"{amount} G Schulden getilgt."

    def advance_day(self, msg: str = "Nächster Tag.") -> None:
        st = self.state
        st.day += 1
        st.debt = int(st.debt * 1.02)
        self.generate_market()
        st.status = msg

    def handle_key(self, key: str) -> bool:
        st = self.state
        if key == "q":
            return False
        if key in {"k"}:
            st.selected_good_index = (st.selected_good_index - 1) % len(GOODS)
        elif key in {"j"}:
            st.selected_good_index = (st.selected_good_index + 1) % len(GOODS)
        elif key == "w":
            st.selected_city_index = (st.selected_city_index - 1) % len(st.cities)
        elif key == "s":
            st.selected_city_index = (st.selected_city_index + 1) % len(st.cities)
        elif key == "b":
            self.buy()
        elif key == "v":
            self.sell()
        elif key == "t":
            self.travel()
        elif key == "r":
            self.refuel()
        elif key == "d":
            self.repay_debt()
        elif key == "n":
            self.advance_day("Du wartest einen Tag und beobachtest den Markt.")
        else:
            st.status = "Unbekannte Taste."
        return True

    def run(self) -> None:
        running = True
        while running:
            self.render()
            key = self.key_reader.read()
            if not key:
                continue
            running = self.handle_key(key)
        self.clear_screen()
        print("Danke fürs Spielen von Neon Trade Tycoon.")


def main() -> None:
    sim = TradeSim()
    sim.run()


if __name__ == "__main__":
    main()
