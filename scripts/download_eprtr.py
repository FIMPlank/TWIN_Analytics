"""Download E-PRTR / Industrial Emissions Portal facility-level data.

Source: https://industry.eea.europa.eu/industrial-emissions/dataset
"Industrial Emissions Directive 2010/75/EU and European Pollutant Release
and Transfer Register Regulation (EC) No 166/2006" dataset (ver. 15.0,
Dec. 2025), ~33,000 facilities, 91 pollutants, 33 countries. Free, no
registration, CC-BY 4.0.

The EEA catalogue page itself is a JS portal with no stable per-file URL,
but its "Direct download" link resolves to a Nextcloud file share
(https://sdi.eea.europa.eu/data/<record-id>) which exposes individual files
at a stable pattern:
    https://sdi.eea.europa.eu/datashare/s/<token>/download?path=<folder>&files=<filename>

FILES below covers the "User-friendly-CSV" folder: national/sector/activity
aggregates (small) plus facility-level tables (large — up to ~300MB). By
default this script skips files above MAX_AUTO_MB to avoid silently pulling
hundreds of MB; pass --all to fetch everything including the big
facility-level tables.

Usage:
    python scripts/download_eprtr.py          # aggregates + mid-size tables only
    python scripts/download_eprtr.py --all     # also fetch large facility-level tables
"""

import sys
from pathlib import Path

import requests

SHARE_TOKEN = "gN8jayNx7igxeMf"
FOLDER = "User-friendly-CSV"
BASE_URL = f"https://sdi.eea.europa.eu/datashare/s/{SHARE_TOKEN}/download"

# name -> approx size in MB, from the live folder listing (ver. 15.0, Dec. 2025)
FILES = {
    "F1_1_Air_Releases_National.csv": 0.8,
    "F1_2_Air_Releases_Sector.csv": 3.5,
    "F1_3_Air_Releases_AnnexIActivity.csv": 6.5,
    "F1_4_Air_Releases_Facilities.csv": 68.9,
    "F2_1_Water_Releases_National.csv": 0.7,
    "F2_2_Water_Releases_Sector.csv": 2.8,
    "F2_3_Water_Releases_AnnexIActivity.csv": 4.9,
    "F2_4_Water_Releases_Facilities.csv": 48.0,
    "F3_1_Transfers_National.csv": 0.5,
    "F3_2_Transfers_Facilities.csv": 12.9,
    "F4_1_WasteTransfers_National.csv": 0.1,
    "F4_2_WasteTransfers_Facilities.csv": 146.4,
    "F5_1_LCP_Energy_Emissions_National.csv": 0.1,
    "F5_2_LCP_Energy_Emissions.csv": 56.7,
    "F6_1_IED_Installations.csv": 304.7,
    "F7_1_IED_WI_coWI.csv": 2.4,
}

MAX_AUTO_MB = 20  # skip files bigger than this unless --all is passed

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eprtr"


def download(filename: str) -> None:
    url = f"{BASE_URL}?path=%2F{FOLDER}&files={filename}"
    out_path = OUT_DIR / filename
    print(f"Downloading {filename} ...")
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    out_path.write_bytes(response.content)
    size_mb = len(response.content) / 1_000_000
    print(f"  saved to {out_path} ({size_mb:.2f} MB)")


def main() -> None:
    fetch_all = "--all" in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    skipped = []
    for filename, approx_mb in FILES.items():
        if not fetch_all and approx_mb > MAX_AUTO_MB:
            skipped.append(filename)
            continue
        download(filename)

    if skipped:
        print(f"\nSkipped {len(skipped)} large facility-level file(s) (>{MAX_AUTO_MB} MB):")
        for filename in skipped:
            print(f"  {filename} (~{FILES[filename]:.0f} MB)")
        print("Re-run with --all to fetch them too.")

    print(
        "\nField/table descriptions: "
        "https://sdi.eea.europa.eu/catalogue/srv/eng/catalog.search#/metadata/9405f714-8015-4b5b-a63c-280b82861b3d "
        "(see 'Information on the database structure and use')."
    )


if __name__ == "__main__":
    main()
