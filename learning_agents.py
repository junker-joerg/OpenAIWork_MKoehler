#!/usr/bin/env python3
"""Kleine, Juno-taugliche Lernschicht für die Hyperion-Simulation.

Die Agenten verwenden tabellarisches Q-Learning statt eines großen
Machine-Learning-Frameworks. Dadurch läuft der Code lokal und offline in Juno
und kann sein Gedächtnis als lesbare JSON-Datei speichern.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from trade_sim import GOOD_DATA, HyperionEconomySim, SimulationConfig


ACTIONS: Tuple[str, ...] = ("hold", "buy", "sell")
DEFAULT_MEMORY_FILE = "agent_memory.json"


@dataclass
class QLearningTrader:
    """Ein einfacher Händler mit eigenem Q-Table-Gedächtnis."""

    name: str
    risk_aversion: float
    alpha: float = 0.22
    gamma: float = 0.90
    epsilon: float = 0.28
    min_epsilon: float = 0.04
    epsilon_decay: float = 0.97
    q_table: Dict[str, Dict[str, float]] = field(default_factory=dict)
    rng: random.Random = field(default_factory=random.Random, repr=False)
    episode_trades: int = field(default=0, init=False)

    def _row(self, state: str) -> Dict[str, float]:
        row = self.q_table.setdefault(state, {})
        for action in ACTIONS:
            row.setdefault(action, 0.0)
        return row

    def choose_action(
        self,
        state: str,
        allowed_actions: Sequence[str] = ACTIONS,
        *,
        explore: bool = True,
    ) -> str:
        """Wählt epsilon-greedy eine erlaubte Aktion."""

        allowed = tuple(action for action in allowed_actions if action in ACTIONS)
        if not allowed:
            raise ValueError("allowed_actions darf nicht leer sein")
        row = self._row(state)
        if explore and self.rng.random() < self.epsilon:
            return self.rng.choice(allowed)
        best_value = max(row[action] for action in allowed)
        best_actions = [action for action in allowed if row[action] == best_value]
        return self.rng.choice(best_actions)

    def update(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        next_allowed_actions: Sequence[str] = ACTIONS,
    ) -> None:
        """Aktualisiert den Q-Wert nach einer beobachteten Belohnung."""

        if action not in ACTIONS:
            raise ValueError(f"Unbekannte Aktion: {action}")
        next_allowed = tuple(
            candidate for candidate in next_allowed_actions if candidate in ACTIONS
        )
        if not next_allowed:
            raise ValueError("next_allowed_actions darf nicht leer sein")
        current = self._row(state)[action]
        next_best = max(self._row(next_state)[candidate] for candidate in next_allowed)
        target = reward + self.gamma * next_best
        self._row(state)[action] = current + self.alpha * (target - current)

    def finish_episode(self) -> None:
        """Senkt den Erkundungsanteil langsam, behält aber Exploration bei."""

        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "risk_aversion": self.risk_aversion,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "epsilon": self.epsilon,
            "min_epsilon": self.min_epsilon,
            "epsilon_decay": self.epsilon_decay,
            "q_table": self.q_table,
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, object], *, rng: Optional[random.Random] = None
    ) -> "QLearningTrader":
        table = payload.get("q_table", {})
        if not isinstance(table, Mapping):
            raise ValueError("agent_memory.json enthält keine gültige q_table")
        return cls(
            name=str(payload["name"]),
            risk_aversion=float(payload["risk_aversion"]),
            alpha=float(payload.get("alpha", 0.22)),
            gamma=float(payload.get("gamma", 0.90)),
            epsilon=float(payload.get("epsilon", 0.28)),
            min_epsilon=float(payload.get("min_epsilon", 0.04)),
            epsilon_decay=float(payload.get("epsilon_decay", 0.97)),
            q_table={
                str(state): {
                    str(action): float(value) for action, value in values.items()
                }
                for state, values in table.items()
                if isinstance(values, Mapping)
            },
            rng=rng or random.Random(),
        )


def create_default_agents(seed: int = 7) -> List[QLearningTrader]:
    """Erzeugt drei bewusst unterschiedliche Rollen für die Demo."""

    specs = (
        ("Profit-Scout", 0.00),
        ("Reserve-Keeper", 0.90),
        ("Hyperion-Speculator", 0.25),
    )
    return [
        QLearningTrader(name, risk, rng=random.Random(seed + index * 101))
        for index, (name, risk) in enumerate(specs)
    ]


def _bucket(value: float, low: float, high: float) -> str:
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "mid"


def market_state(price: float, stability: float, cash: float, inventory: int) -> str:
    """Verdichtet den Markt in einen kleinen, gut erklärbaren Zustand."""

    reference = GOOD_DATA["relikte"]["base_price"]
    price_band = _bucket(price, reference * 0.90, reference * 1.10)
    stability_band = "low" if stability < 0.62 else "high"
    cash_band = "low" if cash < reference else "high"
    inventory_band = "empty" if inventory == 0 else "stocked"
    return f"price={price_band}|stability={stability_band}|cash={cash_band}|inventory={inventory_band}"


def _snapshot(sim: HyperionEconomySim) -> Tuple[float, float, int]:
    worlds = list(sim.worlds)
    hyperion = next(world for world in worlds if world.name == "Hyperion")
    price = float(hyperion.prices["relikte"])
    stability = sum(world.stability for world in worlds) / max(1, len(worlds))
    return price, stability, len(sim.current_event_keys)


def _trade(cash: float, inventory: int, price: float, action: str) -> Tuple[float, int, bool]:
    if action == "buy" and cash >= price and inventory < 3:
        return cash - price, inventory + 1, True
    if action == "sell" and inventory > 0:
        return cash + price, inventory - 1, True
    return cash, inventory, False


def run_episode(
    agents: Sequence[QLearningTrader],
    *,
    years: int = 20,
    seed: int = 7,
    learn: bool = True,
    episode: int = 1,
) -> List[Dict[str, object]]:
    """Lässt alle Agenten dieselbe Welt beobachten und handeln."""

    if years < 1:
        raise ValueError("years muss mindestens 1 sein")
    sim = HyperionEconomySim(
        SimulationConfig(ticks=years, seed=seed, event_chance=0.45)
    )
    positions = {
        agent.name: {"cash": 1000.0, "inventory": 0, "trades": 0, "reward": 0.0}
        for agent in agents
    }
    previous: Dict[str, Tuple[str, str, float, float]] = {}
    actions: Dict[str, Dict[str, int]] = {
        agent.name: {action: 0 for action in ACTIONS} for agent in agents
    }

    for _year in range(years):
        sim.step()
        price, stability, event_count = _snapshot(sim)
        for agent in agents:
            position = positions[agent.name]
            cash = float(position["cash"])
            inventory = int(position["inventory"])
            state = market_state(price, stability, cash, inventory)
            current_value = cash + inventory * price

            if agent.name in previous:
                old_state, old_action, old_value, old_risk = previous[agent.name]
                reward = current_value - old_value - old_risk
                position["reward"] = float(position["reward"]) + reward
                if learn:
                    agent.update(old_state, old_action, reward, state)

            action = agent.choose_action(state, explore=learn)
            new_cash, new_inventory, traded = _trade(cash, inventory, price, action)
            position["cash"] = new_cash
            position["inventory"] = new_inventory
            if traded:
                position["trades"] = int(position["trades"]) + 1
                agent.episode_trades += 1
            actions[agent.name][action] += 1
            risk_cost = agent.risk_aversion * (
                max(0.0, 0.62 - stability) * 8.0 + event_count * 0.30
            )
            previous[agent.name] = (
                state,
                action,
                new_cash + new_inventory * price,
                risk_cost,
            )

    price, _stability, _event_count = _snapshot(sim)
    rows: List[Dict[str, object]] = []
    for agent in agents:
        position = positions[agent.name]
        final_value = float(position["cash"]) + int(position["inventory"]) * price
        if agent.name in previous:
            old_state, old_action, old_value, old_risk = previous[agent.name]
            final_reward = final_value - old_value - old_risk
            position["reward"] = float(position["reward"]) + final_reward
            if learn:
                agent.update(old_state, old_action, final_reward, old_state)
        if learn:
            agent.finish_episode()
        rows.append(
            {
                "episode": episode,
                "agent": agent.name,
                "total_reward": round(float(position["reward"]), 6),
                "final_value": round(final_value, 6),
                "trades": int(position["trades"]),
                "epsilon": round(agent.epsilon, 6),
                "q_states": len(agent.q_table),
                "buy_actions": actions[agent.name]["buy"],
                "sell_actions": actions[agent.name]["sell"],
                "hold_actions": actions[agent.name]["hold"],
            }
        )
        agent.episode_trades = 0
    return rows


def train_agents(
    *,
    episodes: int = 30,
    years: int = 20,
    seed: int = 7,
    agents: Optional[List[QLearningTrader]] = None,
    memory_path: Optional[str] = None,
) -> Dict[str, object]:
    """Trainiert Agenten und gibt notebook-freundliche Listen zurück."""

    if episodes < 1:
        raise ValueError("episodes muss mindestens 1 sein")
    if years < 1:
        raise ValueError("years muss mindestens 1 sein")
    active_agents = agents or create_default_agents(seed)
    history: List[Dict[str, object]] = []
    for episode in range(1, episodes + 1):
        history.extend(
            run_episode(
                active_agents,
                years=years,
                seed=seed + episode - 1,
                learn=True,
                episode=episode,
            )
        )
    if memory_path:
        save_agent_memory(active_agents, memory_path, episodes=episodes, seed=seed)
    return {"agents": active_agents, "history": history}


def evaluate_agents(
    agents: Sequence[QLearningTrader], *, episodes: int = 5, years: int = 20, seed: int = 1007
) -> List[Dict[str, object]]:
    """Bewertet das gelernte Verhalten ohne weitere Q-Table-Änderung."""

    if episodes < 1:
        raise ValueError("episodes muss mindestens 1 sein")
    rows: List[Dict[str, object]] = []
    for episode in range(1, episodes + 1):
        rows.extend(
            run_episode(
                agents,
                years=years,
                seed=seed + episode - 1,
                learn=False,
                episode=episode,
            )
        )
    return rows


def save_agent_memory(
    agents: Iterable[QLearningTrader], path: str, *, episodes: int = 0, seed: int = 7
) -> Path:
    """Speichert die Q-Tables als portable, menschenlesbare JSON-Datei."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": 1,
        "description": "Lokales Q-Learning-Gedächtnis für die Juno-Demo",
        "episodes": episodes,
        "seed": seed,
        "agents": [agent.to_dict() for agent in agents],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_agent_memory(path: str, *, seed: int = 7) -> List[QLearningTrader]:
    """Lädt ein zuvor gespeichertes Agentengedächtnis."""

    source = Path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    agent_payloads = payload.get("agents")
    if not isinstance(agent_payloads, list) or not agent_payloads:
        raise ValueError("agent_memory.json enthält keine Agenten")
    return [
        QLearningTrader.from_dict(
            item, rng=random.Random(seed + index * 101)
        )
        for index, item in enumerate(agent_payloads)
        if isinstance(item, Mapping)
    ]


__all__ = [
    "ACTIONS",
    "DEFAULT_MEMORY_FILE",
    "QLearningTrader",
    "create_default_agents",
    "evaluate_agents",
    "load_agent_memory",
    "market_state",
    "run_episode",
    "save_agent_memory",
    "train_agents",
]
