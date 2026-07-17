"""Juno-optimierte Demo- und Visualisierungsschicht für Hyperion Economy.

Die Simulation selbst bleibt in ``trade_sim.py``. Dieses Modul liefert kleine,
wiederverwendbare Funktionen für ein geführtes Jupyter-Notebook auf dem iPad.
CSV ist der Standardexport; Parquet wird nur geschrieben, wenn eine passende
Engine installiert ist.
"""

from __future__ import annotations

import importlib.util
import json
import platform
import sys
from pathlib import Path
from typing import Dict, Mapping, Optional

import matplotlib.pyplot as plt
import pandas as pd

from trade_sim import HyperionEconomySim, SimulationConfig


DEFAULT_YEARS = 20
DEFAULT_RUNS = 3
DEFAULT_SEED = 7

SCENARIOS: Dict[str, Dict[str, object]] = {
    "baseline": {
        "label": "Baseline",
        "seed": 7,
        "forced_events": {},
        "description": "Normale Wirtschaftsentwicklung mit zufälligen Ereignissen.",
    },
    "farcaster": {
        "label": "Farcaster-Ausfall",
        "seed": 17,
        "forced_events": {3: "farcaster_stoerung"},
        "description": "Ein Farcaster-Ausfall verteuert die interplanetaren Routen.",
    },
    "pilgrim": {
        "label": "Pilgerboom",
        "seed": 27,
        "forced_events": {3: "pilgerboom"},
        "description": "Ein Pilgerboom erhöht die Nachfrage nach Luxus und Relikten.",
    },
}


def environment_report() -> pd.DataFrame:
    """Return a compact package/path report for the first notebook cell."""

    packages = ["pandas", "matplotlib", "ipywidgets", "pyarrow", "bokeh"]
    rows = [{"item": "Python", "available": True, "detail": platform.python_version()}]
    rows.append({"item": "Working directory", "available": True, "detail": str(Path.cwd())})
    for package in packages:
        rows.append(
            {
                "item": package,
                "available": importlib.util.find_spec(package) is not None,
                "detail": "installed" if importlib.util.find_spec(package) else "optional/not installed",
            }
        )
    return pd.DataFrame(rows)


def _empty_frames() -> Dict[str, pd.DataFrame]:
    return {
        "yearly": pd.DataFrame(
            columns=[
                "scenario", "run", "seed", "year", "events", "event_count",
                "core_signal", "ouster_threat", "templar_access",
                "trade_volume", "trade_value",
            ]
        ),
        "world": pd.DataFrame(
            columns=[
                "scenario", "run", "seed", "year", "world", "category", "faction",
                "farcaster", "periphery", "stability", "prosperity", "cash", "time_debt",
                "hyperion_special",
            ]
        ),
        "price": pd.DataFrame(
            columns=["scenario", "run", "seed", "year", "world", "good", "price", "stock"]
        ),
        "events": pd.DataFrame(columns=["scenario", "run", "seed", "year", "event_key", "description"]),
        "trades": pd.DataFrame(
            columns=[
                "scenario", "run", "seed", "year", "good", "seller", "buyer",
                "quantity", "unit_price", "transport_cost", "trade_value",
            ]
        ),
    }


