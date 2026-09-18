"""Download US Census Bureau Annual Business Survey, Module Characteristics
of Business (technology module) -- the intended US analog to EIBIS's
digitalization module. State x county x year, dataset ``absmcb``.

**BLOCKED as of this pull (2026-09-17) -- documented here rather than
silently worked around, the same way analysis/panel_v2/panel_qc.md
documents the DII version break and the EIBIS coverage gap.**

The task brief describes this as "the free Census API, no auth needed."
That is no longer true. Verified directly against the live API (not from
old documentation): **every** ``api.census.gov/data/...`` *data* query
(``get=...``), for *every* dataset tested -- not just ``absmcb`` -- now
returns an HTML "Missing Key" (no ``key=`` parameter) or "Invalid Key"
(bad ``key=`` value) error page instead of JSON. This reproduces even for
the 2020 Decennial Census PL dataset, which historically needed no key at
all, so this is a Census-API-wide policy change, not an absmcb-specific
gate. Confirmed independently via web search: Census's own current
documentation states "all data queries to the Census Data API now require
an API key" (see e.g. https://www.census.gov/data/developers/guidance/api-user-guide.html).
Dataset *metadata* endpoints (``/variables.json``, the dcat catalog JSON)
do NOT require a key and were used below to resolve the BUSCHAR code list
-- only the actual ``get=`` row-returning queries are key-gated.

A free key takes a few minutes to obtain at
https://api.census.gov/data/key_signup.html (name + email, no approval
wait per Census's own documentation) but that is a form submission with
personal data, which this script deliberately does NOT do on its own --
that decision is left to whoever runs this pipeline. Set the key as an
environment variable before running:

    export CENSUS_API_KEY=...        # bash
    $env:CENSUS_API_KEY = "..."      # PowerShell

Without a key, this script prints the BUSCHAR code list it already
resolved (via the keyless metadata calls) and exits without writing data
files, so the panel-build step can detect "not run yet" vs. "ran, found
nothing."

BUSCHAR code resolution (from the keyless ``/variables/BUSCHAR.json``
metadata call, cross-referenced against Census's own ABS technology-module
table pages -- summarized here since the code->label attribute pairing
itself requires a keyed row query to resolve empirically):
  Per Census's 2022 ABS Module: Business Characteristics documentation,
  the technology QDESC groups relevant to a digitalization measure are
  ``B14`` (cloud computing), ``B15`` (specific technologies: AI/machine
  learning, robotics, specialized software), and ``B14``-adjacent codes
  under table AB2200MCB05 ("Technology Characteristics of Businesses").
  The exact BUSCHAR values within those QDESCs (e.g. which single code
  means "uses AI") are NOT independently confirmed here -- they require a
  keyed query against BUSCHAR_LABEL, which this script performs as its
  FIRST live step once a key is present, and prints/logs before pulling
  any state/county rows, specifically so a run with a bad guess fails
  loudly rather than silently mislabeling geography rows.

Geography: state (``for=state:*``) and county (``for=county:*&in=state:*``).
Per the task brief, expect Census disclosure-avoidance suppression at
county level -- this script keeps the ``*_S`` relative-standard-error
companion columns (e.g. ``EMP_S``) alongside their point estimates so the
build step can flag/drop low-reliability cells rather than trusting all
non-null values equally.

Years available for this module per Census's ABS technology-module
documentation: 2018 (``abstcb``, one-off "Technology Characteristics of
Businesses" -- fetched as a robustness/earlier-year source, see
``fetch_abstcb_2018`` below) and 2020-2023 (``absmcb``, recurring
technology QDESC group). This script does NOT assume 2024/2025 exist;
it queries each year's ``/variables.json`` metadata (keyless) to confirm
the dataset exists before attempting a keyed pull, and skips/logs any
year that 404s at the metadata level.

Usage:
    python scripts/download_census_abs_tech.py
"""

import os
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "census_abs"
TIMEOUT = 60

ABSMCB_YEARS = [2020, 2021, 2022, 2023]
ABSTCB_YEAR = 2018

# Geography-and-identifier columns pulled alongside every technology
# variable, for both datasets.
COMMON_COLS = ["NAICS2022", "GEO_ID", "NAME"] if False else []  # resolved per-dataset below


