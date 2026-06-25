"""DuckDB analytical store for Mumbai local delay data."""

import duckdb
import polars as pl


class DelayStore:
    """Manages the DuckDB analytical database for delay data."""

    def __init__(self, db_path: str = "delays.duckdb") -> None:
        self.conn = duckdb.connect(db_path)
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS delays (
                date DATE,
                station_name VARCHAR,
                line VARCHAR,
                hour INTEGER,
                weekday INTEGER,
                period VARCHAR,
                avg_delay FLOAT,
                std_delay FLOAT,
                sample_count INTEGER,
                ci_lower FLOAT,
                ci_upper FLOAT,
                on_time_pct FLOAT,
                PRIMARY KEY (date, station_name, hour)
            )
        """)

    def upsert(self, df: pl.DataFrame) -> None:
        """Insert or replace rows (idempotent via PRIMARY KEY)."""
        arrow_table = df.to_arrow()
        self.conn.register("_upsert_df", arrow_table)
        try:
            self.conn.execute("""
                INSERT INTO delays
                SELECT * FROM _upsert_df
                ON CONFLICT (date, station_name, hour) DO UPDATE SET
                    line = EXCLUDED.line,
                    weekday = EXCLUDED.weekday,
                    period = EXCLUDED.period,
                    avg_delay = EXCLUDED.avg_delay,
                    std_delay = EXCLUDED.std_delay,
                    sample_count = EXCLUDED.sample_count,
                    ci_lower = EXCLUDED.ci_lower,
                    ci_upper = EXCLUDED.ci_upper,
                    on_time_pct = EXCLUDED.on_time_pct
            """)
        finally:
            self.conn.unregister("_upsert_df")

    def worst_stations(self, line: str, n: int = 10) -> pl.DataFrame:
        """Top N stations by mean avg_delay for a given line."""
        result = self.conn.execute(
            """
            SELECT
                station_name,
                AVG(avg_delay) AS mean_delay,
                MAX(avg_delay) AS max_delay,
                AVG(ci_lower)  AS mean_ci_lower,
                AVG(ci_upper)  AS mean_ci_upper,
                AVG(on_time_pct) AS mean_on_time_pct
            FROM delays
            WHERE line = ?
            GROUP BY station_name
            ORDER BY mean_delay DESC
            LIMIT ?
        """,
            [line, n],
        ).arrow()
        df = pl.from_arrow(result)
        assert isinstance(df, pl.DataFrame)
        return df

    def best_stations(self, line: str, n: int = 10) -> pl.DataFrame:
        """Bottom N stations by mean avg_delay for a given line."""
        result = self.conn.execute(
            """
            SELECT
                station_name,
                AVG(avg_delay)   AS mean_delay,
                MIN(avg_delay)   AS min_delay,
                AVG(ci_lower)    AS mean_ci_lower,
                AVG(ci_upper)    AS mean_ci_upper,
                AVG(on_time_pct) AS mean_on_time_pct
            FROM delays
            WHERE line = ?
            GROUP BY station_name
            ORDER BY mean_delay ASC
            LIMIT ?
        """,
            [line, n],
        ).arrow()
        df = pl.from_arrow(result)
        assert isinstance(df, pl.DataFrame)
        return df

    def heatmap(self, station: str) -> pl.DataFrame:
        """Station delay heatmap: hour x weekday -> avg_delay with CI."""
        result = self.conn.execute(
            """
            SELECT
                hour,
                weekday,
                AVG(avg_delay) AS avg_delay,
                AVG(ci_lower)  AS ci_lower,
                AVG(ci_upper)  AS ci_upper,
                COUNT(*)       AS n_records
            FROM delays
            WHERE station_name = ?
            GROUP BY hour, weekday
            ORDER BY weekday, hour
        """,
            [station],
        ).arrow()
        df = pl.from_arrow(result)
        assert isinstance(df, pl.DataFrame)
        return df

    def wave_data(self, line: str, n: int = 15) -> pl.DataFrame:
        """Per-hour avg delay for top N stations on a line.

        Returns one row per station with columns: station_name, line_order,
        hour_0 … hour_23. line_order is rank by all-time avg delay (0 = worst).
        """
        result = self.conn.execute(
            """
            WITH ranked AS (
                SELECT
                    station_name,
                    ROW_NUMBER() OVER (ORDER BY AVG(avg_delay) DESC) - 1 AS line_order
                FROM delays
                WHERE line = ?
                GROUP BY station_name
                ORDER BY AVG(avg_delay) DESC
                LIMIT ?
            ),
            hourly AS (
                SELECT
                    d.station_name,
                    d.hour,
                    AVG(d.avg_delay) AS avg_delay
                FROM delays d
                INNER JOIN ranked r ON d.station_name = r.station_name
                WHERE d.line = ?
                GROUP BY d.station_name, d.hour
            )
            SELECT
                r.station_name,
                r.line_order,
                MAX(CASE WHEN h.hour = 0  THEN h.avg_delay ELSE 0 END) AS hour_0,
                MAX(CASE WHEN h.hour = 1  THEN h.avg_delay ELSE 0 END) AS hour_1,
                MAX(CASE WHEN h.hour = 2  THEN h.avg_delay ELSE 0 END) AS hour_2,
                MAX(CASE WHEN h.hour = 3  THEN h.avg_delay ELSE 0 END) AS hour_3,
                MAX(CASE WHEN h.hour = 4  THEN h.avg_delay ELSE 0 END) AS hour_4,
                MAX(CASE WHEN h.hour = 5  THEN h.avg_delay ELSE 0 END) AS hour_5,
                MAX(CASE WHEN h.hour = 6  THEN h.avg_delay ELSE 0 END) AS hour_6,
                MAX(CASE WHEN h.hour = 7  THEN h.avg_delay ELSE 0 END) AS hour_7,
                MAX(CASE WHEN h.hour = 8  THEN h.avg_delay ELSE 0 END) AS hour_8,
                MAX(CASE WHEN h.hour = 9  THEN h.avg_delay ELSE 0 END) AS hour_9,
                MAX(CASE WHEN h.hour = 10 THEN h.avg_delay ELSE 0 END) AS hour_10,
                MAX(CASE WHEN h.hour = 11 THEN h.avg_delay ELSE 0 END) AS hour_11,
                MAX(CASE WHEN h.hour = 12 THEN h.avg_delay ELSE 0 END) AS hour_12,
                MAX(CASE WHEN h.hour = 13 THEN h.avg_delay ELSE 0 END) AS hour_13,
                MAX(CASE WHEN h.hour = 14 THEN h.avg_delay ELSE 0 END) AS hour_14,
                MAX(CASE WHEN h.hour = 15 THEN h.avg_delay ELSE 0 END) AS hour_15,
                MAX(CASE WHEN h.hour = 16 THEN h.avg_delay ELSE 0 END) AS hour_16,
                MAX(CASE WHEN h.hour = 17 THEN h.avg_delay ELSE 0 END) AS hour_17,
                MAX(CASE WHEN h.hour = 18 THEN h.avg_delay ELSE 0 END) AS hour_18,
                MAX(CASE WHEN h.hour = 19 THEN h.avg_delay ELSE 0 END) AS hour_19,
                MAX(CASE WHEN h.hour = 20 THEN h.avg_delay ELSE 0 END) AS hour_20,
                MAX(CASE WHEN h.hour = 21 THEN h.avg_delay ELSE 0 END) AS hour_21,
                MAX(CASE WHEN h.hour = 22 THEN h.avg_delay ELSE 0 END) AS hour_22,
                MAX(CASE WHEN h.hour = 23 THEN h.avg_delay ELSE 0 END) AS hour_23
            FROM ranked r
            LEFT JOIN hourly h ON r.station_name = h.station_name
            GROUP BY r.station_name, r.line_order
            ORDER BY r.line_order
            """,
            [line, n, line],
        ).arrow()
        df = pl.from_arrow(result)
        assert isinstance(df, pl.DataFrame)
        return df

    def line_trend(self, line: str, days: int = 30) -> pl.DataFrame:
        """Daily avg delay trend for a line over last N days."""
        result = self.conn.execute(
            """
            SELECT
                date,
                AVG(avg_delay)   AS avg_delay,
                AVG(on_time_pct) AS on_time_pct
            FROM delays
            WHERE line = ?
            GROUP BY date
            ORDER BY date DESC
            LIMIT ?
        """,
            [line, days],
        ).arrow()
        df = pl.from_arrow(result)
        assert isinstance(df, pl.DataFrame)
        return df

    def peak_comparison(self, station: str) -> pl.DataFrame:
        """Morning peak vs evening peak vs off-peak delay for a station."""
        result = self.conn.execute(
            """
            SELECT
                period,
                AVG(avg_delay)   AS avg_delay,
                AVG(ci_lower)    AS ci_lower,
                AVG(ci_upper)    AS ci_upper,
                AVG(on_time_pct) AS on_time_pct,
                COUNT(*)         AS n_records
            FROM delays
            WHERE station_name = ?
            GROUP BY period
            ORDER BY avg_delay DESC
        """,
            [station],
        ).arrow()
        df = pl.from_arrow(result)
        assert isinstance(df, pl.DataFrame)
        return df

    def data_quality_report(self) -> pl.DataFrame:
        """Data freshness and completeness per station."""
        result = self.conn.execute("""
            SELECT
                station_name,
                MAX(date)    AS last_updated,
                COUNT(*)     AS row_count,
                MIN(date)    AS first_date,
                COUNT(DISTINCT date) AS unique_dates
            FROM delays
            GROUP BY station_name
            ORDER BY last_updated DESC
        """).arrow()
        df = pl.from_arrow(result)
        assert isinstance(df, pl.DataFrame)
        return df

    def daily_avg(self, station: str) -> pl.DataFrame:
        """Daily avg delay for a station (all hours aggregated). Used by forecasting.

        Uses .pl() instead of .arrow()+from_arrow() because .arrow() raises on empty
        results (unknown station) — .pl() handles the empty case correctly.
        """
        df = self.conn.execute(
            """
            SELECT
                date,
                AVG(avg_delay) AS avg_delay
            FROM delays
            WHERE station_name = ?
            GROUP BY date
            ORDER BY date
            """,
            [station],
        ).pl()
        assert isinstance(df, pl.DataFrame)
        return df

    def peak_window(self) -> str:
        """Return highest-delay weekday+hour as 'Weekday H-H+1 AM/PM'."""
        _DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        result = self.conn.execute("""
            SELECT weekday, hour, AVG(avg_delay) AS avg_delay
            FROM delays
            GROUP BY weekday, hour
            ORDER BY avg_delay DESC
            LIMIT 1
        """).fetchone()
        if result is None:
            return "N/A"
        wd, hr = int(result[0]), int(result[1])
        day = _DAYS[wd] if 0 <= wd < 7 else "Unknown"
        am_pm = "AM" if hr < 12 else "PM"
        display_hr = hr if hr <= 12 else hr - 12
        return f"{day} {display_hr}-{display_hr + 1} {am_pm}"

    def close(self) -> None:
        self.conn.close()
