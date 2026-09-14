"""Fetch the JRC-EU-ETS-FIRMS matching dataset.

Source: https://data.jrc.ec.europa.eu/dataset/bdd1b71f-1bc8-4e65-8123-bbdd8981f116
Maps EU ETS account holders to ORBIS/Bureau van Dijk firm identifiers.
Free, no registration to download the mapping table itself — but linking
onward to actual ORBIS company records requires institutional access to
Bureau van Dijk/Moody's ORBIS (usually via a university library).

The JRC Data Catalogue serves files behind a JS portal with no stable
direct-download URL, so this cannot be scripted as a plain HTTP download.

Manual steps:
  1. Open https://data.jrc.ec.europa.eu/dataset/bdd1b71f-1bc8-4e65-8123-bbdd8981f116
  2. Download the firm-matching table (installation ID <-> ORBIS BvD ID).
  3. Save it as data/raw/jrc_firms/jrc_eu_ets_firms.csv

Usage:
    python scripts/download_jrc_firms.py
"""

from pathlib import Path

from _manual_source import check_or_instruct

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "jrc_firms"

INSTRUCTIONS = """\
1. Open https://data.jrc.ec.europa.eu/dataset/bdd1b71f-1bc8-4e65-8123-bbdd8981f116
2. Download the firm-matching table (installation ID <-> ORBIS BvD ID).
3. Save it as data/raw/jrc_firms/jrc_eu_ets_firms.csv

Note: connecting the BvD IDs to actual ORBIS company records requires
separate institutional access to Bureau van Dijk/Moody's ORBIS.
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expected = [OUT_DIR / "jrc_eu_ets_firms.csv"]
    check_or_instruct(expected, INSTRUCTIONS)


if __name__ == "__main__":
    main()
