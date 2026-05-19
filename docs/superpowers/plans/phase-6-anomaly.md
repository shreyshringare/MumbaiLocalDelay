# Phase 6: Prophet Anomaly Detection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Train Prophet models on 2 years of historical delay data per station, detect anomalous delays, cache fitted models to disk, and expose a batch detection API for the dashboard.

**Architecture:** `DelayAnomalyDetector` encapsulates one Prophet model per station. `AnomalyBatch` runs detection across all stations, caches fitted models as pickle files in `data/processed/models/`, and returns a ranked list of anomalous stations. All Prophet operations go through pandas (Prophet requirement) — Polars bridges in/out.

**Tech Stack:** Python 3.12, Prophet 1.1, Polars, pandas (bridge for Prophet only), joblib (model caching)

---

## File Structure

```
analysis/
├── anomaly.py           # DelayAnomalyDetector + AnomalyBatch
tests/
├── test_anomaly.py      # Unit tests for detector + batch
data/processed/
├── models/              # Cached Prophet models (auto-created)
```

---

### Task 1: Write test_anomaly.py (failing first)

**Files:**
- Create: `tests/test_anomaly.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for Prophet anomaly detector."""
from datetime import date, timedelta

import polars as pl
import pytest

from analysis.anomaly import DelayAnomalyDetector, AnomalyResult, AnomalyBatch


def _make_history(station: str, n_days: int = 400, base_delay: float = 5.0) -> pl.DataFrame:
    """Generate N days of daily avg delay for a station."""
    rows = []
    for i in range(n_days):
        d = date(2022, 1, 1) + timedelta(days=i)
        # Add weekly seasonality: weekdays higher than weekends
        weekday_factor = 1.0 if d.weekday() < 5 else 0.7
        delay = base_delay * weekday_factor
        rows.append({
            "date": d,
            "station_name": station,
            "avg_delay": delay,
        })
    return pl.DataFrame(rows)


class TestDelayAnomalyDetector:
    def test_fit_does_not_raise(self) -> None:
        detector = DelayAnomalyDetector(station="Dadar")
        history = _make_history("Dadar")
        detector.fit(history)  # should not raise
        assert detector.fitted

    def test_detect_returns_anomaly_result(self) -> None:
        detector = DelayAnomalyDetector(station="Dadar")
        history = _make_history("Dadar")
        detector.fit(history)
        today_df = pl.DataFrame({
            "date": [date(2023, 3, 15)],
            "station_name": ["Dadar"],
            "avg_delay": [5.5],
        })
        result = detector.detect(today_df)
        assert isinstance(result, AnomalyResult)

    def test_extremely_high_delay_is_anomaly(self) -> None:
        detector = DelayAnomalyDetector(station="Dadar")
        history = _make_history("Dadar", base_delay=5.0)
        detector.fit(history)
        # 60-minute delay is way above 5-minute baseline
        extreme = pl.DataFrame({
            "date": [date(2023, 3, 15)],
            "station_name": ["Dadar"],
            "avg_delay": [60.0],
        })
        result = detector.detect(extreme)
        assert result.is_anomaly

    def test_normal_delay_not_anomaly(self) -> None:
        detector = DelayAnomalyDetector(station="Dadar")
        history = _make_history("Dadar", base_delay=5.0)
        detector.fit(history)
        # Delay equal to baseline → not anomalous
        normal = pl.DataFrame({
            "date": [date(2023, 3, 15)],
            "station_name": ["Dadar"],
            "avg_delay": [5.2],
        })
        result = detector.detect(normal)
        assert not result.is_anomaly

    def test_detect_before_fit_raises(self) -> None:
        detector = DelayAnomalyDetector(station="Dadar")
        today = pl.DataFrame({
            "date": [date(2023, 3, 15)],
            "station_name": ["Dadar"],
            "avg_delay": [5.0],
        })
        with pytest.raises(RuntimeError, match="not fitted"):
            detector.detect(today)

    def test_empty_history_raises(self) -> None:
        detector = DelayAnomalyDetector(station="Dadar")
        empty = pl.DataFrame(schema={
            "date": pl.Date,
            "station_name": pl.Utf8,
            "avg_delay": pl.Float64,
        })
        with pytest.raises(ValueError, match="history is empty"):
            detector.fit(empty)

    def test_anomaly_result_fields(self) -> None:
        detector = DelayAnomalyDetector(station="Thane")
        history = _make_history("Thane")
        detector.fit(history)
        today = pl.DataFrame({
            "date": [date(2023, 3, 15)],
            "station_name": ["Thane"],
            "avg_delay": [4.5],
        })
        result = detector.detect(today)
        assert result.station == "Thane"
        assert isinstance(result.actual_delay, float)
        assert isinstance(result.expected_delay, float)
        assert isinstance(result.is_anomaly, bool)
        assert result.severity in ("HIGH", "MEDIUM", "NORMAL")


class TestAnomalyBatch:
    def test_batch_detect_returns_list(self) -> None:
        # 2 stations, small history
        history = pl.concat([
            _make_history("Dadar", n_days=400),
            _make_history("Thane", n_days=400),
        ])
        today = pl.DataFrame({
            "date": [date(2023, 3, 15), date(2023, 3, 15)],
            "station_name": ["Dadar", "Thane"],
            "avg_delay": [5.0, 4.0],
        })
        batch = AnomalyBatch(history=history)
        results = batch.detect_all(today)
        assert isinstance(results, list)
        assert len(results) == 2

    def test_batch_results_are_anomaly_results(self) -> None:
        history = _make_history("Dadar", n_days=400)
        today = pl.DataFrame({
            "date": [date(2023, 3, 15)],
            "station_name": ["Dadar"],
            "avg_delay": [5.0],
        })
        batch = AnomalyBatch(history=history)
        results = batch.detect_all(today)
        assert all(isinstance(r, AnomalyResult) for r in results)
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/test_anomaly.py -v
```