def dataset_exists(year: int, dataset: str) -> bool:
    url = f"https://api.census.gov/data/{year}/{dataset}/variables.json"
    r = requests.get(url, timeout=TIMEOUT)
    return r.status_code == 200


def resolve_buschar_codes(year: int, dataset: str, key: str) -> pd.DataFrame:
    """Pull the full BUSCHAR/QDESC code->label crosswalk for one
    year/dataset using a minimal keyed query (national level, all codes),
    so downstream filtering to technology-adoption codes is done against
    verified labels, not a guessed code list."""
    url = (
        f"https://api.census.gov/data/{year}/{dataset}"
        f"?get=NAICS2022,BUSCHAR,BUSCHAR_LABEL,QDESC,QDESC_LABEL"
        f"&for=us:*&key={key}"
    )
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    return df.drop_duplicates(subset=["BUSCHAR", "QDESC"])


def fetch_geo(year: int, dataset: str, key: str, buschar_codes: list, for_geo: str, in_geo: str | None) -> pd.DataFrame:
    get_vars = "NAICS2022,BUSCHAR,BUSCHAR_LABEL,QDESC,EMP,EMP_S,FIRMPDEMP,FIRMPDEMP_S,EMP_PCT,EMP_PCT_S"
    buschar_filter = "&BUSCHAR=" + "&BUSCHAR=".join(buschar_codes) if buschar_codes else ""
    url = f"https://api.census.gov/data/{year}/{dataset}?get={get_vars}&for={for_geo}"
    if in_geo:
        url += f"&in={in_geo}"
    url += buschar_filter + f"&key={key}"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data[1:], columns=data[0])


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    key = os.environ.get("CENSUS_API_KEY", "").strip()

    print("Checking dataset availability (keyless metadata calls) ...")
    for year in ABSMCB_YEARS:
        print(f"  absmcb {year}: {'available' if dataset_exists(year, 'absmcb') else 'NOT FOUND'}")
    print(f"  abstcb {ABSTCB_YEAR}: {'available' if dataset_exists(ABSTCB_YEAR, 'abstcb') else 'NOT FOUND'}")

    if not key:
        print()
        print("=" * 78)
        print("BLOCKED: no CENSUS_API_KEY environment variable set.")
        print("As of this pull, api.census.gov rejects ALL data queries without a key")
        print("(a global API policy change -- see this script's module docstring).")
        print("Get a free key at https://api.census.gov/data/key_signup.html and set")
        print("CENSUS_API_KEY, then re-run this script. No files were written.")
        print("=" * 78)
        return

    for year in ABSMCB_YEARS:
        if not dataset_exists(year, "absmcb"):
            continue
        print(f"Resolving BUSCHAR codes for absmcb {year} ...")
        codes = resolve_buschar_codes(year, "absmcb", key)
        codes.to_csv(OUT_DIR / f"buschar_codes_{year}.csv", index=False)
        tech_codes = codes[codes["QDESC"].astype(str).str.startswith(("B14", "B15"))]
        code_list = sorted(tech_codes["BUSCHAR"].unique().tolist())
        print(f"  {len(code_list)} technology-adoption BUSCHAR codes found for {year}")

        print(f"Fetching state-level absmcb {year} ...")
        state_df = fetch_geo(year, "absmcb", key, code_list, "state:*", None)
        state_df.to_csv(OUT_DIR / f"absmcb_state_{year}.csv", index=False)
        print(f"  saved {len(state_df)} rows")

        print(f"Fetching county-level absmcb {year} ...")
        county_df = fetch_geo(year, "absmcb", key, code_list, "county:*", "state:*")
        county_df.to_csv(OUT_DIR / f"absmcb_county_{year}.csv", index=False)
        print(f"  saved {len(county_df)} rows")

    if dataset_exists(ABSTCB_YEAR, "abstcb"):
        print(f"Resolving BUSCHAR codes for abstcb {ABSTCB_YEAR} ...")
        codes = resolve_buschar_codes(ABSTCB_YEAR, "abstcb", key)
        codes.to_csv(OUT_DIR / f"buschar_codes_abstcb_{ABSTCB_YEAR}.csv", index=False)

    print("Done.")


if __name__ == "__main__":
    main()
