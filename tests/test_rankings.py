"""Integration tests for analysis.rankings — uses real DuckDB (no mocking)."""
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from analysis.rankings import line_summary, peak_rankings
from pipeline.store import DelayStore


@pytest.fixture
def store(tmp_path: Path) -> DelayStore:
    return DelayStore(db_path=str(tmp_path / "test.duckdb"))


@pytest.fixture
def sample_df() -> pl.DataFrame:
    return pl.DataFrame({
        "date": [date(2024, 1, 1)] * 6,
        "station_name": ["Dadar", "Thane", "Dadar", "CST", "Andheri", "Bandra"],
        "line": ["Central", "Central", "Central", "Central", "Western", "Western"],
        "hour": [8, 8, 17, 8, 8, 8],
        "weekday": [0, 0, 0, 0, 0, 0],
        "period": ["morning_peak", "morning_peak", "evening_peak", "morning_peak", "morning_peak", "morning_peak"],
        "avg_delay": [6.5, 4.2, 7.1, 3.0, 5.5, 2.8],
        "std_delay": [2.1, 1.8, 2.3, 1.2, 2.0, 1.5],
        "sample_count": [15, 15, 15, 15, 15, 15],
        "ci_lower": [5.4, 3.3, 5.9, 2.2, 4.6, 2.0],
        "ci_upper": [7.6, 5.1, 8.3, 3.8, 6.4, 3.6],
        "on_time_pct": [32.5, 55.0, 28.1, 65.0, 45.0, 70.0],
    })


class TestLineSummary:
    def test_returns_polars_dataframe(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = line_summary(store)
        assert isinstance(result, pl.DataFrame)

    def test_has_required_columns(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = line_summary(store)
        assert "line" in result.columns
        assert "avg_delay" in result.columns
        assert "on_time_pct" in result.columns

    def test_one_row_per_line(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = line_summary(store)
        assert len(result) == result["line"].n_unique()

    def test_sorted_by_avg_delay_descending(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = line_summary(store)
        delays = result["avg_delay"].to_list()
        assert delays == sorted(delays, reverse=True)

    def test_empty_store_returns_empty(self, store: DelayStore) -> None:
        result = line_summary(store)
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 0


class TestPeakRankings:
    def test_returns_polars_dataframe(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = peak_rankings(store, line="Central", period="morning_peak", n=10)
        assert isinstance(result, pl.DataFrame)

    def test_has_required_columns(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = peak_rankings(store, line="Central", period="morning_peak", n=10)
        assert "station_name" in result.columns
        assert "avg_delay" in result.columns
        assert "ci_lower" in result.columns
        assert "ci_upper" in result.columns

    def test_filters_by_line(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = peak_rankings(store, line="Western", period="morning_peak", n=10)
        # Only Western stations: Andheri, Bandra
        assert len(result) == 2
        assert set(result["station_name"].to_list()) == {"Andheri", "Bandra"}

    def test_filters_by_period(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = peak_rankings(store, line="Central", period="evening_peak", n=10)
        # Only Dadar has evening_peak in sample data
        assert len(result) == 1
        assert result["station_name"][0] == "Dadar"

    def test_respects_n_limit(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = peak_rankings(store, line="Central", period="morning_peak", n=2)
        assert len(result) <= 2

    def test_sorted_by_avg_delay_descending(self, store: DelayStore, sample_df: pl.DataFrame) -> None:
        store.upsert(sample_df)
        result = peak_rankings(store, line="Central", period="morning_peak", n=10)
        delays = result["avg_delay"].to_list()
        assert delays == sorted(delays, reverse=True)

    def test_empty_store_returns_empty(self, store: DelayStore) -> None:
        result = peak_rankings(store, line="Central", period="morning_peak", n=10)
        assert isinstance(result, pl.DataFrame)
        assert len(result) == 0
