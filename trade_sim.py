#!/usr/bin/env python3
"""Hyperion-inspirierte Wirtschafts- und Handelssimulation.

Die Stammdaten werden aus ``spreadsheet_model`` geladen. Dadurch bleiben
Python- und Tabellenmodell synchron und die CLI bleibt ohne Zusatzpakete
nutzbar.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


MODEL_DIR = Path(__file__).resolve().parent / "spreadsheet_model"


def _read_model_csv(filename: str) -> List[Dict[str, str]]:
    path = MODEL_DIR / filename
    if not path.is_file():
        raise FileNotFoundError(f"Modell-Datei fehlt: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _read_parameters() -> Dict[str, float]:
    return {
        row["parameter"]: float(row["value"])
        for row in _read_model_csv("00_parameters.csv")
    }


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "ja", "yes"}


PARAMETERS = _read_parameters()
GOOD_DATA: Dict[str, Dict[str, float]] = {
    row["good"]: {
        "base_price": float(row["base_price"]),
        "volatility": float(row["volatility"]),
        "strategic": float(row["strategic"]),
    }
    for row in _read_model_csv("01_goods.csv")
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
    cash: float = 1000.0

    def __post_init__(self) -> None:
        for good in GOODS:
            self.stock.setdefault(good, 16.0 + self.population_factor * 10)
            self.prices.setdefault(good, GOOD_DATA[good]["base_price"])


@dataclass
class EventEffect:
    name: str
    ticks_left: int
    modifiers: Dict[str, float]
    target_world: Optional[str] = None


@dataclass(frozen=True)
class EventDefinition:
    key: str
    weight: float
    duration: int
    modifiers: Dict[str, float]
    target_world_rule: str
    description: str


def _read_event_definitions() -> List[EventDefinition]:
    definitions = []
    modifier_keys = (
        "farcaster_efficiency",
        "transport_cost_bonus",
        "risk_bonus",
        "core_noise",
        "pilgrim_demand",
        "production_penalty",
        "templar_bonus",
    )
    for row in _read_model_csv("04_events_table.csv"):
        definitions.append(
            EventDefinition(
                key=row["event_key"],
                weight=float(row["weight"]),
                duration=int(row["duration"]),
                modifiers={key: float(row[key]) for key in modifier_keys},
                target_world_rule=row["target_world_rule"],
                description=row["description"],
            )
        )
    if not definitions or sum(item.weight for item in definitions) <= 0:
        raise ValueError("Die Ereignistabelle muss ein positives Gewicht enthalten.")
    return definitions


EVENT_DEFINITIONS = _read_event_definitions()


@dataclass
class SimulationConfig:
    ticks: int = int(PARAMETERS.get("YEARS", 20))
    seed: int = 7
    event_chance: float = PARAMETERS.get("EVENT_CHANCE", 0.45)
    trade_intensity: float = PARAMETERS.get("TRADE_INTENSITY", 1.0)
    faction_strength: float = PARAMETERS.get("FACTION_STRENGTH", 1.0)
    core_fee: float = PARAMETERS.get("CORE_FEE", 0.015)
    route_capacity: float = 6.0
    base_reserve: float = PARAMETERS.get("BASE_RESERVE", 7.5)
    pop_reserve_factor: float = PARAMETERS.get("POP_RESERVE_FACTOR", 2.0)
    farcaster_base_cost: float = PARAMETERS.get("FARCASTER_BASE_COST", 0.8)
    normal_base_cost: float = PARAMETERS.get("NORMAL_BASE_COST", 4.5)
    periphery_route_addon: float = PARAMETERS.get("PERIPHERY_ROUTE_ADDON", 2.3)
    time_debt_normal: float = PARAMETERS.get("TIME_DEBT_NORMAL", 0.35)
    time_debt_periphery_addon: float = PARAMETERS.get("TIME_DEBT_PERIPHERY_ADDON", 0.35)
    scenario_events: Optional[Dict[int, str]] = None

    def __post_init__(self) -> None:
        if self.ticks <= 0:
            raise ValueError("ticks muss größer als 0 sein.")
        if not 0.0 <= self.event_chance <= 1.0:
            raise ValueError("event_chance muss zwischen 0 und 1 liegen.")
        if self.trade_intensity < 0.0:
            raise ValueError("trade_intensity darf nicht negativ sein.")
        if self.faction_strength < 0.0:
            raise ValueError("faction_strength darf nicht negativ sein.")
        if self.core_fee < 0.0:
            raise ValueError("core_fee darf nicht negativ sein.")
        if self.route_capacity <= 0.0:
            raise ValueError("route_capacity muss positiv sein.")


class HyperionEconomySim:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.tick = 0
        self.worlds = self._build_worlds()
        self.active_effects: List[EventEffect] = []
        self.current_events: List[str] = []
        self.current_event_keys: List[str] = []
        self.trade_log: List[str] = []
        self.trade_records: List[Dict[str, object]] = []
        self.faction_state: Dict[str, float] = {
            "hegemony_control": 1.0,
            "core_signal": 1.0,
            "ouster_threat": 1.0,
            "templar_access": 0.0,
        }

    def _build_worlds(self) -> List[World]:
        profiles = _read_model_csv("03_profiles.csv")
        worlds: List[World] = []
        for row in _read_model_csv("02_worlds.csv"):
            world_profiles = [profile for profile in profiles if profile["world"] == row["world"]]
            production = {
                profile["good"]: float(profile["production"])
                for profile in world_profiles
                if float(profile["production"]) > 0
            }
            consumption = {
                profile["good"]: float(profile["consumption"])
                for profile in world_profiles
                if float(profile["consumption"]) > 0
            }
            population = float(row["population_factor"])
            worlds.append(
                World(
                    name=row["world"],
                    category=row["category"],
                    population_factor=population,
                    production=production,
                    consumption=consumption,
                    stability=float(row["stability"]),
                    prosperity=float(row["prosperity"]),
                    faction=row["faction"],
                    farcaster=_as_bool(row["farcaster"]),
                    periphery=_as_bool(row["periphery"]),
                    hyperion_special=_as_bool(row["hyperion_special"]),
                    pilgrim_pull=float(row["pilgrim_pull"]),
                    cash=1000.0 * population,
                )
            )
        return worlds

    @staticmethod
    def _merge_effects(effects: Iterable[EventEffect]) -> Dict[str, float]:
        merged = {
            "farcaster_efficiency": 1.0,
            "transport_cost_bonus": 0.0,
            "risk_bonus": 0.0,
            "core_noise": 0.08,
            "pilgrim_demand": 1.0,
            "production_penalty": 0.0,
            "templar_bonus": 0.0,
        }
        for effect in effects:
            for key, value in effect.modifiers.items():
                if key in {"transport_cost_bonus", "risk_bonus", "core_noise", "production_penalty", "templar_bonus"}:
                    merged[key] += value
                elif key in {"farcaster_efficiency", "pilgrim_demand"}:
                    merged[key] *= value
        return merged

    def _combined_modifiers(self, world: Optional[World] = None) -> Dict[str, float]:
        effects = [
            effect
            for effect in self.active_effects
            if effect.target_world is None
            or (world is not None and effect.target_world == world.name)
        ]
        return self._merge_effects(effects)

    def _route_modifiers(self, source: World, target: World) -> Dict[str, float]:
        endpoints = {source.name, target.name}
        return self._merge_effects(
            effect
            for effect in self.active_effects
            if effect.target_world is None or effect.target_world in endpoints
        )

    def _roll_event(self) -> None:
        self.current_events = []
        self.current_event_keys = []
        forced_key = None
        if self.config.scenario_events:
            forced_key = self.config.scenario_events.get(self.tick)
        if forced_key is None and self.rng.random() > self.config.event_chance:
            return

        if forced_key is not None:
            selected = next(
                (item for item in EVENT_DEFINITIONS if item.key == forced_key),
                None,
            )
            if selected is None:
                raise ValueError(f"Unbekanntes Szenario-Ereignis: {forced_key}")
        else:
            total_weight = sum(item.weight for item in EVENT_DEFINITIONS)
            pick = self.rng.uniform(0.0, total_weight)
            pointer = 0.0
            selected = EVENT_DEFINITIONS[-1]
            for definition in EVENT_DEFINITIONS:
                pointer += definition.weight
                if pick <= pointer:
                    selected = definition
                    break

        target: Optional[World] = None
        if selected.target_world_rule == "random_periphery":
            target = self.rng.choice([world for world in self.worlds if world.periphery])
        elif selected.target_world_rule == "random_hegemony":
            target = self.rng.choice([world for world in self.worlds if world.faction == "Hegemonie"])

        if target is not None:
            if selected.key == "ouster_raid":
                target.stability = max(0.2, target.stability - 0.08 * self.config.faction_strength)
            elif selected.key == "aufstand":
                target.stability = max(0.2, target.stability - 0.12 * self.config.faction_strength)
            elif selected.key == "sanktionen":
                target.embargo_ticks = selected.duration

        self.active_effects.append(
            EventEffect(
                name=selected.key,
                ticks_left=selected.duration,
                modifiers=selected.modifiers,
                target_world=target.name if target is not None else None,
            )
        )
        description = selected.description
        if target is not None:
            description = f"{description} ({target.name})"
        self.current_events.append(description)
        self.current_event_keys.append(selected.key)

    def _advance_effects(self) -> None:
        kept: List[EventEffect] = []
        for effect in self.active_effects:
            effect.ticks_left -= 1
            if effect.ticks_left > 0:
                kept.append(effect)
        self.active_effects = kept

    def _reserve(self, world: World) -> float:
        return self.config.base_reserve + world.population_factor * self.config.pop_reserve_factor

    def _produce_and_consume(self, mods: Optional[Dict[str, float]] = None) -> None:
        for world in self.worlds:
            world_mods = self._combined_modifiers(world)
            prod_penalty = world_mods["production_penalty"] if world.periphery else world_mods["production_penalty"] * 0.4
            stability_factor = 0.85 + world.stability * 0.3
            for good in GOODS:
                produced = world.production.get(good, 0.0) * stability_factor * (1 - prod_penalty)
                world.stock[good] += produced

                demand = world.consumption.get(good, 0.0) * world.population_factor
                if world.hyperion_special and good in {"luxus", "relikte"}:
                    demand *= 1.0 + world.pilgrim_pull * 0.2
                if good in {"luxus", "relikte"}:
                    demand *= world_mods["pilgrim_demand"]

                if world.stock[good] >= demand:
                    world.stock[good] -= demand
                    world.prosperity = min(1.3, world.prosperity + 0.002)
                else:
                    shortage = demand - world.stock[good]
                    world.stock[good] = 0.0
                    world.stability = max(0.2, world.stability - min(0.015 + shortage * 0.002, 0.06))
                    world.prosperity = max(0.2, world.prosperity - min(0.01 + shortage * 0.0015, 0.05))

    def _update_prices(self, mods: Optional[Dict[str, float]] = None) -> None:
        for world in self.worlds:
            world_mods = self._combined_modifiers(world)
            for good in GOODS:
                data = GOOD_DATA[good]
                demand = world.consumption.get(good, 0.0) * max(0.5, world.population_factor)
                available = world.stock[good] + 1.0
                imbalance = (demand + 1.0) / available
                tension = max(0.8, 1.25 - world.stability)
                noise = self.rng.uniform(-world_mods["core_noise"], world_mods["core_noise"])
                noise *= 1.2 if world.periphery else 0.8
                price = (
                    data["base_price"]
                    * (1 + data["volatility"] * (imbalance - 1))
                    * (1 + data["strategic"] * (tension - 1))
                    * (1 + noise)
                )
                world.prices[good] = max(4.0, round(price, 2))

    def _transport_cost(self, source: World, target: World, mods: Optional[Dict[str, float]] = None) -> Tuple[float, float]:
        mods = self._route_modifiers(source, target)
        if source.farcaster and target.farcaster:
            cost = self.config.farcaster_base_cost / max(0.15, mods["farcaster_efficiency"])
            cost += mods["transport_cost_bonus"]
            time_debt = 0.0
        else:
            cost = self.config.normal_base_cost + mods["transport_cost_bonus"]
            if source.periphery or target.periphery:
                cost += self.config.periphery_route_addon
            cost += mods["risk_bonus"] * 0.6
            time_debt = self.config.time_debt_normal
            if source.periphery or target.periphery:
                time_debt += self.config.time_debt_periphery_addon
            if mods["templar_bonus"] > 0 and (source.faction == "Templars" or target.faction == "Templars"):
                cost = max(0.7, cost - 2.5 * mods["templar_bonus"])
                time_debt = max(0.1, time_debt - 0.25)

        cost += self.config.core_fee * 10 * self.faction_state["core_signal"]
        return max(0.2, cost), time_debt

    def _trade(self, mods: Optional[Dict[str, float]] = None) -> None:
        self.trade_log.clear()
        self.trade_records.clear()
        route_capacity = self.config.route_capacity * self.config.trade_intensity
        for good in GOODS:
            remaining_capacity = route_capacity
            exporters = []
            importers = []
            for world in self.worlds:
                reserve = self._reserve(world)
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
                    if remaining_capacity <= 0.1 or remaining <= 0.1 or surplus <= 0.1 or seller is buyer:
                        continue
                    unit_cost, time_debt = self._transport_cost(seller, buyer)
                    landed_price = seller.prices[good] + unit_cost
                    margin = buyer.prices[good] - landed_price
                    if margin <= 0:
                        continue

                    affordable = buyer.cash / landed_price if landed_price > 0 else 0.0
                    qty = min(surplus, remaining, remaining_capacity, affordable)
                    if qty <= 0.1:
                        continue

                    buyer.cash -= qty * landed_price
                    seller.cash += qty * seller.prices[good]
                    seller.stock[good] -= qty
                    buyer.stock[good] += qty
                    seller.prosperity = min(1.4, seller.prosperity + 0.004 * qty)
                    buyer.prosperity = min(1.4, buyer.prosperity + 0.003 * qty)
                    buyer.time_debt += qty * time_debt

                    exporters[idx] = (seller, surplus - qty)
                    remaining -= qty
                    remaining_capacity -= qty
                    self.trade_log.append(
                        f"{good}: {seller.name} -> {buyer.name} "
                        f"({qty:.1f} u, Preis {landed_price:.1f}, Kosten {unit_cost:.1f})"
                    )
                    self.trade_records.append(
                        {
                            "good": good,
                            "seller": seller.name,
                            "buyer": buyer.name,
                            "quantity": qty,
                            "unit_price": landed_price,
                            "transport_cost": unit_cost,
                            "trade_value": qty * landed_price,
                        }
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
        self.faction_state["ouster_threat"] = 1.0 + mods["risk_bonus"] * 0.2
        self.faction_state["core_signal"] = max(0.6, 1.0 + mods["core_noise"] * 0.8)

        self._produce_and_consume(mods)
        self._update_prices(mods)
        self._trade(mods)
        self._update_prices(mods)
        self._post_tick_updates()
        self._advance_effects()

    def summary(self) -> str:
        top_prices: List[Tuple[str, float, str]] = []
        shortages: List[Tuple[float, str, str]] = []
        for world in self.worlds:
            for good in GOODS:
                top_prices.append((good, world.prices[good], world.name))
                shortages.append((self._reserve(world) - world.stock[good], world.name, good))

        top_prices.sort(key=lambda item: item[1], reverse=True)
        shortages.sort(key=lambda item: item[0], reverse=True)
        richest = sorted(self.worlds, key=lambda world: world.prosperity, reverse=True)[:3]
        stable = sorted(self.worlds, key=lambda world: world.stability, reverse=True)[:3]
        lines = [
            f"\n=== Tick {self.tick} ===",
            f"Aktive Ereignisse: {', '.join(self.current_events) if self.current_events else 'keine'}",
            (
                "Fraktionen: "
                f"Hegemonie={self.faction_state['hegemony_control']:.2f} | "
                f"Core-Signal={self.faction_state['core_signal']:.2f} | "
                f"Ouster-Druck={self.faction_state['ouster_threat']:.2f} | "
                f"Templar-Zugang={self.faction_state['templar_access']:.2f}"
            ),
            "Top-Preise:",
        ]
        for good, price, world_name in top_prices[:5]:
            lines.append(f"  - {good:14s} {price:7.2f} @ {world_name}")
        lines.append("Reichste/Prosperierende Welten:")
        for world in richest:
            lines.append(
                f"  - {world.name:12s} Wohlstand={world.prosperity:.2f} "
                f"Stabilität={world.stability:.2f} Cash={world.cash:.1f} "
                f"TimeDebt={world.time_debt:.1f}"
            )
        lines.append("Stabilste Welten:")
        for world in stable:
            lines.append(f"  - {world.name:12s} Stabilität={world.stability:.2f}")
        lines.append("Größte Engpässe:")
        for deficit, world_name, good in shortages[:5]:
            if deficit > 0.2:
                lines.append(f"  - {world_name:12s} fehlt {good:14s} ({deficit:.1f} u)")
        if self.trade_log:
            lines.append("Handelslog (Auszug):")
            lines.extend(f"  - {entry}" for entry in self.trade_log[:6])
        return "\n".join(lines)

    def world_table(self) -> str:
        lines = [
            "\nWELTENSTATUS",
            "Name         Typ          Faction      Stab   Wohlst    Cash TimeDebt Farcaster",
        ]
        for world in self.worlds:
            farcaster = "ja" if world.farcaster else "nein"
            lines.append(
                f"{world.name:12s} {world.category[:12]:12s} {world.faction[:11]:11s} "
                f"{world.stability:>5.2f}  {world.prosperity:>5.2f} {world.cash:>7.1f} "
                f"{world.time_debt:>6.1f}   {farcaster:>3s}"
            )
        return "\n".join(lines)

    def run(self) -> None:
        for _ in range(self.config.ticks):
            self.step()
            print(self.summary())


class TextApp:
    """Interaktive Konsole, kompatibel mit Pythonista."""

    def __init__(self, config: SimulationConfig):
        self.sim = HyperionEconomySim(config)

    @staticmethod
    def _ask_int(prompt: str, default: int) -> int:
        while True:
            raw = input(f"{prompt} [{default}]: ").strip()
            if not raw:
                return default
            try:
                value = int(raw)
            except ValueError:
                print("Bitte eine ganze Zahl eingeben.")
                continue
            if value <= 0:
                print("Bitte eine Zahl größer als 0 eingeben.")
                continue
            return value

    def interactive_loop(self) -> None:
        print("Hyperion Economy - Textanwendung")
        print("Befehle: n=1 Tick, r=mehrere Ticks, w=Weltenstatus, q=beenden")
        while True:
            cmd = input("\nBefehl (n/r/w/q): ").strip().lower() or "n"
            if cmd == "q":
                print("Simulation beendet.")
                return
            if cmd == "w":
                print(self.sim.world_table())
                continue
            if cmd == "r":
                count = self._ask_int("Wie viele Ticks?", 5)
                for _ in range(count):
                    self.sim.step()
                    print(self.sim.summary())
                continue
            if cmd == "n":
                self.sim.step()
                print(self.sim.summary())
                continue
            print("Unbekannter Befehl. Erlaubt sind n, r, w und q.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hyperion-inspirierte interplanetare Wirtschaftssimulation")
    parser.add_argument("--ticks", type=int, default=SimulationConfig.ticks, help="Anzahl der Ticks")
    parser.add_argument("--seed", type=int, default=7, help="Seed für reproduzierbare Läufe")
    parser.add_argument("--event-chance", type=float, default=SimulationConfig.event_chance, help="Wahrscheinlichkeit pro Tick für Ereignisse")
    parser.add_argument("--trade-intensity", type=float, default=SimulationConfig.trade_intensity, help="Handelsintensität")
    parser.add_argument("--faction-strength", type=float, default=SimulationConfig.faction_strength, help="Stärke politischer Fraktionseffekte")
    parser.add_argument("--core-fee", type=float, default=SimulationConfig.core_fee, help="Handelsgebühr pro Einheit")
    parser.add_argument("--route-capacity", type=float, default=SimulationConfig.route_capacity, help="Maximales Handelsvolumen pro Gut und Tick")
    parser.add_argument("--interactive", action="store_true", help="Interaktive Textanwendung starten")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        config = SimulationConfig(
            ticks=args.ticks,
            seed=args.seed,
            event_chance=args.event_chance,
            trade_intensity=args.trade_intensity,
            faction_strength=args.faction_strength,
            core_fee=args.core_fee,
            route_capacity=args.route_capacity,
        )
    except ValueError as error:
        parser.error(str(error))

    if args.interactive or len(sys.argv) == 1:
        TextApp(config).interactive_loop()
    else:
        HyperionEconomySim(config).run()


if __name__ == "__main__":
    main()
