# Phase 2: GTFS Ingestion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parse the real Mumbai suburban railway GTFS static feed to extract 120+ stations, 3 lines (Central/Western/Harbour), and schedule data — saved as Parquet for downstream use.

**Architecture:** `httpx` fetches the GTFS zip asynchronously. A pure-Python parser extracts `stops.txt`, `routes.txt`, and `stop_times.txt` into Polars DataFrames. A canonical station name lookup normalizes "DADAR", "Dadar (CR)", "Dadar" → "Dadar". Output saved to `data/raw/` as Parquet.

**Tech Stack:** Python 3.12, httpx, Polars, pyarrow, python-dotenv

---

## File Structure

```
pipeline/ingest/
├── gtfs.py           # GTFS fetcher + parser (main module)
tests/
├── test_gtfs.py      # Unit + integration tests
data/sample/
├── gtfs/
│   ├── stops.txt     # Minimal sample for tests (5 stations)
│   ├── routes.txt
│   └── stop_times.txt
```

---

### Task 1: Create sample GTFS data for tests

**Files:**
- Create: `data/sample/gtfs/stops.txt`
- Create: `data/sample/gtfs/routes.txt`
- Create: `data/sample/gtfs/stop_times.txt`

- [ ] **Step 1: Write sample stops.txt**

```
stop_id,stop_name,stop_lat,stop_lon,location_type
S001,CSTM,18.9401,72.8353,0
S002,Dadar (CR),19.0178,72.8478,0
S003,DADAR,19.0220,72.8347,0
S004,Kurla,19.0654,72.8792,0
S005,Thane,19.1896,72.9703,0
```

- [ ] **Step 2: Write sample routes.txt**

```
route_id,route_short_name,route_long_name,route_type
R001,CR,Central Railway Main Line,2
R002,WR,Western Railway Main Line,2
R003,HR,Harbour Line,2
```

- [ ] **Step 3: Write sample stop_times.txt**

```
trip_id,arrival_time,departure_time,stop_id,stop_sequence
T001,07:00:00,07:00:00,S001,1
T001,07:15:00,07:16:00,S002,2
T001,07:35:00,07:36:00,S004,3
T001,08:00:00,08:00:00,S005,4
T002,08:00:00,08:00:00,S001,1
T002,08:18:00,08:19:00,S002,2
```

---

### Task 2: Write test_gtfs.py (failing first)

**Files:**
- Create: `tests/test_gtfs.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for GTFS ingestion pipeline."""
import io
import zipfile
from pathlib import Path

import polars as pl
import pytest

from pipeline.ingest.gtfs import GTFSData, parse_gtfs, normalize_station_name


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

    def test_stops_has_required_columns(self, gtfs_zip: bytes, tmp_data_dir: Path) -> None:
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

    def test_station_names_normalized(self, gtfs_zip: bytes, tmp_data_dir: Path) -> None:
        result = parse_gtfs(gtfs_zip, tmp_data_dir / "raw")
        names = result.stops["station_name"].to_list()
        # No uppercase-only names remain
        assert all(name == name.title() or name in ("Chhatrapati Shivaji Maharaj Terminus",) for name in names)

    def test_parquet_readable(self, gtfs_zip: bytes, tmp_data_dir: Path) -> None:
        output_dir = tmp_data_dir / "raw"
        parse_gtfs(gtfs_zip, output_dir)
        df = pl.read_parquet(output_dir / "stops.parquet")
        assert len(df) >= 1
```

- [ ] **Step 2: Run to verify all fail**

```bash
uv run pytest tests/test_gtfs.py -v
```

Expected: `ImportError: cannot import name 'GTFSData' from 'pipeline.ingest.gtfs'` (module doesn't exist yet).

---

### Task 3: Implement pipeline/ingest/gtfs.py

**Files:**
- Create: `pipeline/ingest/gtfs.py`

- [ ] **Step 1: Write the module**

```python
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

    stops: pl.DataFrame       # stop_id, station_name, stop_lat, stop_lon
    routes: pl.DataFrame      # route_id, route_short_name, line
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
        _LINE_MAP.get(code, "Unknown")
        for code in df["route_short_name"].to_list()
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
```

- [ ] **Step 2: Run the tests**

```bash
uv run pytest tests/test_gtfs.py -v
```

Expected: all PASSED. If `test_station_names_normalized` fails, check `normalize_station_name` — the title-case check may need adjustment for multi-word names.

- [ ] **Step 3: Run ruff and mypy**

```bash
uv run ruff check pipeline/ingest/gtfs.py
uv run mypy pipeline/ingest/gtfs.py
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add pipeline/ingest/gtfs.py tests/test_gtfs.py data/sample/gtfs/
git commit -m "feat(ingest): implement GTFS parser with station name normalization"
```

---

### Task 4: Verify GTFS fetch with real URL (manual test)

This task requires a real GTFS URL. Skip if running in CI.

- [ ] **Step 1: Set MUMBAI_GTFS_URL in .env**

Get the Mumbai Suburban Railway GTFS feed. Options:
- Search "Mumbai suburban railway GTFS" on OpenMobilityData (https://transitfeeds.com)
- Check data.gov.in for "GTFS Mumbai"
- Use the BEST bus GTFS as a structural test (different data, same format)

Add to `.env`:
```
MUMBAI_GTFS_URL=<your-url-here>
```

- [ ] **Step 2: Run the module directly**

```bash
uv run python -m pipeline.ingest.gtfs
```

Expected output:
```
Parsed NNN stops, N routes
Saved parquet files to data/raw
```

- [ ] **Step 3: Spot-check the output**

```bash
uv run python -c "
import polars as pl
stops = pl.read_parquet('data/raw/stops.parquet')
print(stops.head(10))
print(f'Total stations: {len(stops)}')
"
```

Expected: ~120+ rows with recognizable Mumbai station names (CST, Dadar, Thane, etc.).
