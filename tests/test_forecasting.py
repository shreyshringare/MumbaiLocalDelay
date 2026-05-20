"""Tests for ForecastCache and daily_avg."""
from datetime import date, timedelta

import polars as pl
import pytest

from pipeline.store import DelayStore


def _make_store(station: str = "Dadar", line: str = "Central", n_days: int = 60) -> DelayStore:
    """In-memory store with n_days of hourly data for one station."""
    store = DelayStore(":memory:")
    rows = []
    for i in range(n_days):
        d = date(2023, 1, 1) + timedelta(days=i)
        for hour in range(24):
            rows.append({
                "date": d,
                "station_name": station,
                "line": line,
                "hour": hour,
                "weekday": d.weekday(),
                "period": "morning_peak" if 7 <= hour <= 9 else "off_peak",
                "avg_delay": 5.0 + hour * 0.1,
                "std_delay": 1.0,
                "sample_count": 10,
                "ci_lower": 4.0,
                "ci_upper": 6.0,
                "on_time_pct": 60.0,
            })
    store.upsert(pl.DataFrame(rows))
    return store


class TestDailyAvg:
    def test_returns_dataframe(self) -> None:
        store = _make_store(n_days=60)
        df = store.daily_avg("Dadar")
        assert isinstance(df, pl.DataFrame)

    def test_columns(self) -> None:
        store = _make_store(n_days=60)
        df = store.daily_avg("Dadar")
        assert "date" in df.columns
        assert "avg_delay" in df.columns

    def test_row_count_matches_days(self) -> None:
        store = _make_store(n_days=60)
        df = store.daily_avg("Dadar")
        assert len(df) == 60

    def test_ordered_ascending(self) -> None:
        store = _make_store(n_days=60)
        df = store.daily_avg("Dadar")
        dates = df["date"].to_list()
        assert dates == sorted(dates)

    def test_unknown_station_returns_empty(self) -> None:
        store = _make_store(n_days=60)
        df = store.daily_avg("NonExistent")
        assert len(df) == 0
