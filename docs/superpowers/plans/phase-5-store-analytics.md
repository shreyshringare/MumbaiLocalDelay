# Phase 5: DuckDB Store + Core Analytics — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist clean delay data in DuckDB, expose query methods for all dashboard data needs, and build a SQL analytics layer showcasing window functions, CTEs, and percentile queries — the exact SQL patterns asked in JPM/MS/Nomura interviews.

**Architecture:** `DelayStore` owns the DuckDB connection and exposes typed query methods. `analysis/delays.py` computes the station × hour delay matrix. `analysis/rankings.py` computes worst/best stations and line comparisons. `analysis/sql_queries.py` contains advanced SQL patterns as documented, runnable queries.

**Tech Stack:** Python 3.12, DuckDB 1.x, Polars 1.x

---

## File Structure

```
pipeline/
├── store.py              # DuckDB connection + upsert + queries
analysis/
├── delays.py             # Delay matrix computation
├── rankings.py           # Worst/best rankings + line comparison
├── sql_queries.py        # SQL analytics showcase (interview-ready)
tests/
├── test_store.py         # Integration tests (real DuckDB)
```

---

### Task 1: Write test_store.py (failing first)

**Files:**
- Create: `tests/test_store.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Integration tests for DelayStore — uses real DuckDB (no mocking)."""
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from pipeline.store import DelayStore


@pytest.fixture
def store(tmp_path: Path) -> DelayStore:
    return DelayStore(db_path=str(tmp_path / "test.duckdb"))


@pytest.fixture
def sample_df() -> pl.DataFrame:
    return pl.DataFrame({
        "date": [date(2024, 1, 1), date(2024, 1, 1), date(2024, 1, 2)],
        "station_name": ["Dadar", "Thane", "Dadar"],
        "line": ["Central", "Central", "Central"],
        "hour": [8, 8, 8],
        "weekday": [0, 0, 1],
        "period": ["morning_peak", "morning_peak", "morning_peak"],
        "avg_delay": [6.5, 4.2, 7.1],
        "std_delay": [2.1, 1.8, 2.3],
        "sample_count": [15, 15, 15],
        "ci_lower": [5.4, 3.3, 5.9],
        "ci_upper": [7.6, 5.1, 8.3],
        "on_time_pct": [32.5, 55.0, 28.1],
    })


class TestDelayStore:
    def test_schema_created_on_init(self, store: DelayStore) -> None:
        tables = store.conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert "delays" in table_names

    def test_upsert_inserts_rows(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        count = store.conn.execute("SELECT COUNT(*) FROM delays").fetchone()[0]
        assert count == 3

    def test_upsert_idempotent(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        """Same data inserted twice should not duplicate rows."""
        store.upsert(sample_df)
        store.upsert(sample_df)
        count = store.conn.execute("SELECT COUNT(*) FROM delays").fetchone()[0]
        assert count == 3

    def test_worst_stations_returns_polars(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = store.worst_stations(line="Central", n=5)
        assert isinstance(result, pl.DataFrame)

    def test_worst_stations_sorted_by_delay(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = store.worst_stations(line="Central", n=10)
        delays = result["mean_delay"].to_list()
        assert delays == sorted(delays, reverse=True)

    def test_heatmap_returns_matrix(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = store.heatmap(station="Dadar")
        assert isinstance(result, pl.DataFrame)
        assert "hour" in result.columns
        assert "weekday" in result.columns
        assert "avg_delay" in result.columns

    def test_line_trend_returns_30_days(self, store: DelayStore) -> None:
        # Insert 35 days of data
        rows = []
        for day in range(35):
            from datetime import timedelta
            d = date(2024, 1, 1) + timedelta(days=day)
            rows.append({
                "date": d, "station_name": "Dadar", "line": "Central",
                "hour": 8, "weekday": day % 7, "period": "morning_peak",
                "avg_delay": 5.0, "std_delay": 2.0, "sample_count": 15,
                "ci_lower": 4.0, "ci_upper": 6.0, "on_time_pct": 40.0,
            })
        store.upsert(pl.DataFrame(rows))
        result = store.line_trend(line="Central", days=30)
        assert len(result) == 30

    def test_data_quality_report(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        report = store.data_quality_report()
        assert isinstance(report, pl.DataFrame)
        assert "station_name" in report.columns
        assert "last_updated" in report.columns
        assert "row_count" in report.columns
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_store.py -v
```

