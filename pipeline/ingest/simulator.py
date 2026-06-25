"""Statistical delay simulator for Mumbai Suburban Railway.

Generates realistic delay data based on known Mumbai patterns:
- Morning peak (7-11 AM): higher delays
- Evening peak (17-21 PM): higher delays
- Monsoon (June-September): +40% delays
- Central line: 15% higher than Western baseline
- Harbour line: 20% lower than Western baseline

All values are clearly simulated — disclosed in README.
"""

import hashlib
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

    # Gap probability: fraction of station-days skipped (simulates missing data)
    gap_probability: float = 0.04

    # Day-of-week multipliers (Mon=0 … Sun=6)
    dow_factors: tuple[float, ...] = (1.15, 1.05, 1.00, 1.02, 1.10, 0.80, 0.65)

    # Number of incident events injected per line per month
    incident_rate: int = 2


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


def _station_personality(station_name: str) -> float:
    """Deterministic per-station delay multiplier in [0.85, 1.25].

    Uses MD5 hash of station name — stable across Python versions and runs.
    """
    digest = int(hashlib.md5(station_name.encode()).hexdigest(), 16)
    return 0.85 + (digest % 1000) / 1000 * 0.40


def _get_incident_stations(
    year: int, month: int, line: str, stations: list[str], rate: int
) -> dict[tuple[str, "date"], float]:
    """Return dict of (station, date) -> multiplier for incident days.

    Seeded by (year, month, line) for reproducibility.
    """
    import calendar as _calendar
    rng = random.Random(f"{year}-{month}-{line}")
    _, days_in_month = _calendar.monthrange(year, month)
    incidents: dict[tuple[str, "date"], float] = {}
    if not stations:
        return incidents
    for _ in range(rate):
        station = rng.choice(stations)
        start_day = rng.randint(1, max(1, days_in_month - 2))
        multiplier = rng.uniform(2.5, 3.2)
        for offset in range(3):
            try:
                from datetime import date as _date
                d = _date(year, month, start_day + offset)
                if d.month == month:
                    incidents[(station, d)] = multiplier
            except ValueError:
                pass
    return incidents


def _is_monsoon(month: int, params: MumbaiDelayParams) -> bool:
    return month in params.monsoon_months


class DelaySimulator:
    """Generates statistically-grounded delay data for Mumbai stations."""

    def __init__(
        self,
        stops: pl.DataFrame,
        params: MumbaiDelayParams,
        baselines: dict[str, float] | None = None,
    ) -> None:
        """
        Args:
            stops: DataFrame with columns [station_name, line, ...]
            params: Mumbai delay distribution parameters
            baselines: Optional dict mapping station_name → real avg_delay (minutes).
                When provided, replaces hardcoded peak means for matching stations.
        """
        self._stops = stops
        self._params = params
        self._baselines: dict[str, float] = baselines or {}

    def generate(self, start_date: date, end_date: date) -> pl.DataFrame:
        """Generate daily delay records for every station and hour.

        Returns one row per (date, station, hour) with avg_delay, std_delay,
        sample_count, and derived columns (weekday, period).
        """
        rows: list[dict[str, object]] = []
        p = self._params
        current = start_date

        # Build line -> stations mapping for incident injection
        station_list = self._stops["station_name"].to_list()
        lines_list = self._stops["line"].to_list() if "line" in self._stops.columns else ["Western"] * len(station_list)
        line_to_stations: dict[str, list[str]] = {}
        for _st, _ln in zip(station_list, lines_list):
            line_to_stations.setdefault(str(_ln), []).append(_st)

        while current <= end_date:
            monsoon = _is_monsoon(current.month, p)
            seasonal = p.monsoon_factor if monsoon else 1.0
            weekday = current.weekday()  # 0=Monday, 6=Sunday
            dow_factor = p.dow_factors[weekday]

            for row in self._stops.iter_rows(named=True):
                # Feature 2: missing day gaps
                if random.random() < p.gap_probability:
                    continue

                station = row["station_name"]
                line = row.get("line", "Western")
                line_factor = _line_factor(str(line), p)

                # Feature 1: station personality
                personality = _station_personality(station)

                # Feature 3: incident injection
                incident_map = _get_incident_stations(
                    current.year, current.month, str(line),
                    line_to_stations.get(str(line), []), p.incident_rate
                )
                incident_mult = incident_map.get((station, current), 1.0)

                for hour in range(24):
                    period = _get_period(hour)

                    if period == "morning_peak":
                        base_mean = self._baselines.get(station, p.morning_peak_mean)
                        base_std = p.morning_peak_std
                    elif period == "evening_peak":
                        base_mean = self._baselines.get(station, p.evening_peak_mean)
                        base_std = p.evening_peak_std
                    else:
                        # Off-peak: scale real baseline down proportionally
                        real = self._baselines.get(station)
                        if real is not None:
                            base_mean = real * (p.offpeak_mean / p.morning_peak_mean)
                        else:
                            base_mean = p.offpeak_mean
                        base_std = p.offpeak_std

                    mean = base_mean * line_factor * seasonal * dow_factor * personality * incident_mult
                    std = base_std * line_factor * personality

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
