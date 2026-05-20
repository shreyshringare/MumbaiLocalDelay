"""Tests for the hardcoded Mumbai station registry."""

from pathlib import Path

import polars as pl

from pipeline.ingest.stations import build_station_dataframe, write_stops_parquet


class TestBuildStationDataframe:
    def test_has_required_columns(self) -> None:
        df = build_station_dataframe()
        assert {"station_name", "latitude", "longitude", "line"}.issubset(
            set(df.columns)
        )

    def test_minimum_station_count(self) -> None:
        df = build_station_dataframe()
        assert len(df) >= 120, f"Expected 120+ stations, got {len(df)}"

    def test_all_three_lines_present(self) -> None:
        df = build_station_dataframe()
        lines = set(df["line"].to_list())
        assert "Central" in lines
        assert "Western" in lines
        assert "Harbour" in lines

    def test_no_null_values(self) -> None:
        df = build_station_dataframe()
        assert df.null_count().sum_horizontal().item() == 0

    def test_latitudes_in_mumbai_range(self) -> None:
        df = build_station_dataframe()
        lats = df["latitude"]
        assert (lats >= 18.7).all(), "Some latitudes are south of Mumbai region"
        assert (lats <= 20.1).all(), "Some latitudes are north of Mumbai region"

    def test_longitudes_in_mumbai_range(self) -> None:
        df = build_station_dataframe()
        lons = df["longitude"]
        assert (lons >= 72.7).all(), "Some longitudes are west of Mumbai"
        assert (lons <= 73.5).all(), "Some longitudes are east of Mumbai"

    def test_no_empty_station_names(self) -> None:
        df = build_station_dataframe()
        names = df["station_name"].to_list()
        assert all(name.strip() for name in names)

    def test_csmt_present(self) -> None:
        df = build_station_dataframe()
        names = df["station_name"].to_list()
        assert "Chhatrapati Shivaji Maharaj Terminus" in names

    def test_dadar_on_both_central_and_western(self) -> None:
        df = build_station_dataframe()
        dadar = df.filter(pl.col("station_name") == "Dadar")
        lines = set(dadar["line"].to_list())
        assert "Central" in lines
        assert "Western" in lines


class TestWriteStopsParquet:
    def test_parquet_file_created(self, tmp_path: Path) -> None:
        write_stops_parquet(tmp_path)
        assert (tmp_path / "stops.parquet").exists()

    def test_parquet_readable_with_correct_schema(self, tmp_path: Path) -> None:
        write_stops_parquet(tmp_path)
        df = pl.read_parquet(tmp_path / "stops.parquet")
        assert "station_name" in df.columns
        assert "latitude" in df.columns
        assert "longitude" in df.columns
        assert "line" in df.columns
        assert len(df) >= 120
