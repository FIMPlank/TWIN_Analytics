"""Download NUTS2021 level-2 region boundary polygons, used in
analysis/phase_c_analysis.py to geocode E-PRTR facilities (lat/lon points)
to their NUTS2 region via point-in-polygon.

Source: Eurostat/GISCO's free distribution service (no auth):
    https://gisco-services.ec.europa.eu/distribution/v2/nuts/

File: NUTS_RG_01M_2021_4326_LEVL_2.geojson -- level-2 (NUTS2) REGION
polygons (not "BN" boundary LINES, which is a different, unusable-for-
point-in-polygon product), highest available resolution (01M = 1:1,000,000
scale; lower resolution files like 60M risk mis-assigning points near
region borders), in CRS EPSG:4326 (plain lat/lon degrees) so it lines up
directly with E-PRTR's Longitude/Latitude columns with no reprojection.

334 NUTS2 regions as of the 2021 nomenclature, ~18MB.

Usage:
    python scripts/download_nuts2_boundaries.py
"""

from pathlib import Path

import requests

URL = "https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_01M_2021_4326_LEVL_2.geojson"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "geo"
OUT_FILE = OUT_DIR / "nuts2_2021.geojson"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {URL} ...")
    response = requests.get(URL, timeout=120)
    response.raise_for_status()
    OUT_FILE.write_bytes(response.content)
    print(f"Saved {len(response.content) / 1e6:.1f} MB to {OUT_FILE}")


if __name__ == "__main__":
    main()