Expected: `ImportError: cannot import name 'DelayStore' from 'pipeline.store'`

---

### Task 2: Implement pipeline/store.py

**Files:**
- Create: `pipeline/store.py`

- [ ] **Step 1: Write the module**

```python
"""DuckDB analytical store for Mumbai local delay data."""
from pathlib import Path

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
        self.conn.execute("""
            INSERT OR REPLACE INTO delays
            SELECT * FROM _upsert_df
        """)
        self.conn.unregister("_upsert_df")

    def worst_stations(self, line: str, n: int = 10) -> pl.DataFrame:
        """Top N stations by mean avg_delay for a given line."""
        result = self.conn.execute("""
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
        """, [line, n]).arrow()
        return pl.from_arrow(result)

    def best_stations(self, line: str, n: int = 10) -> pl.DataFrame:
        """Bottom N stations by mean avg_delay for a given line."""
        result = self.conn.execute("""
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
        """, [line, n]).arrow()
        return pl.from_arrow(result)

    def heatmap(self, station: str) -> pl.DataFrame:
        """Station delay heatmap: hour × weekday → avg_delay with CI."""
        result = self.conn.execute("""
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
        """, [station]).arrow()
        return pl.from_arrow(result)

    def line_trend(self, line: str, days: int = 30) -> pl.DataFrame:
        """Daily avg delay trend for a line over last N days."""
        result = self.conn.execute("""
            SELECT
                date,
                AVG(avg_delay)   AS avg_delay,
                AVG(on_time_pct) AS on_time_pct
            FROM delays
            WHERE line = ?
            AND date >= (SELECT MAX(date) FROM delays) - (? * INTERVAL '1 day')
            GROUP BY date
            ORDER BY date DESC
            LIMIT ?
        """, [line, days - 1, days]).arrow()
        return pl.from_arrow(result)

    def peak_comparison(self, station: str) -> pl.DataFrame:
        """Morning peak vs evening peak vs off-peak delay for a station."""
        result = self.conn.execute("""
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
        """, [station]).arrow()
        return pl.from_arrow(result)

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
        return pl.from_arrow(result)

    def close(self) -> None:
        self.conn.close()
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_store.py -v
```

Expected: all PASSED.

- [ ] **Step 3: Lint and type check**

```bash
uv run ruff check pipeline/store.py
uv run mypy pipeline/store.py
```

- [ ] **Step 4: Commit**

```bash
git add pipeline/store.py tests/test_store.py
git commit -m "feat(store): DuckDB analytical store with typed query methods"
```

---

### Task 3: Implement analysis/delays.py and analysis/rankings.py

**Files:**
- Create: `analysis/delays.py`
- Create: `analysis/rankings.py`

- [ ] **Step 1: Write analysis/delays.py**

```python
"""Core delay analytics: station × hour delay matrix."""
import polars as pl

from pipeline.store import DelayStore


def station_delay_matrix(store: DelayStore, line: str | None = None) -> pl.DataFrame:
    """Compute delay heatmap matrix: station × hour, averaged across all days.

    Args:
        store: DelayStore instance
        line: optional filter by line (Central/Western/Harbour)

    Returns:
        DataFrame with columns [station_name, hour, avg_delay, ci_lower, ci_upper]
    """
    where_clause = "WHERE line = ?" if line else ""
    params = [line] if line else []

    result = store.conn.execute(f"""
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
    """, params).arrow()
    return pl.from_arrow(result)


def worst_hours(store: DelayStore, station: str) -> pl.DataFrame:
    """Top 5 worst hours for a station with CI."""
    result = store.conn.execute("""
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
    """, [station]).arrow()
    return pl.from_arrow(result)
```

