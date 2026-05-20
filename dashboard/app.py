"""Main Plotly Dash application — Mumbai Local Train Delay Visualizer.

7 tabs:
  1. Live Map       — Folium station map, color-coded by delay severity
  2. Heatmap        — Station x hour delay matrix
  3. Rankings       — Worst/best stations per line per period
  4. Anomaly Alerts — Prophet-detected anomalous stations
  5. Line Comparison — Central vs Western vs Harbour 30-day trend
  6. Data Quality   — Pipeline health, freshness, missing data
  7. Business Insights — Plain-English callouts with economic impact
"""
import logging
import os
from pathlib import Path

import polars as pl
from dash import Dash, Input, Output, dcc, html
from dotenv import load_dotenv

from dashboard.charts import (
    make_anomaly_cards_data,
    make_business_insights,
    make_heatmap,
    make_line_trend,
    make_rankings_bar,
)
from dashboard.map import make_station_map
from pipeline.store import DelayStore

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_DB_PATH = os.getenv("DUCKDB_PATH", "delays.duckdb")
_RAW_DIR = Path(os.getenv("DATA_RAW_DIR", "data/raw"))

store = DelayStore(_DB_PATH)

_stops: pl.DataFrame | None = None
_stops_path = _RAW_DIR / "stops.parquet"
if _stops_path.exists():
    _stops = pl.read_parquet(_stops_path)
else:
    logger.warning("stops.parquet not found at %s", _stops_path)

app = Dash(
    __name__,
    title="Mumbai Local Delay Visualizer",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

_DARK = "#1a1a2e"
_LINES = ["Central", "Western", "Harbour"]
_PERIODS = ["morning_peak", "evening_peak", "off_peak"]


def _card(children, style: dict | None = None) -> html.Div:  # type: ignore[type-arg]
    base = {"backgroundColor": "#16213e", "borderRadius": "8px",
            "padding": "16px", "marginBottom": "12px"}
    return html.Div(children, style={**base, **(style or {})})


def _text(content: str, size: str = "14px", color: str = "#eaeaea") -> html.P:
    return html.P(content, style={"color": color, "fontSize": size, "margin": "4px 0"})


app.layout = html.Div(
    style={"backgroundColor": _DARK, "minHeight": "100vh", "fontFamily": "Inter, sans-serif"},
    children=[
        html.Div(
            style={"backgroundColor": "#16213e", "padding": "16px 24px", "marginBottom": "8px"},
            children=[
                html.H1(
                    "Mumbai Local Train Delay Visualizer",
                    style={"color": "#eaeaea", "margin": 0, "fontSize": "22px"},
                ),
                html.P(
                    "Real GTFS data · Prophet anomaly detection · 120+ stations",
                    style={"color": "#888", "margin": "4px 0 0 0", "fontSize": "13px"},
                ),
            ],
        ),
        dcc.Tabs(
            id="tabs",
            value="tab-map",
            style={"backgroundColor": "#16213e"},
            colors={"border": "#1a1a2e", "primary": "#E63946", "background": "#16213e"},
            children=[
                dcc.Tab(label="Live Map", value="tab-map"),
                dcc.Tab(label="Heatmap", value="tab-heatmap"),
                dcc.Tab(label="Rankings", value="tab-rankings"),
                dcc.Tab(label="Anomaly Alerts", value="tab-anomaly"),
                dcc.Tab(label="Line Comparison", value="tab-lines"),
                dcc.Tab(label="Data Quality", value="tab-quality"),
                dcc.Tab(label="Business Insights", value="tab-insights"),
            ],
        ),
        html.Div(id="tab-content", style={"padding": "16px"}),
    ],
)


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab: str) -> html.Div:
    if tab == "tab-map":
        return _render_map_tab()
    if tab == "tab-heatmap":
        return _render_heatmap_tab()
    if tab == "tab-rankings":
        return _render_rankings_tab()
    if tab == "tab-anomaly":
        return _render_anomaly_tab()
    if tab == "tab-lines":
        return _render_lines_tab()
    if tab == "tab-quality":
        return _render_quality_tab()
    if tab == "tab-insights":
        return _render_insights_tab()
    return html.Div("Unknown tab")


def _render_map_tab() -> html.Div:
    map_html = "<p style='color:#888'>stops.parquet not found. Run Phase 2 first.</p>"
    if _stops is not None:
        try:
            today_delays = pl.from_arrow(store.conn.execute("""
                SELECT station_name, AVG(avg_delay) AS avg_delay
                FROM delays
                WHERE date = (SELECT MAX(date) FROM delays)
                GROUP BY station_name
            """).arrow())
            map_html = make_station_map(_stops, today_delays)
        except Exception as e:
            map_html = f"<p style='color:red'>Map error: {e}</p>"

    return html.Div([
        _card([html.Iframe(
            srcDoc=map_html,
            style={"width": "100%", "height": "600px", "border": "none"},
        )]),
    ])


