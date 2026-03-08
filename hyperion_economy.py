#!/usr/bin/env python3
"""Hyperion-inspirierte Wirtschaftssimulation (systemisch, ohne Story-Textkopien)."""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


GOOD_DATA: Dict[str, Dict[str, float]] = {
    "nahrung": {"base_price": 28, "volatility": 0.14, "strategic": 0.7},
    "rohstoffe": {"base_price": 42, "volatility": 0.20, "strategic": 0.8},
    "industrieteile": {"base_price": 67, "volatility": 0.24, "strategic": 0.85},
    "energie": {"base_price": 56, "volatility": 0.19, "strategic": 0.9},
    "luxus": {"base_price": 120, "volatility": 0.28, "strategic": 0.5},
    "biotech": {"base_price": 142, "volatility": 0.30, "strategic": 0.95},
    "core_daten": {"base_price": 175, "volatility": 0.26, "strategic": 0.7},
    "relikte": {"base_price": 260, "volatility": 0.40, "strategic": 0.45},
}
GOODS = list(GOOD_DATA.keys())


@dataclass
class World:
    name: str
    category: str
    population_factor: float
    production: Dict[str, float]
    consumption: Dict[str, float]
    stability: float
    prosperity: float
    faction: str
    farcaster: bool
    periphery: bool
    hyperion_special: bool = False
    pilgrim_pull: float = 0.0
    stock: Dict[str, float] = field(default_factory=dict)
    prices: Dict[str, float] = field(default_factory=dict)
    time_debt: float = 0.0
    embargo_ticks: int = 0

    def __post_init__(self) -> None:
        for good in GOODS:
            self.stock.setdefault(good, 16.0 + self.population_factor * 10)
            self.prices.setdefault(good, GOOD_DATA[good]["base_price"])


@dataclass
class EventEffect:
    name: str
    ticks_left: int
    modifiers: Dict[str, float]


@dataclass
class SimulationConfig:
    ticks: int = 20
    seed: int = 7
    event_chance: float = 0.45
    trade_intensity: float = 1.0
    faction_strength: float = 1.0
    core_fee: float = 0.015


