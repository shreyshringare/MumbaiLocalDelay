"""Tests for the statistical delay simulator."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pipeline.ingest.simulator import DelaySimulator, MumbaiDelayParams


@pytest.fixture
def simulator(sample_data_dir: Path) -> DelaySimulator:
    stops = pl.read_parquet(sample_data_dir / "stops_sample.parquet")
    return DelaySimulator(stops=stops, params=MumbaiDelayParams())


class TestMumbaiDelayParams:
    def test_peak_mean_higher_than_offpeak(self) -> None:
        params = MumbaiDelayParams()
        assert params.morning_peak_mean > params.offpeak_mean
        assert params.evening_peak_mean > params.offpeak_mean

    def test_central_factor_above_one(self) -> None:
        params = MumbaiDelayParams()
        assert params.central_factor > 1.0

    def test_harbour_factor_below_one(self) -> None:
        params = MumbaiDelayParams()
        assert params.harbour_factor < 1.0

    def test_monsoon_factor_above_one(self) -> None:
        params = MumbaiDelayParams()
        assert params.monsoon_factor > 1.0


class TestDelaySimulator:
    def test_generate_returns_dataframe(self, simulator: DelaySimulator) -> None:
        start = date(2024, 1, 1)
        end = date(2024, 1, 7)
        result = simulator.generate(start_date=start, end_date=end)
        assert isinstance(result, pl.DataFrame)

    def test_output_has_required_columns(self, simulator: DelaySimulator) -> None:
        start = date(2024, 1, 1)
        end = date(2024, 1, 3)
        result = simulator.generate(start_date=start, end_date=end)
        required = {
            "date",
            "station_name",
            "line",
            "hour",
            "weekday",
            "period",
            "avg_delay",
            "std_delay",
            "sample_count",
        }
        assert required.issubset(set(result.columns))

    def test_delays_within_valid_range(self, simulator: DelaySimulator) -> None:
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        result = simulator.generate(start_date=start, end_date=end)
        assert result["avg_delay"].min() >= -5.0
        assert result["avg_delay"].max() <= 120.0

    def test_monsoon_delays_higher(self, simulator: DelaySimulator) -> None:
        """July (monsoon) avg delay should be higher than January avg delay."""
        jan = simulator.generate(date(2024, 1, 1), date(2024, 1, 31))
        jul = simulator.generate(date(2024, 7, 1), date(2024, 7, 31))
        assert jul["avg_delay"].mean() > jan["avg_delay"].mean()

    def test_sample_count_positive(self, simulator: DelaySimulator) -> None:
        result = simulator.generate(date(2024, 1, 1), date(2024, 1, 7))
        assert result["sample_count"].min() > 0

    def test_period_values_valid(self, simulator: DelaySimulator) -> None:
        result = simulator.generate(date(2024, 1, 1), date(2024, 1, 7))
        valid = {"morning_peak", "evening_peak", "off_peak"}
        actual = set(result["period"].unique().to_list())
        assert actual.issubset(valid)

    def test_two_year_generation(self, simulator: DelaySimulator) -> None:
        start = date(2022, 1, 1)
        end = date(2023, 12, 31)
        result = simulator.generate(start_date=start, end_date=end)
        # 2 years × 5 stations × 24 hours = 87,600 rows
        assert len(result) > 50_000

    @given(st.integers(min_value=1, max_value=12))
    @settings(max_examples=12)
    def test_any_month_produces_valid_delays(self, month: int) -> None:
        stops = pl.DataFrame(
            {
                "stop_id": ["S001"],
                "station_name": ["Dadar"],
                "stop_lat": [19.0178],
                "stop_lon": [72.8478],
                "line": ["Central"],
            }
        )
        sim = DelaySimulator(stops=stops, params=MumbaiDelayParams())
        result = sim.generate(date(2024, month, 1), date(2024, month, 5))
        assert result["avg_delay"].is_nan().sum() == 0
        assert result["avg_delay"].min() >= -5.0
