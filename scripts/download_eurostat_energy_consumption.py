"""Download industrial final energy consumption, country x year -- used in
analysis/phase_d_analysis.py (item 2) to build an energy-intensity outcome
(energy consumed / industrial value-added), a more proximate mechanism test
than the emissions-change or emissions-intensity outcomes used in Phase B/C.

Source: Eurostat's free dissemination API (JSON-stat 2.0, no auth). Found by
searching Eurostat's dataset table-of-contents
(https://ec.europa.eu/eurostat/api/dissemination/catalogue/toc/txt) for
"final energy consumption", the same method used to find the Digital
Intensity Index and other Eurostat series earlier in this project.

Two candidate datasets were checked, live, before picking one:

  - ``nrg_d_indq_n`` ("Disaggregated final energy consumption in industry by
    NACE Rev. 2 activity") looked ideal (fine NACE breakdown, 2017-2024) but
    its own `nace_r2='TOTAL'` category returns an EMPTY value set for every
    country -- this "disaggregated" dataset does not publish a ready-made
    industry-wide total; only summing the ~50 individual sub-sector codes
    would produce one, with a real risk of double-counting across
    overlapping aggregate/sub-aggregate codes (the same trap flagged
    repeatedly earlier in this project for EU-ETS and DII NACE codes).
  - ``ten00124`` ("Final energy consumption by sector") instead publishes
    exactly five MUTUALLY EXCLUSIVE, pre-aggregated sector totals via its
    `nrg_bal` dimension (FC_E = total, FC_IND_E = industry, FC_TRA_E =
    transport, FC_OTH_CP_E = commercial/public services, FC_OTH_HH_E =
    households) -- no summation or double-counting risk, and a longer
    window (2013-2024, 12 years) with broader country coverage (46 geos
    including EU27_2020, UK, and non-EU comparators) than the disaggregated
    dataset would have given anyway.

This script uses ``ten00124``, ``nrg_bal='FC_IND_E'`` (industry final energy
consumption), unit=KTOE (kilotonnes of oil equivalent, Eurostat's standard
unit for this table).

Usage:
    python scripts/download_eurostat_energy_consumption.py
"""

from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ten00124"

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eurostat"
OUT_FILE = OUT_DIR / "industrial_energy_consumption.csv"


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
    url = f"{BASE_URL}?format=JSON&lang=en&nrg_bal=FC_IND_E"
    print("Fetching ten00124 (nrg_bal=FC_IND_E, industry final energy consumption) ...")
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    df = jsonstat_to_dataframe(response.json())
    df.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(df)} rows to {OUT_FILE}")
    print(f"Countries: {sorted(df['geo'].unique())}")
    print(f"Years: {sorted(df['time'].unique())}")


if __name__ == "__main__":
    main()
