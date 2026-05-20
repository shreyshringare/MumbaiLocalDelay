"""Tests for dashboard chart factory functions."""
from datetime import date

import polars as pl
import plotly.graph_objects as go
import pytest

from dashboard.charts import (
    make_heatmap,
    make_rankings_bar,
    make_line_trend,
    make_anomaly_cards_data,
    make_business_insights,
)


@pytest.fixture
def heatmap_df() -> pl.DataFrame:
    rows = []
    for h in range(24):
        for wd in range(7):
            rows.append({
                "hour": h, "weekday": wd,
                "avg_delay": float(h % 12 + wd),
                "ci_lower": float(h % 12), "ci_upper": float(h % 12 + wd + 2),
                "n_records": 30,
            })
    return pl.DataFrame(rows)


@pytest.fixture
def rankings_df() -> pl.DataFrame:
    return pl.DataFrame({
        "station_name": ["Dadar", "Kurla", "Thane"],
        "mean_delay": [8.3, 6.1, 4.5],
        "mean_ci_lower": [7.5, 5.4, 3.9],
        "mean_ci_upper": [9.1, 6.8, 5.1],
        "mean_on_time_pct": [22.0, 35.0, 51.0],
    })


@pytest.fixture
def trend_df() -> pl.DataFrame:
    return pl.DataFrame({
        "date": [date(2024, 1, i) for i in range(1, 11)],
        "avg_delay": [5.0 + i * 0.1 for i in range(10)],
        "on_time_pct": [40.0 - i * 0.5 for i in range(10)],
    })


class TestMakeHeatmap:
    def test_returns_figure(self, heatmap_df: pl.DataFrame) -> None:
        fig = make_heatmap(heatmap_df, station="Dadar")
        assert isinstance(fig, go.Figure)

    def test_has_data(self, heatmap_df: pl.DataFrame) -> None:
        fig = make_heatmap(heatmap_df, station="Dadar")
        assert len(fig.data) > 0


class TestMakeRankingsBar:
    def test_returns_figure(self, rankings_df: pl.DataFrame) -> None:
        fig = make_rankings_bar(rankings_df, title="Worst Stations")
        assert isinstance(fig, go.Figure)

    def test_has_error_bars(self, rankings_df: pl.DataFrame) -> None:
        fig = make_rankings_bar(rankings_df, title="Test")
        trace = fig.data[0]
        assert trace.error_x is not None or trace.error_y is not None


class TestMakeLineTrend:
    def test_returns_figure(self, trend_df: pl.DataFrame) -> None:
        fig = make_line_trend(trend_df, line_name="Central")
        assert isinstance(fig, go.Figure)


class TestMakeAnomalyCardsData:
    def test_returns_list(self) -> None:
        from analysis.anomaly import AnomalyResult
        results = [
            AnomalyResult("Dadar", 45.0, 6.0, 8.0, True, "HIGH"),
            AnomalyResult("Thane", 4.0, 5.0, 7.0, False, "NORMAL"),
        ]
        cards = make_anomaly_cards_data(results)
        assert isinstance(cards, list)
        assert all(c["is_anomaly"] for c in cards)


class TestMakeBusinessInsights:
    def test_returns_dict(self) -> None:
        from pipeline.store import DelayStore
        store = DelayStore(":memory:")
        insights = make_business_insights(store)
        assert isinstance(insights, dict)
        assert "worst_station" in insights
        assert "best_line" in insights
