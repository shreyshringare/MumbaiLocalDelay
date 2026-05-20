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
        detector.fit(history)
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
        normal = pl.DataFrame({
            "date": [date(2023, 3, 15)],
            "station_name": ["Dadar"],
            "avg_delay": [5.0],
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
            "station_name": pl.String,
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
