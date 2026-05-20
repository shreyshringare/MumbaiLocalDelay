"""Seed the DuckDB database with simulated delay data.

Run at Railway build time to populate delays.duckdb before the dashboard starts.
Uses sample stops data (committed to repo) so no external data fetch needed.
"""
from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path

import polars as pl

from pipeline.ingest.simulator import DelaySimulator, MumbaiDelayParams
from pipeline.store import DelayStore
from pipeline.transform.clean import clean_pipeline
from pipeline.transform.features import add_features

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

STOPS_PATHS = [
    Path("data/raw/stops.parquet"),
    Path("data/sample/stops_sample.parquet"),
]
DB_PATH = os.getenv("DUCKDB_PATH", "delays.duckdb")
# 1 year of data — fast to generate, enough for all analytics
START = date(2023, 6, 1)
END = date(2024, 5, 31)


def main() -> None:
    stops_path = next((p for p in STOPS_PATHS if p.exists()), None)
    if stops_path is None:
        raise FileNotFoundError(f"No stops file found. Tried: {STOPS_PATHS}")
    log.info("Using stops: %s", stops_path)

    stops = pl.read_parquet(stops_path)
    log.info("Loaded %d stations", len(stops))

    log.info("Simulating delays %s → %s ...", START, END)
    sim = DelaySimulator(stops=stops, params=MumbaiDelayParams())
    raw = sim.generate(START, END)
    log.info("Generated %d raw rows", len(raw))

    cleaned, _gaps = clean_pipeline(raw)
    log.info("After clean: %d rows", len(cleaned))

    featured = add_features(cleaned)
    log.info("After features: %d rows", len(featured))

    store = DelayStore(DB_PATH)
    store.upsert(featured)
    count = store.conn.execute("SELECT COUNT(*) FROM delays").fetchone()[0]
    log.info("DuckDB seeded: %d rows in %s", count, DB_PATH)
    store.close()


if __name__ == "__main__":
    main()