class HyperionEconomySim:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.tick = 0
        self.worlds = self._build_worlds()
        self.active_effects: List[EventEffect] = []
        self.current_events: List[str] = []
        self.trade_log: List[str] = []
        self.faction_state: Dict[str, float] = {
            "hegemony_control": 1.0,
            "core_signal": 1.0,
            "ouster_threat": 1.0,
            "templar_access": 0.0,
        }

    def _build_worlds(self) -> List[World]:
        return [
            World("Lusus", "Kernwelt", 1.6, {"luxus": 3, "core_daten": 2}, {"nahrung": 4, "energie": 2}, 0.86, 0.9, "Hegemonie", True, False),
            World("Tau Ceti", "Agrarwelt", 1.4, {"nahrung": 6, "biotech": 1.5}, {"energie": 2, "industrieteile": 2}, 0.84, 0.72, "Hegemonie", True, False),
            World("Maui-Covenant", "Templarwelt", 1.0, {"biotech": 2.2, "nahrung": 2}, {"energie": 1.5, "luxus": 1}, 0.9, 0.7, "Templars", True, False),
            World("Marsim", "Industriewelt", 1.5, {"industrieteile": 5, "energie": 3}, {"rohstoffe": 4, "nahrung": 2.4}, 0.77, 0.78, "Hegemonie", True, False),
            World("Qom-Riyadh", "Datenwelt", 1.2, {"core_daten": 4.4, "luxus": 1.1}, {"nahrung": 2, "energie": 2}, 0.8, 0.83, "TechnoCore", True, False),
            World("Bressia", "Grenzwelt", 0.9, {"rohstoffe": 3.2, "energie": 1.4}, {"nahrung": 2.6, "industrieteile": 1.9}, 0.63, 0.5, "Hegemonie", False, True),
            World("Hebron", "Pilgerwelt", 1.0, {"luxus": 1.3}, {"nahrung": 2.2, "energie": 1.8, "biotech": 1.6}, 0.7, 0.55, "Hegemonie", False, True, pilgrim_pull=1.2),
            World("Hyperion", "Sonderwelt", 0.8, {"relikte": 0.7, "rohstoffe": 1.4}, {"nahrung": 1.8, "energie": 2.1, "luxus": 1.4}, 0.58, 0.45, "Neutral", False, True, hyperion_special=True, pilgrim_pull=2.0),
        ]

    def _combined_modifiers(self) -> Dict[str, float]:
        merged = {
            "farcaster_efficiency": 1.0,
            "transport_cost_bonus": 0.0,
            "risk_bonus": 0.0,
            "core_noise": 0.08,
            "pilgrim_demand": 1.0,
            "production_penalty": 0.0,
            "templar_bonus": 0.0,
        }
        for effect in self.active_effects:
            for key, value in effect.modifiers.items():
                if key in {"transport_cost_bonus", "risk_bonus", "core_noise", "production_penalty", "templar_bonus"}:
                    merged[key] += value
                elif key in {"farcaster_efficiency", "pilgrim_demand"}:
                    merged[key] *= value
        return merged

    def _roll_event(self) -> None:
        self.current_events = []
        if self.rng.random() > self.config.event_chance:
            return

        event_table: List[Tuple[str, float]] = [
            ("farcaster_stoerung", 0.16),
            ("ouster_raid", 0.16),
            ("pilgerboom", 0.14),
            ("sanktionen", 0.12),
            ("core_prognosefehler", 0.12),
            ("core_optimierung", 0.12),
            ("templar_korridor", 0.1),
            ("aufstand", 0.08),
        ]
        pick = self.rng.random()
        pointer = 0.0
        selected = "core_optimierung"
        for name, weight in event_table:
            pointer += weight
            if pick <= pointer:
                selected = name
                break

        if selected == "farcaster_stoerung":
            self.active_effects.append(EventEffect("Farcaster-Störung", 2, {"farcaster_efficiency": 0.25, "transport_cost_bonus": 3.5}))
            self.current_events.append("Farcaster-Störung trifft Kernwelten")
        elif selected == "ouster_raid":
            target = self.rng.choice([w for w in self.worlds if w.periphery])
            target.stability = max(0.2, target.stability - 0.08 * self.config.faction_strength)
            self.active_effects.append(EventEffect("Ouster-Druck", 2, {"risk_bonus": 1.8}))
            self.current_events.append(f"Ouster-Raid bei {target.name}")
        elif selected == "pilgerboom":
            self.active_effects.append(EventEffect("Pilgerboom", 3, {"pilgrim_demand": 1.45}))
            self.current_events.append("Pilgerströme Richtung Hyperion")
        elif selected == "sanktionen":
            target = self.rng.choice([w for w in self.worlds if w.faction == "Hegemonie"])
            target.embargo_ticks = 2
            self.current_events.append(f"Politische Sanktionen gegen {target.name}")
        elif selected == "core_prognosefehler":
            self.active_effects.append(EventEffect("Core-Prognosefehler", 2, {"core_noise": 0.18}))
            self.current_events.append("TechnoCore-Prognosefehler erhöht Marktvolatilität")
        elif selected == "core_optimierung":
            self.active_effects.append(EventEffect("Core-Optimierung", 2, {"core_noise": -0.04, "transport_cost_bonus": -1.2}))
            self.current_events.append("TechnoCore optimiert Handelsnetz temporär")
        elif selected == "templar_korridor":
            self.active_effects.append(EventEffect("Templar-Korridor", 1, {"templar_bonus": 0.9}))
            self.current_events.append("Weltenbaum-Sonderroute verfügbar")
        elif selected == "aufstand":
            target = self.rng.choice([w for w in self.worlds if w.periphery])
            target.stability = max(0.2, target.stability - 0.12)
            self.active_effects.append(EventEffect("Peripherie-Aufstand", 2, {"production_penalty": 0.18, "risk_bonus": 1.2}))
            self.current_events.append(f"Aufstand auf {target.name}")

    def _advance_effects(self) -> None:
        kept: List[EventEffect] = []
        for effect in self.active_effects:
            effect.ticks_left -= 1
            if effect.ticks_left > 0:
                kept.append(effect)
        self.active_effects = kept

    def _produce_and_consume(self, mods: Dict[str, float]) -> None:
        for world in self.worlds:
            prod_penalty = mods["production_penalty"] if world.periphery else mods["production_penalty"] * 0.4
            stability_factor = 0.85 + (world.stability * 0.3)
            for good in GOODS:
                produced = world.production.get(good, 0.0) * stability_factor * (1 - prod_penalty)
                world.stock[good] += produced

                demand = world.consumption.get(good, 0.0) * world.population_factor
                if world.hyperion_special and good in {"luxus", "relikte"}:
                    demand *= 1.0 + (world.pilgrim_pull * 0.2)
                if good in {"luxus", "relikte"}:
                    demand *= mods["pilgrim_demand"]

                if world.stock[good] >= demand:
                    world.stock[good] -= demand
                    world.prosperity = min(1.3, world.prosperity + 0.002)
                else:
                    shortage = demand - world.stock[good]
                    world.stock[good] = 0.0
                    world.stability = max(0.2, world.stability - min(0.015 + shortage * 0.002, 0.06))
                    world.prosperity = max(0.2, world.prosperity - min(0.01 + shortage * 0.0015, 0.05))

    def _update_prices(self, mods: Dict[str, float]) -> None:
        for world in self.worlds:
            for good in GOODS:
                base = GOOD_DATA[good]["base_price"]
                strategic = GOOD_DATA[good]["strategic"]
                volatility = GOOD_DATA[good]["volatility"]
                demand = world.consumption.get(good, 0.0) * max(0.5, world.population_factor)
                available = world.stock[good] + 1.0
                imbalance = (demand + 1.0) / available
                tension = max(0.8, 1.25 - world.stability)
                noise = self.rng.uniform(-mods["core_noise"], mods["core_noise"]) * (1.2 if world.periphery else 0.8)
                price = base * (1 + volatility * (imbalance - 1)) * (1 + strategic * (tension - 1)) * (1 + noise)
                world.prices[good] = max(4.0, round(price, 2))

    def _transport_cost(self, source: World, target: World, mods: Dict[str, float]) -> Tuple[float, float]:
        if source.farcaster and target.farcaster:
            cost = 0.8 / max(0.15, mods["farcaster_efficiency"]) + mods["transport_cost_bonus"]
            time_debt = 0.0
        else:
            cost = 4.5 + mods["transport_cost_bonus"] + (2.3 if source.periphery or target.periphery else 0.0)
            cost += mods["risk_bonus"] * 0.6
            time_debt = 0.35 + (0.35 if source.periphery or target.periphery else 0.0)
            if mods["templar_bonus"] > 0 and (source.faction == "Templars" or target.faction == "Templars"):
                cost = max(0.7, cost - 2.5 * mods["templar_bonus"])
                time_debt = max(0.1, time_debt - 0.25)

        cost += self.config.core_fee * 10 * self.faction_state["core_signal"]
        return max(0.2, cost), time_debt

    def _trade(self, mods: Dict[str, float]) -> None:
        self.trade_log.clear()
        route_capacity = 6.0 * self.config.trade_intensity
        for good in GOODS:
            exporters = []
            importers = []
            for world in self.worlds:
                reserve = 7.5 + world.population_factor * 2.0
                surplus = world.stock[good] - reserve
                deficit = reserve - world.stock[good]
                if surplus > 0.8 and world.embargo_ticks <= 0:
                    exporters.append((world, surplus))
                if deficit > 0.8:
                    importers.append((world, deficit))

            exporters.sort(key=lambda pair: pair[0].prices[good])
            importers.sort(key=lambda pair: pair[0].prices[good], reverse=True)

            for buyer, deficit in importers:
                remaining = deficit
                for idx, (seller, surplus) in enumerate(exporters):
                    if remaining <= 0.1 or surplus <= 0.1:
                        continue
                    if seller is buyer:
                        continue
                    unit_cost, time_debt = self._transport_cost(seller, buyer, mods)
                    margin = buyer.prices[good] - (seller.prices[good] + unit_cost)
                    if margin <= 0:
                        continue

                    qty = min(surplus, remaining, route_capacity)
                    if qty <= 0:
                        continue

                    seller.stock[good] -= qty
                    buyer.stock[good] += qty
                    sale_price = seller.prices[good]
                    seller.prosperity = min(1.4, seller.prosperity + 0.004 * qty)
                    buyer.prosperity = min(1.4, buyer.prosperity + 0.003 * qty)
                    buyer.time_debt += qty * time_debt

                    exporters[idx] = (seller, surplus - qty)
                    remaining -= qty
                    self.trade_log.append(
                        f"{good}: {seller.name} -> {buyer.name} ({qty:.1f} u, kosten {unit_cost:.1f})"
                    )

    def _post_tick_updates(self) -> None:
        for world in self.worlds:
            if world.embargo_ticks > 0:
                world.embargo_ticks -= 1
            if world.time_debt > 0:
                debt_drag = min(0.03, 0.002 + world.time_debt * 0.0001)
                world.prosperity = max(0.2, world.prosperity - debt_drag)
                world.time_debt *= 0.92
            world.prosperity = min(1.5, max(0.2, world.prosperity))

    def step(self) -> None:
        self.tick += 1
        self._roll_event()
        mods = self._combined_modifiers()
        self.faction_state["templar_access"] = mods["templar_bonus"]
        self.faction_state["ouster_threat"] = 1.0 + (mods["risk_bonus"] * 0.2)
        self.faction_state["core_signal"] = max(0.6, 1.0 + mods["core_noise"] * 0.8)

        self._produce_and_consume(mods)
        self._update_prices(mods)
        self._trade(mods)
        self._post_tick_updates()
        self._advance_effects()

    def summary(self) -> str:
        top_prices: List[Tuple[str, float, str]] = []
        shortages: List[Tuple[float, str, str]] = []

        for world in self.worlds:
            for good in GOODS:
                top_prices.append((good, world.prices[good], world.name))
                reserve = 7.5 + world.population_factor * 2
                shortages.append((reserve - world.stock[good], world.name, good))

        top_prices.sort(key=lambda x: x[1], reverse=True)
        shortages.sort(key=lambda x: x[0], reverse=True)
        richest = sorted(self.worlds, key=lambda w: w.prosperity, reverse=True)[:3]
        stable = sorted(self.worlds, key=lambda w: w.stability, reverse=True)[:3]

        lines = [
            f"\n=== Tick {self.tick} ===",
            f"Aktive Ereignisse: {', '.join(self.current_events) if self.current_events else 'keine'}",
            f"Fraktionen: Hegemonie={self.faction_state['hegemony_control']:.2f} | Core-Signal={self.faction_state['core_signal']:.2f} | Ouster-Druck={self.faction_state['ouster_threat']:.2f} | Templar-Zugang={self.faction_state['templar_access']:.2f}",
            "Top-Preise:",
        ]
        for good, price, world_name in top_prices[:5]:
            lines.append(f"  - {good:14s} {price:7.2f} @ {world_name}")

        lines.append("Reichste/Prosperierende Welten:")
        for w in richest:
            lines.append(f"  - {w.name:12s} Wohlstand={w.prosperity:.2f} Stabilität={w.stability:.2f} TimeDebt={w.time_debt:.1f}")

        lines.append("Stabilste Welten:")
        for w in stable:
            lines.append(f"  - {w.name:12s} Stabilität={w.stability:.2f}")

        lines.append("Größte Engpässe:")
        for deficit, world_name, good in shortages[:5]:
            if deficit > 0.2:
                lines.append(f"  - {world_name:12s} fehlt {good:14s} ({deficit:.1f} u)")

        if self.trade_log:
            lines.append("Handelslog (Auszug):")
            for entry in self.trade_log[:6]:
                lines.append(f"  - {entry}")
        return "\n".join(lines)

    def run(self) -> None:
        for _ in range(self.config.ticks):
            self.step()
            print(self.summary())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hyperion-inspirierte interplanetare Wirtschaftssimulation")
    parser.add_argument("--ticks", type=int, default=20, help="Anzahl der Ticks")
    parser.add_argument("--seed", type=int, default=7, help="Seed für reproduzierbare Läufe")
    parser.add_argument("--event-chance", type=float, default=0.45, help="Wahrscheinlichkeit pro Tick für Ereignisse")
    parser.add_argument("--trade-intensity", type=float, default=1.0, help="Handelsintensität")
    parser.add_argument("--faction-strength", type=float, default=1.0, help="Stärke politischer Fraktionseffekte")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = SimulationConfig(
        ticks=args.ticks,
        seed=args.seed,
        event_chance=args.event_chance,
        trade_intensity=args.trade_intensity,
        faction_strength=args.faction_strength,
    )
    HyperionEconomySim(config).run()


if __name__ == "__main__":
    main()
