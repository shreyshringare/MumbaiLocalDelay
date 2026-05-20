"""Authoritative Mumbai Suburban Railway station registry.

Source: Indian Railways timetables + Wikipedia station lists.
120+ stations across Central, Western, and Harbour lines.

Run directly to generate data/raw/stops.parquet:
    uv run python -m pipeline.ingest.stations
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

# fmt: off
# (name, latitude, longitude, line)
# Lines: "Central" | "Western" | "Harbour"
_STATIONS: list[tuple[str, float, float, str]] = [
    # ── Central Railway Main Line (CSTM → Kasara / Khopoli) ──────────────────
    ("Chhatrapati Shivaji Maharaj Terminus", 18.9401, 72.8353, "Central"),
    ("Masjid",                               18.9468, 72.8378, "Central"),
    ("Sandhurst Road",                       18.9530, 72.8400, "Central"),
    ("Byculla",                              18.9764, 72.8350, "Central"),
    ("Chinchpokli",                          18.9833, 72.8355, "Central"),
    ("Currey Road",                          18.9898, 72.8356, "Central"),
    ("Parel",                                19.0003, 72.8424, "Central"),
    ("Dadar",                                19.0178, 72.8435, "Central"),
    ("Matunga",                              19.0266, 72.8574, "Central"),
    ("Sion",                                 19.0392, 72.8651, "Central"),
    ("Kurla",                                19.0654, 72.8792, "Central"),
    ("Vidyavihar",                           19.0752, 72.8880, "Central"),
    ("Ghatkopar",                            19.0863, 72.9085, "Central"),
    ("Vikhroli",                             19.1059, 72.9258, "Central"),
    ("Kanjurmarg",                           19.1167, 72.9398, "Central"),
    ("Bhandup",                              19.1341, 72.9428, "Central"),
    ("Nahur",                                19.1465, 72.9491, "Central"),
    ("Mulund",                               19.1714, 72.9582, "Central"),
    ("Thane",                                19.1896, 72.9703, "Central"),
    ("Kalwa",                                19.1988, 73.0070, "Central"),
    ("Mumbra",                               19.1879, 73.0266, "Central"),
    ("Diva",                                 19.1778, 73.0570, "Central"),
    ("Kopar",                                19.1689, 73.0718, "Central"),
    ("Dombivli",                             19.2108, 73.0870, "Central"),
    ("Thakurli",                             19.2193, 73.0934, "Central"),
    ("Kalyan",                               19.2437, 73.1305, "Central"),
    ("Vithalwadi",                           19.2536, 73.1519, "Central"),
    ("Ulhasnagar",                           19.2210, 73.1600, "Central"),
    ("Ambernath",                            19.2003, 73.1891, "Central"),
    ("Badlapur",                             19.1605, 73.2344, "Central"),
    ("Ambivli",                              19.1352, 73.2755, "Central"),
    ("Vangani",                              19.1200, 73.3014, "Central"),
    ("Shelu",                                19.1012, 73.3429, "Central"),
    ("Neral",                                18.8673, 73.2989, "Central"),
    ("Bhivpuri Road",                        18.8245, 73.3176, "Central"),
    ("Karjat",                               18.9148, 73.3167, "Central"),
    ("Palasdhari",                           18.8827, 73.3463, "Central"),
    ("Khopoli",                              18.7869, 73.3413, "Central"),
    # Kasara branch (from Kalyan)
    ("Titwala",                              19.2990, 73.1938, "Central"),
    ("Khadavli",                             19.3532, 73.2266, "Central"),
    ("Wangani",                              19.3959, 73.2574, "Central"),
    ("Asangaon",                             19.4547, 73.2907, "Central"),
    ("Atgaon",                               19.5210, 73.3236, "Central"),
    ("Khardi",                               19.5681, 73.3390, "Central"),
    ("Kasara",                               19.6058, 73.4706, "Central"),

    # ── Western Railway Main Line (Churchgate → Virar) ────────────────────────
    ("Churchgate",                           18.9322, 72.8264, "Western"),
    ("Marine Lines",                         18.9416, 72.8247, "Western"),
    ("Charni Road",                          18.9523, 72.8198, "Western"),
    ("Grant Road",                           18.9638, 72.8152, "Western"),
    ("Mumbai Central",                       18.9696, 72.8192, "Western"),
    ("Mahalaxmi",                            18.9827, 72.8148, "Western"),
    ("Lower Parel",                          18.9939, 72.8230, "Western"),
    ("Elphinstone Road",                     19.0049, 72.8258, "Western"),
    ("Dadar",                                19.0220, 72.8347, "Western"),
    ("Matunga Road",                         19.0317, 72.8385, "Western"),
    ("Mahim",                                19.0406, 72.8449, "Western"),
    ("Bandra",                               19.0543, 72.8398, "Western"),
    ("Khar Road",                            19.0684, 72.8364, "Western"),
    ("Santacruz",                            19.0821, 72.8347, "Western"),
    ("Vileparle",                            19.0994, 72.8490, "Western"),
    ("Andheri",                              19.1197, 72.8464, "Western"),
    ("Jogeshwari",                           19.1378, 72.8494, "Western"),
    ("Ram Mandir",                           19.1475, 72.8534, "Western"),
    ("Goregaon",                             19.1605, 72.8496, "Western"),
    ("Malad",                                19.1864, 72.8484, "Western"),
    ("Kandivali",                            19.2047, 72.8403, "Western"),
    ("Borivali",                             19.2307, 72.8567, "Western"),
    ("Dahisar",                              19.2523, 72.8585, "Western"),
    ("Mira Road",                            19.2858, 72.8705, "Western"),
    ("Bhayandar",                            19.3003, 72.8594, "Western"),
    ("Naigaon",                              19.3564, 72.8529, "Western"),
    ("Vasai Road",                           19.3698, 72.8259, "Western"),
    ("Nala Sopara",                          19.4175, 72.8197, "Western"),
    ("Virar",                                19.4571, 72.7983, "Western"),
    # Virar → Dahanu Road (extended suburban)
    ("Vaitarna",                             19.5108, 72.7876, "Western"),
    ("Saphale",                              19.5612, 72.7690, "Western"),
    ("Kelve Road",                           19.6037, 72.7506, "Western"),
    ("Palghar",                              19.6965, 72.7657, "Western"),
    ("Boisar",                               19.7949, 72.7650, "Western"),
    ("Vangaon",                              19.8621, 72.7578, "Western"),
    ("Dahanu Road",                          19.9661, 72.7178, "Western"),

    # ── Harbour Line (CSTM → Panvel) ─────────────────────────────────────────
    ("Chhatrapati Shivaji Maharaj Terminus", 18.9401, 72.8353, "Harbour"),
    ("Masjid",                               18.9468, 72.8378, "Harbour"),
    ("Sandhurst Road",                       18.9530, 72.8400, "Harbour"),
    ("Dockyard Road",                        18.9535, 72.8446, "Harbour"),
    ("Reay Road",                            18.9573, 72.8495, "Harbour"),
    ("Cotton Green",                         18.9597, 72.8545, "Harbour"),
    ("Sewri",                                18.9719, 72.8593, "Harbour"),
    ("Wadala Road",                          18.9858, 72.8574, "Harbour"),
    ("King's Circle",                        19.0283, 72.8545, "Harbour"),
    ("Mahim Junction",                       19.0406, 72.8449, "Harbour"),
    ("Dharavi",                              19.0388, 72.8618, "Harbour"),
    ("Kurla",                                19.0654, 72.8792, "Harbour"),
    ("Tilaknagar",                           19.0745, 72.8900, "Harbour"),
    ("Chembur",                              19.0622, 72.9003, "Harbour"),
    ("Govandi",                              19.0595, 72.9148, "Harbour"),
    ("Mankhurd",                             19.0484, 72.9302, "Harbour"),
    ("Vashi",                                19.0769, 72.9987, "Harbour"),
    ("Sanpada",                              19.0704, 73.0096, "Harbour"),
    ("Juinagar",                             19.0638, 73.0185, "Harbour"),
    ("Nerul",                                19.0384, 73.0165, "Harbour"),
    ("Seawood Darave",                       19.0212, 73.0203, "Harbour"),
    ("Belapur",                              19.0218, 73.0342, "Harbour"),
    ("Kharghar",                             19.0470, 73.0599, "Harbour"),
    ("Mansarovar",                           19.0590, 73.0693, "Harbour"),
    ("Khandeshwar",                          19.0641, 73.0815, "Harbour"),
    ("Panvel",                               18.9894, 73.1141, "Harbour"),
    # Panvel → Uran (new Uran line)
    ("Kharkopar",                            19.0285, 73.0600, "Harbour"),
    ("Ukharwadi",                            18.9735, 73.1266, "Harbour"),
    ("Uran",                                 18.8748, 73.1236, "Harbour"),

    # ── Trans-Harbour Line (Thane → Panvel) ───────────────────────────────────
    ("Thane",                                19.1896, 72.9703, "Harbour"),
    ("Airoli",                               19.1565, 72.9994, "Harbour"),
    ("Rabale",                               19.1268, 73.0051, "Harbour"),
    ("Ghansoli",                             19.1163, 73.0074, "Harbour"),
    ("Kopar Khairane",                       19.1029, 73.0106, "Harbour"),
    ("Turbhe",                               19.0899, 73.0175, "Harbour"),
    ("Juinagar",                             19.0638, 73.0185, "Harbour"),  # trans-harbour branch stop

    # ── Central Harbour Line (Kurla → Wadala → CST) ───────────────────────────
    ("Chunabhatti",                          19.0499, 72.8908, "Harbour"),
    ("GTB Nagar",                            19.0454, 72.8987, "Harbour"),
    ("Tilak Nagar",                          19.0745, 72.8900, "Harbour"),
]
# fmt: on


def build_station_dataframe() -> pl.DataFrame:
    """Return the complete Mumbai Suburban station registry as a Polars DataFrame."""
    return pl.DataFrame(
        {
            "station_name": [s[0] for s in _STATIONS],
            "latitude": [s[1] for s in _STATIONS],
            "longitude": [s[2] for s in _STATIONS],
            "line": [s[3] for s in _STATIONS],
        }
    )


def write_stops_parquet(output_dir: Path | None = None) -> pl.DataFrame:
    """Write the station registry to data/raw/stops.parquet.

    Args:
        output_dir: Directory to write stops.parquet. Defaults to data/raw/.

    Returns:
        The station DataFrame written to disk.
    """
    if output_dir is None:
        output_dir = Path("data/raw")
    output_dir.mkdir(parents=True, exist_ok=True)

    df = build_station_dataframe()
    out_path = output_dir / "stops.parquet"
    df.write_parquet(out_path)
    return df


if __name__ == "__main__":
    df = write_stops_parquet()
    print(f"Wrote {len(df)} stations to data/raw/stops.parquet")
    counts = df.group_by("line").agg(pl.len().alias("count")).sort("line")
    for row in counts.iter_rows(named=True):
        print(f"  {row['line']}: {row['count']} stations")
