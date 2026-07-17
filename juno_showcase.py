"""Five-part Juno presentation layer for Hyperion Economy.

The module is intentionally optional around Bokeh: all tables, exports, the
scenario composer, and the flight recorder work without it. When Bokeh is
installed in Juno, the same data becomes interactive iPad-ready views.
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Dict, Mapping, Optional, Sequence, Tuple

import pandas as pd

from juno_demo import kpi_table, run_simulation, scenario_table
from learning_agents import (
    evaluate_agents,
    evaluation_summary,
    run_episode,
    train_agents,
)


try:  # Bokeh is optional on desktop, but supported by Juno.
    from bokeh.embed import file_html
    from bokeh.io import output_notebook
    from bokeh.layouts import column, row
    from bokeh.models import ColumnDataSource, HoverTool
    from bokeh.plotting import figure
    from bokeh.resources import INLINE

    BOKEH_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised on installations without Bokeh
    BOKEH_AVAILABLE = False


AGENT_ROLES: Dict[str, Dict[str, str]] = {
    "Profit-Scout": {
        "algorithm": "SARSA",
        "role": "Rendite-Sucher",
        "brief": "lernt aus der tatsächlich gewählten Folgeaktion",
    },
    "Reserve-Keeper": {
        "algorithm": "Dyna-Q",
        "role": "Reservenwächter",
        "brief": "berücksichtigt Risiko, Ereignisse und Time Debt",
    },
    "Hyperion-Speculator": {
        "algorithm": "Bandit",
        "role": "Opportunist",
        "brief": "vergleicht die durchschnittliche Wirkung der Aktionen",
    },
}

EVENT_CATALOG: Dict[str, Dict[str, str]] = {
    "keines": {"label": "Kein Zwangsevent", "key": ""},
    "farcaster_stoerung": {"label": "Farcaster-Ausfall", "key": "farcaster_stoerung"},
    "ouster_raid": {"label": "Ouster-Raid", "key": "ouster_raid"},
    "pilgerboom": {"label": "Pilgerboom", "key": "pilgerboom"},
    "sanktionen": {"label": "Sanktionen", "key": "sanktionen"},
    "core_prognosefehler": {"label": "Core-Prognosefehler", "key": "core_prognosefehler"},
    "core_optimierung": {"label": "Core-Optimierung", "key": "core_optimierung"},
    "templar_korridor": {"label": "Templar-Korridor", "key": "templar_korridor"},
    "aufstand": {"label": "Aufstand", "key": "aufstand"},
}

DEMO_MODES: Dict[str, Dict[str, object]] = {
    "einsteiger": {
        "label": "Einsteiger \u2013 3 Minuten",
        "description": "Agentenrat und ein klarer Szenariovergleich.",
        "episodes": 8,
        "years": 8,
        "event_year": 3,
        "events": ("keines", "farcaster_stoerung", "pilgerboom"),
        "show_agent_dashboard": True,
        "show_scenario_dashboard": True,
        "show_route_map": False,
        "show_flight_recorder": False,
        "export_capsule": False,
        "recorder_rows": 0,
    },
    "agentenvergleich": {
        "label": "Agentenvergleich \u2013 8 Minuten",
        "description": "Lernkurven, Endwerte und Szenario-Wirkungen vergleichen.",
        "episodes": 20,
        "years": 12,
        "event_year": 3,
        "events": ("keines", "farcaster_stoerung", "pilgerboom", "ouster_raid"),
        "show_agent_dashboard": True,
        "show_scenario_dashboard": True,
        "show_route_map": False,
        "show_flight_recorder": True,
        "export_capsule": False,
        "recorder_rows": 6,
    },
    "tiefenanalyse": {
        "label": "Technische Tiefenanalyse \u2013 20 Minuten",
        "description": "Vollstaendige Agenten-, Routen- und Entscheidungsanalyse.",
        "episodes": 50,
        "years": 20,
        "event_year": 5,
        "events": ("keines", "farcaster_stoerung", "pilgerboom", "ouster_raid"),
        "show_agent_dashboard": True,
        "show_scenario_dashboard": True,
        "show_route_map": True,
        "show_flight_recorder": True,
        "export_capsule": True,
        "recorder_rows": 15,
    },
}


def demo_mode_config(mode: str = "einsteiger") -> Dict[str, object]:
    """Return the notebook settings for one presentation duration."""

    if mode not in DEMO_MODES:
        choices = ", ".join(DEMO_MODES)
        raise ValueError(f"Unbekannter Demo-Modus: {mode}. Erlaubt: {choices}")
    return dict(DEMO_MODES[mode])


def bokeh_status() -> Dict[str, object]:
    return {
        "available": BOKEH_AVAILABLE,
        "message": (
            "Bokeh verfügbar — interaktive Ansichten können angezeigt werden."
            if BOKEH_AVAILABLE
            else "Bokeh nicht installiert — Matplotlib-/Tabellen-Fallback verwenden."
        ),
    }


def configure_bokeh_notebook() -> bool:
    """Enable inline Bokeh output for Jupyter/Juno notebooks."""

    if not BOKEH_AVAILABLE:
        return False
    output_notebook(resources=INLINE, hide_banner=True)
    return True


def build_showcase(
    *,
    episodes: int = 30,
    years: int = 20,
    seed: int = 7,
    scenario: str = "baseline",
) -> Dict[str, object]:
    """Build all data products used by the story notebook."""

    frames = run_simulation(years=years, seed=seed, num_runs=1, scenario=scenario)
    training = train_agents(episodes=episodes, years=years, seed=seed, memory_path=None)
    evaluation = evaluate_agents(training["agents"], episodes=5, years=years, seed=seed + 1000)
    decisions = []
    run_episode(
        training["agents"],
        years=years,
        seed=seed + 2000,
        learn=False,
        episode=0,
        decision_log=decisions,
    )
    scenario_runs = scenario_table(years=years)
    routes, nodes = route_network(frames)
    return {
        "frames": frames,
        "agents": training["agents"],
        "history": pd.DataFrame(training["history"]),
        "evaluation": pd.DataFrame(evaluation),
        "summary": pd.DataFrame(evaluation_summary(evaluation)),
        "decisions": pd.DataFrame(decisions),
        "scenario_runs": scenario_runs,
        "routes": routes,
        "nodes": nodes,
    }


def agent_council_table(summary: pd.DataFrame) -> pd.DataFrame:
    """Turn evaluation metrics into a presentation-ready council table."""

    table = summary.copy()
    table["role"] = table["agent"].map(
        {name: values["role"] for name, values in AGENT_ROLES.items()}
    )
    table["brief"] = table["agent"].map(
        {name: values["brief"] for name, values in AGENT_ROLES.items()}
    )
    columns = [
        "agent", "role", "algorithm", "brief", "avg_final_value",
        "std_final_value", "avg_excess_return", "win_rate",
        "liquidity_stress_rate", "insolvency_rate",
    ]
    return table[[column for column in columns if column in table.columns]].sort_values(
        "avg_final_value", ascending=False
    )


def compose_scenario(
    *,
    event_name: str = "farcaster_stoerung",
    event_year: int = 3,
    years: int = 20,
    seed: int = 7,
    trade_intensity: float = 1.0,
    faction_strength: float = 1.0,
) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
    """Run one user-selected forced-event scenario."""

    if event_year < 1 or event_year > years:
        raise ValueError("event_year muss innerhalb des Simulationszeitraums liegen")
    if event_name not in EVENT_CATALOG:
        raise ValueError(f"Unbekanntes Event: {event_name}")
    event_key = EVENT_CATALOG[event_name]["key"]
    forced = {} if not event_key else {event_year: event_key}
    frames = run_simulation(
        years=years,
        seed=seed,
        num_runs=1,
        scenario="baseline",
        trade_intensity=trade_intensity,
        faction_strength=faction_strength,
        forced_events=forced,
    )
    return frames, kpi_table(frames)


def scenario_comparison(
    *,
    event_names: Optional[Sequence[str]] = None,
    event_year: int = 3,
    years: int = 20,
    seed: int = 7,
) -> pd.DataFrame:
    names = tuple(event_names or ("keines", "farcaster_stoerung", "pilgerboom", "ouster_raid"))
    rows = []
    for index, event_name in enumerate(names):
        _, kpis = compose_scenario(
            event_name=event_name,
            event_year=event_year,
            years=years,
            seed=seed + index,
        )
        row = kpis.iloc[0].to_dict()
        row["event"] = EVENT_CATALOG[event_name]["label"]
        row["event_name"] = event_name
        row["event_year"] = event_year
        rows.append(row)
    return pd.DataFrame(rows).round(2)


def route_network(
    frames: Mapping[str, pd.DataFrame], *, run: int = 1, year: Optional[int] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate actual trades into a schematic, non-geographic route network."""

    trades = frames["trades"]
    worlds = frames["world"]
    if trades.empty or worlds.empty:
        return pd.DataFrame(), pd.DataFrame()
    filtered = trades[trades["run"] == run].copy()
    if year is not None:
        filtered = filtered[filtered["year"] == year]
    if filtered.empty:
        return pd.DataFrame(), pd.DataFrame()
    routes = (
        filtered.groupby(["seller", "buyer"], as_index=False)
        .agg(
            trade_volume=("quantity", "sum"),
            trade_value=("trade_value", "sum"),
            avg_transport_cost=("transport_cost", "mean"),
        )
        .rename(columns={"seller": "source", "buyer": "target"})
    )
    world_run = worlds[worlds["run"] == run].copy()
    if year is None:
        latest = world_run.sort_values("year").groupby("world").tail(1)
    else:
        latest = world_run[world_run["year"] == year]
    category_x = {"core": 0.0, "frontier": 1.0, "periphery": 2.0}
    nodes = latest[["world", "category", "stability", "time_debt", "farcaster"]].copy()
    nodes["x"] = nodes["category"].map(lambda value: category_x.get(str(value).lower(), 1.0))
    nodes["y"] = nodes["stability"].astype(float) * 10.0
    nodes = nodes.rename(columns={"world": "name"})
    routes = routes.merge(nodes[["name", "time_debt"]].rename(columns={"name": "target", "time_debt": "target_time_debt"}), on="target", how="left")
    return routes.round(4), nodes.round(4)


