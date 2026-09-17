"""Download Eurostat's Digital Intensity Index (DII) by NACE Rev.2 activity,
country x sector x year -- the replacement digitalization measure for
analysis/panel_v2/ (see analysis/panel_v2/panel_qc.md for why: EIBIS's own
digitalization module only has a usable 2023-2025 window, see
analysis/first_pass_analysis.md).

Source: Eurostat's free dissemination API (JSON-stat 2.0, no auth):
    https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_e_diin2

Dataset: ``isoc_e_diin2`` -- "Digital Intensity by NACE Rev. 2 activity".
Country x NACE-sector x year, nominally 2015-2025 (checked live, not
assumed). unit=PC_ENT (% of enterprises), size_emp=GE10 (enterprises with
>=10 employees, the only breakdown this dataset offers).

IMPORTANT -- methodology-version break (verified against the live API, not
assumed from documentation): the ``indic_is`` dimension carries FOUR
incompatible versions of the Digital Intensity Index (v1 = ``E_DI_*``,
v2 = ``E_DI2_*``, v3 = ``E_DI3_*``, v4 = ``E_DI4_*``), and only one version
is populated in any given year (2018 is the sole exception, where v1 and v2
both have data). Querying non-null coverage by year+version directly against
the API gives:

    version 1 (E_DI_*)  -> 2015, 2016, 2017, 2018, 2019
    version 2 (E_DI2_*) -> 2018, 2020
    version 3 (E_DI3_*) -> 2021, 2023, 2025
    version 4 (E_DI4_*) -> 2022, 2024

So from 2021 onward the "live" version ALTERNATES by year (odd years = v3,
even years = v4) -- an important and non-obvious fact this script's output
depends on. This script fetches ALL FOUR versions' HI and VHI categories for
every year/sector/geo, and leaves the "which version is authoritative in
which year" decision to the build step (``analysis/panel_v2/build_panel.py``),
which documents and applies the exact version-in-force mapping. Do not
average or otherwise blend versions here -- that decision belongs with the
code that consumes it, next to its justification.

Headline continuous measure used downstream: % of enterprises with HIGH or
VERY HIGH digital intensity (``*_HI`` + ``*_VHI``), the standard "high
digital intensity" headline cut used in Eurostat's own Digital Economy and
Society Index reporting.

NACE sectors fetched: the ~7 industry aggregates needed for the EU-ETS
sector crosswalk (see analysis/panel_v2/panel_qc.md for the crosswalk table
and its confidence caveats) plus 'C' (manufacturing overall, for context/
descriptive use). NOT all 51 available NACE breakdowns in this dataset are
pulled -- add to NACE_SECTORS below if a later analysis needs a different
cut.

Usage:
    python scripts/download_eurostat_dii.py
"""

import json
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/isoc_e_diin2"

# NACE Rev.2 codes used in the analysis/panel_v2 EU-ETS sector crosswalm.
# See analysis/panel_v2/panel_qc.md for what each maps to and how good the
# match is.
NACE_SECTORS = [
    "C",         # Manufacturing (overall) -- context/descriptive only
    "C16-C18",   # Wood, paper & printing (broadest available cut containing paper -> ETS "paper or cardboard")
    "C19",       # Coke & refined petroleum -> ETS "Refining of mineral oil"
    "C20",       # Chemicals -> ETS "Production of bulk chemicals"
    "C22_C23",   # Rubber/plastics + other non-metallic minerals -> ETS "cement clinker" / "lime, dolomite/magnesite"
    "C24_C25",   # Basic metals + fabricated metal products -> ETS "Production of pig iron or steel"
    "D35",       # Electricity, gas, steam & air conditioning supply -> ETS "Combustion of fuels" (partial/approximate, see QC note)
]

# All four DII methodology versions' HIGH and VERY HIGH categories -- the
# version-selection logic lives in the build step, not here.
INDICATORS = [
    "E_DI_HI", "E_DI_VHI",
    "E_DI2_HI", "E_DI2_VHI",
    "E_DI3_HI", "E_DI3_VHI",
    "E_DI4_HI", "E_DI4_VHI",
]

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eurostat"
OUT_FILE = OUT_DIR / "digital_intensity_index.csv"

NON_COUNTRY_GEOS = {"EU27_2020", "EU28", "EU27_2007", "EU15", "EA", "EA20", "EA21"}


def jsonstat_to_dataframe(payload: dict) -> pd.DataFrame:
    dims = payload["id"]
    sizes = payload["size"]
    dim_categories = []
    for dim in dims:
        index = payload["dimension"][dim]["category"]["index"]
        pos_to_code = {v: k for k, v in index.items()}
        dim_categories.append([pos_to_code[i] for i in range(sizes[dims.index(dim)])])

    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    rows = []
    for flat_str, val in payload["value"].items():
        flat = int(flat_str)
        record = {}
        remainder = flat
        for d, dim in enumerate(dims):
            idx = remainder // strides[d]
            remainder -= idx * strides[d]
            record[dim] = dim_categories[d][idx]
        record["value"] = val
        rows.append(record)

    return pd.DataFrame(rows)


def fetch() -> pd.DataFrame:
    params = "&".join(f"nace_r2={s}" for s in NACE_SECTORS)
    params += "&" + "&".join(f"indic_is={i}" for i in INDICATORS)
    params += "&unit=PC_ENT"
    url = f"{BASE_URL}?format=JSON&lang=en&{params}"
    print(f"Fetching isoc_e_diin2 ({len(NACE_SECTORS)} sectors x {len(INDICATORS)} indicators) ...")
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    df = jsonstat_to_dataframe(response.json())
    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = fetch()
    before = len(df)
    df = df[~df["geo"].isin(NON_COUNTRY_GEOS)]
    print(f"Dropped {before - len(df)} EU/EA-aggregate rows, kept {len(df)} country rows")
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df)} rows to {OUT_FILE}")
    print(
        "Raw long format: freq, size_emp, nace_r2, indic_is, unit, geo, time, value. "
        "indic_is mixes 4 incompatible DII methodology versions (E_DI_*/E_DI2_*/E_DI3_*/"
        "E_DI4_*) -- version selection happens in analysis/panel_v2/build_panel.py, "
        "not here. See this script's module docstring for the verified version-by-year "
        "mapping."
    )


if __name__ == "__main__":
    main()
