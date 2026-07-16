#!/usr/bin/env python3
"""Transparent, Juno-friendly learning agents for the Hyperion economy.

The agents observe real snapshots from :mod:`trade_sim` and trade a small
overlay portfolio of Hyperion relics. The learning core uses only the Python
standard library, so it runs locally on an iPad without an RL framework.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from trade_sim import GOOD_DATA, HyperionEconomySim, SimulationConfig


ACTIONS: Tuple[str, ...] = ("halten", "kaufen", "verkaufen")
ALGORITHMS: Tuple[str, ...] = ("sarsa", "dyna-q", "bandit")
MEMORY_FORMAT = 2
INITIAL_CASH = 1000.0
MAX_INVENTORY = 3
TRANSACTION_FEE = 0.005

_DEFAULT_SPECS = {
    "Profit-Scout": ("sarsa", 0.24, 0.94, 0.00),
    "Reserve-Keeper": ("dyna-q", 0.16, 0.86, 0.90),
    "Hyperion-Speculator": ("bandit", 0.20, 0.00, 0.25),
}


def _values(table: Dict[Tuple[int, ...], Dict[str, float]], state: Sequence[int]) -> Dict[str, float]:
    key = tuple(state)
    row = table.setdefault(key, {})
    for action in ACTIONS:
        row.setdefault(action, 0.0)
    return row


def _best(values: Mapping[str, float], allowed: Sequence[str], rng: random.Random) -> str:
    candidates = tuple(action for action in allowed if action in values)
    if not candidates:
        raise ValueError("allowed_actions darf nicht leer sein")
    maximum = max(values[action] for action in candidates)
    return rng.choice([action for action in candidates if values[action] == maximum])


def _bucket(value: float, low: float, high: float) -> int:
    if value < low:
        return 0
    if value > high:
        return 2
    return 1


class Agent:
    """A small SARSA, Dyna-Q, or bandit trader with persistent memory."""

    def __init__(
        self,
        name: str,
        algorithm: str,
        alpha: float,
        gamma: float,
        risk_aversion: float = 0.0,
        seed: int = 7,
    ) -> None:
        if algorithm not in ALGORITHMS:
            raise ValueError(f"Unbekannter Algorithmus: {algorithm}")
        self.name = name
        self.algorithm = algorithm
        self.alpha = float(alpha)
        self.gamma = float(gamma)
        self.risk_aversion = float(risk_aversion)
        self.epsilon = 0.30
        self.epsilon_min = 0.05
        self.epsilon_decay = 0.94
        self.q_table: Dict[Tuple[int, ...], Dict[str, float]] = {}
        self.transitions: Dict[
            Tuple[Tuple[int, ...], str], Tuple[float, Tuple[int, ...]]
        ] = {}
        self.bandit_counts = {action: 0 for action in ACTIONS}
        self.bandit_values = {action: 0.0 for action in ACTIONS}
        self.rng = random.Random(seed)

    def allowed_actions(self, cash: float, inventory: int, price: float) -> Tuple[str, ...]:
        allowed = ["halten"]
        if cash >= price * (1.0 + TRANSACTION_FEE) and inventory < MAX_INVENTORY:
            allowed.append("kaufen")
        if inventory > 0:
            allowed.append("verkaufen")
        return tuple(allowed)

    def choose(
        self,
        state: Sequence[int],
        allowed_actions: Sequence[str] = ACTIONS,
        *,
        explore: bool = True,
    ) -> str:
        allowed = tuple(action for action in allowed_actions if action in ACTIONS)
        if not allowed:
            raise ValueError("allowed_actions darf nicht leer sein")
        values = (
            self.bandit_values
            if self.algorithm == "bandit"
            else _values(self.q_table, state)
        )
        if explore and self.rng.random() < self.epsilon:
            return self.rng.choice(allowed)
        return _best(values, allowed, self.rng)

    def sarsa_update(
        self,
        state: Sequence[int],
        action: str,
        reward: float,
        next_state: Sequence[int],
        next_action: str,
    ) -> None:
        current = _values(self.q_table, state)
        following = _values(self.q_table, next_state)
        target = reward + self.gamma * following[next_action]
        current[action] += self.alpha * (target - current[action])

    def q_update(
        self,
        state: Sequence[int],
        action: str,
        reward: float,
        next_state: Sequence[int],
    ) -> None:
        current = _values(self.q_table, state)
        following = _values(self.q_table, next_state)
        target = reward + self.gamma * max(following.values())
        current[action] += self.alpha * (target - current[action])

    def terminal_update(self, state: Sequence[int], action: str, reward: float) -> None:
        current = _values(self.q_table, state)
        current[action] += self.alpha * (reward - current[action])

    def bandit_update(self, action: str, reward: float) -> None:
        count = self.bandit_counts[action] + 1
        old = self.bandit_values[action]
        self.bandit_counts[action] = count
        self.bandit_values[action] = old + (reward - old) / count

    def remember(
        self,
        state: Sequence[int],
        action: str,
        reward: float,
        next_state: Sequence[int],
    ) -> None:
        self.transitions[(tuple(state), action)] = (float(reward), tuple(next_state))

    def replay(self, steps: int = 8) -> None:
        if not self.transitions:
            return
        items = list(self.transitions.items())
        for _ in range(min(steps, len(items))):
            (state, action), (reward, next_state) = self.rng.choice(items)
            self.q_update(state, action, reward, next_state)

    def finish_episode(self, learn: bool) -> None:
        if learn:
            self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "algorithm": self.algorithm,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "risk_aversion": self.risk_aversion,
            "epsilon": self.epsilon,
            "epsilon_min": self.epsilon_min,
            "epsilon_decay": self.epsilon_decay,
            "q_table": [[list(state), values] for state, values in self.q_table.items()],
            "transitions": [
                [list(state), action, reward, list(next_state)]
                for (state, action), (reward, next_state) in self.transitions.items()
            ],
            "bandit_counts": self.bandit_counts,
            "bandit_values": self.bandit_values,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, object], *, seed: int = 7) -> "Agent":
        name = str(payload.get("name", "Agent"))
        default_algorithm, default_alpha, default_gamma, default_risk = _DEFAULT_SPECS.get(
            name, ("sarsa", 0.20, 0.90, 0.0)
        )
        agent = cls(
            name=name,
            algorithm=str(payload.get("algorithm", default_algorithm)),
            alpha=float(payload.get("alpha", default_alpha)),
            gamma=float(payload.get("gamma", default_gamma)),
            risk_aversion=float(payload.get("risk_aversion", default_risk)),
            seed=seed,
        )
        agent.epsilon = float(payload.get("epsilon", agent.epsilon))
        agent.epsilon_min = float(payload.get("epsilon_min", agent.epsilon_min))
        agent.epsilon_decay = float(payload.get("epsilon_decay", agent.epsilon_decay))

        raw_q = payload.get("q_table", [])
        if isinstance(raw_q, list):
            agent.q_table = {
                tuple(int(value) for value in state): {
                    str(action): float(value) for action, value in values.items()
                }
                for state, values in raw_q
                if isinstance(state, list) and isinstance(values, Mapping)
            }
        elif isinstance(raw_q, Mapping):
            # Compatibility with the first local implementation, which used
            # string keys. Such states remain usable as opaque one-state keys.
            agent.q_table = {
                (index,): {str(action): float(value) for action, value in values.items()}
                for index, values in enumerate(raw_q.values())
                if isinstance(values, Mapping)
            }

        raw_transitions = payload.get("transitions", [])
        if isinstance(raw_transitions, list):
            agent.transitions = {
                (tuple(int(value) for value in state), str(action)): (
                    float(reward),
                    tuple(int(value) for value in next_state),
                )
                for state, action, reward, next_state in raw_transitions
                if isinstance(state, list) and isinstance(next_state, list)
            }
        if isinstance(payload.get("bandit_counts"), Mapping):
            agent.bandit_counts.update(
                {str(action): int(value) for action, value in payload["bandit_counts"].items()}
            )
        if isinstance(payload.get("bandit_values"), Mapping):
            agent.bandit_values.update(
                {str(action): float(value) for action, value in payload["bandit_values"].items()}
            )
        return agent


def create_default_agents(seed: int = 7) -> List[Agent]:
    return [
        Agent(name, algorithm, alpha, gamma, risk, seed=seed + index * 101)
        for index, (name, (algorithm, alpha, gamma, risk)) in enumerate(
            _DEFAULT_SPECS.items()
        )
    ]


def market_snapshot(sim: HyperionEconomySim) -> Dict[str, float]:
    worlds = list(sim.worlds)
    hyperion = next(world for world in worlds if world.name == "Hyperion")
    stability = sum(world.stability for world in worlds) / max(1, len(worlds))
    return {
        "price": float(hyperion.prices["relikte"]),
        "stability": float(stability),
        "time_debt": float(hyperion.time_debt),
        "event_count": float(len(sim.current_event_keys)),
        "stock": float(hyperion.stock["relikte"]),
    }


def market_state(snapshot: Mapping[str, float], cash: float, inventory: int) -> Tuple[int, ...]:
    reference = GOOD_DATA["relikte"]["base_price"]
    return (
        _bucket(snapshot["price"], reference * 0.90, reference * 1.10),
        _bucket(snapshot["stability"], 0.40, 0.70),
        _bucket(snapshot["time_debt"], 1.5, 4.0),
        _bucket(snapshot["event_count"], 0.5, 2.5),
        _bucket(snapshot["stock"], 10.0, 25.0),
        _bucket(cash, reference, reference * 4.0),
        _bucket(float(inventory), 0.5, 1.5),
    )


def _risk_penalty(agent: Agent, snapshot: Mapping[str, float]) -> float:
    signal = (
        max(0.0, 0.70 - snapshot["stability"]) / 0.70
        + min(1.0, snapshot["time_debt"] / 6.0)
        + min(1.0, snapshot["event_count"] / 2.0)
    )
    return agent.risk_aversion * signal * 2.0


def _execute_trade(
    cash: float, inventory: int, price: float, action: str
) -> Tuple[float, int, bool, bool]:
    fee = price * TRANSACTION_FEE
    if action == "kaufen" and cash >= price + fee and inventory < MAX_INVENTORY:
        return cash - price - fee, inventory + 1, True, False
    if action == "verkaufen" and inventory > 0:
        return cash + price - fee, inventory - 1, True, False
    return cash, inventory, False, action != "halten"


def _update_transition(
    agent: Agent,
    state: Sequence[int],
    action: str,
    reward: float,
    next_state: Sequence[int],
    next_action: str,
    *,
    learn: bool,
) -> None:
    if not learn:
        return
    if agent.algorithm == "sarsa":
        agent.sarsa_update(state, action, reward, next_state, next_action)
    elif agent.algorithm == "dyna-q":
        agent.q_update(state, action, reward, next_state)
        agent.remember(state, action, reward, next_state)
        agent.replay()
    else:
        agent.bandit_update(action, reward)


def run_episode(
    agents: Sequence[Agent],
    *,
    years: int = 20,
    seed: int = 7,
    learn: bool = True,
    episode: int = 1,
) -> List[Dict[str, object]]:
    if years < 1:
        raise ValueError("years muss mindestens 1 sein")
    sim = HyperionEconomySim(
        SimulationConfig(ticks=years, seed=seed, event_chance=0.45)
    )
    positions = {
        agent.name: {
            "cash": INITIAL_CASH,
            "inventory": 0,
            "reward": 0.0,
            "trades": 0,
            "min_cash": INITIAL_CASH,
        }
        for agent in agents
    }
    previous: Dict[str, Tuple[Tuple[int, ...], str, float, float]] = {}
    actions = {
        agent.name: {action: 0 for action in ACTIONS} for agent in agents
    }
    buy_hold_units = 0
    buy_hold_cash = INITIAL_CASH
    first_price: Optional[float] = None
    final_snapshot: Optional[Dict[str, float]] = None

    for _year in range(years):
        sim.step()
        snapshot = market_snapshot(sim)
        final_snapshot = snapshot
        price = snapshot["price"]
        if first_price is None:
            first_price = price
            buy_hold_units = int(INITIAL_CASH // first_price)
            buy_hold_cash = INITIAL_CASH - buy_hold_units * first_price

        for agent in agents:
            position = positions[agent.name]
            cash = float(position["cash"])
            inventory = int(position["inventory"])
            current_value = cash + inventory * price
            state = market_state(snapshot, cash, inventory)
            allowed = agent.allowed_actions(cash, inventory, price)

            if agent.name in previous:
                old_state, old_action, old_value, old_cost = previous[agent.name]
                reward = current_value - old_value - old_cost
                position["reward"] = float(position["reward"]) + reward
                _update_transition(
                    agent,
                    old_state,
                    old_action,
                    reward,
                    state,
                    "halten",
                    learn=learn,
                )

            action = agent.choose(state, allowed, explore=learn)
            new_cash, new_inventory, traded, invalid = _execute_trade(
                cash, inventory, price, action
            )
            position["cash"] = new_cash
            position["inventory"] = new_inventory
            position["min_cash"] = min(float(position["min_cash"]), new_cash)
            if traded:
                position["trades"] = int(position["trades"]) + 1
            actions[agent.name][action] += 1
            immediate_cost = 0.25 if invalid else 0.0
            risk_cost = _risk_penalty(agent, snapshot) + immediate_cost
            previous[agent.name] = (
                state,
                action,
                new_cash + new_inventory * price,
                risk_cost,
            )

    if final_snapshot is None or first_price is None:
        raise RuntimeError("Episode lieferte keinen Markt-Snapshot")
    final_price = final_snapshot["price"]
    benchmark_value = buy_hold_cash + buy_hold_units * final_price
    rows: List[Dict[str, object]] = []
    for agent in agents:
        position = positions[agent.name]
        final_value = float(position["cash"]) + int(position["inventory"]) * final_price
        if agent.name in previous:
            old_state, old_action, old_value, old_cost = previous[agent.name]
            terminal_reward = final_value - old_value - old_cost
            position["reward"] = float(position["reward"]) + terminal_reward
            if learn:
                agent.terminal_update(old_state, old_action, terminal_reward)
        agent.finish_episode(learn)
        min_cash = float(position["min_cash"])
        rows.append(
            {
                "episode": episode,
                "agent": agent.name,
                "algorithm": agent.algorithm,
                "final_value": round(final_value, 6),
                "benchmark_value": round(benchmark_value, 6),
                "excess_return": round(final_value - benchmark_value, 6),
                "total_reward": round(float(position["reward"]), 6),
                "trades": int(position["trades"]),
                "epsilon": round(agent.epsilon, 6),
                "q_states": len(agent.q_table),
                "min_cash": round(min_cash, 6),
                "liquidity_stress": min_cash < final_price,
                "insolvent": min_cash < 0.0 or final_value <= 0.0,
                "buy_actions": actions[agent.name]["kaufen"],
                "sell_actions": actions[agent.name]["verkaufen"],
                "hold_actions": actions[agent.name]["halten"],
            }
        )
    return rows


def train_agents(
    episodes: int = 30,
    years: int = 20,
    seed: int = 7,
    memory_path: Optional[str] = "agent_memory.json",
    agents: Optional[List[Agent]] = None,
) -> Dict[str, object]:
    if episodes < 1 or years < 1:
        raise ValueError("episodes und years müssen mindestens 1 sein")
    active_agents = agents if agents is not None else create_default_agents(seed)
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
    agents: Sequence[Agent],
    episodes: int = 5,
    years: int = 20,
    seed: int = 1007,
) -> List[Dict[str, object]]:
    if episodes < 1 or years < 1:
        raise ValueError("episodes und years müssen mindestens 1 sein")
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


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    average = _mean(values)
    return math.sqrt(sum((value - average) ** 2 for value in values) / len(values))


def evaluation_summary(rows: Iterable[Mapping[str, object]]) -> List[Dict[str, object]]:
    grouped: Dict[str, List[Mapping[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["agent"]), []).append(row)
    summary = []
    for agent, items in grouped.items():
        final_values = [float(item["final_value"]) for item in items]
        excess = [float(item["excess_return"]) for item in items]
        summary.append(
            {
                "agent": agent,
                "algorithm": str(items[0]["algorithm"]),
                "avg_final_value": round(_mean(final_values), 6),
                "std_final_value": round(_std(final_values), 6),
                "avg_excess_return": round(_mean(excess), 6),
                "avg_reward": round(_mean([float(item["total_reward"]) for item in items]), 6),
                "avg_trades": round(_mean([float(item["trades"]) for item in items]), 6),
                "win_rate": round(
                    sum(value > 0 for value in excess) / max(1, len(excess)), 6
                ),
                "liquidity_stress_rate": round(
                    sum(bool(item["liquidity_stress"]) for item in items)
                    / max(1, len(items)),
                    6,
                ),
                "insolvency_rate": round(
                    sum(bool(item["insolvent"]) for item in items) / max(1, len(items)),
                    6,
                ),
            }
        )
    return sorted(summary, key=lambda item: float(item["avg_final_value"]), reverse=True)


def save_agent_memory(
    agents: Iterable[Agent], path: str, *, episodes: int = 0, seed: int = 7
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": MEMORY_FORMAT,
        "description": "Lokales Hyperion-Agentengedächtnis für Juno",
        "episodes": episodes,
        "seed": seed,
        "agents": [agent.to_dict() for agent in agents],
    }
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def load_agent_memory(path: str = "agent_memory.json", *, seed: int = 7) -> List[Agent]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, Mapping) and isinstance(payload.get("agents"), list):
        items = payload["agents"]
    else:
        raise ValueError("Das Agentengedächtnis enthält keine gültige Agentenliste")
    agents = [
        Agent.from_dict(item, seed=seed + index * 101)
        for index, item in enumerate(items)
        if isinstance(item, Mapping)
    ]
    if not agents:
        raise ValueError("Das Agentengedächtnis enthält keine Agenten")
    return agents


__all__ = [
    "ACTIONS",
    "ALGORITHMS",
    "Agent",
    "create_default_agents",
    "evaluate_agents",
    "evaluation_summary",
    "load_agent_memory",
    "market_snapshot",
    "market_state",
    "run_episode",
    "save_agent_memory",
    "train_agents",
]