def explain_decision(row: Mapping[str, object]) -> str:
    action = str(row.get("action", "halten"))
    event_count = int(row.get("event_count", 0))
    time_debt = float(row.get("time_debt", 0.0))
    stability = float(row.get("stability", 0.0))
    if bool(row.get("exploratory")):
        return "Exploration: Der Agent testet eine nicht aktuell führende Aktion."
    if action == "kaufen":
        return f"Kauf bei Reliktpreis {float(row['price']):.2f}; Stabilität {stability:.2f}, Events {event_count}."
    if action == "verkaufen":
        return f"Verkauf bei Time Debt {time_debt:.2f}; Bestand wird zur Liquidität gemacht."
    return f"Halten: Stabilität {stability:.2f}, Time Debt {time_debt:.2f}, Events {event_count}."


def flight_recorder_table(decisions: pd.DataFrame) -> pd.DataFrame:
    result = decisions.copy()
    if result.empty:
        return result
    result["explanation"] = result.apply(explain_decision, axis=1)
    return result


def _require_bokeh() -> None:
    if not BOKEH_AVAILABLE:
        raise RuntimeError(
            "Bokeh ist nicht installiert. In Juno über den Paketmanager installieren "
            "oder den Matplotlib-Fallback verwenden."
        )


def bokeh_agent_dashboard(showcase: Mapping[str, object]):
    """Create the interactive agent council dashboard."""

    _require_bokeh()
    history = showcase["history"]
    evaluation = showcase["evaluation"]
    colors = {"Profit-Scout": "#2563eb", "Reserve-Keeper": "#059669", "Hyperion-Speculator": "#d97706"}
    reward_plot = figure(title="Agentenrat: Lernfortschritt", height=330, sizing_mode="stretch_width", tools="pan,wheel_zoom,box_zoom,reset,save")
    for agent, frame in history.groupby("agent"):
        source = ColumnDataSource(frame)
        reward_plot.line("episode", "total_reward", source=source, line_width=2, color=colors.get(agent, "#64748b"), legend_label=agent)
    reward_plot.add_tools(HoverTool(tooltips=[("Episode", "@episode"), ("Reward", "@total_reward{0.00}"), ("Action", "@buy_actions kaufen / @sell_actions verkaufen")]))
    reward_plot.legend.location = "top_left"
    reward_plot.xaxis.axis_label = "Episode"
    reward_plot.yaxis.axis_label = "Reward"

    value_plot = figure(title="Neue Marktverläufe vs. Buy-and-Hold", height=330, sizing_mode="stretch_width", tools="pan,wheel_zoom,box_zoom,reset,save")
    for agent, frame in evaluation.groupby("agent"):
        source = ColumnDataSource(frame)
        value_plot.scatter("episode", "final_value", source=source, marker="circle", size=9, color=colors.get(agent, "#64748b"), legend_label=agent)
    benchmark = evaluation[["episode", "benchmark_value"]].drop_duplicates()
    value_plot.line("episode", "benchmark_value", source=ColumnDataSource(benchmark), line_dash="dashed", line_width=2, color="#64748b", legend_label="Buy-and-Hold")
    value_plot.add_tools(HoverTool(tooltips=[("Episode", "@episode"), ("Endwert", "@final_value{0.00}"), ("Benchmark", "@benchmark_value{0.00}"), ("Excess", "@excess_return{0.00}")]))
    value_plot.legend.location = "top_left"
    value_plot.xaxis.axis_label = "Bewertungslauf"
    value_plot.yaxis.axis_label = "Portfolio-Wert"
    return column(row(reward_plot, value_plot, sizing_mode="stretch_width"), sizing_mode="stretch_width")


