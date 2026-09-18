"""Build the US state x year and county x year panels for the Twin
Transformation US extension.

Inputs:
  - data/raw/epa_ghgrp/facilities.csv, emissions.csv, gas_lookup.csv
    (scripts/download_epa_ghgrp.py)
  - data/raw/bls_qcew/qcew_tech_industries_2015_2023.csv
    (scripts/download_bls_qcew_tech.py -- the digitalization-adjacent
    proxy used in place of the blocked Census ABS technology module; see
    that script's module docstring for why)

Outputs (analysis/output/ under this folder's own `output/` dir):
  - output/panel_state_year_us.csv
  - output/panel_county_year_us.csv

Key construction choices, stated explicitly (mirrors the discipline of
analysis/panel_v2/build_panel.py):

1. **Biogenic CO2 excluded from the emissions total.** GHGRP's gas_id=8
   ("Biogenic CO2") is reported separately from fossil CO2/CH4/N2O/etc.
   under US GHG-inventory convention (biogenic CO2 is typically excluded
   from regulatory/reporting totals because it's treated as part of the
   natural carbon cycle) -- the same exclusion logic
   analysis/first_pass_analysis.md applied to E-PRTR's biomass CO2 in the
   EU data. `total_co2e` here = sum of co2e_emission across all gas_id
   EXCEPT 8.
1b. **"Supplier" sectors excluded -- the single most important data-quality
   finding in this build, the US analog of the EU project's `20-99`
   double-count trap.** GHGRP's `PUB_DIM_SECTOR` table carries a
   `sector_type` field: `E` = direct Emitter (Power Plants, Refineries,
   Chemicals, Metals, Pulp and Paper, Minerals, Waste, Petroleum and
   Natural Gas Systems, Other), `S` = fuel/gas Supplier (Petroleum Product
   Suppliers, Natural Gas and NGL Suppliers, Industrial Gas Suppliers, CO2
   Suppliers, Coal-based Liquid Fuel Supply, import/export of fluorinated-
   GHG equipment), `I` = CO2 Injection (its own category -- injected, not
   emitted). **Unweighted, the two largest sectors in the raw emissions
   table by a wide margin are BOTH suppliers**: "Petroleum Product
   Suppliers" (Subpart MM) and "Natural Gas and NGL Suppliers" (Subpart
   NN) report the *potential* CO2e content of fuel they supply into
   commerce -- an upstream, national-accounting-style quantity, not a
   facility's own combustion/process emissions, and NOT the same concept
   as EU ETS's installation-level verified emissions. A small number of
   large supplier facilities (refineries' bulk product terminals, gas
   processing hubs) would otherwise dominate any county/state aggregate by
   construction, unrelated to that area's actual industrial activity.
   **Fix: `emissions` is filtered to `sector_type == 'E'` (direct emitters
   only) before any aggregation** -- confirmed by checking
   `facilities.facility_types`, which independently carries an explicit
   "Supplier" vs. "Direct Emitter" tag agreeing with the sector-level
   classification. CO2 Injection (`sector_type == 'I'`, 894 facility-years,
   $6.4\times10^7$ t CO2e total, <0.1% of the unfiltered total) is also
   excluded on the same logic -- injected CO2 is not an atmospheric
   emission.
2. **State/county FIPS derived from EPA's own `county_fips` field, not a
   separate crosswalk.** `state_fips = county_fips[:2]`. This avoids
   introducing a second geographic reconciliation step (unlike the EU
   analyses, which needed a real country-code crosswalk between ETS/EIBIS/
   E-PRTR) -- one clean advantage of GHGRP's facility file over E-PRTR's.
3. **Facility-year duplicates in PUB_DIM_FACILITY are collapsed by taking
   the first row per (facility_id, year)** before merging -- the raw table
   has one row per (facility_id, year, PROGRAM_NAME) combination, and
   county/state/NAICS are constant across those duplicate rows for a given
   facility-year (spot-checked, not assumed).
4. **QCEW tech employment share** = (emplvl NAICS 51 + emplvl NAICS 5415)
   / emplvl NAICS 10 (total), own_code=5 (private ownership -- see
   scripts/download_bls_qcew_tech.py's docstring for why own_code=0
   returns no rows for detailed industries). Missing/zero
   denominator or numerator suppressed by BLS disclosure rules
   (`disclosure_code` non-null on the underlying row) is propagated as
   NaN, not zero -- the same fix panel_v2's QC report had to retrofit for
   Eurostat DII after finding a silent fillna(0) bug; done correctly from
   the start here.
5. **`d_log_emissions`** = year-over-year change in log(total_co2e) within
   each county/state's own time series -- identical construction to the EU
   panels' outcome variable, for direct comparability.
"""

