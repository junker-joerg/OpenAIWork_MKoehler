"""Compact local Bokeh web UI for the Hyperion Juno demo.

The page is deliberately designed for an iPad in landscape orientation:
controls stay in a narrow left rail and the results occupy one fixed-height
workspace on the right. No notebook cell output is required once the server
has started.
"""

from __future__ import annotations

import html
import threading
from dataclasses import dataclass
from typing import Mapping, Optional, Tuple

import pandas as pd

from juno_showcase import (
    BOKEH_AVAILABLE,
    DEMO_MODES,
    EVENT_CATALOG,
    bokeh_agent_dashboard,
    bokeh_route_map,
    bokeh_scenario_dashboard,
    build_showcase,
    compose_scenario,
    demo_mode_config,
    flight_recorder_table,
    route_network,
    scenario_comparison,
)


if BOKEH_AVAILABLE:  # Keep importing this module safe on a minimal desktop.
    from bokeh.application import Application
    from bokeh.application.handlers.function import FunctionHandler
    from bokeh.document import Document
    from bokeh.io import curdoc
    from bokeh.layouts import column, row
    from bokeh.models import Button, Div, Select, Spinner
    from bokeh.server.server import Server


def _require_bokeh() -> None:
    if not BOKEH_AVAILABLE:
        raise RuntimeError(
            "Bokeh ist nicht installiert. In Juno zuerst das Paket 'bokeh' installieren."
        )


@dataclass
class JunoWebServerHandle:
    """Thread-backed server handle; unlike subprocesses this works on iOS."""

    server: object
    thread: threading.Thread
    url: str

    def stop(self) -> None:
        io_loop = self.server.io_loop
        io_loop.add_callback(self.server.stop)
        io_loop.add_callback(io_loop.stop)
        self.thread.join(timeout=2.0)


def _number(value: object) -> str:
    try:
        return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "-"


def _kpi_panel(kpi: pd.DataFrame, mode_label: str, event_name: str, event_year: int):
    row_data = kpi.iloc[0]
    event_label = EVENT_CATALOG[event_name]["label"]
    text = (
        f"<b>{html.escape(mode_label)}</b><br>"
        f"Event: {html.escape(event_label)} / Jahr {event_year}<br>"
        f"Stabilitaet <b>{_number(row_data['final_stability'])}</b> &nbsp; "
        f"Prosperitaet <b>{_number(row_data['final_prosperity'])}</b><br>"
        f"Handelswert {_number(row_data['total_trade_value'])} &nbsp; "
        f"Time Debt {_number(row_data['final_time_debt'])}"
    )
    return Div(
        text=text,
        width=235,
        height=215,
        styles={
            "font-size": "12px",
            "line-height": "1.45",
            "padding": "8px",
            "overflow": "hidden",
        },
    )


def _flight_panel(showcase: Mapping[str, object], config: Mapping[str, object]):
    if not config["show_flight_recorder"]:
        text = "<b>Flight Recorder</b><br>Im gewaehlten Modus ab Agentenvergleich verfuegbar."
    else:
        recorder = flight_recorder_table(showcase["decisions"])
        limit = int(config["recorder_rows"])
        lines = ["<b>Letzte Entscheidungen</b>"]
        for _, item in recorder.head(limit).iterrows():
            lines.append(
                f"J{int(item['year'])} {html.escape(str(item['agent']))}: "
                f"<b>{html.escape(str(item['action']))}</b> - "
                f"{html.escape(str(item['explanation']))}"
            )
        text = "<br>".join(lines)
    return Div(
        text=text,
        height=215,
        sizing_mode="stretch_width",
        styles={
            "font-size": "11px",
            "line-height": "1.35",
            "padding": "8px",
            "overflow": "hidden",
        },
    )


def _route_panel(showcase: Mapping[str, object], config: Mapping[str, object]):
    if not config["show_route_map"]:
        return Div(
            text="<b>Time-Debt-Routenkarte</b><br>Im Tiefenanalyse-Modus verfuegbar.",
            height=215,
            sizing_mode="stretch_width",
            styles={"font-size": "12px", "padding": "8px", "overflow": "hidden"},
        )
    return bokeh_route_map(showcase["routes"], showcase["nodes"], height=215)