def bokeh_scenario_dashboard(scenarios: pd.DataFrame):
    _require_bokeh()
    source = ColumnDataSource(scenarios)
    plot = figure(
        x_range=list(scenarios["event"]),
        title="Scenario Composer: Auswirkungen des Ereignisses",
        height=380,
        sizing_mode="stretch_width",
        tools="pan,wheel_zoom,reset,save",
    )
    plot.vbar(x="event", top="final_stability", width=0.35, source=source, color="#2563eb", legend_label="Stabilität")
    plot.add_tools(HoverTool(tooltips=[("Event", "@event"), ("Stabilität", "@final_stability"), ("Wohlstand", "@final_prosperity"), ("Time Debt", "@final_time_debt")]))
    plot.xaxis.major_label_orientation = 0.8
    plot.yaxis.axis_label = "Wert"
    return plot


def bokeh_route_map(routes: pd.DataFrame, nodes: pd.DataFrame):
    _require_bokeh()
    plot = figure(title="Hyperion-Handelsrouten und Time Debt", height=430, sizing_mode="stretch_width", tools="pan,wheel_zoom,reset,save")
    if not nodes.empty:
        node_source = ColumnDataSource(nodes)
        node_lookup = nodes.set_index("name")
        segments = routes.copy()
        if not segments.empty:
            segments["x0"] = segments["source"].map(node_lookup["x"])
            segments["y0"] = segments["source"].map(node_lookup["y"])
            segments["x1"] = segments["target"].map(node_lookup["x"])
            segments["y1"] = segments["target"].map(node_lookup["y"])
            segments = segments.dropna(subset=["x0", "y0", "x1", "y1"])
            if not segments.empty:
                route_source = ColumnDataSource(segments)
                plot.segment("x0", "y0", "x1", "y1", source=route_source, line_width=2, alpha=0.45, color="#64748b")
                plot.add_tools(HoverTool(tooltips=[("Route", "@source → @target"), ("Volumen", "@trade_volume{0.00}"), ("Transportkosten", "@avg_transport_cost{0.00}"), ("Ziel-Time Debt", "@target_time_debt{0.00}")]))
        plot.scatter("x", "y", source=node_source, marker="circle", size=14, color="#2563eb")
        plot.add_tools(HoverTool(tooltips=[("Welt", "@name"), ("Stabilität", "@stability{0.00}"), ("Time Debt", "@time_debt{0.00}"), ("Farcaster", "@farcaster")]))
        plot.xaxis.axis_label = "Kern → Grenze → Peripherie"
        plot.yaxis.axis_label = "Stabilitätsniveau"
    return plot