def _render_heatmap_tab() -> html.Div:
    stations = []
    try:
        stations = (
            pl.from_arrow(store.conn.execute(
                "SELECT DISTINCT station_name FROM delays ORDER BY station_name"
            ).arrow())["station_name"].to_list()
        )
    except Exception:
        pass

    return html.Div([
        _card([
            html.Label("Station:", style={"color": "#eaeaea", "marginRight": "8px"}),
            dcc.Dropdown(
                id="heatmap-station",
                options=[{"label": s, "value": s} for s in stations],
                value=stations[0] if stations else None,
                style={"width": "300px", "display": "inline-block"},
                clearable=False,
            ),
        ]),
        dcc.Graph(id="heatmap-graph"),
    ])


@app.callback(Output("heatmap-graph", "figure"), Input("heatmap-station", "value"))
def update_heatmap(station: str | None):  # type: ignore[return]
    if not station:
        return {}
    try:
        df = store.heatmap(station)
        return make_heatmap(df, station=station)
    except Exception as e:
        return {"layout": {"title": f"Error: {e}"}}


def _render_rankings_tab() -> html.Div:
    return html.Div([
        _card([
            html.Label("Line:", style={"color": "#eaeaea", "marginRight": "8px"}),
            dcc.Dropdown(
                id="rank-line",
                options=[{"label": line, "value": line} for line in _LINES],
                value="Central",
                style={"width": "200px", "display": "inline-block"},
                clearable=False,
            ),
            html.Label("Period:", style={"color": "#eaeaea", "margin": "0 8px 0 16px"}),
            dcc.Dropdown(
                id="rank-period",
                options=[{"label": p.replace("_", " ").title(), "value": p} for p in _PERIODS],
                value="morning_peak",
                style={"width": "200px", "display": "inline-block"},
                clearable=False,
            ),
        ]),
        dcc.Graph(id="rank-worst-graph"),
        dcc.Graph(id="rank-best-graph"),
    ])


@app.callback(
    Output("rank-worst-graph", "figure"),
    Output("rank-best-graph", "figure"),
    Input("rank-line", "value"),
    Input("rank-period", "value"),
)
def update_rankings(line: str, period: str):  # type: ignore[return]
    try:
        from analysis.rankings import peak_rankings
        worst = peak_rankings(store, line, period, n=10)
        best = store.best_stations(line, n=10)
        fig_worst = make_rankings_bar(
            worst.rename({"avg_delay": "mean_delay", "ci_lower": "mean_ci_lower", "ci_upper": "mean_ci_upper"}),
            f"Worst 10 — {line} — {period.replace('_', ' ').title()}"
        )
        fig_best = make_rankings_bar(best, f"Best 10 — {line}")
        return fig_worst, fig_best
    except Exception as e:
        err = {"layout": {"title": f"Error: {e}"}}
        return err, err


def _build_anomaly_cards() -> list:  # type: ignore[type-arg]
    try:
        from analysis.anomaly import AnomalyBatch

        history = pl.from_arrow(store.conn.execute("""
            SELECT date, station_name, AVG(avg_delay) AS avg_delay
            FROM delays GROUP BY date, station_name
        """).arrow())

        today_data = pl.from_arrow(store.conn.execute("""
            SELECT station_name, AVG(avg_delay) AS avg_delay, MAX(date) AS date
            FROM delays
            WHERE date = (SELECT MAX(date) FROM delays)
            GROUP BY station_name
        """).arrow())

        if len(today_data) == 0:
            return [_text("No data for today.", color="#888")]

        batch = AnomalyBatch(history=history)
        results = batch.detect_all(today_data)
        cards_data = make_anomaly_cards_data(results)

        if not cards_data:
            return [_card([_text("No anomalies detected today.", color="#2A9D8F")])]

        cards = []
        for c in cards_data:
            color = {"HIGH": "#E63946", "MEDIUM": "#E9C46A"}.get(c["severity"], "#2A9D8F")
            cards.append(_card([
                html.H4(c["station"], style={"color": color, "margin": "0 0 8px 0"}),
                _text(f"Severity: {c['severity']}", color=color),
                _text(f"Actual delay: {c['actual_delay']:.1f} min"),
                _text(f"Expected: {c['expected_delay']:.1f} min (95% upper: {c['upper_bound']:.1f} min)"),
                _text(f"Excess: +{c['excess_pct']:.0f}% above expected", color="#E9C46A"),
            ], style={"borderLeft": f"4px solid {color}"}))
        return cards
    except Exception as e:
        return [_text(f"Anomaly detection error: {e}", color="red")]


def _render_anomaly_tab() -> html.Div:
    return html.Div([
        _card([_text("Prophet anomaly detection — stations where today's delay exceeds the 95% confidence bound.", color="#888")]),
        html.Div(id="anomaly-content", children=_build_anomaly_cards()),
    ])


