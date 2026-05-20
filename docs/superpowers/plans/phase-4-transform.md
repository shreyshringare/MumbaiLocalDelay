# Phase 4: Transform Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Polars-based cleaning and feature engineering pipeline that validates raw delay data, normalizes stations, detects gaps, and outputs analysis-ready Parquet files.

**Architecture:** Two modules: `clean.py` handles validation and normalization; `features.py` adds derived columns. Both are pure functions operating on Polars DataFrames — no side effects, easy to test. Schema is enforced: unexpected columns raise, missing columns raise.

**Tech Stack:** Python 3.12, Polars 1.x, Hypothesis (property-based tests)

---

## File Structure

```
pipeline/transform/
├── clean.py          # Validation, normalization, gap detection
├── features.py       # Feature engineering (hour, weekday, period, CI)
tests/
├── test_clean.py     # Unit + property-based tests
```

---

### Task 1: Write test_clean.py (failing first)

**Files:**
- Create: `tests/test_clean.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the Polars cleaning and feature engineering pipeline."""
from datetime import date

import polars as pl
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pipeline.transform.clean import (
    validate_delays,
    normalize_stations,
    detect_gaps,
    CANONICAL_STATIONS,
)
from pipeline.transform.features import add_features, add_confidence_interval


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
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run python -m pytest tests/test_clean.py -v
```

Expected: `ImportError` on all tests.

---

### Task 2: Implement pipeline/transform/clean.py

**Files:**
- Create: `pipeline/transform/clean.py`

- [ ] **Step 1: Write the module**

```python
"""Polars cleaning pipeline for Mumbai local delay data.

Three-stage validation:
1. Schema check — required columns present
2. Range filter — delays in [-5, 120] minutes, sample_count > 0
3. Station normalization — canonical names via lookup table
4. Gap detection — flag missing 2-hour windows (not interpolated)
"""
import polars as pl

# Required columns in raw delay DataFrame
REQUIRED_COLUMNS = frozenset({
    "date", "station_name", "line", "hour", "weekday",
    "period", "avg_delay", "std_delay", "sample_count",
})

# Canonical station names (ground truth — no suffixes, proper case)
CANONICAL_STATIONS: frozenset[str] = frozenset({
    "Chhatrapati Shivaji Maharaj Terminus", "Masjid", "Sandhurst Road",
    "Byculla", "Chinchpokli", "Currey Road", "Parel", "Dadar",
    "Matunga", "Sion", "Kurla", "Vidyavihar", "Ghatkopar",
    "Vikhroli", "Kanjurmarg", "Bhandup", "Nahur", "Mulund",
    "Thane", "Kalwa", "Mumbra", "Diva", "Dombivli", "Thakurli",
    "Kalyan", "Shahad", "Ambivli", "Titwala", "Khadavli",
    "Vasind", "Asangaon", "Atgaon", "Khardi", "Umbermali",
    "Kasara", "Churchgate", "Marine Lines", "Charni Road",
    "Grant Road", "Mumbai Central", "Mahalaxmi", "Lower Parel",
    "Prabhadevi", "Andheri", "Jogeshwari", "Goregaon",
    "Malad", "Kandivali", "Borivali", "Dahisar", "Mira Road",
    "Bhayandar", "Naigaon", "Vasai Road", "Nallasopara",
    "Virar", "Lokmanya Tilak Terminus", "Panvel",
})

# Normalization lookup: raw name variants → canonical
_NAME_MAP: dict[str, str] = {
    "CSTM": "Chhatrapati Shivaji Maharaj Terminus",
    "CST": "Chhatrapati Shivaji Maharaj Terminus",
    "VT": "Chhatrapati Shivaji Maharaj Terminus",
    "LTT": "Lokmanya Tilak Terminus",
    "PNVL": "Panvel",
    "BCU": "Byculla",
}

_SUFFIXES = [" (CR)", " (WR)", " (HR)", " CR", " WR", " HR", " (C)", " (W)"]


def _normalize_name(raw: str) -> str:
    stripped = raw.strip()
    if stripped in _NAME_MAP:
        return _NAME_MAP[stripped]
    for suffix in _SUFFIXES:
        stripped = stripped.replace(suffix, "")
    return stripped.strip().title()


def validate_delays(df: pl.DataFrame) -> pl.DataFrame:
    """Stage 1+2: Schema check then range filter.

    Raises ValueError if required columns are missing.
    Filters rows where avg_delay outside [-5, 120] or sample_count <= 0.
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    return df.filter(
        pl.col("avg_delay").is_between(-5.0, 120.0)
        & (pl.col("sample_count") > 0)
    )


def normalize_stations(df: pl.DataFrame) -> pl.DataFrame:
    """Stage 3: Map raw station names to canonical form."""
    normalized = [_normalize_name(n) for n in df["station_name"].to_list()]
    return df.with_columns(pl.Series("station_name", normalized))


def detect_gaps(df: pl.DataFrame) -> pl.DataFrame:
    """Stage 4: Find (date, station) pairs missing expected hourly records.

    Returns a DataFrame of gap records — flagged but NOT interpolated.
    Missing data is surfaced in the Data Quality dashboard tab.
    """
    if len(df) == 0:
        return pl.DataFrame(schema={"date": pl.Date, "station_name": pl.String,
                                    "missing_hours": pl.List(pl.Int64)})

    # Build expected: every (date, station) should have 24 hours
    all_hours = set(range(24))
    gaps: list[dict[str, object]] = []

    grouped = df.group_by(["date", "station_name"]).agg(
        pl.col("hour").alias("present_hours")
    )

    for row in grouped.iter_rows(named=True):
        present = set(row["present_hours"])
        missing = sorted(all_hours - present)
        if missing:
            gaps.append({
                "date": row["date"],
                "station_name": row["station_name"],
                "missing_hours": missing,
            })

    if not gaps:
        return pl.DataFrame(schema={"date": pl.Date, "station_name": pl.String,
                                    "missing_hours": pl.List(pl.Int64)})
    return pl.DataFrame(gaps)


def clean_pipeline(raw: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Run the full 4-stage cleaning pipeline.

    Returns:
        (clean_df, gaps_df) — clean data and gap report.
    """
    validated = validate_delays(raw)
    normalized = normalize_stations(validated)
    gaps = detect_gaps(normalized)
    return normalized, gaps
```

