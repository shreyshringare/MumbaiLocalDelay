"""Tests for GTFS ingestion pipeline."""

import io
import zipfile
from pathlib import Path

import polars as pl
import pytest

from pipeline.ingest.gtfs import GTFSData, normalize_station_name, parse_gtfs


def _make_gtfs_zip(sample_dir: Path) -> bytes:
    """Package sample CSVs into a GTFS zip for testing."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for fname in ["stops.txt", "routes.txt", "stop_times.txt"]:
            zf.write(sample_dir / "gtfs" / fname, fname)
    return buf.getvalue()


@pytest.fixture
def gtfs_zip(sample_data_dir: Path) -> bytes:
    return _make_gtfs_zip(sample_data_dir)


class TestNormalizeStationName:
    def test_uppercase_normalized(self) -> None:
        assert normalize_station_name("DADAR") == "Dadar"

    def test_cr_suffix_stripped(self) -> None:
        assert normalize_station_name("Dadar (CR)") == "Dadar"

    def test_wr_suffix_stripped(self) -> None:
        assert normalize_station_name("Andheri (WR)") == "Andheri"

    def test_already_clean(self) -> None:
        assert normalize_station_name("Thane") == "Thane"

    def test_cstm_canonical(self) -> None:
        assert normalize_station_name("CSTM") == "Chhatrapati Shivaji Maharaj Terminus"

    def test_extra_whitespace_stripped(self) -> None:
        assert normalize_station_name("  Kurla  ") == "Kurla"


class TestParseGTFS:
    def test_returns_gtfs_data(self, gtfs_zip: bytes, tmp_data_dir: Path) -> None:
        result = parse_gtfs(gtfs_zip, tmp_data_dir / "raw")
        assert isinstance(result, GTFSData)

    def test_stops_has_required_columns(
        self, gtfs_zip: bytes, tmp_data_dir: Path
    ) -> None:
        result = parse_gtfs(gtfs_zip, tmp_data_dir / "raw")
        assert "stop_id" in result.stops.columns
        assert "station_name" in result.stops.columns
        assert "stop_lat" in result.stops.columns
        assert "stop_lon" in result.stops.columns

    def test_routes_has_line_column(self, gtfs_zip: bytes, tmp_data_dir: Path) -> None:
        result = parse_gtfs(gtfs_zip, tmp_data_dir / "raw")
        assert "line" in result.routes.columns

    def test_stops_saved_as_parquet(self, gtfs_zip: bytes, tmp_data_dir: Path) -> None:
        output_dir = tmp_data_dir / "raw"
        parse_gtfs(gtfs_zip, output_dir)
        assert (output_dir / "stops.parquet").exists()
        assert (output_dir / "routes.parquet").exists()
        assert (output_dir / "stop_times.parquet").exists()

    def test_station_names_normalized(
        self, gtfs_zip: bytes, tmp_data_dir: Path
    ) -> None:
        result = parse_gtfs(gtfs_zip, tmp_data_dir / "raw")
        names = result.stops["station_name"].to_list()
        # No uppercase-only names remain
        assert all(
            name == name.title() or name in ("Chhatrapati Shivaji Maharaj Terminus",)
            for name in names
        )

    def test_parquet_readable(self, gtfs_zip: bytes, tmp_data_dir: Path) -> None:
        output_dir = tmp_data_dir / "raw"
        parse_gtfs(gtfs_zip, output_dir)
        df = pl.read_parquet(output_dir / "stops.parquet")
        assert len(df) >= 1
