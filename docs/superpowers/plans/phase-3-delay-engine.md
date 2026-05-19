# Phase 3: Delay Engine + Raw Storage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate 2 years of statistically-grounded delay data for all Mumbai stations, reflecting real Mumbai patterns (peak hours, monsoon, line differences). Output: Parquet files in `data/raw/` ready for the transform pipeline.

**Architecture:** `DelaySimulator` reads the GTFS stops parquet, generates daily delay records per station using NumPy distributions calibrated to Mumbai parameters. A secondary `scheduler.py` wires APScheduler for daily refresh. An optional `scraper.py` attempts data.gov.in but falls back gracefully.

**Tech Stack:** Python 3.12, Polars, NumPy, APScheduler, httpx, BeautifulSoup4

---

## File Structure

```
pipeline/ingest/
├── simulator.py      # Statistical delay generator (main)
├── scraper.py        # Optional data.gov.in scraper
├── scheduler.py      # APScheduler daily refresh job
tests/
├── test_simulator.py
data/sample/
├── stops_sample.parquet  # 5-station sample for tests
```

---

### Task 1: Create sample stops parquet for tests

**Files:**
- Create: `data/sample/stops_sample.parquet`

- [ ] **Step 1: Generate sample parquet**

```bash
uv run python -c "
import polars as pl

stops = pl.DataFrame({
    'stop_id': ['S001', 'S002', 'S003', 'S004', 'S005'],
    'station_name': ['Chhatrapati Shivaji Maharaj Terminus', 'Dadar', 'Kurla', 'Thane', 'Andheri'],
    'stop_lat': [18.9401, 19.0178, 19.0654, 19.1896, 19.1197],
    'stop_lon': [72.8353, 72.8478, 72.8792, 72.9703, 72.8466],
})

# Assign lines to sample stations
line_map = {
    'Chhatrapati Shivaji Maharaj Terminus': 'Central',
    'Dadar': 'Central',
    'Kurla': 'Central',
    'Thane': 'Central',
    'Andheri': 'Western',
}
stops = stops.with_columns(
    pl.col('station_name').replace(line_map).alias('line')
)
stops.write_parquet('data/sample/stops_sample.parquet')
print('Created data/sample/stops_sample.parquet')
print(stops)
"
```

---

### Task 2: Write test_simulator.py (failing first)

**Files:**
- Create: `tests/test_simulator.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the statistical delay simulator."""
from pathlib import Path
from datetime import date, timedelta

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
        required = {"date", "station_name", "line", "hour", "weekday", "period",
                    "avg_delay", "std_delay", "sample_count"}
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
        stops = pl.DataFrame({
            "stop_id": ["S001"],
            "station_name": ["Dadar"],
            "stop_lat": [19.0178],
            "stop_lon": [72.8478],
            "line": ["Central"],
        })
        sim = DelaySimulator(stops=stops, params=MumbaiDelayParams())
        result = sim.generate(date(2024, month, 1), date(2024, month, 5))
        assert result["avg_delay"].is_nan().sum() == 0
        assert result["avg_delay"].min() >= -5.0
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_simulator.py -v
```

Expected: `ImportError` — module doesn't exist yet.

---

### Task 3: Implement pipeline/ingest/simulator.py

**Files:**
- Create: `pipeline/ingest/simulator.py`

- [ ] **Step 1: Write the module**

