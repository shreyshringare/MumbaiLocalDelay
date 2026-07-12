"""Delay data endpoints: heatmap, rankings, line trend."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from analysis.rankings import peak_rankings
from api.deps import get_store
from api.schemas import HeatmapResponse, LineTrendPoint, RankingEntry
from pipeline.store import DelayStore

router = APIRouter(tags=["delays"])


@router.get("/heatmap", response_model=HeatmapResponse)
def get_heatmap(
    station: str = Query(default="Dadar CR", description="Station name"),
    store: DelayStore = Depends(get_store),  # noqa: B008
) -> HeatmapResponse:
    """7×24 delay heatmap (weekday × hour) for a station."""
    df = store.heatmap(station)

    # Build a guaranteed 7×24 matrix (None where no data)
    matrix: list[list[float | None]] = [[None] * 24 for _ in range(7)]
    for row in df.iter_rows(named=True):
        wd = int(row["weekday"])
        hr = int(row["hour"])
        if 0 <= wd < 7 and 0 <= hr < 24:
            val = row["avg_delay"]
            matrix[wd][hr] = float(val) if val is not None else None

    return HeatmapResponse(station=station, matrix=matrix)


@router.get("/rankings", response_model=list[RankingEntry])
def get_rankings(
    line: str = Query(default="Central", description="Line name: Central, Western, or Harbour"),
    period: str = Query(default="morning_peak", description="Period: morning_peak, evening_peak, off_peak, night"),
    store: DelayStore = Depends(get_store),  # noqa: B008
) -> list[RankingEntry]:
    """Top stations by avg delay for a specific line and period."""
    df = peak_rankings(store, line, period)
    results: list[RankingEntry] = []
    for row in df.iter_rows(named=True):
        results.append(
            RankingEntry(
                station_name=row["station_name"],
                line=line,
                avg_delay=float(row["avg_delay"]) if row["avg_delay"] is not None else 0.0,
                ci_lower=float(row["ci_lower"]) if row.get("ci_lower") is not None else None,
                ci_upper=float(row["ci_upper"]) if row.get("ci_upper") is not None else None,
            )
        )
    return results


@router.get("/line-trend", response_model=list[LineTrendPoint])
def get_line_trend(
    line: str = Query(default="Central", description="Line name: Central, Western, or Harbour"),
    store: DelayStore = Depends(get_store),  # noqa: B008
) -> list[LineTrendPoint]:
    """30-day avg delay trend for a line."""
    df = store.line_trend(line)
    results: list[LineTrendPoint] = []
    for row in df.iter_rows(named=True):
        results.append(
            LineTrendPoint(
                date=str(row["date"]),
                line=line,
                avg_delay=float(row["avg_delay"]) if row["avg_delay"] is not None else 0.0,
            )
        )
    return results
