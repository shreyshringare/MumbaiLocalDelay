"""Load and aggregate real etrain delay data for Mumbai stations.

Reads etrain_delays.csv, filters to verified Mumbai station codes,
aggregates per-station delay metrics, and writes a parquet baseline.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

# Verified Mumbai station codes present in etrain_delays.csv
MUMBAI_CODES: dict[str, tuple[str, str]] = {
    "CSTM": ("Chhatrapati Shivaji Maharaj Terminus", "Central"),
    "CSMT": ("Chhatrapati Shivaji Maharaj Terminus", "Central"),
    "DR": ("Dadar", "Central"),
    "TNA": ("Thane", "Central"),
    "KYN": ("Kalyan", "Central"),
    "LTT": ("Lokmanya Tilak Terminus", "Central"),
    "PNVL": ("Panvel", "Harbour"),
    "BSR": ("Vasai Road", "Western"),
    "VR": ("Virar", "Western"),
    "ADH": ("Andheri", "Western"),
    "BVI": ("Borivali", "Western"),
    "BDTS": ("Bandra Terminus", "Western"),
    "MMCT": ("Mumbai Central", "Western"),
}

# Lookup maps derived from MUMBAI_CODES
_CODE_TO_NAME: dict[str, str] = {code: names[0] for code, names in MUMBAI_CODES.items()}
_CODE_TO_LINE: dict[str, str] = {code: names[1] for code, names in MUMBAI_CODES.items()}


def load_mumbai_baselines(csv_path: Path) -> pl.DataFrame:
    """Read etrain_delays.csv and return per-station aggregated baselines.

    Args:
        csv_path: Path to etrain_delays.csv.

    Returns:
        DataFrame with columns: station_code, station_name, line,
        avg_delay_real, pct_right_time, pct_slight_delay,
        pct_significant_delay, sample_trains, data_source.
    """
    raw = pl.read_csv(
        csv_path,
        null_values=["", "NA", "N/A", "null"],
        infer_schema_length=2000,
    )

    # Filter to Mumbai station codes only
    mumbai_codes = list(MUMBAI_CODES.keys())
    filtered = raw.filter(pl.col("station_code").is_in(mumbai_codes))

    # Aggregate per station_code
    agg = filtered.group_by("station_code").agg(
        pl.col("average_delay_minutes").cast(pl.Float64).mean().alias("avg_delay_real"),
        pl.col("pct_right_time").cast(pl.Float64).mean().alias("pct_right_time"),
        pl.col("pct_slight_delay").cast(pl.Float64).mean().alias("pct_slight_delay"),
        pl.col("pct_significant_delay")
        .cast(pl.Float64)
        .mean()
        .alias("pct_significant_delay"),
        pl.col("train_number").n_unique().alias("sample_trains"),
    )

    # Map station_code → canonical name and line
    # replace_strict raises on unknown keys; all codes are in MUMBAI_CODES so this is safe.
    name_series = agg["station_code"].replace_strict(
        _CODE_TO_NAME,
        default=None,
        return_dtype=pl.String,
    )
    line_series = agg["station_code"].replace_strict(
        _CODE_TO_LINE,
        default=None,
        return_dtype=pl.String,
    )

    result = agg.with_columns(
        name_series.alias("station_name"),
        line_series.alias("line"),
        pl.lit("real_aggregate").alias("data_source"),
    )

    # Drop rows where avg_delay_real is null (no usable delay data)
    result = result.filter(pl.col("avg_delay_real").is_not_null())

    # Select and order final columns
    result = result.select(
        [
            "station_code",
            "station_name",
            "line",
            "avg_delay_real",
            "pct_right_time",
            "pct_slight_delay",
            "pct_significant_delay",
            "sample_trains",
            "data_source",
        ]
    )

    return result


def write_baselines(df: pl.DataFrame, out_path: Path) -> None:
    """Write baselines DataFrame to parquet, creating parent dirs as needed.

    Args:
        df: DataFrame returned by load_mumbai_baselines.
        out_path: Destination parquet path.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out_path)


if __name__ == "__main__":
    csv = Path("data/raw/real/etrain_delays.csv")
    out = Path("data/raw/real_baselines.parquet")
    df = load_mumbai_baselines(csv)
    print(f"Mumbai stations found: {df['station_name'].n_unique()}")
    print(df.select(["station_name", "line", "avg_delay_real", "sample_trains"]))
    write_baselines(df, out)
    print(f"Saved → {out}")