- [ ] **Step 2: Run relevant tests**

```bash
uv run python -m pytest tests/test_clean.py::TestValidateDelays tests/test_clean.py::TestNormalizeStations tests/test_clean.py::TestDetectGaps -v
```

Expected: all PASSED.

---

### Task 3: Implement pipeline/transform/features.py

**Files:**
- Create: `pipeline/transform/features.py`

- [ ] **Step 1: Write the module**

```python
"""Feature engineering for Mumbai delay data.

Adds derived columns to clean DataFrames:
- ci_lower, ci_upper: 95% confidence interval around avg_delay
- on_time_pct: % of trains arriving within 2 minutes (estimated)
"""
import math

import polars as pl

# On-time threshold: delay <= this is considered "on time"
ON_TIME_THRESHOLD_MINUTES = 2.0


def add_confidence_interval(df: pl.DataFrame) -> pl.DataFrame:
    """Add 95% CI columns: ci_lower, ci_upper.

    Formula: mean ± 1.96 * (std / sqrt(n))
    Clamps ci_lower to -5.0 (physical minimum).
    """
    return df.with_columns(
        (
            pl.col("avg_delay")
            - 1.96 * pl.col("std_delay") / pl.col("sample_count").cast(pl.Float64).sqrt()
        ).clip(-5.0, 120.0).alias("ci_lower"),
        (
            pl.col("avg_delay")
            + 1.96 * pl.col("std_delay") / pl.col("sample_count").cast(pl.Float64).sqrt()
        ).clip(-5.0, 120.0).alias("ci_upper"),
    )


def add_on_time_pct(df: pl.DataFrame) -> pl.DataFrame:
    """Estimate % of trains on time (delay <= 2 min).

    Assumes Normal distribution with observed mean and std.
    P(X <= 2) using normal CDF approximation.
    """
    def normal_cdf(x: float, mean: float, std: float) -> float:
        if std <= 0:
            return 100.0 if mean <= x else 0.0
        z = (x - mean) / std
        # Abramowitz & Stegun approximation
        t = 1.0 / (1.0 + 0.2316419 * abs(z))
        poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
        cdf = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
        return (cdf if z >= 0 else 1.0 - cdf) * 100.0

    pcts = [
        normal_cdf(ON_TIME_THRESHOLD_MINUTES, row["avg_delay"], row["std_delay"])
        for row in df.iter_rows(named=True)
    ]
    return df.with_columns(pl.Series("on_time_pct", pcts))


def add_features(df: pl.DataFrame) -> pl.DataFrame:
    """Apply all feature engineering steps."""
    return add_on_time_pct(add_confidence_interval(df))
```

- [ ] **Step 2: Run feature tests**

```bash
uv run python -m pytest tests/test_clean.py::TestAddFeatures -v
```

Expected: all PASSED.

- [ ] **Step 3: Run full test suite**

```bash
uv run python -m pytest tests/ -v
```

Expected: all PASSED.

- [ ] **Step 4: Lint and type check**

```bash
uv run ruff check pipeline/transform/
uv run mypy pipeline/transform/
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add pipeline/transform/clean.py pipeline/transform/features.py tests/test_clean.py
git commit -m "feat(transform): Polars cleaning pipeline with gap detection and CI features"
```

---

### Task 4: Wire clean pipeline end-to-end (manual verification)

Requires Phase 3 to have run (delays_raw.parquet must exist).

- [ ] **Step 1: Run clean pipeline on raw data**

```bash
uv run python -c "
from pathlib import Path
import polars as pl
from pipeline.transform.clean import clean_pipeline
from pipeline.transform.features import add_features

raw = pl.read_parquet('data/raw/delays_raw.parquet')
print(f'Raw rows: {len(raw):,}')

clean, gaps = clean_pipeline(raw)
print(f'Clean rows: {len(clean):,}')
print(f'Gap records: {len(gaps)}')

featured = add_features(clean)
print('Sample with CI and on-time%:')
print(featured.select(['station_name', 'hour', 'avg_delay', 'ci_lower', 'ci_upper', 'on_time_pct']).head(5))

featured.write_parquet('data/processed/delays_clean.parquet')
print('Saved → data/processed/delays_clean.parquet')
"
```

Expected: rows close to raw count (simulation data is already valid), 0 or very few gaps, CI columns present.
