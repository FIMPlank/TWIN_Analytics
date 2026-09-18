"""Download BLS Quarterly Census of Employment and Wages (QCEW), filtered
to "digital economy" NAICS industries -- the PRACTICAL digitalization
measure actually used by this US extension, in place of the Census ABS
technology module (blocked -- see scripts/download_census_abs_tech.py's
module docstring for why, and try that script first if you have a free
Census API key).

**Why this substitution, stated up front:** Census's Annual Business
Survey technology module (adoption of cloud/AI/robotics by businesses in
ANY sector) is conceptually the closer analog to EIBIS's digitalization
module. BLS QCEW instead measures the *employment share of NAICS
industries that are themselves part of the digital economy* (software
publishing, computing infrastructure/data processing, computer systems
design). These are DIFFERENT constructs: QCEW tells you whether a
county's economy is composed of tech-producing firms, not whether firms in
polluting/manufacturing sectors have adopted digital tools. This is a
structural/compositional proxy, not an adoption-intensity proxy -- flag
this explicitly in any analysis built on it, the same way panel_v2's QC
report flags the D35/combustion conceptual mismatch. It is used here only
because it is free, keyless, and immediately available; it is NOT a
like-for-like replacement for the brief's intended Census measure.

Source: BLS QCEW Open Data, no auth, bulk annual "singlefile" CSVs (one
per year, ALL areas x ALL industries x ALL ownership sectors in one file):

    https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip

Confirmed live: ~75-80MB per year zip, single CSV inside named
``{year}.annual.singlefile.csv``. There is also a per-area, per-quarter
REST-like path (``/cew/data/api/{year}/a/area/{fips}.csv``) but pulling
~3,200 counties x 9 years individually would be ~29,000 requests --
the bulk singlefile is fetched once per year instead and filtered locally
to the area/industry rows this analysis needs, matching the "pull, then
filter in the build step" discipline used elsewhere in this repo (e.g.
download_eurostat_dii.py pulls all 4 DII methodology versions and leaves
version selection to the build step).

Geography in the singlefile: ``area_fips`` is 5-digit. State totals use
FIPS + "000" (e.g. "06000" = California statewide); county rows use the
real county FIPS (e.g. "06001" = Alameda County). Confirmed against BLS's
own area_titles.csv lookup (fetched below and saved for reference).

**Ownership-code gotcha, found only by inspecting a raw singlefile, not
documented anywhere obvious beforehand:** QCEW's ``own_code=0`` ("Total
covered", all ownership sectors combined) is populated for
``industry_code=10`` (grand total) but is almost entirely ABSENT for
detailed NAICS industries -- a first pull using ``own_code=0`` throughout
returned zero rows for every tech industry code (51, 5112, 5182, 5415),
silently producing a tech-share panel that was 100% missing. QCEW instead
reports detailed industries broken out BY ownership sector (own_code
1=federal, 2=state, 3=local, 5=private) separately, not pre-summed. Fixed
by switching to ``own_code=5`` ("Private") throughout, for both the
numerator (tech industries) and the denominator (total, all industries) --
i.e. this measures **private-sector** tech-employment share of
**private-sector** total employment, not all-ownership. This is the
standard convention for "Total Private" QCEW series and is the right
comparison anyway (software publishers, data processing and computer
systems design are overwhelmingly private-sector industries; including
government employment in the denominator would only dilute the signal).
Also found: ``industry_code=5112`` (software publishers alone) returns
ZERO rows in the singlefile at any geography -- this specific 4-digit
detail is apparently not one of the aggregation levels BLS publishes in
the bulk annual singlefile (it likely requires the per-area API path
instead). Dropped from the kept set rather than silently left in as an
always-empty, misleading column; NAICS 51 (Information, which contains
5112) and 5415 already capture the intended construct without it.

Industries kept (own_code=5, "Private ownership"; verified against BLS's
industry_titles.csv, not guessed):
  - 10    Total, all industries (denominator)
  - 51    NAICS 51 Information (publishing, telecom, data processing --
          broad "digital economy" sector)
  - 5112  NAICS 5112 Software publishers
  - 5182  NAICS 5182 Computing infrastructure providers, data processing,
          web hosting, and related services
  - 5415  NAICS 5415 Computer systems design and related services
NOTE: 5112 and 5182 are SUBSETS of 51 (avoid double-counting if summing);
5415 sits under NAICS 54 and is NOT part of 51, so 51 + 5415 is a
non-overlapping "digital economy employment" numerator used for the tech
employment share built downstream.

Years: 2015-2023, matching the EPA GHGRP facility-emissions panel's
available range (see download_epa_ghgrp.py -- GHGRP tops out at 2023).

Usage:
    python scripts/download_bls_qcew_tech.py
"""

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "bls_qcew"
TIMEOUT = 300
YEARS = list(range(2015, 2024))  # 2015-2023 inclusive

KEEP_INDUSTRIES = {"10", "51", "5415"}
KEEP_OWN_CODE = "5"  # Private ownership -- see module docstring for why not "0"

USECOLS = [
    "area_fips",
    "own_code",
    "industry_code",
    "agglvl_code",
    "year",
    "annual_avg_estabs",
    "annual_avg_emplvl",
    "total_annual_wages",
    "avg_annual_pay",
    "disclosure_code",
]


def fetch_year(year: int) -> pd.DataFrame:
    url = f"https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_singlefile.zip"
    print(f"Downloading {url} ...")
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    print(f"  {len(r.content) / 1e6:.1f} MB downloaded, extracting ...")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = z.namelist()[0]
    with z.open(name) as f:
        df = pd.read_csv(f, usecols=USECOLS, dtype={"area_fips": str, "industry_code": str, "own_code": str})
    before = len(df)
    df = df[df["industry_code"].isin(KEEP_INDUSTRIES) & (df["own_code"] == KEEP_OWN_CODE)]
    print(f"  {before} rows in file -> {len(df)} rows kept after industry/ownership filter")
    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching area titles lookup ...")
    area_titles = pd.read_csv(
        "https://data.bls.gov/cew/doc/titles/area/area_titles.csv", dtype=str
    )
    area_titles.to_csv(OUT_DIR / "area_titles.csv", index=False)
    print(f"  saved {len(area_titles)} rows")

    print("Fetching industry titles lookup ...")
    industry_titles = pd.read_csv(
        "https://data.bls.gov/cew/doc/titles/industry/industry_titles.csv", dtype=str
    )
    industry_titles.to_csv(OUT_DIR / "industry_titles.csv", index=False)
    print(f"  saved {len(industry_titles)} rows")

    frames = []
    for year in YEARS:
        frames.append(fetch_year(year))
    all_years = pd.concat(frames, ignore_index=True)
    out_path = OUT_DIR / "qcew_tech_industries_2015_2023.csv"
    all_years.to_csv(out_path, index=False)
    print(f"Saved {len(all_years)} rows ({YEARS[0]}-{YEARS[-1]}) to {out_path}")


if __name__ == "__main__":
    main()