from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent.parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent / "output"

BIOGENIC_GAS_ID = 8
TECH_INDUSTRIES = {"51", "5415"}
TOTAL_INDUSTRY = "10"


def load_facility_emissions() -> pd.DataFrame:
    facilities = pd.read_csv(RAW / "epa_ghgrp" / "facilities.csv", dtype={"county_fips": str}, low_memory=False)
    emissions = pd.read_csv(RAW / "epa_ghgrp" / "emissions.csv")
    sector = pd.read_csv(RAW / "epa_ghgrp" / "sector_lookup.csv")

    # Collapse facility-year duplicates (multiple PROGRAM_NAME rows).
    fac_cols = ["facility_id", "year", "state", "county", "county_fips", "naics_code", "latitude", "longitude"]
    facilities = facilities[fac_cols].drop_duplicates(subset=["facility_id", "year"], keep="first")

    # Direct emitters only (sector_type == 'E') -- excludes "Supplier"
    # sectors (upstream fuel-supply potential emissions, not facility
    # emissions) and CO2 Injection (not an atmospheric emission). See the
    # module docstring, point 1b, for why this matters a great deal here.
    emitter_sector_ids = sector.loc[sector["sector_type"] == "E", "sector_id"].tolist()
    em = emissions[emissions["sector_id"].isin(emitter_sector_ids)]
    before_filter = emissions["co2e_emission"].sum()
    after_filter = em["co2e_emission"].sum()
    print(f"Sector filter (direct emitters only): {after_filter/before_filter:.1%} of raw co2e_emission mass kept "
          f"({after_filter:.3e} of {before_filter:.3e} t CO2e)")

    # Total CO2e per facility-year, excluding biogenic CO2 (gas_id=8).
    #
    # REVIEW FIX (round 3, R1, blocking): this exclusion filter was
    # ACCIDENTALLY DELETED during the round-2 min_count=1 edit -- the
    # BIOGENIC_GAS_ID constant and the surrounding comments survived, but
    # the actual `em = em[em["gas_id"] != BIOGENIC_GAS_ID]` line did not,
    # so round 2's delivered panels silently included biogenic CO2 (a
    # Reviewer round-2 pass rebuilt the panel both ways and matched the
    # published CSVs exactly to the WITH-biogenic reconstruction: 27,955/
    # 27,955 county rows, 756/756 state rows). Biogenic is 4.67% of
    # direct-emitter mass, concentrated in pulp/paper and biomass-co-firing
    # facilities specifically (not random) and trending over the period --
    # restored here, with an explicit assertion below so this exact filter
    # cannot silently vanish again without the build failing loudly.
    em = em[em["gas_id"] != BIOGENIC_GAS_ID]
    assert (em["gas_id"] == BIOGENIC_GAS_ID).sum() == 0, "biogenic CO2 filter did not take effect"

    # REVIEW FIX (round 2, B3, blocking): a facility-year whose remaining
    # emission rows are ALL NaN was silently becoming co2e_emission == 0.0
    # under a bare `.sum()` (pandas treats an all-NaN group's sum as 0, not
    # NaN). This affected 15.8% of direct-emitter facility-years overall,
    # with a strong time trend (0% in 2010-2012 rising to 28.5% by 2023).
    # `min_count=1` makes an all-NaN group sum to NaN instead. **Round-3
    # correction, per Reviewer R2:** this fix turned out to be a
    # mathematical no-op for `d_log_emissions` specifically (the affected
    # cells already produced `log(0)` -> NaN via the `.where(total > 0)`
    # guard below either way) -- it is still correct and retained (it
    # protects `total_co2e` in levels, and any future use of that column
    # in isolation), but it is not the reason any headline number moved
    # between rounds. The reason C1 moved was the biogenic-filter deletion
    # above, restored in this round.
    em_agg = em.groupby(["facility_id", "year"], as_index=False)["co2e_emission"].sum(min_count=1)
    em_agg = em_agg.rename(columns={"co2e_emission": "total_co2e"})

    # Also carry sector_code per facility-year (for the PETRO_NG robustness
    # cut, S2 -- Subpart W "Petroleum and Natural Gas Systems" is reported
    # at basin/operator level for onshore production and gathering &
    # boosting, i.e. a multi-county upstream aggregate booked to a single
    # county, the same error *type* as the supplier catch above, one level
    # down within the direct-emitter set). A facility can appear across
    # more than one sector_id in principle; flag a facility-year as
    # "PETRO_NG" if ANY of its retained emission rows carry that sector.
    sector_code_map = sector.set_index("sector_id")["sector_code"]
    em = em.copy()
    em["sector_code"] = em["sector_id"].map(sector_code_map)
    petro_ng_flag = (
        em.groupby(["facility_id", "year"])["sector_code"]
        .apply(lambda s: bool((s == "PETRO_NG").any()))
        .rename("is_petro_ng")
        .reset_index()
    )
    em_agg = em_agg.merge(petro_ng_flag, on=["facility_id", "year"], how="left")

    merged = em_agg.merge(facilities, on=["facility_id", "year"], how="left")
    merged["county_fips"] = merged["county_fips"].astype(str).str.zfill(5)
    merged = merged[merged["county_fips"].str.len() == 5]
    merged["state_fips"] = merged["county_fips"].str[:2]
    return merged


