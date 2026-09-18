"""Download EU Cohesion Policy 2014-2020 digital-investment (ICT) declared
expenditure, country x year -- used in analysis/phase_d_analysis.py (item 1)
as the funding-timing source for an event-study / DiD design.

Source: EU Cohesion Open Data Platform, https://cohesiondata.ec.europa.eu,
a Socrata portal (free, no auth, SoQL query params:
https://cohesiondata.ec.europa.eu/resource/<dataset-id>.json).

How this dataset was found: the platform's own catalog search API
(https://cohesiondata.ec.europa.eu/api/catalog/v1?q=<term>) was queried with
"digital", "ICT", "broadband" and "recovery and resilience". The catalog
surfaces mostly pre-built chart/story assets (type="chart"/"story"), which
are NOT directly queryable -- each references its underlying raw dataset via
a `parent_fxf` field. The chart "2014-2020 Digital investments" (id
9bxn-hukz) points to the real dataset, id **3kkx-ekfq** ("2014-2020 -
Financial data - Detail by category" or similar internal name), which IS a
genuine row-level, queryable resource.

No comparable RRF (Recovery and Resilience Facility) actuals dataset was
found on this platform -- RRF disbursement tracking lives on a different EU
system (the Recovery and Resilience Scoreboard), out of scope here. This is
a checked absence, not an assumption: catalog searches for "recovery and
resilience" / "RRF" on this platform return only Cohesion-Policy-adjacent
material (e.g. REACT-EU), not RRF-specific expenditure data.

Geographic/temporal granularity (checked, not assumed):
  - `dimension_type` slices the SAME underlying expenditure by different
    breakdowns (Location, Intervention Field, Economic Activity, etc.) --
    these are NOT additive; summing across dimension_type would double-count.
    This script uses ONLY `dimension_type == "Thematic Objective"`, which for
    a given programme-year is a single, non-overlapping total (one row per
    programme's TO2 spending in that year) -- safe to sum across programmes
    within a country-year without double-counting.
  - Thematic Objective **02 = "Information & Communication Technologies"**
    (the pre-2021 Cohesion Policy's standard classification of ICT/digital
    investment) -- confirmed against the dataset's own `to`/`to_short`
    fields.
  - Data is at MEMBER STATE level in this cut (`ms`), not NUTS2/NUTS3 --
    the `dimension_type == "Location"` cut does carry regional codes, but
    only for a subset of countries/rows and cannot be relied on as a
    complete regional panel (checked: most countries report location-level
    breakdowns without ever including their own country-level total row,
    making within-country regional aggregation error-prone). Item 1
    therefore uses a COUNTRY-YEAR panel, matched against the EU-ETS
    country-level verified-emissions panel already used throughout this
    project, not the NUTS2 regional panel from Phase C.
  - Values (`eu_elig_expenditure_declared_fin_data_notional`,
    `total_elig_expenditure_declared_fin_data`) are CUMULATIVE declared
    expenditure since programme start, reported at each annual closure --
    confirmed by inspecting a full country series (monotonically
    non-decreasing for 20 of 21 countries; the one exception, UK, is
    consistent with post-Brexit programme wind-down). Annual disbursement
    FLOW is derived downstream (analysis/phase_d_analysis.py) as the
    year-over-year first difference, not computed here.
  - Years available: 2016-2023 (8 years). The underlying 2014-2020
    programming period technically starts in 2014; this dataset's earliest
    reported reference year is 2016, so any country already disbursing by
    2016 is LEFT-CENSORED in this window (true onset unknown, <=2016) --
    flagged and handled explicitly in the analysis script, not glossed over.
  - Country coverage: 21 of ~28 countries reporting a TO2 cofinancing
    programme via this dimension (checked: AT, BE, BG, DK, FI, LU, NL never
    appear -- either genuinely no ICT-earmarked ERDF/ESF spending recorded
    this way, or tracked under a different categorisation not captured by
    this cut; not investigated further given time constraints, noted as a
    coverage gap).

Usage:
    python scripts/download_cohesion_digital_funding.py
"""

from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://cohesiondata.ec.europa.eu/resource/3kkx-ekfq.json"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "cohesion"
OUT_FILE = OUT_DIR / "digital_investment_2014_2020.csv"

SELECT_COLS = (
    "ms,cci,title,fund,category_of_region,year,dimension_type,"
    "dimension_code,dimension_title,eu_cofinancing_rate,"
    "total_eligible_costs_selected_fin_data,eu_eligible_costs_selected_fin_data_notional,"
    "total_elig_expenditure_declared_fin_data,eu_elig_expenditure_declared_fin_data_notional,"
    "reference_date"
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    params = {
        "$select": SELECT_COLS,
        "to": "02",  # Thematic Objective 02 = Information & Communication Technologies
        "dimension_type": "Thematic Objective",  # single non-overlapping cut -- see module docstring
        "$limit": 5000,
    }
    print("Fetching Cohesion Policy 2014-2020 digital (TO2) expenditure "
          "(dataset 3kkx-ekfq, dimension_type='Thematic Objective') ...")
    response = requests.get(BASE_URL, params=params, timeout=120)
    response.raise_for_status()
    df = pd.DataFrame(response.json())
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df)} rows to {OUT_FILE}")
    print(f"Countries: {sorted(df['ms'].unique())}")
    print(f"Years: {sorted(df['year'].unique())}")


if __name__ == "__main__":
    main()
