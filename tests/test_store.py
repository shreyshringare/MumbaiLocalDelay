"""Integration tests for DelayStore — uses real DuckDB (no mocking)."""
from datetime import date, timedelta
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
        rows = []
        for day in range(35):
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
