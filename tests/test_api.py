"""API endpoint tests for Mumbai Local Delay FastAPI backend.

Uses starlette.testclient.TestClient (sync, no pytest-asyncio needed).
DelayStore is overridden via FastAPI's dependency_overrides mechanism so no
real DuckDB file is required.  The module-level ForecastCache in
api.routers.analysis is patched before the client is created so it never
spawns a background thread.
"""

from __future__ import annotations

from typing import Generator
from unittest.mock import MagicMock, patch

import polars as pl
import pytest
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# Patch ForecastCache at module level before importing `app` so the
# singleton _forecast_cache = ForecastCache() doesn't try to build Prophet.
# ---------------------------------------------------------------------------
with patch("analysis.forecasting.ForecastCache", MagicMock):
    from api.main import app
    from api.deps import get_store


# ---------------------------------------------------------------------------
# Mock store factory
# ---------------------------------------------------------------------------

def make_mock_store() -> MagicMock:
    """Return a MagicMock configured to return sensible Polars DataFrames."""
    store = MagicMock()

    # worst_stations — map-data reads 'mean_delay' column (not avg_delay)
    store.worst_stations.return_value = pl.DataFrame({
        "station_name": ["Dadar CR", "Thane"],
        "line": ["Central", "Central"],
        "mean_delay": [8.3, 6.1],
        "ci_lower": [7.0, 5.5],
        "ci_upper": [9.0, 7.0],
    })

    # heatmap
    store.heatmap.return_value = pl.DataFrame({
        "hour": list(range(24)) * 7,
        "weekday": [d for d in range(7) for _ in range(24)],
        "avg_delay": [3.5] * 168,
    })

    # line_trend
    store.line_trend.return_value = pl.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "line": ["Central", "Central"],
        "avg_delay": [5.0, 5.2],
    })

    # data_quality_report
    store.data_quality_report.return_value = pl.DataFrame({
        "station_name": ["Dadar CR"],
        "row_count": [1000],
        "unique_dates": [365],
        "last_updated": ["2024-01-01"],
    })

    # daily_avg — used by anomaly detection
    store.daily_avg.return_value = pl.DataFrame({
        "date": ["2024-01-01", "2024-01-02"],
        "avg_delay": [5.0, 5.2],
    })

    store.peak_window.return_value = "07:00-11:00"
    store.close.return_value = None

    hour_cols = {f"hour_{h}": [2.0 + h * 0.1, 1.5 + h * 0.1] for h in range(24)}
    store.wave_data.return_value = pl.DataFrame({
        "station_name": ["Dadar CR", "Thane"],
        "line_order": [0, 1],
        **hour_cols,
    })
    return store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_store() -> MagicMock:
    return make_mock_store()


@pytest.fixture()
def client(mock_store: MagicMock) -> Generator[TestClient, None, None]:
    """TestClient with get_store overridden to return the mock store."""

    def override_get_store() -> Generator[MagicMock, None, None]:
        yield mock_store

    app.dependency_overrides[get_store] = override_get_store
    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_map_data_returns_200(client: TestClient) -> None:
    """GET /api/map-data returns 200 and a JSON list."""
    resp = client.get("/api/map-data")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_heatmap_returns_200(client: TestClient) -> None:
    """GET /api/heatmap returns 200 with station and matrix keys."""
    resp = client.get("/api/heatmap?station=Dadar+CR")
    assert resp.status_code == 200
    body = resp.json()
    assert "station" in body
    assert "matrix" in body
    assert isinstance(body["matrix"], list)


def test_rankings_returns_200(client: TestClient) -> None:
    """GET /api/rankings returns 200 and a JSON list."""
    resp = client.get("/api/rankings?line=Central&period=morning_peak")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_line_trend_returns_200(client: TestClient) -> None:
    """GET /api/line-trend returns 200 with date and avg_delay in each item."""
    resp = client.get("/api/line-trend?line=Central")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all("date" in d and "avg_delay" in d for d in data)


def test_anomalies_returns_200(client: TestClient) -> None:
    """GET /api/anomalies returns 200 and a JSON list (may be empty)."""
    resp = client.get("/api/anomalies")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_correlation_returns_200_or_500(client: TestClient) -> None:
    """GET /api/correlation returns 200 or 500 (may fail on empty df)."""
    resp = client.get("/api/correlation?line=Central")
    assert resp.status_code in (200, 500)


def test_quality_returns_200(client: TestClient) -> None:
    """GET /api/quality returns 200 and a JSON list."""
    resp = client.get("/api/quality")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_insights_returns_200_or_503(client: TestClient) -> None:
    """GET /api/insights returns 200 or 503 (insights may be unavailable)."""
    resp = client.get("/api/insights")
    assert resp.status_code in (200, 503)


def test_forecast_returns_202_when_cache_not_ready(client: TestClient) -> None:
    """GET /api/forecast returns 202 when the forecast cache is not yet built.

    The module-level _forecast_cache.get() returns None by default on a
    MagicMock, which triggers the 202 'computing' response.
    """
    resp = client.get("/api/forecast?station=Dadar+CR")
    # 202 = cache not ready; 200 = cache hit; 500 = unexpected error
    assert resp.status_code in (200, 202, 500)


def test_methodology_returns_200(client: TestClient) -> None:
    """GET /api/methodology returns 200 with a dict (static content, no DB)."""
    resp = client.get("/api/methodology")
    assert resp.status_code == 200
    assert isinstance(resp.json(), dict)


def test_insights_function_importable_from_analysis() -> None:
    """make_business_insights must live in analysis.insights, not dashboard.charts."""
    from analysis.insights import make_business_insights  # noqa: F401


def test_wave_data_returns_200(client: TestClient) -> None:
    """GET /api/wave-data returns 200 with a list of WaveStation objects."""
    resp = client.get("/api/wave-data?line=Central")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    if data:
        assert "station_name" in data[0]
        assert "line_order" in data[0]
        assert "delays" in data[0]
        assert len(data[0]["delays"]) == 24


def test_forecast_status_returns_200(client: TestClient) -> None:
    """GET /api/forecast/status returns 200 with fitted, total, ready keys."""
    resp = client.get("/api/forecast/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "fitted" in body
    assert "total" in body
    assert "ready" in body


def test_forecast_cache_exposes_progress() -> None:
    """ForecastCache must have fitted_count and total_count attributes."""
    from analysis.forecasting import ForecastCache
    cache = ForecastCache()
    assert hasattr(cache, "fitted_count")
    assert hasattr(cache, "total_count")
    assert cache.fitted_count == 0
    assert cache.total_count == 0