def run_simulation(
    years: int = DEFAULT_YEARS,
    seed: int = DEFAULT_SEED,
    num_runs: int = DEFAULT_RUNS,
    event_chance: float = 0.45,
    trade_intensity: float = 1.0,
    faction_strength: float = 1.0,
    scenario: str = "baseline",
    forced_events: Optional[Mapping[int, str]] = None,
) -> Dict[str, pd.DataFrame]:
    """Run a compact experiment and return analysis-ready DataFrames."""

    if years <= 0 or num_runs <= 0:
        raise ValueError("years und num_runs müssen größer als 0 sein.")
    if scenario not in SCENARIOS:
        raise ValueError(f"Unbekanntes Szenario: {scenario}")

    frames = _empty_frames()
    scenario_data = SCENARIOS[scenario]
    selected_events = dict(
        scenario_data["forced_events"] if forced_events is None else forced_events
    )
    base_seed = int(scenario_data["seed"]) if seed == DEFAULT_SEED else seed
    yearly_rows = []
    world_rows = []
    price_rows = []
    event_rows = []
    trade_rows = []

    for run in range(1, num_runs + 1):
        run_seed = base_seed + run - 1
        config = SimulationConfig(
            ticks=years,
            seed=run_seed,
            event_chance=event_chance,
            trade_intensity=trade_intensity,
            faction_strength=faction_strength,
            scenario_events=selected_events,
        )
        sim = HyperionEconomySim(config)

        for _ in range(years):
            sim.step()
            trade_volume = sum(float(record["quantity"]) for record in sim.trade_records)
            trade_value = sum(float(record["trade_value"]) for record in sim.trade_records)
            yearly_rows.append(
                {
                    "scenario": scenario,
                    "run": run,
                    "seed": run_seed,
                    "year": sim.tick,
                    "events": "; ".join(sim.current_events) if sim.current_events else "keine",
                    "event_count": len(sim.current_events),
                    "core_signal": sim.faction_state["core_signal"],
                    "ouster_threat": sim.faction_state["ouster_threat"],
                    "templar_access": sim.faction_state["templar_access"],
                    "trade_volume": trade_volume,
                    "trade_value": trade_value,
                }
            )
            for event_key, description in zip(sim.current_event_keys, sim.current_events):
                event_rows.append(
                    {
                        "scenario": scenario,
                        "run": run,
                        "seed": run_seed,
                        "year": sim.tick,
                        "event_key": event_key,
                        "description": description,
                    }
                )
            for record in sim.trade_records:
                trade_rows.append({"scenario": scenario, "run": run, "seed": run_seed, "year": sim.tick, **record})
            for world in sim.worlds:
                world_rows.append(
                    {
                        "scenario": scenario,
                        "run": run,
                        "seed": run_seed,
                        "year": sim.tick,
                        "world": world.name,
                        "category": world.category,
                        "faction": world.faction,
                        "farcaster": world.farcaster,
                        "periphery": world.periphery,
                        "stability": world.stability,
                        "prosperity": world.prosperity,
                        "cash": world.cash,
                        "time_debt": world.time_debt,
                        "hyperion_special": world.hyperion_special,
                    }
                )
                for good, price in world.prices.items():
                    price_rows.append(
                        {
                            "scenario": scenario,
                            "run": run,
                            "seed": run_seed,
                            "year": sim.tick,
                            "world": world.name,
                            "good": good,
                            "price": price,
                            "stock": world.stock[good],
                        }
                    )

    frames["yearly"] = pd.DataFrame(yearly_rows)
    frames["world"] = pd.DataFrame(world_rows)
    frames["price"] = pd.DataFrame(price_rows)
    frames["events"] = pd.DataFrame(event_rows, columns=list(frames["events"].columns))
    frames["trades"] = pd.DataFrame(trade_rows, columns=list(frames["trades"].columns))
    return frames