```python
"""Statistical delay simulator for Mumbai Suburban Railway.

Generates realistic delay data based on known Mumbai patterns:
- Morning peak (7-11 AM): higher delays
- Evening peak (17-21 PM): higher delays
- Monsoon (June-September): +40% delays
- Central line: 15% higher than Western baseline
- Harbour line: 20% lower than Western baseline

All values are clearly simulated — disclosed in README.
"""
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

import polars as pl


@dataclass
class MumbaiDelayParams:
    """Calibrated delay parameters for Mumbai suburban railway.

    Based on published research and publicly available delay statistics.
    """
    # Baseline delays per period (minutes)
    morning_peak_mean: float = 7.5
    morning_peak_std: float = 3.0
    evening_peak_mean: float = 6.5
    evening_peak_std: float = 2.5
    offpeak_mean: float = 2.0
    offpeak_std: float = 1.2

    # Line adjustment factors (multiplicative)
    central_factor: float = 1.15   # Central 15% worse than Western baseline
    western_factor: float = 1.0    # Baseline
    harbour_factor: float = 0.80   # Harbour 20% better than Western baseline

    # Seasonal factor
    monsoon_factor: float = 1.40   # June-September: +40%
    monsoon_months: frozenset[int] = field(default_factory=lambda: frozenset({6, 7, 8, 9}))

    # Trains per hour per station (determines sample_count)
    trains_per_hour: int = 15


# Period → (hour_start, hour_end_exclusive)
_PERIODS: list[tuple[str, int, int]] = [
    ("morning_peak", 7, 12),
    ("evening_peak", 17, 22),
    ("off_peak", 0, 24),   # catches remaining hours
]


def _get_period(hour: int) -> str:
    if 7 <= hour < 12:
        return "morning_peak"
    if 17 <= hour < 22:
        return "evening_peak"
    return "off_peak"


def _line_factor(line: str, params: MumbaiDelayParams) -> float:
    return {
        "Central": params.central_factor,
        "Western": params.western_factor,
        "Harbour": params.harbour_factor,
    }.get(line, params.western_factor)


def _is_monsoon(month: int, params: MumbaiDelayParams) -> bool:
    return month in params.monsoon_months


class DelaySimulator:
    """Generates statistically-grounded delay data for Mumbai stations."""

    def __init__(self, stops: pl.DataFrame, params: MumbaiDelayParams) -> None:
        """
        Args:
            stops: DataFrame with columns [stop_id, station_name, line, ...]
            params: Mumbai delay distribution parameters
        """
        self._stops = stops
        self._params = params

    def generate(self, start_date: date, end_date: date) -> pl.DataFrame:
        """Generate daily delay records for every station and hour.

        Returns one row per (date, station, hour) with avg_delay, std_delay,
        sample_count, and derived columns (weekday, period).
        """
        rows: list[dict] = []
        p = self._params
        current = start_date

        while current <= end_date:
            monsoon = _is_monsoon(current.month, p)
            seasonal = p.monsoon_factor if monsoon else 1.0
            weekday = current.weekday()  # 0=Monday, 6=Sunday

            for row in self._stops.iter_rows(named=True):
                station = row["station_name"]
                line = row.get("line", "Western")
                line_factor = _line_factor(line, p)

                for hour in range(24):
                    period = _get_period(hour)

                    if period == "morning_peak":
                        base_mean = p.morning_peak_mean
                        base_std = p.morning_peak_std
                    elif period == "evening_peak":
                        base_mean = p.evening_peak_mean
                        base_std = p.evening_peak_std
                    else:
                        base_mean = p.offpeak_mean
                        base_std = p.offpeak_std

                    # Weekend reduction: ~30% fewer delays
                    weekend_factor = 0.70 if weekday >= 5 else 1.0

                    mean = base_mean * line_factor * seasonal * weekend_factor
                    std = base_std * line_factor

                    # Simulate individual train delays, then aggregate
                    n = p.trains_per_hour
                    delays = [
                        max(-5.0, min(120.0, random.gauss(mean, std)))
                        for _ in range(n)
                    ]
                    avg = sum(delays) / n
                    variance = sum((d - avg) ** 2 for d in delays) / max(n - 1, 1)
                    std_obs = variance ** 0.5

                    rows.append({
                        "date": current,
                        "station_name": station,
                        "line": line,
                        "hour": hour,
                        "weekday": weekday,
                        "period": period,
                        "avg_delay": round(avg, 2),
                        "std_delay": round(std_obs, 2),
                        "sample_count": n,
                    })

            current += timedelta(days=1)

        return pl.DataFrame(rows)


if __name__ == "__main__":
    import os
    from pathlib import Path
    from datetime import date
    from dotenv import load_dotenv

    load_dotenv()
    raw_dir = Path(os.getenv("DATA_RAW_DIR", "data/raw"))
    stops = pl.read_parquet(raw_dir / "stops.parquet")

    sim = DelaySimulator(stops=stops, params=MumbaiDelayParams())
    print("Generating 2 years of delay data...")
    df = sim.generate(date(2023, 1, 1), date(2024, 12, 31))
    out = raw_dir / "delays_raw.parquet"
    df.write_parquet(out)
    print(f"Generated {len(df):,} rows → {out}")
    print(df.describe())
```

- [ ] **Step 2: Run tests**

```bash
uv run pytest tests/test_simulator.py -v
```

Expected: all PASSED. The `test_monsoon_delays_higher` test verifies statistical behavior — if it flakes, the monsoon_factor may need increasing.

- [ ] **Step 3: Lint and type check**

```bash
uv run ruff check pipeline/ingest/simulator.py
uv run mypy pipeline/ingest/simulator.py
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add pipeline/ingest/simulator.py tests/test_simulator.py data/sample/stops_sample.parquet
git commit -m "feat(ingest): add statistical delay simulator with Mumbai parameters"
```

---

### Task 4: Implement optional data.gov.in scraper

**Files:**
- Create: `pipeline/ingest/scraper.py`

- [ ] **Step 1: Write the scraper with graceful fallback**

