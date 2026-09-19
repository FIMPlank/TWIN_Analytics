"""Download Eurostat regional EPO patent applications (Phase F).

Datasets (Eurostat free dissemination API, JSON-stat 2.0):
  * pat_ep_rtot -- EPO patent applications by priority year by NUTS 3 region,
                   all fields, 1977-2012, unit=NR (number; regional data are
                   assigned by INVENTOR residence with fractional counting when
                   a patent has inventors in several regions -- values like 40.7).
  * pat_ep_ripc -- same, by IPC section / class (131 categories). We fetch only
                   the classes needed for the digital / non-digital split
                   (see IPC_CODES). NOTE: counting is FRACTIONAL across IPC classes as well (verified live:
                   sections A-H sum to the IPC total, 59,024 vs 59,037 in 2004), so
                   class rows DO sum to the total and digital + non-digital = total.
The full pat_ep_ripc cube is ~3.9M cells, so we filter by IPC server-side and
request one block of years at a time. Only NUTS-3 (5-char) rows and country
(2-char) rows are kept for ripc (NUTS1/2 are recomputed by prefix summation in
the analysis, which avoids mixing hierarchy levels); rtot keeps all levels.

Usage:  python scripts/download_eurostat_patents.py
"""
from pathlib import Path
import time
import pandas as pd
import requests

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "eurostat"

# 'IPC' = total. Digital core: G06 G11 H03 H04. Broad extras: H01 G05 G08 G09.
# Sections give the non-digital comparison fields.
IPC_CODES = ["IPC", "G06", "G11", "H03", "H04", "H01", "G05", "G08", "G09",
             "A", "B", "C", "D", "E", "F", "G", "H"]


def jsonstat_to_df(p):
    dims, sizes = p["id"], p["size"]
    cats = []
    for d in dims:
        idx = p["dimension"][d]["category"]["index"]
        if isinstance(idx, list):
            idx = {c: i for i, c in enumerate(idx)}
        inv = {v: k for k, v in idx.items()}
        cats.append([inv[i] for i in range(len(idx))])
    strides = [1] * len(dims)
    for i in range(len(dims) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    vals = p["value"]
    items = vals.items() if isinstance(vals, dict) else enumerate(vals)
    rows = []
    for k, v in items:
        if v is None:
            continue
        rem = int(k)
        rec = {}
        for d, dim in enumerate(dims):
            i = rem // strides[d]
            rem -= i * strides[d]
            rec[dim] = cats[d][i]
        rec["value"] = v
        rows.append(rec)
    return pd.DataFrame(rows)


def get(url, tries=4):
    for t in range(tries):
        r = requests.get(url, timeout=300)
        if r.status_code == 200:
            return r.json()
        print("  HTTP", r.status_code, r.text[:200])
        time.sleep(5 * (t + 1))
    raise RuntimeError(url)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print("pat_ep_rtot (all fields) ...")
    pj = get(f"{BASE}pat_ep_rtot?format=JSON&lang=en&unit=NR")
    # full geo dimension (incl. regions with no non-null cell): defines the NUTS
    # vintage the patent data sit on, used for the vintage-stability QC.
    lab = pj["dimension"]["geo"]["category"]["label"]
    pd.DataFrame({"geo": list(lab), "label": list(lab.values())}).to_csv(OUT / "patents_geo_list.csv", index=False)
    d = jsonstat_to_df(pj)
    d.to_csv(OUT / "patents_regional_total.csv", index=False)
    print("  rows", len(d))
    # per-million-inhabitants version: NR / P_MHAB * 1e6 = the population Eurostat
    # itself used on the patent-side NUTS vintage -> used as a boundary-stability
    # check against the (NUTS 2021) population in nama_10r_3popgdp.
    dp = jsonstat_to_df(get(f"{BASE}pat_ep_rtot?format=JSON&lang=en&unit=P_MHAB"))
    dp[dp["geo"].str.len().isin([4, 5])].to_csv(OUT / "patents_regional_total_per_mhab.csv", index=False)
    print("  per-mhab rows", len(dp))

    ipc_q = "&".join(f"ipc={c}" for c in IPC_CODES)
    frames = []
    for y0 in range(1977, 2013, 4):
        yrs = "&".join(f"time={y}" for y in range(y0, min(y0 + 4, 2013)))
        d = jsonstat_to_df(get(f"{BASE}pat_ep_ripc?format=JSON&lang=en&unit=NR&{ipc_q}&{yrs}"))
        d = d[d["geo"].str.len().isin([2, 5])]
        print("  ripc", y0, "rows kept", len(d))
        frames.append(d)
    pd.concat(frames).to_csv(OUT / "patents_regional_ipc.csv", index=False)


if __name__ == "__main__":
    main()
