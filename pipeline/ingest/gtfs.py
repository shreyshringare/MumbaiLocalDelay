"""GTFS static feed fetcher and parser for Mumbai Suburban Railway."""

import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import httpx
import polars as pl

# Canonical station name overrides (abbreviations → full names)
_CANONICAL: dict[str, str] = {
    "CSTM": "Chhatrapati Shivaji Maharaj Terminus",
    "CST": "Chhatrapati Shivaji Maharaj Terminus",
    "LTT": "Lokmanya Tilak Terminus",
    "PNVL": "Panvel",
    "ADH": "Andheri",
    "BDR": "Bandra",
}

# Line suffixes to strip
_SUFFIXES = [" (CR)", " (WR)", " (HR)", " CR", " WR", " HR"]

# Route ID → line name mapping
_LINE_MAP: dict[str, str] = {
    "CR": "Central",
    "WR": "Western",
    "HR": "Harbour",
}


def normalize_station_name(raw: str) -> str:
    """Normalize a raw GTFS stop name to a canonical station name.

    Rules (applied in order):
    1. Strip whitespace
    2. Check canonical override table
    3. Strip line suffixes like '(CR)', '(WR)'
    4. Title-case the result
    """
    name = raw.strip()
    if name in _CANONICAL:
        return _CANONICAL[name]
    for suffix in _SUFFIXES:
        name = name.replace(suffix, "")
    return name.strip().title()


@dataclass
class GTFSData:
    """Parsed GTFS feed with normalized station names."""

    stops: pl.DataFrame  # stop_id, station_name, stop_lat, stop_lon
    routes: pl.DataFrame  # route_id, route_short_name, line
    stop_times: pl.DataFrame  # trip_id, stop_id, departure_time, stop_sequence


def parse_gtfs(zip_bytes: bytes, output_dir: Path) -> GTFSData:
    """Parse a GTFS zip archive and return normalized DataFrames.

    Also writes stops.parquet, routes.parquet, stop_times.parquet to output_dir.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        stops_raw = pl.read_csv(io.BytesIO(zf.read("stops.txt")))
        routes_raw = pl.read_csv(io.BytesIO(zf.read("routes.txt")))
        stop_times_raw = pl.read_csv(io.BytesIO(zf.read("stop_times.txt")))

    stops = _normalize_stops(stops_raw)
    routes = _normalize_routes(routes_raw)
    stop_times = _normalize_stop_times(stop_times_raw)

    stops.write_parquet(output_dir / "stops.parquet")
    routes.write_parquet(output_dir / "routes.parquet")
    stop_times.write_parquet(output_dir / "stop_times.parquet")

    return GTFSData(stops=stops, routes=routes, stop_times=stop_times)


def _normalize_stops(df: pl.DataFrame) -> pl.DataFrame:
    """Add normalized station_name column, keep required columns."""
    names = [normalize_station_name(n) for n in df["stop_name"].to_list()]
    return df.with_columns(pl.Series("station_name", names)).select(
        ["stop_id", "station_name", "stop_lat", "stop_lon"]
    )


def _normalize_routes(df: pl.DataFrame) -> pl.DataFrame:
    """Map route_short_name to line (Central/Western/Harbour)."""
    lines = [
        _LINE_MAP.get(code, "Unknown") for code in df["route_short_name"].to_list()
    ]
    return df.with_columns(pl.Series("line", lines)).select(
        ["route_id", "route_short_name", "line"]
    )


def _normalize_stop_times(df: pl.DataFrame) -> pl.DataFrame:
    """Select required columns from stop_times."""
    return df.select(["trip_id", "stop_id", "departure_time", "stop_sequence"])


async def fetch_gtfs(url: str) -> bytes:
    """Asynchronously fetch a GTFS zip from the given URL."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response.content


if __name__ == "__main__":
    import asyncio
    import os

    from dotenv import load_dotenv

    load_dotenv()
    gtfs_url = os.environ["MUMBAI_GTFS_URL"]
    raw_dir = Path(os.getenv("DATA_RAW_DIR", "data/raw"))

    zip_bytes = asyncio.run(fetch_gtfs(gtfs_url))
    data = parse_gtfs(zip_bytes, raw_dir)
    print(f"Parsed {len(data.stops)} stops, {len(data.routes)} routes")
    print(f"Saved parquet files to {raw_dir}")