def save_bokeh_html(layout, path: str) -> Path:
    _require_bokeh()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(file_html(layout, INLINE, title="Hyperion Juno Demo"), encoding="utf-8")
    return target


def export_demo_capsule(showcase: Mapping[str, object], output_dir: str = "demo_capsule") -> Dict[str, object]:
    """Write a portable presentation package with data, report, and optional HTML."""

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    frames = showcase["frames"]
    written = []
    for name, frame in frames.items():
        path = destination / f"{name}.csv"
        frame.to_csv(path, index=False)
        written.append(str(path))
    for name in ("history", "evaluation", "summary", "decisions", "scenario_runs", "routes", "nodes"):
        frame = showcase[name]
        path = destination / f"{name}.csv"
        frame.to_csv(path, index=False)
        written.append(str(path))
    report = destination / "DEMO_REPORT.md"
    summary = showcase["summary"]
    lines = [
        "# Hyperion Economy — Juno Demo Capsule",
        "",
        "Diese Capsule enthält reproduzierbare Daten für Agentenrat, Scenario Composer, Routenkarte und Flight Recorder.",
        "",
        "## Agentenrat",
        "",
        showcase["council_markdown"] if "council_markdown" in showcase else summary.to_string(index=False),
        "",
        "## Wiederholung",
        "",
        "- Notebook: `Juno_Story_Capsule.ipynb`",
        "- Gedächtnis bleibt absichtlich lokal: `agent_memory.json`",
        "- Alle Läufe verwenden feste Seeds und werden als CSV exportiert.",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")
    html_path = None
    if BOKEH_AVAILABLE:
        html_path = save_bokeh_html(bokeh_agent_dashboard(showcase), str(destination / "agent_dashboard.html"))
    metadata = {
        "python": sys.version,
        "platform": platform.platform(),
        "bokeh_available": BOKEH_AVAILABLE,
        "files": written + [str(report)] + ([str(html_path)] if html_path else []),
    }
    metadata_path = destination / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"files": metadata["files"], "metadata": str(metadata_path)}


__all__ = [
    "AGENT_ROLES",
    "BOKEH_AVAILABLE",
    "DEMO_MODES",
    "EVENT_CATALOG",
    "agent_council_table",
    "bokeh_agent_dashboard",
    "bokeh_route_map",
    "bokeh_scenario_dashboard",
    "bokeh_status",
    "build_showcase",
    "configure_bokeh_notebook",
    "compose_scenario",
    "demo_mode_config",
    "evaluation_summary",
    "explain_decision",
    "export_demo_capsule",
    "flight_recorder_table",
    "route_network",
    "save_bokeh_html",
    "scenario_comparison",
]
