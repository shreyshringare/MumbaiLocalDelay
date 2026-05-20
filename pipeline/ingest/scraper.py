"""Optional scraper for data.gov.in historical delay reports.

Falls back silently if the source is unavailable. Never blocks
the main pipeline — simulation is the primary data source.
"""

import io
import logging
from pathlib import Path

import httpx
import polars as pl
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# data.gov.in search URL for Mumbai suburban railway datasets
_DATAGOV_SEARCH = "https://data.gov.in/search?q=mumbai+suburban+railway"


def try_fetch_historical(output_dir: Path) -> bool:
    """Attempt to fetch historical delay CSVs from data.gov.in.

    Returns True if data was fetched, False if unavailable.
    Writes any fetched data to output_dir/historical_raw.parquet.
    """
    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.get(_DATAGOV_SEARCH, follow_redirects=True)
            response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # Look for downloadable CSV links
        csv_links = [
            a["href"]
            for a in soup.find_all("a", href=True)
            if str(a["href"]).endswith(".csv") and "railway" in str(a["href"]).lower()
        ]
        if not csv_links:
            logger.info("data.gov.in: no railway CSV links found — using simulation")
            return False

        frames: list[pl.DataFrame] = []
        for url in csv_links[:3]:  # cap at 3 files
            try:
                r = httpx.get(str(url), timeout=30.0, follow_redirects=True)
                r.raise_for_status()
                df = pl.read_csv(io.BytesIO(r.content), infer_schema_length=1000)
                frames.append(df)
                logger.info(f"Fetched {url}: {len(df)} rows")
            except Exception as e:
                logger.warning(f"Failed to fetch {url}: {e}")
                continue

        if frames:
            combined = pl.concat(frames, how="diagonal")
            output_dir.mkdir(parents=True, exist_ok=True)
            combined.write_parquet(output_dir / "historical_raw.parquet")
            logger.info(f"Saved {len(combined)} historical rows")
            return True

    except Exception as e:
        logger.info(f"data.gov.in unavailable: {e} — using simulation only")
    return False
