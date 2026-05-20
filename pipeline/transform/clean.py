"""Polars cleaning pipeline for Mumbai local delay data.

Three-stage validation:
1. Schema check — required columns present
2. Range filter — delays in [-5, 120] minutes, sample_count > 0
3. Station normalization — canonical names via lookup table
4. Gap detection — flag missing 2-hour windows (not interpolated)
"""

import polars as pl

# Required columns in raw delay DataFrame
REQUIRED_COLUMNS = frozenset(
    {
        "date",
        "station_name",
        "line",
        "hour",
        "weekday",
        "period",
        "avg_delay",
        "std_delay",
        "sample_count",
    }
)

# Canonical station names (ground truth — no suffixes, proper case)
CANONICAL_STATIONS: frozenset[str] = frozenset(
    {
        "Chhatrapati Shivaji Maharaj Terminus",
        "Masjid",
        "Sandhurst Road",
        "Byculla",
        "Chinchpokli",
        "Currey Road",
        "Parel",
        "Dadar",
        "Matunga",
        "Sion",
        "Kurla",
        "Vidyavihar",
        "Ghatkopar",
        "Vikhroli",
        "Kanjurmarg",
        "Bhandup",
        "Nahur",
        "Mulund",
        "Thane",
        "Kalwa",
        "Mumbra",
        "Diva",
        "Dombivli",
        "Thakurli",
        "Kalyan",
        "Shahad",
        "Ambivli",
        "Titwala",
        "Khadavli",
        "Vasind",
        "Asangaon",
        "Atgaon",
        "Khardi",
        "Umbermali",
        "Kasara",
        "Churchgate",
        "Marine Lines",
        "Charni Road",
        "Grant Road",
        "Mumbai Central",
        "Mahalaxmi",
        "Lower Parel",
        "Prabhadevi",
        "Andheri",
        "Jogeshwari",
        "Goregaon",
        "Malad",
        "Kandivali",
        "Borivali",
        "Dahisar",
        "Mira Road",
        "Bhayandar",
        "Naigaon",
        "Vasai Road",
        "Nallasopara",
        "Virar",
        "Lokmanya Tilak Terminus",
        "Panvel",
    }
)

# Normalization lookup: raw name variants → canonical
_NAME_MAP: dict[str, str] = {
    "CSTM": "Chhatrapati Shivaji Maharaj Terminus",
    "CST": "Chhatrapati Shivaji Maharaj Terminus",
    "VT": "Chhatrapati Shivaji Maharaj Terminus",
    "LTT": "Lokmanya Tilak Terminus",
    "PNVL": "Panvel",
    "BCU": "Byculla",
}

_SUFFIXES = [" (CR)", " (WR)", " (HR)", " CR", " WR", " HR", " (C)", " (W)"]


def _normalize_name(raw: str) -> str:
    stripped = raw.strip()
    if stripped in _NAME_MAP:
        return _NAME_MAP[stripped]
    for suffix in _SUFFIXES:
        stripped = stripped.replace(suffix, "")
    return stripped.strip().title()


def validate_delays(df: pl.DataFrame) -> pl.DataFrame:
    """Stage 1+2: Schema check then range filter.

    Raises ValueError if required columns are missing.
    Filters rows where avg_delay outside [-5, 120] or sample_count <= 0.
    """
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    return df.filter(
        pl.col("avg_delay").is_between(-5.0, 120.0) & (pl.col("sample_count") > 0)
    )


def normalize_stations(df: pl.DataFrame) -> pl.DataFrame:
    """Stage 3: Map raw station names to canonical form."""
    normalized = [_normalize_name(n) for n in df["station_name"].to_list()]
    return df.with_columns(pl.Series("station_name", normalized))


def detect_gaps(df: pl.DataFrame) -> pl.DataFrame:
    """Stage 4: Find (date, station) pairs missing expected hourly records.

    Returns a DataFrame of gap records — flagged but NOT interpolated.
    Missing data is surfaced in the Data Quality dashboard tab.
    """
    if len(df) == 0:
        return pl.DataFrame(
            schema={
                "date": pl.Date,
                "station_name": pl.String,
                "missing_hours": pl.List(pl.Int64),
            }
        )

    # Build expected: every (date, station) should have 24 hours
    all_hours = set(range(24))
    gaps: list[dict[str, object]] = []

    grouped = df.group_by(["date", "station_name"]).agg(
        pl.col("hour").alias("present_hours")
    )

    for row in grouped.iter_rows(named=True):
        present = set(row["present_hours"])
        missing = sorted(all_hours - present)
        if missing:
            gaps.append(
                {
                    "date": row["date"],
                    "station_name": row["station_name"],
                    "missing_hours": missing,
                }
            )

    if not gaps:
        return pl.DataFrame(
            schema={
                "date": pl.Date,
                "station_name": pl.String,
                "missing_hours": pl.List(pl.Int64),
            }
        )
    return pl.DataFrame(gaps)


def clean_pipeline(raw: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Run the full 4-stage cleaning pipeline.

    Returns:
        (clean_df, gaps_df) — clean data and gap report.
    """
    validated = validate_delays(raw)
    normalized = normalize_stations(validated)
    gaps = detect_gaps(normalized)
    return normalized, gaps
