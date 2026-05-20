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
from datetime import date  # noqa: F401
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
    if upper <= 0 or actual > 2 * upper:
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
        self._model: "Prophet | None" = None  # TYPE_CHECKING guard not needed — string annotation  # noqa: F821 UP037
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
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=True,
            seasonality_mode="multiplicative",
            interval_width=0.95,
        )
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

    def detect(self, today: pl.DataFrame) -> "AnomalyResult":
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
                logger.warning("Anomaly detection failed for %s: %s", station, e)
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
