"""Download Eurostat broadband coverage (supply-side infrastructure) datasets
for the Phase E instrument-feasibility study (analysis/phase_e_broadband_iv.md).

  isoc_cbs -- coverage by speed tier (>2/>30/>100 Mbps, >1 Gbps), % households,
              total territory, country level, 2013-2025.
  isoc_cbt -- coverage by technology (DSL, VDSL, DOCSIS, FTTP, FWA, LTE, 5G, ...),
              % households, TOTAL and rural (terrtypo=DEG3), country level.
  isoc_r_broad_h -- regional household broadband ACCESS (demand-side take-up,
              NOT infrastructure; fetched only to document why it is not used).

Outputs: data/raw/eurostat/broadband_coverage_{speed,technology}.csv and
         broadband_household_access_regional.csv
Usage: python scripts/download_eurostat_broadband.py
"""
from pathlib import Path
import pandas as pd
import requests

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eurostat"
NON_COUNTRY = {"EU27_2020", "EU28", "EU27_2007", "EU15", "EA", "EA20", "EA21"}


def jsonstat_to_dataframe(payload: dict) -> pd.DataFrame:
    dims, sizes = payload["id"], payload["size"]
    cats = []
    for d, s in zip(dims, sizes):
        pos = {v: k for k, v in payload["dimension"][d]["category"]["index"].items()}
        cats.append([pos[i] for i in range(s)])
    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    rows = []
    for k, v in payload["value"].items():
        rem, rec = int(k), {}
        for d, dim in enumerate(dims):
            idx = rem // strides[d]
            rem -= idx * strides[d]
            rec[dim] = cats[d][idx]
        rec["value"] = v
        rows.append(rec)
    return pd.DataFrame(rows)


def fetch(code: str) -> pd.DataFrame:
    r = requests.get(f"{BASE}{code}?format=JSON&lang=en", timeout=180)
    r.raise_for_status()
    return jsonstat_to_dataframe(r.json())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for code, fname in [("isoc_cbs", "broadband_coverage_speed.csv"),
                        ("isoc_cbt", "broadband_coverage_technology.csv"),
                        ("isoc_r_broad_h", "broadband_household_access_regional.csv")]:
        df = fetch(code)
        n0 = len(df)
        df = df[~df["geo"].isin(NON_COUNTRY)]
        df.to_csv(OUT_DIR / fname, index=False)
        print(f"{code}: {n0} non-null cells, {len(df)} after dropping aggregates -> {fname}")


if __name__ == "__main__":
    main()
