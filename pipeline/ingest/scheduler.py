"""APScheduler job for daily delay data refresh."""

import logging
import os
from datetime import date
from pathlib import Path

import polars as pl
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

from pipeline.ingest.scraper import try_fetch_historical
from pipeline.ingest.simulator import DelaySimulator, MumbaiDelayParams

load_dotenv()
logger = logging.getLogger(__name__)


def refresh_daily() -> None:
    """Run daily: try real data, fallback to simulation, append to parquet."""
    raw_dir = Path(os.getenv("DATA_RAW_DIR", "data/raw"))
    stops_path = raw_dir / "stops.parquet"

    if not stops_path.exists():
        logger.error(
            f"stops.parquet not found at {stops_path}. Run station ingestion first."
        )
        return

    stops = pl.read_parquet(stops_path)
    today = date.today()

    # Try real data first
    fetched = try_fetch_historical(raw_dir)

    if not fetched:
        # Simulate today's data
        sim = DelaySimulator(stops=stops, params=MumbaiDelayParams())
        df = sim.generate(today, today)
        out_path = raw_dir / f"delays_{today.isoformat()}.parquet"
        df.write_parquet(out_path)
        logger.info(f"Simulated {len(df)} rows for {today} -> {out_path}")


def start_scheduler() -> BackgroundScheduler:
    """Start background scheduler. Runs refresh_daily at 02:00 AM daily."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(refresh_daily, "cron", hour=2, minute=0)
    scheduler.start()
    logger.info("Scheduler started: daily refresh at 02:00")
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    refresh_daily()  # run once immediately
    print("One-shot refresh complete.")
