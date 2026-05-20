"""Plotly chart factory functions for Mumbai local dashboard.

All functions are pure: take DataFrames/data, return Plotly figures.
No side effects. Easy to test.
"""
from typing import Any

import plotly.graph_objects as go
import polars as pl

from analysis.anomaly import AnomalyResult

# Mumbai brand colors
_COLORS = {
    "Central": "#E63946",
    "Western": "#457B9D",
    "Harbour": "#2A9D8F",
    "LOW": "#2A9D8F",
    "MEDIUM": "#E9C46A",
    "HIGH": "#E63946",
}

_DARK_BG = "#1a1a2e"
_CARD_BG = "#16213e"
_TEXT = "#eaeaea"


def _dark_layout(**kwargs: Any) -> dict:  # type: ignore[type-arg]
    """Base dark theme layout."""
    return {
        "paper_bgcolor": _DARK_BG,
        "plot_bgcolor": _CARD_BG,
        "font": {"color": _TEXT, "family": "Inter, sans-serif"},
        "margin": {"l": 60, "r": 20, "t": 50, "b": 60},
        **kwargs,
    }


def make_heatmap(df: pl.DataFrame, station: str) -> go.Figure:
    """Station delay heatmap: hour (x) x weekday (y) -> avg_delay (color)."""
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    z = []
    for wd in range(7):
        row_data = df.filter(pl.col("weekday") == wd).sort("hour")
        z.append(row_data["avg_delay"].to_list())

    fig = go.Figure(go.Heatmap(
        z=z,
        x=list(range(24)),
        y=day_labels,
        colorscale="Viridis",
        colorbar={"title": "Avg Delay (min)", "tickfont": {"color": _TEXT}},
        hovertemplate="Hour: %{x}:00<br>Day: %{y}<br>Delay: %{z:.1f} min<extra></extra>",
    ))
    fig.update_layout(
        title=f"Delay Heatmap — {station}",
        xaxis_title="Hour of Day",
        yaxis_title="",
        **_dark_layout(),
    )
    return fig


def make_rankings_bar(df: pl.DataFrame, title: str) -> go.Figure:
    """Horizontal bar chart of station rankings with 95% CI error bars."""
    sorted_df = df.sort("mean_delay", descending=True)
    stations = sorted_df["station_name"].to_list()
    delays = sorted_df["mean_delay"].to_list()
    ci_lower = sorted_df["mean_ci_lower"].to_list()
    ci_upper = sorted_df["mean_ci_upper"].to_list()
    error_minus = [d - lo for d, lo in zip(delays, ci_lower, strict=True)]
    error_plus = [hi - d for d, hi in zip(delays, ci_upper, strict=True)]

    fig = go.Figure(go.Bar(
        x=delays,
        y=stations,
        orientation="h",
        marker_color="#E63946",
        error_x={
            "type": "data",
            "symmetric": False,
            "array": error_plus,
            "arrayminus": error_minus,
            "color": _TEXT,
        },
        hovertemplate="%{y}<br>Avg delay: %{x:.1f} min<extra></extra>",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Avg Delay (min)",
        yaxis={"categoryorder": "total ascending"},
        **_dark_layout(),
    )
    return fig


def make_line_trend(df: pl.DataFrame, line_name: str) -> go.Figure:
    """30-day avg delay trend line with on-time % overlay."""
    sorted_df = df.sort("date")
    dates = sorted_df["date"].to_list()
    delays = sorted_df["avg_delay"].to_list()
    on_time = sorted_df["on_time_pct"].to_list()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=delays,
        name="Avg Delay (min)",
        line={"color": _COLORS.get(line_name, "#457B9D"), "width": 2},
        hovertemplate="%{x}<br>Delay: %{y:.1f} min<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=on_time,
        name="On-Time %",
        yaxis="y2",
        line={"color": "#2A9D8F", "width": 2, "dash": "dot"},
        hovertemplate="%{x}<br>On-time: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=f"{line_name} Line — 30-Day Delay Trend",
        xaxis_title="Date",
        yaxis={"title": "Avg Delay (min)"},
        yaxis2={"title": "On-Time %", "overlaying": "y", "side": "right"},
        legend={"bgcolor": "rgba(0,0,0,0)"},
        **_dark_layout(),
    )
    return fig


def make_anomaly_cards_data(results: list[AnomalyResult]) -> list[dict[str, Any]]:
    """Convert anomaly results to card data dicts. Returns only anomalous stations."""
    severity_order = {"HIGH": 0, "MEDIUM": 1, "NORMAL": 2}
    anomalies = [r for r in results if r.is_anomaly]
    anomalies.sort(key=lambda r: severity_order.get(r.severity, 3))
    return [
        {
            "station": r.station,
            "actual_delay": r.actual_delay,
            "expected_delay": r.expected_delay,
            "upper_bound": r.upper_bound,
            "is_anomaly": r.is_anomaly,
            "severity": r.severity,
            "excess_pct": round((r.actual_delay - r.expected_delay) / max(r.expected_delay, 0.1) * 100, 1),
        }
        for r in anomalies
    ]


def make_business_insights(store: Any) -> dict[str, Any]:
    """Compute plain-English business insight stats."""
    try:
        worst_central = store.worst_stations("Central", n=1)
        worst_station = worst_central["station_name"][0] if len(worst_central) > 0 else "N/A"
        worst_delay = float(worst_central["mean_delay"][0]) if len(worst_central) > 0 else 0.0
    except Exception:
        worst_station, worst_delay = "N/A", 0.0

    try:
        from analysis.rankings import line_summary
        summary = line_summary(store)
        best_line_row = summary.sort("avg_delay").head(1)
        best_line = best_line_row["line"][0] if len(best_line_row) > 0 else "N/A"
        best_line_delay = float(best_line_row["avg_delay"][0]) if len(best_line_row) > 0 else 0.0
    except Exception:
        best_line, best_line_delay = "N/A", 0.0

    delay_minutes_per_day = worst_delay * 15 * 3000 * 8 / 60

    return {
        "worst_station": worst_station,
        "worst_station_delay": round(worst_delay, 1),
        "best_line": best_line,
        "best_line_delay": round(best_line_delay, 1),
        "peak_window": "Monday 8-9 AM",
        "delay_hours_per_day": round(delay_minutes_per_day, 0),
        "commuters_affected": "7.5M daily",
    }
