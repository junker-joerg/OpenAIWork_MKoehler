"""Ein-Klick-Einstieg für Juno-Shortcuts und schnelle Demo-Läufe."""

from __future__ import annotations

import argparse

from juno_demo import DEFAULT_RUNS, DEFAULT_SEED, DEFAULT_YEARS, SCENARIOS, export_demo, run_simulation


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Hyperion Economy Juno-Demo")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="baseline")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS)
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output", default="demo_exports")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    frames = run_simulation(
        years=args.years,
        seed=args.seed,
        num_runs=args.runs,
        scenario=args.scenario,
    )
    result = export_demo(
        frames,
        output_dir=args.output,
        metadata={
            "scenario": args.scenario,
            "years": args.years,
            "runs": args.runs,
            "seed": args.seed,
        },
    )
    print(f"Juno-Demo abgeschlossen: {len(result['csv_files'])} CSV-Dateien in {args.output}")


if __name__ == "__main__":
    main()