def kpi_table(frames: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """Create one compact KPI row per run."""

    world = frames["world"].sort_values(["scenario", "run", "year"])
    yearly = frames["yearly"]
    if world.empty:
        return pd.DataFrame()
    final = world.groupby(["scenario", "run"], as_index=False).tail(1)
    result = final[["scenario", "run", "year", "prosperity", "stability", "cash", "time_debt"]].rename(
        columns={
            "year": "final_year",
            "prosperity": "final_prosperity",
            "stability": "final_stability",
            "cash": "final_cash",
            "time_debt": "final_time_debt",
        }
    )
    trade = yearly.groupby(["scenario", "run"], as_index=False).agg(
        total_trade_volume=("trade_volume", "sum"),
        total_trade_value=("trade_value", "sum"),
        event_count=("event_count", "sum"),
    )
    return result.merge(trade, on=["scenario", "run"], how="left").round(2)


def scenario_table(
    years: int = DEFAULT_YEARS,
    event_chance: float = 0.45,
    trade_intensity: float = 1.0,
    faction_strength: float = 1.0,
) -> pd.DataFrame:
    """Compare the three fixed demo scenarios with one reproducible run each."""

    rows = []
    for name, data in SCENARIOS.items():
        frames = run_simulation(
            years=years,
            seed=int(data["seed"]),
            num_runs=1,
            event_chance=event_chance,
            trade_intensity=trade_intensity,
            faction_strength=faction_strength,
            scenario=name,
        )
        kpis = kpi_table(frames).iloc[0].to_dict()
        rows.append(
            {
                "scenario": data["label"],
                "final_prosperity": kpis["final_prosperity"],
                "final_stability": kpis["final_stability"],
                "total_trade_value": kpis["total_trade_value"],
                "final_time_debt": kpis["final_time_debt"],
            }
        )
    return pd.DataFrame(rows).round(2)


def plot_dashboard(frames: Mapping[str, pd.DataFrame], run: int = 1):
    """Plot the four most useful demo views in a large iPad-friendly figure."""

    yearly = frames["yearly"]
    world = frames["world"]
    price = frames["price"]
    scenario = str(yearly["scenario"].iloc[0])
    yearly = yearly[(yearly["run"] == run) & (yearly["scenario"] == scenario)]
    world = world[(world["run"] == run) & (world["scenario"] == scenario)]
    price = price[(price["run"] == run) & (price["scenario"] == scenario)]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    fig.suptitle(f"Hyperion Economy — {SCENARIOS[scenario]['label']} — Lauf {run}", fontsize=16)
    mean_world = world.groupby("year", as_index=False)[["prosperity", "stability"]].mean()
    axes[0, 0].plot(mean_world["year"], mean_world["prosperity"], label="Wohlstand", linewidth=2.5)
    axes[0, 0].plot(mean_world["year"], mean_world["stability"], label="Stabilität", linewidth=2.5)
    axes[0, 0].set_title("Wohlstand und Stabilität")
    axes[0, 0].legend()
    hyperion = price[(price["world"] == "Hyperion") & (price["good"] == "relikte")]
    axes[0, 1].plot(hyperion["year"], hyperion["price"], color="purple", linewidth=2.5)
    axes[0, 1].set_title("Hyperion: Reliktpreis")
    axes[0, 1].set_xlabel("Jahr")
    axes[1, 0].plot(yearly["year"], yearly["trade_value"], color="darkgreen", linewidth=2.5)
    axes[1, 0].set_title("Handelswert pro Jahr")
    axes[1, 0].set_xlabel("Jahr")
    axes[1, 1].bar(yearly["year"], yearly["event_count"], color="darkorange")
    axes[1, 1].set_title("Ereignisse pro Jahr")
    axes[1, 1].set_xlabel("Jahr")
    for axis in axes.flat:
        axis.grid(alpha=0.25)
    return fig, axes


def plot_world_detail(frames: Mapping[str, pd.DataFrame], world_name: str, run: int = 1):
    world = frames["world"][(frames["world"]["world"] == world_name) & (frames["world"]["run"] == run)]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    axes[0].plot(world["year"], world["prosperity"], label="Wohlstand", linewidth=2.5)
    axes[0].plot(world["year"], world["stability"], label="Stabilität", linewidth=2.5)
    axes[0].set_title(f"{world_name}: Zustand")
    axes[0].legend()
    axes[1].plot(world["year"], world["cash"], label="Cash", linewidth=2.5)
    axes[1].plot(world["year"], world["time_debt"], label="Time Debt", linewidth=2.5)
    axes[1].set_title(f"{world_name}: Ressourcen")
    axes[1].legend()
    for axis in axes:
        axis.grid(alpha=0.25)
    return fig, axes


def plot_good_detail(frames: Mapping[str, pd.DataFrame], good: str, world_name: Optional[str] = None, run: int = 1):
    data = frames["price"][(frames["price"]["good"] == good) & (frames["price"]["run"] == run)]
    if world_name:
        data = data[data["world"] == world_name]
    grouped = data.groupby("year", as_index=False)[["price", "stock"]].mean()
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), constrained_layout=True)
    axes[0].plot(grouped["year"], grouped["price"], color="firebrick", linewidth=2.5)
    axes[0].set_title(f"{good}: Preis")
    axes[1].plot(grouped["year"], grouped["stock"], color="steelblue", linewidth=2.5)
    axes[1].set_title(f"{good}: Lagerbestand")
    for axis in axes:
        axis.grid(alpha=0.25)
    return fig, axes


def export_demo(frames: Mapping[str, pd.DataFrame], output_dir: str = "demo_exports", metadata: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """Write compact CSV exports and optionally Parquet files."""

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for name, frame in frames.items():
        path = destination / f"{name}.csv"
        frame.to_csv(path, index=False)
        written.append(str(path))
    kpis = kpi_table(frames)
    kpi_path = destination / "kpis.csv"
    kpis.to_csv(kpi_path, index=False)
    written.append(str(kpi_path))

    parquet_written = []
    if importlib.util.find_spec("pyarrow") is not None:
        for name, frame in frames.items():
            path = destination / f"{name}.parquet"
            frame.to_parquet(path, index=False)
            parquet_written.append(str(path))
    metadata_path = destination / "metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "python": sys.version,
                "platform": platform.platform(),
                "csv_files": written,
                "parquet_files": parquet_written,
                **(metadata or {}),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return {"csv_files": written, "parquet_files": parquet_written, "metadata": str(metadata_path)}