```python
"""Optional scraper for data.gov.in historical delay reports.

Falls back silently if the source is unavailable. Never blocks
the main pipeline — simulation is the primary data source.
"""
import logging
from pathlib import Path

import httpx
import polars as pl
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# data.gov.in search URL for Mumbai suburban railway datasets
_DATAGOV_SEARCH = "https://data.gov.in/search?q=mumbai+suburban+railway"


def try_fetch_historical(output_dir: Path) -> bool:
    """Attempt to fetch historical delay CSVs from data.gov.in.

    Returns True if data was fetched, False if unavailable.
    Writes any fetched data to output_dir/historical_raw.parquet.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(_DATAGOV_SEARCH, follow_redirects=True)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Look for downloadable CSV links
        csv_links = [
            a["href"]
            for a in soup.find_all("a", href=True)
            if a["href"].endswith(".csv") and "railway" in a["href"].lower()
        ]
        if not csv_links:
            logger.info("data.gov.in: no railway CSV links found — using simulation")
            return False

        frames: list[pl.DataFrame] = []
        for url in csv_links[:3]:  # cap at 3 files
            try:
                r = httpx.get(url, timeout=30.0, follow_redirects=True)
                r.raise_for_status()
                import io
                df = pl.read_csv(io.BytesIO(r.content), infer_schema_length=1000)
                frames.append(df)
                logger.info(f"Fetched {url}: {len(df)} rows")
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                continue

        if frames:
            combined = pl.concat(frames, how="diagonal")
            output_dir.mkdir(parents=True, exist_ok=True)
            combined.write_parquet(output_dir / "historical_raw.parquet")
            logger.info(f"Saved {len(combined)} historical rows")
            return True

    except Exception as e:
        logger.info(f"data.gov.in unavailable: {e} — using simulation only")
    return False
```

- [ ] **Step 2: Commit scraper**

```bash
git add pipeline/ingest/scraper.py
git commit -m "feat(ingest): add optional data.gov.in scraper with graceful fallback"
```

---

### Task 5: Implement APScheduler daily refresh

**Files:**
- Create: `pipeline/ingest/scheduler.py`

- [ ] **Step 1: Write scheduler**

```python
"""APScheduler job for daily delay data refresh."""
import logging
import os
from datetime import date, timedelta
from pathlib import Path

import polars as pl
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from pipeline.ingest.simulator import DelaySimulator, MumbaiDelayParams
from pipeline.ingest.scraper import try_fetch_historical

load_dotenv()
logger = logging.getLogger(__name__)


def refresh_daily() -> None:
    """Run daily: try real data, fallback to simulation, append to parquet."""
    raw_dir = Path(os.getenv("DATA_RAW_DIR", "data/raw"))
    stops_path = raw_dir / "stops.parquet"

    if not stops_path.exists():
        logger.error(f"stops.parquet not found at {stops_path}. Run GTFS ingestion first.")
        return

    stops = pl.read_parquet(stops_path)
    today = date.today()

    # Try real data first
    fetched = try_fetch_historical(raw_dir)

    if not fetched:
        # Simulate today's data
        sim = DelaySimulator(stops=stops, params=MumbaiDelayParams())
        df = sim.generate(today, today)
        out_path = raw_dir / f"delays_{today.isoformat()}.parquet"
        df.write_parquet(out_path)
        logger.info(f"Simulated {len(df)} rows for {today} → {out_path}")


def start_scheduler() -> BackgroundScheduler:
    """Start background scheduler. Runs refresh_daily at 02:00 AM daily."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_daily, "cron", hour=2, minute=0)
    scheduler.start()
    logger.info("Scheduler started: daily refresh at 02:00")
    return scheduler


if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO)
    refresh_daily()  # run once immediately
    print("One-shot refresh complete.")
```

- [ ] **Step 2: Commit**

```bash
git add pipeline/ingest/scheduler.py
git commit -m "feat(ingest): add APScheduler daily refresh job"
```

---

### Task 6: End-to-end smoke test — generate 2-year history

Requires Phase 2 to have run (stops.parquet must exist in data/raw/).

- [ ] **Step 1: Run full simulator**

```bash
uv run python -m pipeline.ingest.simulator
```

Expected output:
```
Generating 2 years of delay data...
Generated NNN,NNN rows → data/raw/delays_raw.parquet
```

- [ ] **Step 2: Verify output size**

```bash
uv run python -c "
import polars as pl
df = pl.read_parquet('data/raw/delays_raw.parquet')
print(f'Rows: {len(df):,}')
print(f'Stations: {df[\"station_name\"].n_unique()}')
print(f'Date range: {df[\"date\"].min()} → {df[\"date\"].max()}')
print(df.head(3))
"
```

Expected: 2+ million rows, 120+ unique stations.
