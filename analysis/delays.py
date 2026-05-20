"""Core delay analytics: station x hour delay matrix."""

import polars as pl

from pipeline.store import DelayStore


def station_delay_matrix(store: DelayStore, line: str | None = None) -> pl.DataFrame:
    """Compute delay heatmap matrix: station x hour, averaged across all days.

    Args:
        store: DelayStore instance
        line: optional filter by line (Central/Western/Harbour)

    Returns:
        DataFrame with columns [station_name, hour, avg_delay, ci_lower, ci_upper]
    """
    where_clause = "WHERE line = ?" if line else ""
    params: list[str] = [line] if line else []

    result = store.conn.execute(
        f"""
        SELECT
            station_name,
            hour,
            AVG(avg_delay) AS avg_delay,
            AVG(ci_lower)  AS ci_lower,
            AVG(ci_upper)  AS ci_upper,
            COUNT(*)       AS n_records
        FROM delays
        {where_clause}
        GROUP BY station_name, hour
        ORDER BY station_name, hour
    """,
        params,
    ).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def worst_hours(store: DelayStore, station: str) -> pl.DataFrame:
    """Top 5 worst hours for a station with CI."""
    result = store.conn.execute(
        """
        SELECT
            hour,
            AVG(avg_delay) AS avg_delay,
            AVG(ci_lower)  AS ci_lower,
            AVG(ci_upper)  AS ci_upper
        FROM delays
        WHERE station_name = ?
        GROUP BY hour
        ORDER BY avg_delay DESC
        LIMIT 5
    """,
        [station],
    ).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df
