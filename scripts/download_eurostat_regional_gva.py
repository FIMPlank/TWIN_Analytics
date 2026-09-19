"""Download Eurostat regional outcome / control data (Phase F).

  * nama_10r_3gva   -- gross value added by NUTS 3 and NACE r2. We fetch
                       B-E (industry excl. construction), C (manufacturing),
                       TOTAL in units CP_MNAC (current prices, national currency),
                       PYP_MNAC (previous-year prices, national currency; lets us
                       build chain-linked VOLUME growth as PYP_t / CP_{t-1}, free of
                       exchange-rate and inflation effects) and CP_MEUR.
  * nama_10r_3empers-- employment (thousand persons) NUTS 3, TOTAL and B-E, EMP.
  * nama_10r_3popgdp-- average annual population (thousand) NUTS 3.
  * nama_10_a10     -- NATIONAL industry (B-E) GVA, current (CP_MNAC) and chain-linked
                       (CLV20_MNAC) in national currency -> national B-E deflator,
                       needed only for specifications WITHOUT country fixed effects
                       (regional PYP/volume series exist for only 9 countries, so
                       regional real growth = nominal NAC growth - national deflator).
  * nama_10r_2gdp   -- GDP per inhabitant (PPS EU27_2020 per head) NUTS 2.
Only 2000-2024 exist. NUTS vintage: NUTS 2021 (checked in analysis QC).

Usage:  python scripts/download_eurostat_regional_gva.py
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from download_eurostat_patents import get, jsonstat_to_df, BASE, OUT


def fetch(code, params, fname, geo_len=None):
    url = f"{BASE}{code}?format=JSON&lang=en&{params}"
    print(code, "...")
    d = jsonstat_to_df(get(url))
    if geo_len:
        d = d[d["geo"].str.len().isin(geo_len)]
    d.to_csv(OUT / fname, index=False)
    print("  rows", len(d))


def main():
    nace = "&".join(f"nace_r2={n}" for n in ["B-E", "C", "TOTAL"])
    fetch("nama_10r_3gva", f"{nace}&unit=CP_MNAC&unit=PYP_MNAC&unit=CP_MEUR", "regional_gva_nuts3.csv", [2, 3, 4, 5])
    fetch("nama_10r_3empers", "nace_r2=TOTAL&nace_r2=B-E&wstatus=EMP", "regional_employment_nuts3.csv", [2, 3, 4, 5])
    fetch("nama_10r_3popgdp", "", "regional_population_nuts3.csv", [2, 3, 4, 5])
    fetch("nama_10_a10", "nace_r2=B-E&nace_r2=TOTAL&na_item=B1G&unit=CP_MNAC&unit=CLV20_MNAC", "national_gva_nac.csv")
    fetch("nama_10r_2gdp", "unit=PPS_EU27_2020_HAB&unit=EUR_HAB", "regional_gdp_pc_nuts2.csv", [2, 3, 4])


if __name__ == "__main__":
    main()
