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
            - 1.96
            * pl.col("std_delay")
            / pl.col("sample_count").cast(pl.Float64).sqrt()
        )
        .clip(-5.0, 120.0)
        .alias("ci_lower"),
        (
            pl.col("avg_delay")
            + 1.96
            * pl.col("std_delay")
            / pl.col("sample_count").cast(pl.Float64).sqrt()
        )
        .clip(-5.0, 120.0)
        .alias("ci_upper"),
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
        poly = t * (
            0.319381530
            + t
            * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429)))
        )
        cdf = 1.0 - (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
        return (cdf if z >= 0 else 1.0 - cdf) * 100.0

    pcts = [
        normal_cdf(
            ON_TIME_THRESHOLD_MINUTES, float(row["avg_delay"]), float(row["std_delay"])
        )
        for row in df.iter_rows(named=True)
    ]
    return df.with_columns(pl.Series("on_time_pct", pcts))


def add_features(df: pl.DataFrame) -> pl.DataFrame:
    """Apply all feature engineering steps."""
    return add_on_time_pct(add_confidence_interval(df))