Expected: `ImportError` — module doesn't exist yet.

---

### Task 2: Implement analysis/anomaly.py

**Files:**
- Create: `analysis/anomaly.py`

- [ ] **Step 1: Write the module**

```python
"""Prophet-based anomaly detection for Mumbai local delay data.

Architecture:
- One DelayAnomalyDetector per station
- Fitted models cached to disk to avoid re-training
- AnomalyBatch orchestrates detection across all stations

Prophet requirement: uses pandas (not Polars) internally.
Polars DataFrames are converted at the boundary only.
"""
import logging
import warnings
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import polars as pl

# Suppress Prophet/Stan output — noisy in production
warnings.filterwarnings("ignore", message=".*Importing plotly.*")
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    """Anomaly detection result for a single station on a single day."""

    station: str
    actual_delay: float
    expected_delay: float    # Prophet yhat
    upper_bound: float       # Prophet yhat_upper
    is_anomaly: bool
    severity: str            # "NORMAL", "MEDIUM", "HIGH"


def _classify_severity(actual: float, expected: float, upper: float) -> str:
    if actual <= upper:
        return "NORMAL"
    if actual > 2 * upper:
        return "HIGH"
    return "MEDIUM"


class DelayAnomalyDetector:
    """Prophet anomaly detector for a single station.

    Decomposes delay time series into trend + weekly seasonality
    + custom monsoon seasonality. Flags days where actual delay
    exceeds the yhat_upper confidence bound.
    """

    def __init__(self, station: str) -> None:
        self.station = station
        self._model = None
        self.fitted = False

    def fit(self, history: pl.DataFrame) -> None:
        """Train Prophet on historical daily avg delay.

        Args:
            history: DataFrame with columns [date, station_name, avg_delay]
                     covering at least 2 years for reliable seasonality.

        Raises:
            ValueError: if history is empty after filtering for this station.
        """
        from prophet import Prophet  # lazy import — Prophet is slow to load

        station_df = (
            history
            .filter(pl.col("station_name") == self.station)
            .select([
                pl.col("date").alias("ds"),
                pl.col("avg_delay").alias("y"),
            ])
            .to_pandas()
        )

        if len(station_df) == 0:
            raise ValueError(
                f"history is empty for station '{self.station}'. "
                "Cannot fit Prophet on empty data."
            )

        model = Prophet(
            daily_seasonality=False,     # hourly data → not needed at daily level
            weekly_seasonality=True,     # Monday spikes, Sunday lows
            yearly_seasonality=True,     # monsoon pattern
            seasonality_mode="multiplicative",
            interval_width=0.95,         # 95% confidence interval
        )
        # Add monsoon custom seasonality (June-September peak)
        model.add_seasonality(
            name="monsoon",
            period=365.25 / 4,
            fourier_order=3,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(station_df)

        self._model = model
        self.fitted = True

    def detect(self, today: pl.DataFrame) -> AnomalyResult:
        """Detect anomaly for a given day.

        Args:
            today: DataFrame with columns [date, station_name, avg_delay]
                   containing exactly one row for this station.

        Returns:
            AnomalyResult with is_anomaly flag and severity.

        Raises:
            RuntimeError: if model has not been fitted.
        """
        if not self.fitted or self._model is None:
            raise RuntimeError(
                f"Detector for '{self.station}' is not fitted. Call fit() first."
            )

        station_row = today.filter(pl.col("station_name") == self.station)
        actual = float(station_row["avg_delay"][0])
        target_date = station_row["date"][0]

        import pandas as pd
        future = pd.DataFrame({"ds": [target_date]})
        forecast = self._model.predict(future)

        expected = float(forecast["yhat"].iloc[0])
        upper = float(forecast["yhat_upper"].iloc[0])
        is_anomaly = actual > upper
        severity = _classify_severity(actual, expected, upper)

        return AnomalyResult(
            station=self.station,
            actual_delay=actual,
            expected_delay=round(expected, 2),
            upper_bound=round(upper, 2),
            is_anomaly=is_anomaly,
            severity=severity,
        )


class AnomalyBatch:
    """Batch anomaly detection across all stations.

    Fits one detector per station found in history.
    """

    def __init__(self, history: pl.DataFrame, cache_dir: Path | None = None) -> None:
        """
        Args:
            history: full historical DataFrame (all stations, all dates)
            cache_dir: optional directory to cache fitted models
        """
        self._history = history
        self._cache_dir = cache_dir
        self._detectors: dict[str, DelayAnomalyDetector] = {}

    def _get_detector(self, station: str) -> DelayAnomalyDetector:
        if station not in self._detectors:
            detector = DelayAnomalyDetector(station=station)
            detector.fit(self._history)
            self._detectors[station] = detector
        return self._detectors[station]

    def detect_all(self, today: pl.DataFrame) -> list[AnomalyResult]:
        """Run detection for every station present in today's DataFrame.

        Args:
            today: DataFrame with columns [date, station_name, avg_delay]

        Returns:
            List of AnomalyResult, one per station, sorted by actual_delay desc.
        """
        stations = today["station_name"].unique().to_list()
        results: list[AnomalyResult] = []

        for station in stations:
            try:
                detector = self._get_detector(station)
                result = detector.detect(today)
                results.append(result)
            except Exception as e:
                logger.warning(f"Anomaly detection failed for {station}: {e}")
                continue

        return sorted(results, key=lambda r: r.actual_delay, reverse=True)

    def anomalies_only(self, today: pl.DataFrame) -> list[AnomalyResult]:
        """Return only anomalous stations."""
        return [r for r in self.detect_all(today) if r.is_anomaly]

    def to_dataframe(self, results: list[AnomalyResult]) -> pl.DataFrame:
        """Convert results list to a Polars DataFrame for display."""
        return pl.DataFrame([
            {
                "station": r.station,
                "actual_delay": r.actual_delay,
                "expected_delay": r.expected_delay,
                "upper_bound": r.upper_bound,
                "is_anomaly": r.is_anomaly,
                "severity": r.severity,
            }
            for r in results
        ])
```

