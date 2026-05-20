"""Station co-delay Pearson correlation using DuckDB CORR().

Uses a self-join on (date, hour) to find how closely paired stations
co-vary in delay — revealing network cascade patterns.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from pipeline.store import DelayStore


def station_correlation(
    store: DelayStore, line: str, n: int = 15
) -> tuple[list[str], list[list[float]]]:
    """Pearson r matrix for top-N delay stations on a given line.

    Args:
        store: DelayStore instance
        line: "Central", "Western", or "Harbour"
        n: number of stations (top N by mean delay)

    Returns:
        (stations, matrix) where matrix[i][j] = Pearson r between
        station[i] and station[j] delays, matched on same date+hour pairs.
        Diagonal is forced to 1.0. Empty lists if line has < 2 stations.
    """
    try:
        top = store.worst_stations(line, n=n)
    except Exception:
        return [], []
    if len(top) < 2:
        return [], []

    stations = top["station_name"].to_list()
    placeholders = ", ".join(["?" for _ in stations])
    params: list[str] = [line, line] + stations + stations

    result = store.conn.execute(
        f"""
        SELECT
            a.station_name AS station_a,
            b.station_name AS station_b,
            CORR(a.avg_delay, b.avg_delay) AS pearson_r
        FROM delays a
        JOIN delays b ON a.date = b.date AND a.hour = b.hour
        WHERE a.line = ? AND b.line = ?
          AND a.station_name IN ({placeholders})
          AND b.station_name IN ({placeholders})
        GROUP BY a.station_name, b.station_name
        """,
        params,
    ).arrow()
    df = pl.from_arrow(result)

    station_idx = {s: i for i, s in enumerate(stations)}
    n_stations = len(stations)
    matrix: list[list[float]] = [[0.0] * n_stations for _ in range(n_stations)]

    for row in df.iter_rows(named=True):
        i = station_idx.get(row["station_a"])
        j = station_idx.get(row["station_b"])
        if i is not None and j is not None and row["pearson_r"] is not None:
            matrix[i][j] = float(row["pearson_r"])

    for k in range(n_stations):
        matrix[k][k] = 1.0

    return stations, matrix
