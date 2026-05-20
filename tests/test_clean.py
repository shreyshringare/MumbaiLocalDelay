"""Tests for the Polars cleaning and feature engineering pipeline."""
from datetime import date

import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pipeline.transform.clean import (
    CANONICAL_STATIONS,
    detect_gaps,
    normalize_stations,
    validate_delays,
)
from pipeline.transform.features import add_features


def _make_raw(overrides: dict[str, object] | None = None) -> pl.DataFrame:
    """Helper: build a minimal valid raw delay DataFrame."""
    base = {
        "date": [date(2024, 1, 15)],
        "station_name": ["Dadar"],
        "line": ["Central"],
        "hour": [8],
        "weekday": [0],
        "period": ["morning_peak"],
        "avg_delay": [5.5],
        "std_delay": [2.1],
        "sample_count": [15],
    }
    if overrides:
        base.update(overrides)
    return pl.DataFrame(base)


class TestValidateDelays:
    def test_valid_row_passes(self) -> None:
        df = _make_raw()
        result = validate_delays(df)
        assert len(result) == 1

    def test_delay_above_120_filtered(self) -> None:
        df = _make_raw({"avg_delay": [150.0]})
        result = validate_delays(df)
        assert len(result) == 0

    def test_delay_below_minus5_filtered(self) -> None:
        df = _make_raw({"avg_delay": [-10.0]})
        result = validate_delays(df)
        assert len(result) == 0

    def test_delay_at_boundary_kept(self) -> None:
        df_low = _make_raw({"avg_delay": [-5.0]})
        df_high = _make_raw({"avg_delay": [120.0]})
        assert len(validate_delays(df_low)) == 1
        assert len(validate_delays(df_high)) == 1

    def test_zero_sample_count_filtered(self) -> None:
        df = _make_raw({"sample_count": [0]})
        result = validate_delays(df)
        assert len(result) == 0

    def test_missing_required_column_raises(self) -> None:
        df = pl.DataFrame({"station_name": ["Dadar"], "avg_delay": [5.0]})
        with pytest.raises(ValueError, match="Missing required columns"):
            validate_delays(df)

    @given(st.floats(min_value=-100.0, max_value=200.0))
    @settings(max_examples=100)
    def test_only_valid_range_passes(self, delay: float) -> None:
        df = _make_raw({"avg_delay": [delay]})
        result = validate_delays(df)
        if -5.0 <= delay <= 120.0:
            assert len(result) == 1
        else:
            assert len(result) == 0


class TestNormalizeStations:
    def test_dadar_cr_normalized(self) -> None:
        df = _make_raw({"station_name": ["Dadar (CR)"]})
        result = normalize_stations(df)
        assert result["station_name"][0] == "Dadar"

    def test_uppercase_normalized(self) -> None:
        df = _make_raw({"station_name": ["THANE"]})
        result = normalize_stations(df)
        assert result["station_name"][0] == "Thane"

    def test_already_canonical_unchanged(self) -> None:
        df = _make_raw({"station_name": ["Dadar"]})
        result = normalize_stations(df)
        assert result["station_name"][0] == "Dadar"

    def test_all_canonical_stations_map_to_themselves(self) -> None:
        for canonical in CANONICAL_STATIONS:
            df = _make_raw({"station_name": [canonical]})
            result = normalize_stations(df)
            assert result["station_name"][0] == canonical


class TestDetectGaps:
    def test_no_gaps_returns_empty(self) -> None:
        rows = [
            {"date": date(2024, 1, 1), "station_name": "Dadar", "hour": h,
             "line": "Central", "weekday": 0, "period": "off_peak",
             "avg_delay": 2.0, "std_delay": 1.0, "sample_count": 15}
            for h in range(24)
        ]
        df = pl.DataFrame(rows)
        gaps = detect_gaps(df)
        assert len(gaps) == 0

    def test_missing_hour_flagged(self) -> None:
        rows = [
            {"date": date(2024, 1, 1), "station_name": "Dadar", "hour": h,
             "line": "Central", "weekday": 0, "period": "off_peak",
             "avg_delay": 2.0, "std_delay": 1.0, "sample_count": 15}
            for h in range(24) if h != 8  # hour 8 missing
        ]
        df = pl.DataFrame(rows)
        gaps = detect_gaps(df)
        assert len(gaps) > 0


class TestAddFeatures:
    def test_ci_lower_less_than_mean(self) -> None:
        df = _make_raw()
        result = add_features(df)
        assert "ci_lower" in result.columns
        assert "ci_upper" in result.columns
        assert result["ci_lower"][0] < result["avg_delay"][0]
        assert result["ci_upper"][0] > result["avg_delay"][0]

    def test_ci_columns_present(self) -> None:
        df = _make_raw()
        result = add_features(df)
        assert "ci_lower" in result.columns
        assert "ci_upper" in result.columns
        assert "on_time_pct" in result.columns

    def test_on_time_pct_between_0_and_100(self) -> None:
        df = _make_raw()
        result = add_features(df)
        pct = result["on_time_pct"][0]
        assert 0.0 <= pct <= 100.0
