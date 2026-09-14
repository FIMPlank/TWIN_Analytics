"""Download EU ETS verified-emissions data (EUTL mirror).

Source: https://github.com/datasets/eu-emissions-trading-system
This is a community-maintained, machine-readable mirror of the EEA's
EU Emissions Trading System data from the EU Transaction Log (EUTL).
Free, public domain (ODC-PDDL-1.0), no registration required.

Pulls two resources:
  - eu-ets.csv                 installation-level verified emissions panel
  - eu-ets-sector-emissions.csv  emissions aggregated by sector and year

Usage:
    python scripts/download_eu_ets.py
"""

from pathlib import Path

import requests

BASE_URL = (
    "https://raw.githubusercontent.com/datasets/"
    "eu-emissions-trading-system/master/data"
)
RESOURCES = ["eu-ets.csv", "eu-ets-sector-emissions.csv"]

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eu_ets"


def download(resource: str) -> None:
    url = f"{BASE_URL}/{resource}"
    out_path = OUT_DIR / resource
    print(f"Downloading {url} ...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    out_path.write_bytes(response.content)
    size_mb = len(response.content) / 1_000_000
    print(f"  saved to {out_path} ({size_mb:.2f} MB)")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for resource in RESOURCES:
        download(resource)
    print("Done. See docs/data_sources.md for field descriptions.")


if __name__ == "__main__":
    main()