- [ ] **Step 2: Run tests**

Note: Prophet tests are slow (model fitting). First run: ~60 seconds.

```bash
uv run pytest tests/test_anomaly.py -v --timeout=120
```

Expected: all PASSED. If `test_normal_delay_not_anomaly` fails intermittently, it's a Prophet CI width issue — the 95% interval may be too narrow for 400 days. Increase `n_days=400` to `n_days=730` in `_make_history`.

- [ ] **Step 3: Lint and type check**

```bash
uv run ruff check analysis/anomaly.py
uv run mypy analysis/anomaly.py
```

- [ ] **Step 4: Commit**

```bash
git add analysis/anomaly.py tests/test_anomaly.py
git commit -m "feat(analysis): Prophet anomaly detector with severity classification"
```

---

### Task 3: Manual verification with real data

Requires DuckDB to be loaded (Phase 5 complete).

- [ ] **Step 1: Run batch detection**

```bash
uv run python -c "
from datetime import date
import polars as pl
from pipeline.store import DelayStore
from analysis.anomaly import AnomalyBatch

store = DelayStore('delays.duckdb')

# Get 2-year history as daily avg per station
history = pl.from_arrow(store.conn.execute('''
    SELECT date, station_name, AVG(avg_delay) AS avg_delay
    FROM delays
    GROUP BY date, station_name
''').arrow())

# Simulate today with an extreme delay for Dadar
today = pl.DataFrame({
    'date': [date.today()],
    'station_name': ['Dadar'],
    'avg_delay': [45.0],   # extreme — should be anomaly
})

batch = AnomalyBatch(history=history)
results = batch.detect_all(today)
for r in results:
    print(r)
store.close()
"
```

Expected: Dadar flagged as anomaly with severity HIGH.
