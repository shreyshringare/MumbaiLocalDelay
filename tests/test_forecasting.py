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


class TestForecastCache:
    def test_get_returns_none_before_build(self) -> None:
        from analysis.forecasting import ForecastCache
        cache = ForecastCache()
        assert cache.get("Dadar") is None

    def test_stations_empty_before_build(self) -> None:
        from analysis.forecasting import ForecastCache
        cache = ForecastCache()
        assert cache.stations() == []

    def test_ready_false_before_build(self) -> None:
        from analysis.forecasting import ForecastCache
        cache = ForecastCache()
        assert cache.ready is False

    @pytest.mark.timeout(120)
    def test_build_populates_cache(self) -> None:
        from analysis.forecasting import ForecastCache
        store = _make_store(n_days=60)
        cache = ForecastCache()
        cache.build(store)
        assert cache.ready is True
        result = cache.get("Dadar")
        assert result is not None

    @pytest.mark.timeout(120)
    def test_build_returns_tuple_of_dataframes(self) -> None:
        import pandas as pd

        from analysis.forecasting import ForecastCache
        store = _make_store(n_days=60)
        cache = ForecastCache()
        cache.build(store)
        history_df, forecast_df = cache.get("Dadar")  # type: ignore[misc]
        assert isinstance(history_df, pd.DataFrame)
        assert isinstance(forecast_df, pd.DataFrame)

    @pytest.mark.timeout(120)
    def test_forecast_has_7_rows(self) -> None:
        from analysis.forecasting import ForecastCache
        store = _make_store(n_days=60)
        cache = ForecastCache()
        cache.build(store)
        _, forecast_df = cache.get("Dadar")  # type: ignore[misc]
        assert len(forecast_df) == 7

    @pytest.mark.timeout(120)
    def test_forecast_columns(self) -> None:
        from analysis.forecasting import ForecastCache
        store = _make_store(n_days=60)
        cache = ForecastCache()
        cache.build(store)
        _, forecast_df = cache.get("Dadar")  # type: ignore[misc]
        assert "ds" in forecast_df.columns
        assert "yhat" in forecast_df.columns
        assert "yhat_lower" in forecast_df.columns
        assert "yhat_upper" in forecast_df.columns

    @pytest.mark.timeout(120)
    def test_station_with_too_few_rows_skipped(self) -> None:
        from analysis.forecasting import ForecastCache
        store = _make_store(n_days=10)  # < 30 days threshold
        cache = ForecastCache()
        cache.build(store)
        assert cache.get("Dadar") is None

    @pytest.mark.timeout(120)
    def test_stations_after_build(self) -> None:
        from analysis.forecasting import ForecastCache
        store = _make_store(n_days=60)
        cache = ForecastCache()
        cache.build(store)
        assert "Dadar" in cache.stations()