def _result_layout(
    showcase: Mapping[str, object],
    selected_frames: Mapping[str, pd.DataFrame],
    selected_kpi: pd.DataFrame,
    scenarios: pd.DataFrame,
    config: Mapping[str, object],
    event_name: str,
    event_year: int,
):
    selected_routes, selected_nodes = route_network(selected_frames)
    selected_showcase = dict(showcase)
    selected_showcase["routes"] = selected_routes
    selected_showcase["nodes"] = selected_nodes
    top = row(
        _kpi_panel(selected_kpi, str(config["label"]), event_name, event_year),
        bokeh_scenario_dashboard(scenarios, height=215),
        sizing_mode="stretch_width",
    )
    bottom = row(
        _route_panel(selected_showcase, config),
        _flight_panel(showcase, config),
        sizing_mode="stretch_width",
    )
    return column(
        top,
        bokeh_agent_dashboard(showcase, height=215),
        bottom,
        sizing_mode="stretch_both",
    )


def modify_doc(doc: "Document") -> None:
    """Populate a Bokeh document with the compact control-and-results UI."""

    _require_bokeh()
    mode = Select(title="Demo-Modus", value="einsteiger", options=list(DEMO_MODES), width=205)
    event = Select(
        title="Ereignis",
        value="farcaster_stoerung",
        options=list(EVENT_CATALOG),
        width=205,
    )
    year = Spinner(title="Event-Jahr", low=1, high=8, value=3, step=1, width=205)
    seed = Spinner(title="Seed", low=0, high=999999, value=7, step=1, width=205)
    run_button = Button(label="Simulation ausfuehren", button_type="primary", width=205)
    status = Div(text="Bereit.", width=205, height=50, styles={"font-size": "11px"})
    results = column(sizing_mode="stretch_both")

    def update_mode(attr: str, old: str, new: str) -> None:
        config = demo_mode_config(new)
        year.high = int(config["years"])
        year.value = min(int(config["event_year"]), year.high)
        status.text = f"{html.escape(str(config['label']))}: Auswahl bereit."

    def run_view() -> None:
        config = demo_mode_config(mode.value)
        event_year = min(int(year.value), int(config["years"]))
        try:
            status.text = "Simulation laeuft ..."
            showcase = build_showcase(
                episodes=int(config["episodes"]),
                years=int(config["years"]),
                seed=int(seed.value),
            )
            selected_frames, selected_kpi = compose_scenario(
                event_name=event.value,
                event_year=event_year,
                years=int(config["years"]),
                seed=int(seed.value),
            )
            scenarios = scenario_comparison(
                event_names=config["events"],
                event_year=event_year,
                years=int(config["years"]),
                seed=int(seed.value),
            )
            results.children = [
                _result_layout(
                    showcase,
                    selected_frames,
                    selected_kpi,
                    scenarios,
                    config,
                    event.value,
                    event_year,
                )
            ]
            status.text = f"Fertig: {int(config['episodes'])} Episoden / {int(config['years'])} Jahre."
        except Exception as exc:  # Keep the UI usable after invalid input.
            status.text = f"Fehler: {html.escape(str(exc))}"

    mode.on_change("value", update_mode)
    run_button.on_click(run_view)
    controls = column(
        Div(text="<b>Hyperion Economy</b><br>Lokale Web-Demo", width=205, height=42),
        mode,
        event,
        year,
        seed,
        run_button,
        status,
        width=220,
        sizing_mode="stretch_height",
    )
    run_view()
    doc.title = "Hyperion Economy - Juno Web Demo"
    doc.add_root(row(controls, results, sizing_mode="stretch_both"))


def start_juno_webserver(
    *, port: int = 5006, address: str = "127.0.0.1"
) -> Tuple[JunoWebServerHandle, str]:
    """Start Bokeh in-process so the launcher is compatible with iOS/Juno."""

    _require_bokeh()
    application = Application(FunctionHandler(modify_doc))
    server = Server(
        {"/": application},
        address=address,
        port=port,
        allow_websocket_origin=[f"localhost:{port}", f"127.0.0.1:{port}"],
    )
    server.start()
    url = f"http://localhost:{port}/"
    thread = threading.Thread(
        target=server.io_loop.start,
        name="hyperion-bokeh-server",
        daemon=True,
    )
    thread.start()
    return JunoWebServerHandle(server, thread, url), url


def stop_juno_webserver(process: Optional[JunoWebServerHandle]) -> None:
    """Stop a server previously returned by start_juno_webserver."""

    if process is not None:
        process.stop()


__all__ = [
    "JunoWebServerHandle",
    "modify_doc",
    "start_juno_webserver",
    "stop_juno_webserver",
]
