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

    def close(self) -> None:
        self.conn.close()
