"""Prophet-based 7-day delay forecasts per station.

Architecture:
- ForecastCache pre-computes Prophet fits for every station in a background thread.
- Tab callback reads from cache dict; returns spinner if station not yet ready.
- Mirrors the existing AnomalyBatch / _anomaly_cache pattern in dashboard/app.py.
"""
from __future__ import annotations

import logging
import threading
import warnings
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from pipeline.store import DelayStore

warnings.filterwarnings("ignore", message=".*Importing plotly.*")
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

_MIN_DAYS = 30  # minimum history rows required to fit Prophet


class ForecastCache:
    """Pre-computes and caches Prophet 7-day forecasts for all stations.

    Usage:
        cache = ForecastCache()
        threading.Thread(target=cache.build, args=(store,), daemon=True).start()
        ...
        result = cache.get("Dadar")  # None until that station is computed
    """

    def __init__(self) -> None:
        self._cache: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
        self._lock = threading.Lock()
        self.ready = False

    def build(self, store: DelayStore) -> None:
        """Entry point for background thread. Fits Prophet for every station.

        Stations with fewer than _MIN_DAYS rows are silently skipped.
        Sets self.ready = True when all stations have been attempted.
        """
        from prophet import Prophet

        try:
            rows = store.conn.execute(
                "SELECT DISTINCT station_name FROM delays ORDER BY station_name"
            ).fetchall()
            station_list = [row[0] for row in rows]

            for station in station_list:
                try:
                    history = store.daily_avg(station)
                    if len(history) < _MIN_DAYS:
                        continue

                    pandas_df = history.to_pandas()
                    pandas_df = pandas_df.rename(columns={"date": "ds", "avg_delay": "y"})
                    pandas_df["ds"] = pd.to_datetime(pandas_df["ds"])

                    model = Prophet(
                        daily_seasonality=False,
                        weekly_seasonality=True,
                        yearly_seasonality=True,
                        seasonality_mode="multiplicative",
                        interval_width=0.95,
                    )
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model.fit(pandas_df)

                    future = model.make_future_dataframe(periods=7)
                    forecast = model.predict(future)

                    history_30d = pandas_df.tail(30).reset_index(drop=True)
                    last_actual_date = pandas_df["ds"].max()
                    forecast_7d = forecast[forecast["ds"] > last_actual_date].reset_index(drop=True)

                    with self._lock:
                        self._cache[station] = (history_30d, forecast_7d)

                except Exception:
                    logger.debug("Forecast skipped for %s", station, exc_info=True)

        except Exception:
            logger.exception("ForecastCache.build failed")
        finally:
            self.ready = True

    def get(self, station: str) -> tuple[pd.DataFrame, pd.DataFrame] | None:
        """Return (history_30d, forecast_7d) for station, or None if not ready."""
        with self._lock:
            return self._cache.get(station)

    def stations(self) -> list[str]:
        """Sorted list of stations that have been successfully forecast."""
        with self._lock:
            return sorted(self._cache.keys())
