"""SQL analytics showcase for Mumbai local delay data.

Each function demonstrates a specific SQL concept relevant to
DA/DE interviews at JPM, Morgan Stanley, Nomura, Barclays, etc.

All queries use DuckDB SQL dialect.
"""

import polars as pl

from pipeline.store import DelayStore


def ranked_stations_per_line(store: DelayStore) -> pl.DataFrame:
    """WINDOW FUNCTION: RANK() to rank stations within each line.

    SQL concept: RANK() OVER (PARTITION BY ... ORDER BY ...)
    Interview context: "Rank employees by salary within department"
    """
    result = store.conn.execute("""
        WITH station_avgs AS (
            SELECT
                station_name,
                line,
                AVG(avg_delay) AS avg_delay
            FROM delays
            GROUP BY station_name, line
        )
        SELECT
            station_name,
            line,
            avg_delay,
            RANK() OVER (
                PARTITION BY line
                ORDER BY avg_delay DESC
            ) AS delay_rank
        FROM station_avgs
        ORDER BY line, delay_rank
    """).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def rolling_7day_avg(store: DelayStore, line: str) -> pl.DataFrame:
    """WINDOW FUNCTION: 7-day rolling average delay per line.

    SQL concept: AVG() OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
    Interview context: "Compute rolling 7-day average sales"
    """
    result = store.conn.execute(
        """
        WITH daily AS (
            SELECT
                date,
                line,
                AVG(avg_delay) AS daily_avg
            FROM delays
            WHERE line = ?
            GROUP BY date, line
        )
        SELECT
            date,
            line,
            daily_avg,
            AVG(daily_avg) OVER (
                ORDER BY date
                ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
            ) AS rolling_7d_avg
        FROM daily
        ORDER BY date
    """,
        [line],
    ).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def percentile_delays_per_station(store: DelayStore, line: str) -> pl.DataFrame:
    """PERCENTILE: p50, p90, p95 delays per station.

    SQL concept: PERCENTILE_CONT() WITHIN GROUP (ORDER BY ...)
    Interview context: "Find p99 latency per API endpoint"
    """
    result = store.conn.execute(
        """
        SELECT
            station_name,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY avg_delay) AS p50_delay,
            PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY avg_delay) AS p90_delay,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY avg_delay) AS p95_delay,
            MAX(avg_delay) AS max_delay
        FROM delays
        WHERE line = ?
        GROUP BY station_name
        ORDER BY p95_delay DESC
    """,
        [line],
    ).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def conditional_aggregation_peak_vs_offpeak(store: DelayStore) -> pl.DataFrame:
    """CONDITIONAL AGGREGATION: pivot peak vs off-peak in one query.

    SQL concept: AVG(CASE WHEN ... THEN ... END)
    Interview context: "Compare metric A vs metric B in a single query"
    """
    result = store.conn.execute("""
        SELECT
            station_name,
            line,
            AVG(CASE WHEN period = 'morning_peak'  THEN avg_delay END) AS morning_peak_delay,
            AVG(CASE WHEN period = 'evening_peak'  THEN avg_delay END) AS evening_peak_delay,
            AVG(CASE WHEN period = 'off_peak'      THEN avg_delay END) AS offpeak_delay,
            AVG(avg_delay)                                               AS overall_delay
        FROM delays
        GROUP BY station_name, line
        ORDER BY overall_delay DESC
    """).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def week_over_week_change(store: DelayStore, line: str) -> pl.DataFrame:
    """CTE + LAG: week-over-week delay change per line.

    SQL concept: LAG() window function, multi-step CTE
    Interview context: "Compare this week's revenue to last week"
    """
    result = store.conn.execute(
        """
        WITH weekly AS (
            SELECT
                DATE_TRUNC('week', date) AS week_start,
                line,
                AVG(avg_delay)           AS weekly_avg
            FROM delays
            WHERE line = ?
            GROUP BY DATE_TRUNC('week', date), line
        ),
        with_prev AS (
            SELECT
                week_start,
                line,
                weekly_avg,
                LAG(weekly_avg) OVER (ORDER BY week_start) AS prev_week_avg
            FROM weekly
        )
        SELECT
            week_start,
            line,
            weekly_avg,
            prev_week_avg,
            ROUND(
                (weekly_avg - prev_week_avg) / NULLIF(prev_week_avg, 0) * 100,
                2
            ) AS pct_change
        FROM with_prev
        ORDER BY week_start DESC
    """,
        [line],
    ).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def top_n_per_group(store: DelayStore, n: int = 3) -> pl.DataFrame:
    """CTE + RANK: top N worst stations per line (classic interview question).

    SQL concept: ROW_NUMBER() for top-N per group
    Interview context: "Find top 3 products by revenue in each category"
    """
    result = store.conn.execute(
        """
        WITH station_avgs AS (
            SELECT
                station_name,
                line,
                AVG(avg_delay) AS avg_delay
            FROM delays
            GROUP BY station_name, line
        ),
        ranked AS (
            SELECT
                station_name,
                line,
                avg_delay,
                ROW_NUMBER() OVER (
                    PARTITION BY line
                    ORDER BY avg_delay DESC
                ) AS rn
            FROM station_avgs
        )
        SELECT station_name, line, avg_delay, rn AS rank
        FROM ranked
        WHERE rn <= ?
        ORDER BY line, rn
    """,
        [n],
    ).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df
