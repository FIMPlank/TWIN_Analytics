"""Download Eurostat country-year covariates used as controls in
analysis/extension_analysis.md: real GDP per capita, industrial value-added
share, and an industrial electricity-price series.

Source: Eurostat's free public "dissemination API" (JSON-stat 2.0, no
authentication needed):
    https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/<dataset_code>

Dataset codes used (verified by direct query -- see comments below):

- ``sdg_08_10`` -- "Real GDP per capita" (SDG indicator 8.1, chain-linked
  volumes, EUR per inhabitant, unit=CLV20_EUR_HAB). Chosen over the raw
  ``nama_10_pc`` table because it's a single, pre-selected, real-terms
  per-capita series with no extra na_item/unit disambiguation needed.
- ``nama_10_a10`` -- "Gross value added and income by main industry (NACE
  Rev.2)", filtered to na_item=B1G (gross value added), unit=PC_TOT (percent
  of the total economy), nace_r2=B-E ("Industry, including energy" --
  mining, manufacturing, energy and water supply -- the standard
  industry-structure aggregate, and the one that overlaps with EU ETS
  coverage). This is the "how industrial is this economy" control.
- ``nrg_pc_205`` -- "Electricity prices for industrial consumers"
  (semi-annual since 2007), filtered to nrg_cons=TOT_KWH (all consumption
  bands combined), tax=X_TAX (excl. taxes/levies, the most internationally
  comparable cut), currency=EUR. Used as the energy-price proxy; electricity
  (not gas) was chosen because it has much better country coverage across
  the panel's 2022-2025 window. Semi-annual (S1/S2) values are averaged to
  annual in the merge step (see analysis/analysis.py), not here -- this
  script saves the raw semi-annual series.

All three endpoints were checked directly against the API (not guessed from
documentation): each returns JSON-stat with 'EL' for Greece, matching the
convention already used for EU ETS/EIBIS/E-PRTR elsewhere in this repo, and
years running through 2025 (GDP, industry share) or 2025-S2 (electricity
price).

Usage:
    python scripts/download_eurostat.py
"""

import json
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eurostat"

DATASETS = {
    "gdp_per_capita": {
        "code": "sdg_08_10",
        "params": {"unit": "CLV20_EUR_HAB"},
        "out_file": "gdp_per_capita.csv",
    },
    "industry_value_added_share": {
        "code": "nama_10_a10",
        "params": {"na_item": "B1G", "unit": "PC_TOT", "nace_r2": "B-E"},
        "out_file": "industry_value_added_share.csv",
    },
    "industrial_electricity_price": {
        "code": "nrg_pc_205",
        "params": {"nrg_cons": "TOT_KWH", "tax": "X_TAX", "currency": "EUR"},
        "out_file": "industrial_electricity_price.csv",
    },
}


def jsonstat_to_dataframe(payload: dict) -> pd.DataFrame:
    """Flatten a JSON-stat 2.0 dataset payload into a long-format DataFrame
    with one column per dimension plus a 'value' column."""
    dims = payload["id"]
    sizes = payload["size"]
    dim_categories = []
    for dim in dims:
        index = payload["dimension"][dim]["category"]["index"]
        # index maps category code -> position; invert to position -> code
        pos_to_code = {v: k for k, v in index.items()}
        dim_categories.append([pos_to_code[i] for i in range(sizes[dims.index(dim)])])

    values = payload["value"]  # dict of flat-index (as string) -> value

    rows = []
    # JSON-stat flat index is row-major over dims in the order given by 'id',
    # with the LAST dimension varying fastest.
    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]

    for flat_str, val in values.items():
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


def fetch_dataset(code: str, params: dict) -> pd.DataFrame:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{BASE_URL}/{code}?format=JSON&lang=en&{query}"
    print(f"Fetching {code} ({query}) ...")
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    payload = response.json()
    df = jsonstat_to_dataframe(payload)
    return df


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, spec in DATASETS.items():
        df = fetch_dataset(spec["code"], spec["params"])
        out_path = OUT_DIR / spec["out_file"]
        df.to_csv(out_path, index=False)
        print(f"Saved {len(df)} rows to {out_path}")
    print(
        "\nEurostat country-year covariates for the extension analysis "
        "(GDP per capita, industry value-added share, industrial "
        "electricity price). See analysis/extension_analysis.md."
    )


if __name__ == "__main__":
    main()