def load_qcew_tech_share() -> pd.DataFrame:
    qcew = pd.read_csv(RAW / "bls_qcew" / "qcew_tech_industries_2015_2023.csv", dtype={"area_fips": str, "industry_code": str})
    # annual_avg_emplvl can load as object dtype from the raw BLS file (mixed
    # numeric/blank cells) -- coerce explicitly rather than trust pandas'
    # inferred dtype.
    qcew["annual_avg_emplvl"] = pd.to_numeric(qcew["annual_avg_emplvl"], errors="coerce")
    # Flag disclosure-suppressed cells (BLS disclosure_code non-null/non-empty means suppressed).
    qcew["suppressed"] = qcew["disclosure_code"].notna() & (qcew["disclosure_code"].astype(str).str.strip() != "")
    qcew.loc[qcew["suppressed"], "annual_avg_emplvl"] = np.nan

    total = qcew[qcew["industry_code"] == TOTAL_INDUSTRY][["area_fips", "year", "annual_avg_emplvl"]].rename(
        columns={"annual_avg_emplvl": "emp_total"}
    )
    tech = qcew[qcew["industry_code"].isin(TECH_INDUSTRIES)]
    tech_agg = tech.groupby(["area_fips", "year"], as_index=False)["annual_avg_emplvl"].sum(min_count=1)
    tech_agg = tech_agg.rename(columns={"annual_avg_emplvl": "emp_tech"})

    merged = total.merge(tech_agg, on=["area_fips", "year"], how="left")
    merged["tech_emp_share"] = merged["emp_tech"] / merged["emp_total"]
    merged.loc[merged["emp_total"] <= 0, "tech_emp_share"] = np.nan
    return merged


def _finalize_emissions_panel(em_grouped: pd.DataFrame, unit_col: str) -> pd.DataFrame:
    """Shared log/diff logic for the state and county aggregates, including
    the PETRO_NG-excluded (S2 robustness) total alongside the headline one.

    REVIEW FIX (round 3, N1 in round-1 review, made mandatory by round-2's
    R2b finding): `.diff()` on a unit's `log_emissions` series spans
    whatever gap sits between two consecutive ROWS in the dataframe, not
    two consecutive CALENDAR YEARS. Every state/county-year combination
    that occurs in `facility_emissions` (`build_state_panel` /
    `build_county_panel`'s own groupby) is present as a row even when
    `total_co2e` is NaN for it, so a plain `.diff()` here is safe UNLESS a
    unit is missing a whole (unit, year) row entirely (e.g. a county with
    zero reporting facilities in some year has no groupby row for that
    year at all, not a NaN row) -- in that case `.diff()` silently spans
    the gap and reports it as a one-year change. This was exactly how a
    Reviewer's own round-2 reimplementation (which dropped NaN rows
    *before* aggregating, rather than keeping them) manufactured 44
    spurious multi-year "annual" changes. Guarded here explicitly: any
    diff computed across a year gap other than exactly 1 is set to NaN,
    regardless of which implementation produced the gap.
    """
    em_grouped = em_grouped.sort_values([unit_col, "year"])
    year_gap = em_grouped.groupby(unit_col)["year"].diff()
    for suffix, col in [("", "total_co2e"), ("_excl_petro_ng", "total_co2e_excl_petro_ng")]:
        n_zero = (em_grouped[col] == 0).sum()
        n_missing_input = em_grouped[col].isna().sum()
        if n_zero or n_missing_input:
            print(f"  {unit_col} panel, {col}: {n_zero} rows == 0 (genuinely reported zero net CO2e -- "
                  f"NOT the same as missing), {n_missing_input} rows NaN (all underlying facility-years "
                  f"missing after the min_count=1 fix). log(0) set to NaN, not -inf.")
        em_grouped[f"log_emissions{suffix}"] = np.log(em_grouped[col].where(em_grouped[col] > 0))
        d = em_grouped.groupby(unit_col)[f"log_emissions{suffix}"].diff()
        n_gap = ((year_gap != 1) & d.notna()).sum()
        if n_gap:
            print(f"  {unit_col} panel, d_log_emissions{suffix}: {n_gap} rows span a year gap != 1 "
                  f"(a unit missing a whole year's row) -- set to NaN rather than reported as a "
                  f"one-year change.")
        d = d.where(year_gap == 1)
        em_grouped[f"d_log_emissions{suffix}"] = d
    return em_grouped


