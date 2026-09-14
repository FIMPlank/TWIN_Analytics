"""Fetch E-PRTR / Industrial Emissions Portal facility-level data.

Source: https://industry.eea.europa.eu/industrial-emissions/dataset
~33,000 facilities, 91 pollutants, 33 countries. Free, no registration —
but the EEA portal is a JS-driven catalogue with no stable bulk-CSV URL,
so this cannot be scripted as a plain HTTP download.

Manual steps:
  1. Open https://industry.eea.europa.eu/industrial-emissions/dataset
  2. Under "Industrial Reporting under the Industrial Emissions Directive
     2010/75/EU and European Pollutant Release and Transfer Register
     Regulation (EC) No 166/2006", choose "Download" and export the
     facility-level release/transfer table as CSV.
  3. Save the file as data/raw/eprtr/eprtr_facilities.csv

Legacy (pre-portal) dataset, also usable:
  https://www.eea.europa.eu/data-and-maps/data/member-states-reporting-art-7-under-the-european-pollutant-release-and-transfer-register-e-prtr-regulation-23

Usage:
    python scripts/download_eprtr.py
"""

from pathlib import Path

from _manual_source import check_or_instruct

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eprtr"

INSTRUCTIONS = """\
1. Open https://industry.eea.europa.eu/industrial-emissions/dataset
2. Export the facility-level release/transfer table as CSV.
3. Save it as data/raw/eprtr/eprtr_facilities.csv

Alternative (legacy) dataset page:
  https://www.eea.europa.eu/data-and-maps/data/member-states-reporting-art-7-under-the-european-pollutant-release-and-transfer-register-e-prtr-regulation-23
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    expected = [OUT_DIR / "eprtr_facilities.csv"]
    check_or_instruct(expected, INSTRUCTIONS)


if __name__ == "__main__":
    main()
