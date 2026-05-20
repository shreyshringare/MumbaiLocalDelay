"""Tests for station co-delay Pearson correlation."""
from datetime import date, timedelta

import polars as pl
import pytest

from pipeline.store import DelayStore


def _make_store_two_stations(n_days: int = 90) -> DelayStore:
    store = DelayStore(":memory:")
    rows = []
    for i in range(n_days):
        d = date(2023, 1, 1) + timedelta(days=i)
        for hour in range(24):
            dadar_delay = 5.0 + (i % 7) * 0.5 + hour * 0.1
            thane_delay = dadar_delay * 0.8
            for station, delay in [("Dadar", dadar_delay), ("Thane", thane_delay)]:
                rows.append({
                    "date": d, "station_name": station, "line": "Central",
                    "hour": hour, "weekday": d.weekday(),
                    "period": "morning_peak" if 7 <= hour <= 9 else "off_peak",
                    "avg_delay": delay, "std_delay": 1.0, "sample_count": 10,
                    "ci_lower": delay - 1.0, "ci_upper": delay + 1.0, "on_time_pct": 60.0,
                })
    store.upsert(pl.DataFrame(rows))
    return store


class TestStationCorrelation:
    def test_returns_tuple(self) -> None:
        from analysis.correlation import station_correlation
        store = _make_store_two_stations()
        result = station_correlation(store, line="Central", n=2)
        assert isinstance(result, tuple) and len(result) == 2

    def test_stations_list(self) -> None:
        from analysis.correlation import station_correlation
        store = _make_store_two_stations()
        stations, _ = station_correlation(store, line="Central", n=2)
        assert isinstance(stations, list) and len(stations) == 2

    def test_matrix_is_square(self) -> None:
        from analysis.correlation import station_correlation
        store = _make_store_two_stations()
        stations, matrix = station_correlation(store, line="Central", n=2)
        n = len(stations)
        assert len(matrix) == n and all(len(row) == n for row in matrix)

    def test_diagonal_is_one(self) -> None:
        from analysis.correlation import station_correlation
        store = _make_store_two_stations()
        stations, matrix = station_correlation(store, line="Central", n=2)
        for i in range(len(stations)):
            assert matrix[i][i] == pytest.approx(1.0)

    def test_values_in_range(self) -> None:
        from analysis.correlation import station_correlation
        store = _make_store_two_stations()
        _, matrix = station_correlation(store, line="Central", n=2)
        for row in matrix:
            for val in row:
                assert -1.0 <= val <= 1.0

    def test_correlated_stations_have_high_r(self) -> None:
        from analysis.correlation import station_correlation
        store = _make_store_two_stations()
        stations, matrix = station_correlation(store, line="Central", n=2)
        i, j = stations.index("Dadar"), stations.index("Thane")
        assert matrix[i][j] > 0.9

    def test_empty_line_returns_empty(self) -> None:
        from analysis.correlation import station_correlation
        store = _make_store_two_stations()
        stations, matrix = station_correlation(store, line="Western", n=15)
        assert stations == [] and matrix == []
