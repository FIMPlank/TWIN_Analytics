"""Fetch EIBIS aggregate (country/sector-level) survey results.

Source: https://data.eib.org/eibis/
Country- and sector-level results (not firm microdata) on digitalization and
climate investment. Free, no registration. Useful for descriptive/contextual
figures while pursuing firm-level microdata access separately (see
docs/data_sources.md, "EIBIS firm-level microdata").

The download tool at https://data.eib.org/eibis/download is an interactive
picker (choose survey wave, question, breakdown) with no stable direct-file
URL, so this cannot be scripted as a plain HTTP download.

Manual steps:
  1. Open https://data.eib.org/eibis/download
  2. Select the survey wave(s) and questions/topics needed (e.g.
     digitalization module, climate/environmental investment module).
  3. Export as CSV/Excel.
  4. Save the file(s) under data/raw/eibis/

Usage:
    python scripts/download_eibis_aggregate.py
"""

from pathlib import Path

from _manual_source import check_or_instruct

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eibis"

INSTRUCTIONS = """\
1. Open https://data.eib.org/eibis/download
2. Select survey wave(s) and topics (digitalization + climate/environmental
   investment modules).
3. Export as CSV/Excel.
4. Save file(s) under data/raw/eibis/ (e.g. eibis_aggregate.csv)

Background: https://www.eib.org/en/publications-research/economics/surveys-data/eibis/about/index
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expected = [OUT_DIR / "eibis_aggregate.csv"]
    check_or_instruct(expected, INSTRUCTIONS)


if __name__ == "__main__":
    main()
