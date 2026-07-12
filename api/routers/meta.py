"""Metadata/summary endpoints: map data, quality, insights, methodology."""

from __future__ import annotations

import logging
from typing import Any

import polars as pl
from fastapi import APIRouter, Depends, HTTPException

from analysis.insights import make_business_insights
from api.deps import get_store
from api.schemas import InsightsResponse, QualityEntry, StationDelay
from pipeline.store import DelayStore

logger = logging.getLogger(__name__)

router = APIRouter(tags=["meta"])

_STOPS_PATH = "data/raw/stops.parquet"
_LINES = ["Central", "Western", "Harbour"]


def _load_stops() -> pl.DataFrame:
    """Load stops parquet with lat/lon. Returns empty DataFrame on failure."""
    try:
        return pl.read_parquet(_STOPS_PATH)
    except Exception as e:
        logger.warning("Failed to load stops parquet: %s", e)
        return pl.DataFrame({"stop_name": [], "latitude": [], "longitude": []})


@router.get("/map-data", response_model=list[StationDelay])
def get_map_data(
    store: DelayStore = Depends(get_store),  # noqa: B008
) -> list[StationDelay]:
    """Worst 200 stations per line, joined with lat/lon from stops parquet."""
    stops = _load_stops()
    # Build a lookup: stop_name -> (latitude, longitude)
    stop_lookup: dict[str, tuple[float | None, float | None]] = {}
    for row in stops.iter_rows(named=True):
        name = row.get("stop_name") or row.get("name") or ""
        lat = row.get("latitude")
        lon = row.get("longitude")
        stop_lookup[str(name)] = (
            float(lat) if lat is not None else None,
            float(lon) if lon is not None else None,
        )

    results: list[StationDelay] = []
    for line in _LINES:
        try:
            df = store.worst_stations(line, n=200)
        except Exception:
            continue

        for row in df.iter_rows(named=True):
            station_name = row["station_name"]
            # Try exact match first, then partial
            lat, lon = stop_lookup.get(station_name, (None, None))
            if lat is None:
                for stop_name, coords in stop_lookup.items():
                    if station_name in stop_name or stop_name in station_name:
                        lat, lon = coords
                        break

            results.append(
                StationDelay(
                    station_name=station_name,
                    line=line,
                    avg_delay=float(row["mean_delay"]) if row.get("mean_delay") is not None else 0.0,
                    latitude=lat,
                    longitude=lon,
                )
            )
    return results


@router.get("/quality", response_model=list[QualityEntry])
def get_quality(
    store: DelayStore = Depends(get_store),  # noqa: B008
) -> list[QualityEntry]:
    """Data freshness and completeness report per station."""
    df = store.data_quality_report()
    results: list[QualityEntry] = []
    for row in df.iter_rows(named=True):
        last_updated = row.get("last_updated")
        results.append(
            QualityEntry(
                station_name=row["station_name"],
                row_count=int(row["row_count"]),
                unique_dates=int(row["unique_dates"]),
                last_updated=str(last_updated) if last_updated is not None else None,
            )
        )
    return results


@router.get("/insights", response_model=InsightsResponse)
def get_insights(
    store: DelayStore = Depends(get_store),  # noqa: B008
) -> InsightsResponse:
    """High-level business insights derived from the delay dataset."""
    try:
        data = make_business_insights(store)
    except Exception:
        raise HTTPException(status_code=503, detail="Insights unavailable") from None
    return InsightsResponse(
        worst_station=str(data.get("worst_station", "N/A")),
        worst_delay=float(data.get("worst_station_delay", 0.0)),
        best_line=str(data.get("best_line", "N/A")),
        best_line_delay=float(data.get("best_line_delay", 0.0)),
        peak_window=str(data.get("peak_window", "N/A")),
        delay_hours_per_day=float(data.get("delay_hours_per_day", 0.0)),
        commuters_affected=str(data.get("commuters_affected", "N/A")),
    )


@router.get("/methodology")
def get_methodology() -> dict[str, Any]:
    """Static methodology text for the Methodology dashboard tab."""
    return {
        "data_sources": {
            "title": "Data Sources",
            "content": (
                "Delays are simulated using a statistical model calibrated on real "
                "Indian Railways timetable data and published delay research. "
                "Covers Central, Western, and Harbour lines with hourly granularity. "
                "This is NOT live data — see the provenance label on the Dashboard tab."
            ),
        },
        "delay_calculation": {
            "title": "Delay Calculation",
            "content": (
                "avg_delay is the mean delay in minutes across all trains at a station in a "
                "given hour. Delays are measured as the difference between scheduled and "
                "actual arrival times. ci_lower/ci_upper are 95% confidence intervals "
                "computed using a bootstrap approach over the observation window."
            ),
        },
        "anomaly_detection": {
            "title": "Anomaly Detection",
            "content": (
                "Prophet (Facebook/Meta) time-series decomposition is used to model expected "
                "delay patterns including weekly seasonality and Mumbai monsoon seasonality "
                "(June–September uplift). A day is flagged as anomalous when the actual delay "
                "exceeds the yhat_upper confidence bound. Severity: HIGH if actual > 2× upper, "
                "MEDIUM if actual > upper, NORMAL otherwise."
            ),
        },
        "forecasting": {
            "title": "7-Day Forecast",
            "content": (
                "Prophet models are fitted per station using daily avg_delay history "
                "(minimum 30 days required). Forecasts are pre-computed in a background thread "
                "at application startup and cached in memory. The 95% uncertainty interval "
                "(yhat_lower, yhat_upper) reflects Prophet's posterior predictive distribution."
            ),
        },
        "correlation": {
            "title": "Station Correlation",
            "content": (
                "Pearson r is computed between pairs of stations on the same line using "
                "DuckDB's CORR() aggregate, matched on identical (date, hour) pairs. "
                "High positive correlation (r > 0.7) indicates stations whose delays "
                "co-move — a signal of upstream cascade effects in the network."
            ),
        },
        "rankings": {
            "title": "Peak-Period Rankings",
            "content": (
                "Stations are ranked by avg_delay within a time period: morning_peak "
                "(06:00–10:00), evening_peak (17:00–21:00), off_peak (10:00–17:00), "
                "night (21:00–06:00). Rankings use all available history for the selected "
                "line and period."
            ),
        },
        "data_quality": {
            "title": "Data Quality",
            "content": (
                "The quality report shows row count, unique date count, and last updated "
                "timestamp per station. Stations with fewer than 30 unique dates are "
                "excluded from Prophet-based analyses (anomaly detection, forecasting)."
            ),
        },
        "business_impact": {
            "title": "Business Impact Estimation",
            "content": (
                "Passenger-hours lost is estimated as: worst_station_delay × 15 trains/hr "
                "× 3,000 commuters/train × 8 peak hours/day ÷ 60. This is a conservative "
                "lower bound using Mumbai suburban average train loading figures."
            ),
        },
    }
