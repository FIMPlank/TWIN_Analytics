"""Download EPA Greenhouse Gas Reporting Program (GHGRP) facility-level
verified emissions, via the free Envirofacts efservice API -- the US analog
to EU ETS verified emissions used in analysis/panel_v2. No auth needed.

Endpoint pattern confirmed live (NOT as scoped in the task brief -- the
brief guessed ``/TABLE/JSON`` with a ``/ROWS/START:END`` segment inserted in
the middle; the actual working pattern puts the row-range segment BEFORE
the format segment, and paths are case-sensitive on the table name only):

    https://data.epa.gov/efservice/{TABLE}/ROWS/{start}:{end}/JSON

``https://data.epa.gov/efservice/{TABLE}/JSON/ROWS/{start}:{end}`` (the form
implied by the brief) returns XML regardless of the JSON keyword's position
in some slot orderings -- verified by direct request, not assumed.

Tables used (verified against the live API, field names confirmed from an
actual response, not from documentation):

- ``PUB_DIM_FACILITY`` -- facility_id x year dimension table: lat/lon,
  state, county, county_fips (!), naics_code, facility_name. 136,005 rows
  live (one row per facility x reporting-year x program combination --
  duplicates on facility_id are expected and are collapsed downstream, not
  here). County FIPS is already attached -- no geocoding step needed,
  unlike the EU E-PRTR facility file.
- ``PUB_FACTS_SECTOR_GHG_EMISSION`` -- facility_id x year x sector_id x
  subsector_id x gas_id -> co2e_emission (already expressed in CO2e, not
  raw gas mass -- summing across gas_id within a facility-year gives total
  CO2e). 346,683 rows live.
- ``PUB_DIM_GHG`` -- gas_id -> gas_code/name lookup (17 rows, small, no
  pagination needed).
- ``PUB_DIM_SECTOR`` -- sector_id -> sector_name lookup (16 rows).

**Coverage gotcha, verified against the live API, not assumed:** GHGRP
facility-level reporting years run **2010-2023 only** as of this pull
(2026-09-17). Querying ``year/2024`` or ``year/2009`` on either table
returns zero rows -- 2024/2025 data is not yet published at facility level
(GHGRP has a real reporting lag; most recent EPA press coverage discusses
2023 as the latest full facility-level year), and 2009 predates the
program's first mandatory reporting year. This means the EPA side of the US
panel tops out one to two years earlier than the EU ETS series used
elsewhere in this repo (which runs through 2025) -- noted here so the
build step doesn't assume symmetry with the EU panels' year range.

Usage:
    python scripts/download_epa_ghgrp.py
"""

import time
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.epa.gov/efservice"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "epa_ghgrp"
PAGE_SIZE = 50_000
TIMEOUT = 120


def fetch_table(table: str, total: int | None = None) -> pd.DataFrame:
    if total is None:
        r = requests.get(f"{BASE}/{table}/COUNT/JSON", timeout=TIMEOUT)
        r.raise_for_status()
        total = r.json()[0]["TOTALQUERYRESULTS"]
    print(f"{table}: {total} rows total, fetching in pages of {PAGE_SIZE} ...")
    frames = []
    start = 0
    while start < total:
        end = min(start + PAGE_SIZE - 1, total - 1)
        url = f"{BASE}/{table}/ROWS/{start}:{end}/JSON"
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=TIMEOUT)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"  retry {attempt+1} for rows {start}:{end}: {e}")
                time.sleep(3)
        else:
            raise RuntimeError(f"Failed to fetch {table} rows {start}:{end}")
        data = r.json()
        frames.append(pd.DataFrame(data))
        print(f"  fetched rows {start}:{end} ({len(data)} records)")
        start = end + 1
    df = pd.concat(frames, ignore_index=True)
    print(f"{table}: {len(df)} rows fetched total")
    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Small lookup tables first -- no pagination needed.
    gas = pd.DataFrame(requests.get(f"{BASE}/PUB_DIM_GHG/JSON", timeout=TIMEOUT).json())
    gas.to_csv(OUT_DIR / "gas_lookup.csv", index=False)
    print(f"Saved {len(gas)} rows to gas_lookup.csv")

    sector = pd.DataFrame(requests.get(f"{BASE}/PUB_DIM_SECTOR/JSON", timeout=TIMEOUT).json())
    sector.to_csv(OUT_DIR / "sector_lookup.csv", index=False)
    print(f"Saved {len(sector)} rows to sector_lookup.csv")

    subsector = pd.DataFrame(requests.get(f"{BASE}/PUB_DIM_SUBSECTOR/JSON", timeout=TIMEOUT).json())
    subsector.to_csv(OUT_DIR / "subsector_lookup.csv", index=False)
    print(f"Saved {len(subsector)} rows to subsector_lookup.csv")

    # Large fact/dimension tables -- paginated.
    facility = fetch_table("PUB_DIM_FACILITY")
    facility.to_csv(OUT_DIR / "facilities.csv", index=False)
    print(f"Saved {len(facility)} rows to facilities.csv")

    emissions = fetch_table("PUB_FACTS_SECTOR_GHG_EMISSION")
    emissions.to_csv(OUT_DIR / "emissions.csv", index=False)
    print(f"Saved {len(emissions)} rows to emissions.csv")

    print("Done. Year range and CO2e-only filtering happen in the build step, not here.")


if __name__ == "__main__":
    main()
