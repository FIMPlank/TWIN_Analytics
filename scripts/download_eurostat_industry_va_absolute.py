"""Download industrial value-added in ABSOLUTE terms (chain-linked volumes,
million EUR), country x year -- used in analysis/phase_c_analysis.py to
build an emissions-intensity outcome (verified emissions / industrial
value-added) alongside the existing raw-emissions-change outcome.

Same dataset as the existing industry-structure share
(data/raw/eurostat/industry_value_added_share.csv, from
scripts/download_eurostat.py), but with unit=CLV20_MEUR (chain-linked
volumes, million EUR, 2020 reference base) instead of unit=PC_TOT (percent
of the total economy) -- this dataset gives the euro-denominated LEVEL of
manufacturing/industry value-added, not the percentage share, which is
what an emissions-per-unit-of-output "intensity" measure needs as its
denominator.

Dataset: nama_10_a10 ("Gross value added and income by main industry, NACE
Rev.2"), na_item=B1G (gross value added), nace_r2=B-E ("Industry, including
energy" -- mining, manufacturing, energy and water supply; same aggregate
used for industry_value_added_share.csv, chosen there and here because it
overlaps with EU ETS coverage).

Usage:
    python scripts/download_eurostat_industry_va_absolute.py
"""

import json
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10_a10"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eurostat"
OUT_FILE = OUT_DIR / "industry_value_added_absolute.csv"


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
    url = f"{BASE_URL}?format=JSON&lang=en&na_item=B1G&unit=CLV20_MEUR&nace_r2=B-E"
    print("Fetching nama_10_a10 (na_item=B1G, unit=CLV20_MEUR, nace_r2=B-E) ...")
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    df = jsonstat_to_dataframe(response.json())
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df)} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()
