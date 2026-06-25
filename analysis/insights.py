"""Business insight computations — pure Python, no Dash/Plotly dependency."""
from __future__ import annotations

from typing import Any


def make_business_insights(store: Any) -> dict[str, Any]:
    """Compute plain-English business insight stats from the delay store."""
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

    # Constants: 15 trains/hr (Mumbai suburban headway) × 3,000 commuters/train
    # (avg loading) × 8 peak hours/day ÷ 60 converts delay-minutes to hours.
    delay_minutes_per_day = worst_delay * 15 * 3000 * 8 / 60

    try:
        peak_window = store.peak_window()
    except Exception:
        peak_window = "N/A"

    return {
        "worst_station": worst_station,
        "worst_station_delay": round(worst_delay, 1),
        "best_line": best_line,
        "best_line_delay": round(best_line_delay, 1),
        "peak_window": peak_window,
        "delay_hours_per_day": round(delay_minutes_per_day, 0),
        "commuters_affected": "7.5M daily",
    }
