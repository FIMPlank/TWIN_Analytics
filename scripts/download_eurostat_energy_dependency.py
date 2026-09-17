"""Download Eurostat's energy import dependency series, country x year --
used in analysis/panel_v2/ as a country-differential energy-shock-exposure
control (replacing the "year fixed effects absorb the energy shock equally
for everyone" assumption in analysis/first_pass_analysis.md /
analysis/extension_analysis.md with actual cross-country variation in how
exposed each country was).

Source: Eurostat's free dissemination API (JSON-stat 2.0, no auth):
    https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sdg_07_50

Dataset: ``sdg_07_50`` -- "Energy import dependency by products" (SDG
indicator 7.50 series). Country x year, verified live: 2000-2024 (25 years),
unit=PC (% of gross available energy met by net imports). ``siec`` (product)
dimension offers TOTAL / solid fossil fuels / oil & petroleum ex-biofuel /
natural gas -- this script pulls siec=TOTAL, the standard "overall energy
import dependency" headline figure.

Usage:
    python scripts/download_eurostat_energy_dependency.py
"""

from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/sdg_07_50"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eurostat"
OUT_FILE = OUT_DIR / "energy_import_dependency.csv"

NON_COUNTRY_GEOS = {
    "EU27_2020", "EU28", "EU27_2007", "EU15", "EA", "EA20", "EA21",
    "AL", "BA", "GE", "MD", "ME", "MK", "RS",  # non-EU enlargement/candidate countries, out of scope
}


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
    url = f"{BASE_URL}?format=JSON&lang=en&siec=TOTAL"
    print("Fetching sdg_07_50 (siec=TOTAL) ...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    df = jsonstat_to_dataframe(response.json())
    before = len(df)
    df = df[~df["geo"].isin(NON_COUNTRY_GEOS)]
    print(f"Dropped {before - len(df)} non-EU/aggregate rows, kept {len(df)} country rows")
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df)} rows to {OUT_FILE}")


if __name__ == "__main__":
    main()