- [ ] **Step 2: Write analysis/rankings.py**

```python
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
    return pl.from_arrow(result)


def peak_rankings(store: DelayStore, line: str, period: str, n: int = 10) -> pl.DataFrame:
    """Worst N stations for a specific period and line."""
    result = store.conn.execute("""
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
    """, [line, period, n]).arrow()
    return pl.from_arrow(result)
```

- [ ] **Step 3: Commit**

```bash
git add analysis/delays.py analysis/rankings.py
git commit -m "feat(analysis): delay matrix and route ranking queries"
```

---

### Task 4: Implement analysis/sql_queries.py — SQL showcase

This file is the interview SQL portfolio. Every query is documented with the SQL concept it demonstrates.

**Files:**
- Create: `analysis/sql_queries.py`

- [ ] **Step 1: Write the module**

```python
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
    return pl.from_arrow(result)


def rolling_7day_avg(store: DelayStore, line: str) -> pl.DataFrame:
    """WINDOW FUNCTION: 7-day rolling average delay per line.

    SQL concept: AVG() OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
    Interview context: "Compute rolling 7-day average sales"
    """
    result = store.conn.execute("""
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
    """, [line]).arrow()
    return pl.from_arrow(result)


def percentile_delays_per_station(store: DelayStore, line: str) -> pl.DataFrame:
    """PERCENTILE: p50, p90, p95 delays per station.

    SQL concept: PERCENTILE_CONT() WITHIN GROUP (ORDER BY ...)
    Interview context: "Find p99 latency per API endpoint"
    """
    result = store.conn.execute("""
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
    """, [line]).arrow()
    return pl.from_arrow(result)


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
    return pl.from_arrow(result)


def week_over_week_change(store: DelayStore, line: str) -> pl.DataFrame:
    """CTE + LAG: week-over-week delay change per line.

    SQL concept: LAG() window function, multi-step CTE
    Interview context: "Compare this week's revenue to last week"
    """
    result = store.conn.execute("""
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
    """, [line]).arrow()
    return pl.from_arrow(result)


def top_n_per_group(store: DelayStore, n: int = 3) -> pl.DataFrame:
    """CTE + RANK: top N worst stations per line (classic interview question).

    SQL concept: ROW_NUMBER() for top-N per group
    Interview context: "Find top 3 products by revenue in each category"
    """
    result = store.conn.execute("""
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
    """, [n]).arrow()
    return pl.from_arrow(result)
```

- [ ] **Step 2: Commit**

```bash
git add analysis/sql_queries.py
git commit -m "feat(analysis): SQL analytics showcase — window functions, CTEs, percentiles"
```

---

### Task 5: Manual verification with real data

Requires Phase 3 + 4 to have run (delays_clean.parquet must exist).

- [ ] **Step 1: Load processed data into DuckDB**

```bash
uv run python -c "
import os
from pathlib import Path
import polars as pl
from dotenv import load_dotenv
from pipeline.store import DelayStore

load_dotenv()
store = DelayStore(os.getenv('DUCKDB_PATH', 'delays.duckdb'))
df = pl.read_parquet('data/processed/delays_clean.parquet')
store.upsert(df)
count = store.conn.execute('SELECT COUNT(*) FROM delays').fetchone()[0]
print(f'Loaded {count:,} rows into DuckDB')
store.close()
"
```

- [ ] **Step 2: Spot-check worst stations**

```bash
uv run python -c "
from pipeline.store import DelayStore
store = DelayStore('delays.duckdb')
print(store.worst_stations('Central', n=5))
store.close()
"
```

- [ ] **Step 3: Spot-check SQL showcase**

```bash
uv run python -c "
from pipeline.store import DelayStore
from analysis.sql_queries import top_n_per_group, percentile_delays_per_station

store = DelayStore('delays.duckdb')
print('=== Top 3 per line ===')
print(top_n_per_group(store, n=3))
print()
print('=== Percentiles: Central ===')
print(percentile_delays_per_station(store, 'Central').head(5))
store.close()
"
```