_line_colors = {"Central": "#E63946", "Western": "#457B9D", "Harbour": "#2A9D8F"}


def _render_lines_tab() -> html.Div:
    figs = []
    try:
        from analysis.rankings import line_summary
        summary = line_summary(store)
        on_time_col = summary["on_time_pct"].to_list() if "on_time_pct" in summary.columns else [0] * len(summary)
        fig_ontime = {
            "data": [{"type": "bar", "x": summary["line"].to_list(), "y": on_time_col,
                       "marker": {"color": [_line_colors.get(ln, "#888") for ln in summary["line"].to_list()]}}],
            "layout": {"title": "On-Time % by Line", "paper_bgcolor": _DARK,
                        "plot_bgcolor": "#16213e", "font": {"color": "#eaeaea"}},
        }
        figs.append(dcc.Graph(figure=fig_ontime))
    except Exception as e:
        figs.append(_text(f"Summary error: {e}", color="red"))

    for line in _LINES:
        try:
            trend = store.line_trend(line, days=30)
            figs.append(dcc.Graph(figure=make_line_trend(trend, line)))
        except Exception as e:
            figs.append(_text(f"{line} trend error: {e}", color="red"))

    return html.Div([_card(figs)])


def _render_quality_tab() -> html.Div:
    try:
        report = store.data_quality_report()
        total = len(report)
        fresh = report.filter(pl.col("last_updated") == report["last_updated"].max())
        health_pct = round(len(fresh) / max(total, 1) * 100, 0)
        color = "#2A9D8F" if health_pct >= 90 else "#E9C46A" if health_pct >= 70 else "#E63946"

        table_rows = [
            html.Tr([
                html.Td(r["station_name"], style={"color": "#eaeaea", "padding": "4px 8px"}),
                html.Td(str(r["last_updated"]), style={"color": "#aaa", "padding": "4px 8px"}),
                html.Td(f"{r['row_count']:,}", style={"color": "#aaa", "padding": "4px 8px"}),
                html.Td(str(r["unique_dates"]), style={"color": "#aaa", "padding": "4px 8px"}),
            ])
            for r in report.head(20).iter_rows(named=True)
        ]

        return html.Div([
            _card([
                html.H3(f"Pipeline Health: {health_pct:.0f}%", style={"color": color}),
                _text(f"{len(fresh)}/{total} stations have fresh data (latest date)"),
            ]),
            _card([html.Table([
                html.Thead(html.Tr([
                    html.Th("Station", style={"color": "#888", "textAlign": "left", "padding": "4px 8px"}),
                    html.Th("Last Updated", style={"color": "#888", "textAlign": "left", "padding": "4px 8px"}),
                    html.Th("Rows", style={"color": "#888", "textAlign": "left", "padding": "4px 8px"}),
                    html.Th("Unique Days", style={"color": "#888", "textAlign": "left", "padding": "4px 8px"}),
                ])),
                html.Tbody(table_rows),
            ], style={"width": "100%", "borderCollapse": "collapse"})]),
        ])
    except Exception as e:
        return _card([_text(f"Quality report error: {e}", color="red")])


def _render_insights_tab() -> html.Div:
    try:
        insights = make_business_insights(store)
        return html.Div([
            _card([
                html.H3("Key Findings", style={"color": "#eaeaea"}),
                html.Hr(style={"borderColor": "#333"}),
                _text(f"Worst station: {insights['worst_station']} — avg {insights['worst_station_delay']} min delay", size="16px"),
                _text(f"Most reliable line: {insights['best_line']} — avg {insights['best_line_delay']} min delay", size="16px"),
                _text(f"Peak delay window: {insights['peak_window']}", size="16px"),
            ]),
            _card([
                html.H3("Economic Impact Estimate", style={"color": "#E9C46A"}),
                _text(f"~{insights['delay_hours_per_day']:,.0f} passenger-hours lost per day at {insights['worst_station']}", size="15px"),
                _text("Based on: 15 trains/hr x 3,000 commuters x 8 peak hours", color="#888", size="13px"),
                _text(f"Across all lines: {insights['commuters_affected']} affected", size="15px"),
            ]),
            _card([
                html.H3("Recommendations", style={"color": "#2A9D8F"}),
                _text("1. Prioritize infrastructure investment at worst stations first"),
                _text("2. Stagger peak hour services to reduce crowding-induced delays"),
                _text("3. Alert frequent commuters 30 min before predicted anomalies"),
            ]),
        ])
    except Exception as e:
        return _card([_text(f"Insights error: {e}", color="red")])


if __name__ == "__main__":
    port = int(os.getenv("DASH_PORT", "8050"))
    debug = os.getenv("DASH_DEBUG", "false").lower() == "true"
    logger.info("Starting dashboard on port %s", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
