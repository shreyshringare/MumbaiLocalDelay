"""Route rankings and line comparison analytics."""

import polars as pl

from pipeline.store import DelayStore


def line_summary(store: DelayStore) -> pl.DataFrame:
    """Summary stats per line: avg delay, on-time %, p95 delay."""
    result = store.conn.execute("""
        SELECT
            line,
            AVG(avg_delay)                    AS avg_delay,
            AVG(on_time_pct)                  AS on_time_pct,
            PERCENTILE_CONT(0.95)
                WITHIN GROUP (ORDER BY avg_delay) AS p95_delay,
            COUNT(DISTINCT station_name)       AS station_count
        FROM delays
        GROUP BY line
        ORDER BY avg_delay DESC
    """).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def peak_rankings(
    store: DelayStore, line: str, period: str, n: int = 10
) -> pl.DataFrame:
    """Worst N stations for a specific period and line."""
    result = store.conn.execute(
        """
        SELECT
            station_name,
            AVG(avg_delay)   AS avg_delay,
            AVG(ci_lower)    AS ci_lower,
            AVG(ci_upper)    AS ci_upper,
            AVG(on_time_pct) AS on_time_pct
        FROM delays
        WHERE line = ?
        AND period = ?
        GROUP BY station_name
        ORDER BY avg_delay DESC
        LIMIT ?
    """,
        [line, period, n],
    ).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df
