"""Analytical endpoints: anomalies, correlation, forecast."""

from __future__ import annotations

import datetime
import threading
from typing import Any

import polars as pl
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from analysis.anomaly import AnomalyBatch
from analysis.correlation import station_correlation
from analysis.forecasting import ForecastCache
from api.deps import get_store
from api.schemas import AnomalyEntry, ForecastPoint
from pipeline.store import DelayStore

router = APIRouter(tags=["analysis"])

# Module-level ForecastCache — shared across requests, built once in lifespan
_forecast_cache: ForecastCache = ForecastCache()


def get_forecast_cache() -> ForecastCache:
    return _forecast_cache


def start_forecast_cache(store: DelayStore) -> None:
    """Kick off background forecast building. Called from lifespan."""
    thread = threading.Thread(target=_forecast_cache.build, args=(store,), daemon=True)
    thread.start()


@router.get("/anomalies", response_model=list[AnomalyEntry])
def get_anomalies(
    store: DelayStore = Depends(get_store),
) -> list[AnomalyEntry]:
    """Anomaly detection across top 5 stations per line (Central, Western, Harbour)."""
    lines = ["Central", "Western", "Harbour"]
    top_stations: list[str] = []
    for line in lines:
        try:
            df = store.worst_stations(line, n=5)
            top_stations.extend(df["station_name"].to_list())
        except Exception:
            continue

    if not top_stations:
        return []

    # Build history from daily_avg for each top station
    history_parts: list[pl.DataFrame] = []
    for station in top_stations:
        try:
            daily = store.daily_avg(station)
            if len(daily) == 0:
                continue
            daily = daily.with_columns(pl.lit(station).alias("station_name"))
            # Ensure date column is a string for consistent schema
            daily = daily.with_columns(pl.col("date").cast(pl.Utf8).alias("date"))
            history_parts.append(daily)
        except Exception:
            continue

    if not history_parts:
        return []

    history = pl.concat(history_parts)

    # Use today's snapshot — latest available date per station
    today_parts: list[pl.DataFrame] = []
    for station in top_stations:
        station_hist = history.filter(pl.col("station_name") == station)
        if len(station_hist) == 0:
            continue
        latest = station_hist.sort("date").tail(1)
        today_parts.append(latest)

    if not today_parts:
        return []

    today = pl.concat(today_parts)

    try:
        batch = AnomalyBatch(history=history)
        results = batch.detect_all(today)
    except Exception:
        return []

    today_str = str(datetime.date.today())
    entries: list[AnomalyEntry] = []
    for r in results:
        entries.append(
            AnomalyEntry(
                station=r.station,
                severity=r.severity,
                actual=r.actual_delay,
                expected=r.expected_delay,
                upper=r.upper_bound,
                date=today_str,
            )
        )
    return entries


@router.get("/correlation")
def get_correlation(
    line: str = Query(default="Central", description="Line name: Central, Western, or Harbour"),
    store: DelayStore = Depends(get_store),
) -> dict[str, Any]:
    """Pearson r correlation matrix for top-15 stations on a line."""
    try:
        stations, matrix = station_correlation(store, line)
        return {"stations": stations, "matrix": matrix}
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "stations": [], "matrix": []},
        )


@router.get("/forecast")
def get_forecast(
    station: str = Query(default="Dadar CR", description="Station name"),
) -> Any:
    """7-day Prophet forecast for a station. Returns 202 if still computing."""
    cache = get_forecast_cache()
    result = cache.get(station)

    if result is None:
        return JSONResponse(status_code=202, content={"status": "computing"})

    try:
        _history_df, forecast_df = result
        points: list[ForecastPoint] = []
        # forecast_df is a pandas DataFrame (returned by Prophet); use iterrows()
        for _, row in forecast_df.iterrows():
            points.append(
                ForecastPoint(
                    ds=str(row["ds"])[:10],  # YYYY-MM-DD
                    yhat=float(row["yhat"]),
                    yhat_lower=float(row["yhat_lower"]),
                    yhat_upper=float(row["yhat_upper"]),
                )
            )
        return points
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )
