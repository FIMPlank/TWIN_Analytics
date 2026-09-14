"""Download the JRC-EU-ETS-FIRMS matching dataset.

Source: https://data.jrc.ec.europa.eu/dataset/bdd1b71f-1bc8-4e65-8123-bbdd8981f116
Maps EU ETS account holders to ORBIS/Bureau van Dijk firm identifiers.
Free, no registration, CC-BY 4.0. Linking onward to actual ORBIS company
records requires separate institutional access to Bureau van Dijk/Moody's
ORBIS.

The catalogue page itself is a JS portal, but the underlying file is served
from JRC's own file server at a stable URL, so it can be downloaded directly.

Usage:
    python scripts/download_jrc_firms.py
"""

from pathlib import Path

import requests

URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EnergyUnion/"
    "JRC-EU%20ETS-FIRMS_V2_012022_public.xlsx"
)

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "jrc_firms"
OUT_FILE = OUT_DIR / "jrc_eu_ets_firms.xlsx"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {URL} ...")
    response = requests.get(URL, timeout=60)
    response.raise_for_status()
    OUT_FILE.write_bytes(response.content)
    size_mb = len(response.content) / 1_000_000
    print(f"  saved to {OUT_FILE} ({size_mb:.2f} MB)")
    print(
        "Note: this file contains ORBIS/BvD firm identifiers only. "
        "Connecting them to actual ORBIS company records requires separate "
        "institutional access to Bureau van Dijk/Moody's ORBIS."
    )


if __name__ == "__main__":
    main()
