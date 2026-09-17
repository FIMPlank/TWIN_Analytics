"""Download Eurostat's 5 NUTS2-regional enterprise-digitalization component
datasets, used in analysis/phase_c_analysis.py to build a regional
digitalization composite for panel v3 (region x year).

Eurostat has no ready-made regional equivalent of the country-level Digital
Intensity Index (isoc_e_diin2, used in panel v2). Instead it publishes five
separate NUTS2-region enterprise survey components, each by NACE activity x
NUTS2 region x year. All five verified live via the API (no registration):

  - isoc_r_eb_ain2   "Artificial intelligence"                    -- 2023-2025
  - isoc_r_eb_icsn2  "Integration with customers/suppliers"       -- 2023 ONLY
  - isoc_r_eb_iipn2  "Integration of internal processes"          -- 2023, 2025 (skips 2024)
  - isoc_r_ec_eseln2 "E-commerce sales"                           -- 2023-2025
  - isoc_r_eb_dan2   "Data analytics"                             -- 2023-2025

Year coverage differs BY DATASET, confirmed live, not assumed -- the
resulting composite (built in phase_c_analysis.py, not here) is therefore
built from whichever components are actually available in a given
region-year, and is explicitly a 2023-2025 (at most 3-year) regional panel,
NOT a regional equivalent of DII's 11-year country panel. See
analysis/phase_c_analysis.md for how this trade-off (far more cross-
sectional units, far less time depth) is handled.

One headline indicator was picked per dataset (the closest to "any/overall
adoption" available in that dataset; see indicator labels in each
dataset's own metadata for the full list of alternatives):

  - isoc_r_eb_ain2:   E_AI_TANY  "enterprises using at least one AI technology"
  - isoc_r_eb_icsn2:  E_INV4S_AP "enterprises sending eInvoices suitable for automated processing"
                       (closest available proxy for customer/supplier
                       integration at NUTS2 level -- this dataset has no
                       broader "any integration" indicator)
  - isoc_r_eb_iipn2:  E_BSANY    "enterprises using any business software (ERP/CRM/BI)"
  - isoc_r_ec_eseln2: E_AWSELL   "enterprises with web sales" (only indicator in this dataset)
  - isoc_r_eb_dan2:   E_DA       "data analytics performed by own staff or an external provider"

All fetched at nace_r2='C' (manufacturing, enterprises >=10 employees, the
only size_emp breakdown available), unit='PC_ENT' (% of enterprises) --
matching the country-level DII's own scope choices for direct comparability.

Usage:
    python scripts/download_eurostat_dii_regional.py
"""

from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

DATASETS = {
    "isoc_r_eb_ain2": "E_AI_TANY",
    "isoc_r_eb_icsn2": "E_INV4S_AP",
    "isoc_r_eb_iipn2": "E_BSANY",
    "isoc_r_ec_eseln2": "E_AWSELL",
    "isoc_r_eb_dan2": "E_DA",
}

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eurostat"
OUT_FILE = OUT_DIR / "dii_regional_components.csv"


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


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = []
    for dataset, indicator in DATASETS.items():
        url = f"{BASE_URL}/{dataset}?format=JSON&lang=en&nace_r2=C&unit=PC_ENT&indic_is={indicator}"
        print(f"Fetching {dataset} (indic_is={indicator}) ...")
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        df = jsonstat_to_dataframe(response.json())
        df["source_dataset"] = dataset
        frames.append(df)
        print(f"  {len(df)} rows")

    combined = pd.concat(frames, ignore_index=True, sort=False)
    # Keep only NUTS2-level geo codes (4-character, e.g. "BE21", "CZ01") --
    # the raw pull also carries country-level (2-char) and NUTS1 (3-char)
    # aggregate rows, which are not usable for the region-level panel.
    combined = combined[combined["geo"].str.len() == 4]
    combined.to_csv(OUT_FILE, index=False)
    print(f"\nSaved {len(combined)} NUTS2-level rows to {OUT_FILE}")
    print(
        "Year coverage differs by dataset (see module docstring) -- the "
        "composite built in analysis/phase_c_analysis.py handles this "
        "explicitly, averaging over whichever components exist for a given "
        "region-year rather than requiring all five."
    )


if __name__ == "__main__":
    main()
