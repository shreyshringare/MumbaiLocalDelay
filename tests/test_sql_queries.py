"""Tests for the three new SQL analytics queries."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from analysis.sql_queries import monsoon_vs_dry_pivot, rolling_deviation, yoy_delay_change
from pipeline.store import DelayStore


@pytest.fixture
def store(tmp_path: Path) -> DelayStore:
    import duckdb

    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE delays (
            date DATE, station_name VARCHAR, line VARCHAR,
            hour INTEGER, weekday INTEGER, period VARCHAR,
            avg_delay DOUBLE, std_delay DOUBLE, sample_count INTEGER
        )
    """)
    rows = []
    for m in range(1, 13):
        for d in range(1, 28):
            rows.append((date(2023, m, d), "Dadar", "Central", 9, 0, "morning_peak", 5.0, 1.0, 15))
    for m in range(1, 13):
        for d in range(1, 28):
            rows.append((date(2024, m, d), "Dadar", "Central", 9, 0, "morning_peak", 7.0, 1.0, 15))
    conn.executemany("INSERT INTO delays VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    conn.close()
    return DelayStore(db_path)


def test_yoy_delay_change_columns(store: DelayStore) -> None:
    result = yoy_delay_change(store)
    assert isinstance(result, pl.DataFrame)
    assert {"station_name", "line", "avg_2023", "avg_2024", "yoy_pct_change"}.issubset(set(result.columns))


def test_yoy_delay_change_positive_for_worsening(store: DelayStore) -> None:
    result = yoy_delay_change(store)
    dadar = result.filter(pl.col("station_name") == "Dadar")
    assert len(dadar) == 1
    assert dadar["yoy_pct_change"][0] > 0


def test_monsoon_vs_dry_columns(store: DelayStore) -> None:
    result = monsoon_vs_dry_pivot(store)
    assert {"station_name", "line", "monsoon_avg", "dry_avg", "monsoon_ratio"}.issubset(set(result.columns))


def test_rolling_deviation_columns(store: DelayStore) -> None:
    result = rolling_deviation(store, "Central")
    assert {"date", "station_name", "rolling_7d_avg", "baseline_30d_avg", "deviation_ratio"}.issubset(set(result.columns))
