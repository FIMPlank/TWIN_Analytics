"""
Build panel v2: replaces EIBIS's 3-year-usable digitalization measure with
Eurostat's Digital Intensity Index (DII), which has an 11-year nominal
window (2015-2025) and a NACE-sector breakdown -- letting us build both a
country x year panel (v2a) and a country x sector x year panel (v2b).

Phase A only (data engineering): this script builds and QCs the panels. It
runs NO regressions -- see analysis/panel_v2/panel_qc.md for the coverage
report this script produces, and analysis/first_pass_analysis.md /
analysis/extension_analysis.md for the Phase-B-style regression work this
panel is meant to eventually support (on the OLD EIBIS-based panel).

Inputs (all in data/raw/, all fetched by scripts/download_*.py):
  - data/raw/eurostat/digital_intensity_index.csv   (scripts/download_eurostat_dii.py)
  - data/raw/eurostat/energy_import_dependency.csv  (scripts/download_eurostat_energy_dependency.py)
  - data/raw/eurostat/gdp_per_capita.csv             (scripts/download_eurostat.py, already existed)
  - data/raw/eu_ets/eu-ets.csv                       (scripts/download_eu_ets.py, already existed)
  - data/raw/eibis/eibis_aggregate.csv               (scripts/download_eibis_aggregate.py, already existed)

Outputs:
  - analysis/output/panel_country_year_v2.csv
  - analysis/output/panel_sector_country_year_v2.csv
  - analysis/panel_v2/panel_qc.md (written by a separate pass over this
    script's printed output -- see that file for the actual QC report)

Usage:
    python analysis/panel_v2/build_panel.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "analysis" / "output"
OUT.mkdir(parents=True, exist_ok=True)

pd.set_option("display.width", 160)

# ---------------------------------------------------------------------------
# 0. DII methodology-version-in-force mapping
#    ----------------------------------------
#    Verified LIVE against the API (not assumed from documentation): the
#    isoc_e_diin2 dataset's indic_is dimension carries 4 incompatible
#    versions of the Digital Intensity Index, each populated only in
#    specific years:
#       version 1 (E_DI_*)  -> 2015, 2016, 2017, 2018, 2019
#       version 2 (E_DI2_*) -> 2018, 2020
#       version 3 (E_DI3_*) -> 2021, 2023, 2025
#       version 4 (E_DI4_*) -> 2022, 2024
#    2018 is the only year with two versions both populated (v1 and v2).
#    This script picks v1 for 2018 to keep 2015-2019 on one continuous
#    version, and uses v2 only for its unique year, 2020. From 2021 onward
#    the live version ALTERNATES every year (odd=v3, even=v4) -- this
#    alternation is a genuine property of the source data, not a choice.
#
#    IMPORTANT: this means the resulting series has THREE version breaks
#    (2019->2020: v1->v2; 2020->2021: v2->v3; and then v3/v4 alternate every
#    single year from 2021 on). A level or trend comparison across any of
#    these boundaries is NOT guaranteed methodologically comparable -- flag
#    this explicitly to whoever runs regressions on this panel (Phase B).
# ---------------------------------------------------------------------------
VERSION_IN_FORCE = {
    2015: "", 2016: "", 2017: "", 2018: "", 2019: "",   # version 1 = no suffix (E_DI_HI / E_DI_VHI)
    2020: "2",
    2021: "3", 2023: "3", 2025: "3",
    2022: "4", 2024: "4",
}

VERSION_BREAK_YEARS = [2020, 2021, 2022, 2023, 2024, 2025]  # every year from 2020 on is a version boundary vs. its predecessor
# Wired up below (section 7/8): used to flag, per row, whether that
# observation's own prior-year DII version differs from its current one --
# i.e. whether a first-differenced digitalization regressor built from this
# panel would be crossing a methodology boundary for that specific
# country/sector/year. Not resolved here (that is a Phase-B modeling
# choice), just made inspectable rather than left as dead code.

# DII (isoc_e_diin2, unit=PC_ENT, size_emp=GE10) only covers enterprises
# with >=10 employees -- it is NOT a population-wide digitalization measure,
# and micro-enterprises (which can be a large share of firm counts, though a
# much smaller share of emissions-relevant industrial activity) are excluded
# by construction. Worth remembering when interpreting dii_high_share as "how
# digitalized this country/sector is."

# ---------------------------------------------------------------------------
# 1. Digital Intensity Index: apply version-in-force, build HI+VHI share
# ---------------------------------------------------------------------------
dii_raw = pd.read_csv(RAW / "eurostat" / "digital_intensity_index.csv")
dii_raw = dii_raw.rename(columns={"geo": "country_code", "time": "year"})

rows = []
for year, suffix in VERSION_IN_FORCE.items():
    hi_code = f"E_DI{suffix}_HI"
    vhi_code = f"E_DI{suffix}_VHI"
    sub = dii_raw[(dii_raw["year"] == year) & (dii_raw["indic_is"].isin([hi_code, vhi_code]))]
    piv = sub.pivot_table(index=["country_code", "nace_r2"], columns="indic_is", values="value", aggfunc="first")
    if hi_code not in piv.columns:
        piv[hi_code] = np.nan
    if vhi_code not in piv.columns:
        piv[vhi_code] = np.nan
    # FIX (per analysis/panel_v2/panel_qc_review.md, issue 1): a missing HI
    # or VHI cell in this dataset is a Eurostat confidentiality suppression
    # for a small underlying enterprise population, NOT a definitional zero
    # -- confirmed against the live API (e.g. DE C19 2022: HI=57.63,
    # VHI=suppressed; recording that as HI+0=57.6% would understate the true
    # (unknown, but >=57.6%) share). The share must therefore be NaN whenever
    # EITHER component is missing, not only when BOTH are missing -- a plain
    # fillna(0)+fillna(0) silently treats "suppressed" as "zero" and drags
    # affected cells toward zero. Using .sum(min_count=2) enforces this: the
    # sum is NaN unless both inputs are present.
    piv["dii_high_share"] = piv[[hi_code, vhi_code]].sum(axis=1, min_count=2) / 100.0
    piv = piv.reset_index()
    piv["year"] = year
    piv["dii_version"] = suffix if suffix else "1"
    rows.append(piv[["country_code", "nace_r2", "year", "dii_version", "dii_high_share"]])

dii = pd.concat(rows, ignore_index=True).dropna(subset=["dii_high_share"])
dii.to_csv(OUT / "panel_v2_dii_long.csv", index=False)

_VERSION_BY_YEAR = {y: (suffix if suffix else "1") for y, suffix in VERSION_IN_FORCE.items()}


def dii_version_break_vs_prior_year(year: int) -> bool:
    """True if a first difference of dii_high_share between `year` and
    `year - 1` would cross a DII methodology-version boundary (including
    the case where year-1 predates DII entirely, i.e. no valid
    same-methodology comparison is even possible). Not used to compute
    anything here -- exposed as a per-row flag so Phase B can see, and
    decide how to handle, which rows a first-differenced digitalization
    regressor would be unsafe for."""
    prev_version = _VERSION_BY_YEAR.get(year - 1)
    cur_version = _VERSION_BY_YEAR.get(year)
    if prev_version is None or cur_version is None:
        return True
    return prev_version != cur_version

print("=== DII (version-resolved) coverage by sector x year (country count) ===")
cov = dii.pivot_table(index="nace_r2", columns="year", values="country_code", aggfunc="nunique")
print(cov.reindex(columns=sorted(cov.columns)))

# ---------------------------------------------------------------------------
# 2. EU ETS verified emissions, country x main_activity x year, for the 8
#    ETS activities used in the sector crosswalk (see NACE_ETS_CROSSWALK
#    below and panel_qc.md for the full table with confidence notes).
#    NOTE ON SOURCE FILE: the brief pointed at
#    data/raw/eu_ets/eu-ets-sector-emissions.csv, but that file is an
#    EU-WIDE total by sector x year with NO country dimension (3 columns:
#    sector, year, emissions_mt) -- it cannot support a country x sector x
#    year panel. The country x sector x year build below instead uses the
#    original data/raw/eu_ets/eu-ets.csv (country_code x main_activity_code
#    x year), filtered to the same 8 main_activity_code values that
#    eu-ets-sector-emissions.csv itself aggregates from. This is a necessary
#    substitution, not an oversight -- documented here and in panel_qc.md.
# ---------------------------------------------------------------------------
NACE_ETS_CROSSWALK = {
    # ets_main_activity_code: (ets_activity_name, dii_nace_r2, confidence, note)
    "21": ("Refining of mineral oil", "C19", "high",
           "Clean 1:1 -- NACE C19 'Manufacture of coke and refined petroleum products' is essentially "
           "the same activity as the ETS category."),
    "42": ("Production of bulk chemicals", "C20", "medium-high",
           "NACE C20 'Manufacture of chemicals and chemical products' is broader than ETS's narrower "
           "'bulk chemicals by cracking/reforming/oxidation' definition, but it is the closest available "
           "NACE aggregate and the two populations overlap heavily."),
    "24": ("Production of pig iron or steel", "C24_C25", "medium",
           "DII only offers C24_C25 combined ('basic metals' + 'fabricated metal products'); ETS's pig "
           "iron/steel activity sits inside C24 alone, so C25 (fabricated metal products -- a much larger, "
           "more downstream, and less energy-intensive sector) dilutes the match. Directionally right, "
           "noisier than the other high-confidence rows."),
    "29": ("Production of cement clinker", "C22_C23", "low-medium",
           "DII's finest available cut is C22_C23 (rubber & plastic products + other non-metallic mineral "
           "products combined). Cement clinker sits inside C23 alone; C22 (rubber/plastics) is unrelated "
           "and roughly comparable in size, so this is a real dilution, not just a labeling nuance."),
    "30": ("Production of lime, or calcination of dolomite/magnesite", "C22_C23", "low-medium",
           "Same DII cell and same caveat as cement clinker above -- lime/dolomite is also inside C23, "
           "diluted by C22."),
    "36": ("Production of paper or cardboard", "C16-C18", "medium",
           "DII's finest available cut is C16-C18 (wood products + paper + printing combined). Paper "
           "(C17) is only one of three sub-industries in this cell; wood products (C16) and printing "
           "(C18) are meaningfully different digitalization profiles, so this dilutes the match."),
    "20": ("Combustion of fuels", "D35", "low",
           "Conceptual mismatch, not just a granularity issue: ETS 'Combustion of fuels' is a PROCESS "
           "that occurs across many industries (any large combustion installation, wherever it sits), "
           "while DII's D35 is an ENTERPRISE classification (electricity/gas/steam utilities only). Most "
           "combustion-activity ETS emissions come from installations inside chemical plants, refineries, "
           "steel mills etc. that are NOT classified as NACE D35 enterprises. Treat this mapping as a "
           "weak proxy for the utility-sector slice of combustion emissions only, not the whole activity."),
    "10": ("Aviation", None, "no match",
           "No DII NACE breakdown exists for air transport specifically -- the finest available transport "
           "cut in this dataset is the whole of NACE H (transportation and storage, covering land, water "
           "and air transport plus warehousing and postal/courier activities together). Excluded from the "
           "sector-level panel entirely rather than forced into a mapping with no discriminating power."),
}

# ETS main_activity_code "50" is NOT in the crosswalk above and NOT in this
# panel at all: the source data itself (data/raw/eu_ets/eu-ets.csv) gives it
# a blank/unlabeled main_activity_name ("50", no description), and it is
# 90.4 Mt in 2024 (8.7% of stationary-installation ETS emissions) -- not
# negligible. Unlike Aviation (documented, deliberately excluded because no
# DII match exists), activity 50 has no clear real-world referent to even
# attempt a NACE mapping for, given the source data provides no description.
# Flagged here so its absence is a documented decision, not a silent gap.

print("\n=== NACE-ETS crosswalk ===")
for code, (name, nace, conf, note) in NACE_ETS_CROSSWALK.items():
    print(f"ETS {code:>2s} {name:45s} -> DII {str(nace):10s} [{conf}]")

eu = pd.read_csv(RAW / "eu_ets" / "eu-ets.csv")
eu = eu[eu["year"].str.fullmatch(r"\d{4}")].copy()
eu["year"] = eu["year"].astype(int)
ets_codes = list(NACE_ETS_CROSSWALK.keys())
ets = eu[
    (eu["main_activity_code"].isin(ets_codes))
    & (eu["citl_information"] == "2. Verified emissions")
].copy()
ets = ets.rename(columns={"value": "verified_emissions_t"})[
    ["country_code", "main_activity_code", "year", "verified_emissions_t"]
]
non_country = {"Innovation fund", "Modernisation Fund", "NER 300 auctions", "RRF"}
ets = ets[~ets["country_code"].isin(non_country)]
# Country-code reconciliation: EU ETS -> Eurostat convention (matches the
# convention already used in analysis/analysis.py and analysis/extension_analysis.py)
ets["country_code"] = ets["country_code"].replace({"GR": "EL", "GB": "UK"})
ets = ets.sort_values(["country_code", "main_activity_code", "year"])
ets["log_emissions"] = np.log(ets["verified_emissions_t"].clip(lower=1))
ets["d_log_emissions"] = ets.groupby(["country_code", "main_activity_code"])["log_emissions"].diff()

print("\n=== EU-ETS country x activity x year coverage (country count per activity x year) ===")
cov_ets = ets.pivot_table(index="main_activity_code", columns="year", values="country_code", aggfunc="nunique")
print(cov_ets.reindex(columns=sorted(cov_ets.columns)))

# ---------------------------------------------------------------------------
# 3. EU ETS "20-99" country total (all stationary installations) for the
#    country-year panel v2a -- same construction as analysis/analysis.py.
# ---------------------------------------------------------------------------
ets_total = eu[
    (eu["main_activity_code"] == "20-99")
    & (eu["citl_information"] == "2. Verified emissions")
].copy()
ets_total = ets_total.rename(columns={"value": "verified_emissions_t"})[
    ["country_code", "year", "verified_emissions_t"]
]
ets_total = ets_total[~ets_total["country_code"].isin(non_country)]
ets_total["country_code"] = ets_total["country_code"].replace({"GR": "EL", "GB": "UK"})
ets_total = ets_total.sort_values(["country_code", "year"])
ets_total["log_emissions"] = np.log(ets_total["verified_emissions_t"].clip(lower=1))
ets_total["d_log_emissions"] = ets_total.groupby("country_code")["log_emissions"].diff()

# ---------------------------------------------------------------------------
# 4. EIBIS digital_multi (secondary/robustness column, 2023-2025 only)
# ---------------------------------------------------------------------------
eib = pd.read_csv(RAW / "eibis" / "eibis_aggregate.csv")
eib = eib[~eib["country"].isin(["EU", "US"])]
eib_all = eib[(eib["sector"] == "ALL") & (eib["size"] == "ALL") &
              (eib["indicator"] == "Implementation of digital technologies")]
eibis_digital = eib_all[["country", "survey_wave", "Multiple technologies"]].dropna()
eibis_digital = eibis_digital.rename(columns={
    "country": "country_code", "survey_wave": "year", "Multiple technologies": "eibis_digital_multi"
})

# ---------------------------------------------------------------------------
# 5. GDP growth (derived, no new fetch) + energy import dependency
# ---------------------------------------------------------------------------
gdp = pd.read_csv(RAW / "eurostat" / "gdp_per_capita.csv")
gdp = gdp.rename(columns={"geo": "country_code", "time": "year", "value": "gdp_per_capita"})[
    ["country_code", "year", "gdp_per_capita"]
]
gdp = gdp.sort_values(["country_code", "year"])
gdp["log_gdp_per_capita"] = np.log(gdp["gdp_per_capita"])
gdp["d_log_gdp_per_capita"] = gdp.groupby("country_code")["log_gdp_per_capita"].diff()

energy_dep = pd.read_csv(RAW / "eurostat" / "energy_import_dependency.csv")
energy_dep = energy_dep.rename(columns={"geo": "country_code", "time": "year", "value": "energy_import_dependency_pct"})[
    ["country_code", "year", "energy_import_dependency_pct"]
]

# ---------------------------------------------------------------------------
# 6. EU accession cohort lookup (hardcoded, no fetch)
# ---------------------------------------------------------------------------
EU_ACCESSION_COHORT = {
    # EU-15 (pre-2004 members)
    **{c: "EU-15" for c in ["AT", "BE", "DE", "DK", "EL", "ES", "FI", "FR", "IE", "IT", "LU", "NL", "PT", "SE", "UK"]},
    # 2004 enlargement wave
    **{c: "2004" for c in ["CZ", "EE", "CY", "LV", "LT", "HU", "MT", "PL", "SK", "SI"]},
    # 2007 enlargement wave
    **{c: "2007" for c in ["BG", "RO"]},
    # 2013 enlargement wave
    "HR": "2013",
}

# ---------------------------------------------------------------------------
# 7. Panel v2a: country x year
#    ------------------------------------------------------------------
#    SCOPE-MISMATCH CAVEAT (per panel_qc_review.md issue 3): the outcome
#    here, ets_total (main_activity_code "20-99"), is ALL stationary
#    installations -- combustion (activity 20, ~57% of the stationary
#    total in 2024) included. But dii_high_share_manufacturing is DII's
#    nace_r2=='C' (manufacturing only, enterprises >=10 employees), which
#    does not cover combustion/utility installations (NACE D35) at all.
#    So v2a pairs a digitalization measure that covers a MINORITY of the
#    emissions it is being used to explain. This is a defensible
#    country-level proxy (manufacturing digitalization as a stand-in for
#    overall industrial digitalization), but it is a real scope mismatch,
#    not a full-coverage measure, and should be read as such rather than
#    as "how digitalized this country is" in general.
#
#    An alternative composite column, dii_high_share_c_or_d35, is also
#    provided: a simple (unweighted, enterprise-count-blind) average of the
#    'C' and 'D35' shares where both exist, widening coverage toward the
#    combustion/utility side at the cost of being a cruder blend of two
#    different enterprise populations. Neither column should be treated as
#    a true population-wide digitalization measure (see the >=10-employee
#    caveat above) -- both are reported so Phase B can compare rather than
#    have this choice made for it.
# ---------------------------------------------------------------------------
dii_country = dii[dii["nace_r2"] == "C"][["country_code", "year", "dii_high_share", "dii_version"]].rename(
    columns={"dii_high_share": "dii_high_share_manufacturing"}
)
dii_d35 = dii[dii["nace_r2"] == "D35"][["country_code", "year", "dii_high_share"]].rename(
    columns={"dii_high_share": "dii_high_share_d35"}
)

panel_v2a = ets_total.merge(dii_country, on=["country_code", "year"], how="left")
panel_v2a = panel_v2a.merge(dii_d35, on=["country_code", "year"], how="left")
panel_v2a["dii_high_share_c_or_d35"] = panel_v2a[["dii_high_share_manufacturing", "dii_high_share_d35"]].mean(axis=1)
panel_v2a = panel_v2a.merge(eibis_digital, on=["country_code", "year"], how="left")
panel_v2a = panel_v2a.merge(gdp[["country_code", "year", "gdp_per_capita", "d_log_gdp_per_capita"]],
                             on=["country_code", "year"], how="left")
panel_v2a = panel_v2a.merge(energy_dep, on=["country_code", "year"], how="left")
panel_v2a["eu_accession_cohort"] = panel_v2a["country_code"].map(EU_ACCESSION_COHORT)
panel_v2a["dii_version_break_vs_prior_year"] = panel_v2a["year"].apply(dii_version_break_vs_prior_year)
panel_v2a.to_csv(OUT / "panel_country_year_v2.csv", index=False)

print("\n=== Panel v2a (country x year) ===")
print(f"rows={len(panel_v2a)}, countries={panel_v2a['country_code'].nunique()}, "
      f"years={sorted(panel_v2a['year'].unique())}")
usable_v2a = panel_v2a.dropna(subset=["d_log_emissions", "dii_high_share_manufacturing"])
print(f"rows with BOTH d_log_emissions and DII (manufacturing) non-missing: {len(usable_v2a)}, "
      f"countries={usable_v2a['country_code'].nunique()}, years={sorted(usable_v2a['year'].unique())}")

# ---------------------------------------------------------------------------
# 8. Panel v2b: country x ETS-sector x year (the harder, more valuable one)
# ---------------------------------------------------------------------------
sector_rows = []
for ets_code, (ets_name, dii_nace, confidence, note) in NACE_ETS_CROSSWALK.items():
    if dii_nace is None:
        continue  # Aviation -- no DII match, excluded
    sub_ets = ets[ets["main_activity_code"] == ets_code].copy()
    sub_dii = dii[dii["nace_r2"] == dii_nace][["country_code", "year", "dii_high_share", "dii_version"]]
    merged = sub_ets.merge(sub_dii, on=["country_code", "year"], how="left")
    merged["ets_activity_code"] = ets_code
    merged["ets_activity_name"] = ets_name
    merged["dii_nace_r2"] = dii_nace
    merged["crosswalk_confidence"] = confidence
    sector_rows.append(merged)

panel_v2b = pd.concat(sector_rows, ignore_index=True)
panel_v2b = panel_v2b.merge(gdp[["country_code", "year", "gdp_per_capita", "d_log_gdp_per_capita"]],
                             on=["country_code", "year"], how="left")
panel_v2b = panel_v2b.merge(energy_dep, on=["country_code", "year"], how="left")
panel_v2b["eu_accession_cohort"] = panel_v2b["country_code"].map(EU_ACCESSION_COHORT)
panel_v2b["dii_version_break_vs_prior_year"] = panel_v2b["year"].apply(dii_version_break_vs_prior_year)
panel_v2b.to_csv(OUT / "panel_sector_country_year_v2.csv", index=False)

print("\n=== Panel v2b (country x ETS-sector x year) ===")
print(f"rows={len(panel_v2b)}, countries={panel_v2b['country_code'].nunique()}, "
      f"sectors={panel_v2b['ets_activity_code'].nunique()}, years={sorted(panel_v2b['year'].unique())}")
usable_v2b = panel_v2b.dropna(subset=["d_log_emissions", "dii_high_share"])
print(f"rows with BOTH d_log_emissions and DII non-missing: {len(usable_v2b)}")
print("\nUsable rows by sector x year (DII + emissions both present):")
cov_v2b = usable_v2b.pivot_table(index="ets_activity_code", columns="year", values="country_code", aggfunc="nunique")
print(cov_v2b.reindex(columns=sorted(usable_v2b["year"].unique())))

# ---------------------------------------------------------------------------
# 8b. Two explicit Phase-B cuts of panel v2b: the full sector set, and an
#     alternative excluding ETS activity 20 (Combustion of fuels) -- the
#     "low" confidence mapping that (see emissions-weighted table below)
#     turns out to carry the majority of the panel's emissions mass. Both
#     are written out so Phase B can compare side by side rather than have
#     this choice made for it here.
# ---------------------------------------------------------------------------
panel_v2b_excl_combustion = panel_v2b[panel_v2b["ets_activity_code"] != "20"].copy()
panel_v2b_excl_combustion.to_csv(OUT / "panel_sector_country_year_v2_excl_combustion.csv", index=False)
print(f"\nAlternative cut written: panel_sector_country_year_v2_excl_combustion.csv "
      f"({len(panel_v2b_excl_combustion)} rows, drops ETS activity 20 'Combustion of fuels')")

# ---------------------------------------------------------------------------
# 8c. Emissions-weighted crosswalk-confidence summary (per
#     panel_qc_review.md issue 2): the per-row confidence table in
#     NACE_ETS_CROSSWALK is honest but UNWEIGHTED, so it understates how
#     much the panel's substantive results would be dominated by its
#     weakest mapping. Weight by each sector's actual emissions mass
#     (2024, among usable v2b rows -- i.e. rows with a non-missing DII
#     match) to show the real picture.
# ---------------------------------------------------------------------------
mass_2024 = usable_v2b[usable_v2b["year"] == 2024].groupby("ets_activity_code")["verified_emissions_t"].sum()
mass_2024_mt = (mass_2024 / 1e6).rename("emissions_mt_2024")
crosswalk_weighted = pd.DataFrame([
    {"ets_activity_code": code, "ets_activity_name": name, "dii_nace_r2": nace, "confidence": conf}
    for code, (name, nace, conf, note) in NACE_ETS_CROSSWALK.items()
    if nace is not None
]).set_index("ets_activity_code")
crosswalk_weighted = crosswalk_weighted.join(mass_2024_mt, how="left")
crosswalk_weighted["share_of_v2b_mass"] = crosswalk_weighted["emissions_mt_2024"] / crosswalk_weighted["emissions_mt_2024"].sum()
crosswalk_weighted = crosswalk_weighted.sort_values("share_of_v2b_mass", ascending=False)
crosswalk_weighted.to_csv(OUT / "panel_v2b_crosswalk_emissions_weighted.csv")

print("\n=== Emissions-weighted crosswalk confidence (2024, usable v2b rows) ===")
print(crosswalk_weighted[["ets_activity_name", "confidence", "emissions_mt_2024", "share_of_v2b_mass"]].to_string())

conf_grouped = crosswalk_weighted.groupby("confidence")["share_of_v2b_mass"].sum().sort_values(ascending=False)
print("\nShare of v2b emissions mass by confidence tier:")
print((conf_grouped * 100).round(1).astype(str) + "%")

print(f"\nOutputs written to {OUT}")
