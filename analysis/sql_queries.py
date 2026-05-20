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


def yoy_delay_change(store: DelayStore) -> pl.DataFrame:
    """CONDITIONAL AGGREGATION: year-over-year delay change per station.

    SQL concept: conditional aggregation by year + percent difference
    Interview analog: "Compare this year's revenue vs last year by product"
    """
    result = store.conn.execute("""
        SELECT
            station_name,
            line,
            AVG(CASE WHEN YEAR(date) = 2023 THEN avg_delay END) AS avg_2023,
            AVG(CASE WHEN YEAR(date) = 2024 THEN avg_delay END) AS avg_2024,
            ROUND(
                (
                    AVG(CASE WHEN YEAR(date) = 2024 THEN avg_delay END)
                  - AVG(CASE WHEN YEAR(date) = 2023 THEN avg_delay END)
                ) / NULLIF(AVG(CASE WHEN YEAR(date) = 2023 THEN avg_delay END), 0) * 100,
                2
            ) AS yoy_pct_change
        FROM delays
        GROUP BY station_name, line
        HAVING avg_2023 IS NOT NULL AND avg_2024 IS NOT NULL
        ORDER BY yoy_pct_change DESC
    """).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def monsoon_vs_dry_pivot(store: DelayStore) -> pl.DataFrame:
    """CONDITIONAL AGGREGATION: monsoon (Jun-Sep) vs dry season delay pivot.

    SQL concept: CASE WHEN MONTH() pivot — seasonal comparison in one query
    Interview analog: "Compare Q1 vs Q3 performance by region"
    """
    result = store.conn.execute("""
        SELECT
            station_name,
            line,
            AVG(CASE WHEN MONTH(date) IN (6, 7, 8, 9) THEN avg_delay END) AS monsoon_avg,
            AVG(CASE WHEN MONTH(date) NOT IN (6, 7, 8, 9) THEN avg_delay END) AS dry_avg,
            ROUND(
                AVG(CASE WHEN MONTH(date) IN (6, 7, 8, 9) THEN avg_delay END)
              / NULLIF(AVG(CASE WHEN MONTH(date) NOT IN (6, 7, 8, 9) THEN avg_delay END), 0),
                3
            ) AS monsoon_ratio
        FROM delays
        GROUP BY station_name, line
        HAVING monsoon_avg IS NOT NULL AND dry_avg IS NOT NULL
        ORDER BY monsoon_ratio DESC
    """).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df


def rolling_deviation(store: DelayStore, line: str) -> pl.DataFrame:
    """NESTED WINDOW FUNCTIONS: rolling 7-day avg vs 30-day baseline deviation.

    SQL concept: ratio of short-window to long-window rolling average
    Deviation > 1.2 signals a worsening trend worth investigating.
    Interview analog: "Flag products whose 7-day sales deviate >20% from 30-day baseline"
    """
    result = store.conn.execute(
        """
        WITH daily AS (
            SELECT
                date,
                station_name,
                AVG(avg_delay) AS daily_avg
            FROM delays
            WHERE line = ?
            GROUP BY date, station_name
        ),
        windowed AS (
            SELECT
                date,
                station_name,
                daily_avg,
                AVG(daily_avg) OVER (
                    PARTITION BY station_name
                    ORDER BY date
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) AS rolling_7d_avg,
                AVG(daily_avg) OVER (
                    PARTITION BY station_name
                    ORDER BY date
                    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                ) AS baseline_30d_avg
            FROM daily
        )
        SELECT
            date,
            station_name,
            ROUND(rolling_7d_avg, 3)   AS rolling_7d_avg,
            ROUND(baseline_30d_avg, 3) AS baseline_30d_avg,
            ROUND(rolling_7d_avg / NULLIF(baseline_30d_avg, 0), 3) AS deviation_ratio
        FROM windowed
        WHERE baseline_30d_avg IS NOT NULL
        ORDER BY date DESC, deviation_ratio DESC
    """,
        [line],
    ).arrow()
    df = pl.from_arrow(result)
    assert isinstance(df, pl.DataFrame)
    return df
