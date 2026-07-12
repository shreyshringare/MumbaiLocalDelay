"""Tests for pipeline/ingest/real_data.py"""

from pathlib import Path

import polars as pl
import pytest

from pipeline.ingest.real_data import (
    load_mumbai_baselines,
)

REAL_CSV = Path("data/raw/real/etrain_delays.csv")


@pytest.mark.skipif(not REAL_CSV.exists(), reason="real data not present")
class TestLoadMumbaiBaselines:
    def test_returns_dataframe(self) -> None:
        df = load_mumbai_baselines(REAL_CSV)
        assert isinstance(df, pl.DataFrame)

    def test_has_required_columns(self) -> None:
        df = load_mumbai_baselines(REAL_CSV)
        required = {
            "station_code",
            "station_name",
            "line",
            "avg_delay_real",
            "pct_right_time",
            "pct_slight_delay",
            "pct_significant_delay",
            "sample_trains",
            "data_source",
        }
        assert required.issubset(set(df.columns))

    def test_no_null_avg_delay(self) -> None:
        df = load_mumbai_baselines(REAL_CSV)
        assert df["avg_delay_real"].null_count() == 0

    def test_data_source_tag(self) -> None:
        df = load_mumbai_baselines(REAL_CSV)
        assert df["data_source"].unique().to_list() == ["real_aggregate"]

    def test_line_values_valid(self) -> None:
        df = load_mumbai_baselines(REAL_CSV)
        valid = {"Central", "Western", "Harbour"}
        actual = set(df["line"].unique().to_list())
        assert actual.issubset(valid)

    def test_avg_delay_in_range(self) -> None:
        df = load_mumbai_baselines(REAL_CSV)
        assert df["avg_delay_real"].min() >= 0.0
        assert df["avg_delay_real"].max() <= 120.0

    def test_sample_trains_positive(self) -> None:
        df = load_mumbai_baselines(REAL_CSV)
        assert df["sample_trains"].min() >= 1

    def test_known_station_present(self) -> None:
        df = load_mumbai_baselines(REAL_CSV)
        names = df["station_name"].to_list()
        # At least one of these must be present (verified in data)
        known = {"Dadar", "Thane", "Kalyan", "Borivali", "Lokmanya Tilak Terminus"}
        assert len(known & set(names)) > 0
