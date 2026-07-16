#!/usr/bin/env python3
"""Ein-Klick-Einstieg für das lokale Juno-Agentenexperiment."""

from __future__ import annotations

import argparse
from pathlib import Path

from learning_agents import evaluate_agents, load_agent_memory, train_agents


def main() -> None:
    parser = argparse.ArgumentParser(description="Lernende Hyperion-Agenten trainieren")
    parser.add_argument("--episodes", type=int, default=30)
    parser.add_argument("--years", type=int, default=20)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--memory", default="agent_memory.json")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="vorhandenes JSON-Gedächtnis laden und weitertrainieren",
    )
    args = parser.parse_args()

    agents = None
    if args.resume and Path(args.memory).is_file():
        agents = load_agent_memory(args.memory, seed=args.seed)
    result = train_agents(
        episodes=args.episodes,
        years=args.years,
        seed=args.seed,
        agents=agents,
        memory_path=args.memory,
    )
    evaluation = evaluate_agents(
        result["agents"], episodes=5, years=args.years, seed=args.seed + 1000
    )
    best = max(evaluation, key=lambda row: float(row["final_value"]))
    print(f"Training abgeschlossen: {args.episodes} Episoden × {args.years} Jahre")
    print(f"Gedächtnis gespeichert: {Path(args.memory).resolve()}")
    print(
        "Bester Evaluationslauf: "
        f"{best['agent']} mit Endwert {best['final_value']:.2f}"
    )


if __name__ == "__main__":
    main()