def _sum_min1(s: pd.Series) -> float:
    """sum() that returns NaN (not 0) when every value in the group is
    NaN -- the same min_count=1 fix as the facility-level aggregation
    above, applied again here because plain pandas `.agg("sum")` on a
    named aggregation does NOT accept min_count and would silently
    reintroduce the B3 bug one level up (an all-missing county/state-year
    would otherwise sum to 0.0)."""
    return s.sum(min_count=1)


def build_state_panel(facility_emissions: pd.DataFrame, qcew: pd.DataFrame) -> pd.DataFrame:
    fe = facility_emissions.copy()
    fe["total_co2e_excl_petro_ng"] = fe["total_co2e"].where(~fe["is_petro_ng"].fillna(False))
    state_em = fe.groupby(["state_fips", "year"], as_index=False).agg(
        total_co2e=("total_co2e", _sum_min1),
        total_co2e_excl_petro_ng=("total_co2e_excl_petro_ng", _sum_min1),
        n_facilities=("facility_id", "nunique"),
    )
    state_em = _finalize_emissions_panel(state_em, "state_fips")

    qcew_state = qcew[qcew["area_fips"].str.endswith("000") & (qcew["area_fips"] != "US000")].copy()
    qcew_state["state_fips"] = qcew_state["area_fips"].str[:2]

    panel = state_em.merge(qcew_state[["state_fips", "year", "tech_emp_share", "emp_total", "emp_tech"]], on=["state_fips", "year"], how="left")
    panel["tech_emp_share_diff"] = panel.groupby("state_fips")["tech_emp_share"].diff()
    return panel


def build_county_panel(facility_emissions: pd.DataFrame, qcew: pd.DataFrame) -> pd.DataFrame:
    fe = facility_emissions.copy()
    fe["total_co2e_excl_petro_ng"] = fe["total_co2e"].where(~fe["is_petro_ng"].fillna(False))
    county_em = fe.groupby(["county_fips", "state_fips", "year"], as_index=False).agg(
        total_co2e=("total_co2e", _sum_min1),
        total_co2e_excl_petro_ng=("total_co2e_excl_petro_ng", _sum_min1),
        n_facilities=("facility_id", "nunique"),
    )
    county_em = _finalize_emissions_panel(county_em, "county_fips")

    qcew_county = qcew[~qcew["area_fips"].str.endswith("000")].rename(columns={"area_fips": "county_fips"})

    panel = county_em.merge(qcew_county[["county_fips", "year", "tech_emp_share", "emp_total", "emp_tech"]], on=["county_fips", "year"], how="left")
    panel["tech_emp_share_diff"] = panel.groupby("county_fips")["tech_emp_share"].diff()
    return panel


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fac_em = load_facility_emissions()
    qcew = load_qcew_tech_share()

    state_panel = build_state_panel(fac_em, qcew)
    state_panel.to_csv(OUT / "panel_state_year_us.csv", index=False)
    print(f"State panel: {len(state_panel)} rows, {state_panel['state_fips'].nunique()} states, "
          f"{state_panel['year'].min()}-{state_panel['year'].max()}")

    county_panel = build_county_panel(fac_em, qcew)
    county_panel.to_csv(OUT / "panel_county_year_us.csv", index=False)
    print(f"County panel: {len(county_panel)} rows, {county_panel['county_fips'].nunique()} counties, "
          f"{county_panel['year'].min()}-{county_panel['year'].max()}")

    usable_state = state_panel.dropna(subset=["d_log_emissions", "tech_emp_share"])
    usable_county = county_panel.dropna(subset=["d_log_emissions", "tech_emp_share"])
    print(f"Usable state-year rows (both vars non-missing): {len(usable_state)}")
    print(f"Usable county-year rows (both vars non-missing): {len(usable_county)}")


if __name__ == "__main__":
    main()
