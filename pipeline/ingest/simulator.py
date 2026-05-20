"""Statistical delay simulator for Mumbai Suburban Railway.

Generates realistic delay data based on known Mumbai patterns:
- Morning peak (7-11 AM): higher delays
- Evening peak (17-21 PM): higher delays
- Monsoon (June-September): +40% delays
- Central line: 15% higher than Western baseline
- Harbour line: 20% lower than Western baseline

All values are clearly simulated — disclosed in README.
"""

import os
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import polars as pl
from dotenv import load_dotenv


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
    central_factor: float = 1.15  # Central 15% worse than Western baseline
    western_factor: float = 1.0  # Baseline
    harbour_factor: float = 0.80  # Harbour 20% better than Western baseline

    # Seasonal factor
    monsoon_factor: float = 1.40  # June-September: +40%
    monsoon_months: frozenset[int] = field(
        default_factory=lambda: frozenset({6, 7, 8, 9})
    )

    # Trains per hour per station (determines sample_count)
    trains_per_hour: int = 15


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
            stops: DataFrame with columns [station_name, line, ...]
            params: Mumbai delay distribution parameters
        """
        self._stops = stops
        self._params = params

    def generate(self, start_date: date, end_date: date) -> pl.DataFrame:
        """Generate daily delay records for every station and hour.

        Returns one row per (date, station, hour) with avg_delay, std_delay,
        sample_count, and derived columns (weekday, period).
        """
        rows: list[dict[str, object]] = []
        p = self._params
        current = start_date

        while current <= end_date:
            monsoon = _is_monsoon(current.month, p)
            seasonal = p.monsoon_factor if monsoon else 1.0
            weekday = current.weekday()  # 0=Monday, 6=Sunday

            for row in self._stops.iter_rows(named=True):
                station = row["station_name"]
                line = row.get("line", "Western")
                line_factor = _line_factor(str(line), p)

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
                        max(-5.0, min(120.0, random.gauss(mean, std))) for _ in range(n)
                    ]
                    avg = sum(delays) / n
                    variance = sum((d - avg) ** 2 for d in delays) / max(n - 1, 1)
                    std_obs = variance**0.5

                    rows.append(
                        {
                            "date": current,
                            "station_name": station,
                            "line": line,
                            "hour": hour,
                            "weekday": weekday,
                            "period": period,
                            "avg_delay": round(avg, 2),
                            "std_delay": round(std_obs, 2),
                            "sample_count": n,
                        }
                    )

            current += timedelta(days=1)

        return pl.DataFrame(rows)


if __name__ == "__main__":
    load_dotenv()
    raw_dir = Path(os.getenv("DATA_RAW_DIR", "data/raw"))
    stops = pl.read_parquet(raw_dir / "stops.parquet")

    sim = DelaySimulator(stops=stops, params=MumbaiDelayParams())
    print("Generating 2 years of delay data...")
    df = sim.generate(date(2023, 1, 1), date(2024, 12, 31))
    out = raw_dir / "delays_raw.parquet"
    df.write_parquet(out)
    print(f"Generated {len(df):,} rows -> {out}")
    print(f"Stations: {df['station_name'].n_unique()}")
    print(f"Date range: {str(df['date'].min())} -> {str(df['date'].max())}")
    avg_delay: float = df["avg_delay"].cast(pl.Float64).mean() or 0.0  # type: ignore[assignment]
    print(f"Avg delay: {avg_delay:.2f} min")
