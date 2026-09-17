"""
Phase C: three EU refinements on top of the Phase B panels.

Item 1: NUTS2 regional panel (v3) -- built by analysis/phase_c_build_panel.py
  (run that first; this script loads its outputs). Regression results here
  are PROVISIONAL pending the same Reviewer sign-off Phase A/B panels went
  through -- flagged explicitly throughout, not run with headline
  confidence.
Item 2: emissions intensity (verified emissions / industrial value-added)
  as an alternative outcome to raw emissions change, on the Reviewer-
  approved Phase B panels (v2a, v2b both cuts).
Item 3: EIBIS large-firm-only cross-check against the EIBIS all-firms
  aggregate (DII has no firm-size breakdown at all -- GE10 only -- so this
  item is EIBIS-only, stated plainly).

Reuses the same small-cluster-robust inference machinery (naive z,
t(G-1), wild cluster bootstrap) validated in analysis/extension_analysis.py
and analysis/phase_b_analysis.py, and the same discipline: DII/composite
regressors never first-differenced, controls as changes/pre-determined
baselines, v2b always both cuts with sector FE.

Usage:
    python analysis/phase_c_build_panel.py   # if not already run
    python analysis/phase_c_analysis.py
"""

import numpy as np
import pandas as pd
import patsy
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT.parent / "data" / "raw"
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

pd.set_option("display.width", 160)
BASE_SEED = 20260201
N_BOOT = 1999

# ---------------------------------------------------------------------------
# Small-cluster-robust OLS machinery (same as phase_b_analysis.py)
# ---------------------------------------------------------------------------

def ols_fit(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return beta, resid


def cluster_robust_vcov(X, resid, groups):
    n, k = X.shape
    bread = np.linalg.inv(X.T @ X)
    uniq = np.unique(groups)
    G = len(uniq)
    meat = np.zeros((k, k))
    for g in uniq:
        idx = groups == g
        Xg, ug = X[idx], resid[idx]
        Sg = Xg.T @ ug
        meat += np.outer(Sg, Sg)
    dfc = (G / (G - 1)) * ((n - 1) / (n - k))
    return dfc * (bread @ meat @ bread), G


def t_stat(y, X, groups, col_idx):
    beta, resid = ols_fit(y, X)
    V, G = cluster_robust_vcov(X, resid, groups)
    se = np.sqrt(V[col_idx, col_idx])
    return beta[col_idx], se, beta[col_idx] / se, G


def wild_cluster_bootstrap_p(y, X, groups, col_idx, n_boot, seed):
    beta_obs, se_obs, t_obs, G = t_stat(y, X, groups, col_idx)
    X_r = np.delete(X, col_idx, axis=1)
    beta_r, resid_r = ols_fit(y, X_r)
    fitted_r = y - resid_r
    uniq = np.unique(groups)
    group_pos = {g: (groups == g) for g in uniq}
    rng = np.random.default_rng(seed)
    t_boot = np.empty(n_boot)
    for b in range(n_boot):
        w = rng.choice([-1.0, 1.0], size=G)
        wvec = np.empty(len(y))
        for g, wg in zip(uniq, w):
            wvec[group_pos[g]] = wg
        y_star = fitted_r + resid_r * wvec
        _, _, t_boot[b], _ = t_stat(y_star, X, groups, col_idx)
    p = float(np.mean(np.abs(t_boot) >= np.abs(t_obs)))
    return beta_obs, se_obs, t_obs, p, G


def fit_report(df, formula, target_col, cluster_col, model_id, seed_offset, n_boot=N_BOOT):
    y, X = patsy.dmatrices(formula, data=df, return_type="dataframe")
    col_idx = list(X.columns).index(target_col)
    y = y.to_numpy().ravel()
    Xm = X.to_numpy()
    groups = df.loc[X.index, cluster_col].to_numpy()
    n = len(y)
    beta, se, t_obs, G = t_stat(y, Xm, groups, col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    p_t = 2 * (1 - stats.t.cdf(np.abs(t_obs), df=G - 1))
    if G < 6 or n < G + 4:
        p_wild = np.nan
        note = "SKIPPED (too few clusters/obs for a meaningful bootstrap)"
    else:
        _, _, _, p_wild, _ = wild_cluster_bootstrap_p(y, Xm, groups, col_idx, n_boot, BASE_SEED + seed_offset)
        note = ""
    row = {
        "model": model_id, "target": target_col, "n": n, "G_clusters": G,
        "coef": beta, "se_cluster": se, "t_stat": t_obs,
        "p_naive_z": p_z, "p_t_Gminus1": p_t, "p_wild_bootstrap": p_wild,
    }
    pw_str = f"{p_wild:.4f}" if not np.isnan(p_wild) else "n/a"
    print(f"{model_id:55s} target={target_col:30s} n={n:4d} G={G:3d} "
          f"coef={beta:+.4f}  p(z)={p_z:.4f}  p(t)={p_t:.4f}  p(wild)={pw_str} {note}")
    return row


all_results = []
_seed_counter = [0]


def run(df, formula, target_col, cluster_col, model_id, tag):
    _seed_counter[0] += 1
    row = fit_report(df, formula, target_col, cluster_col, model_id, _seed_counter[0])
    row["item"] = tag
    all_results.append(row)
    return row


# ===========================================================================
# ITEM 1: NUTS2 regional panel (v3) -- PROVISIONAL, pending Reviewer sign-off
# ===========================================================================
print("=" * 90)
print("ITEM 1: NUTS2 regional panel (v3) -- PROVISIONAL, same as any unreviewed panel")
print("=" * 90)

v3_excl = pd.read_csv(OUT / "phase_c_panel_region_year_v3_excl_biomass.csv")
v3_incl = pd.read_csv(OUT / "phase_c_panel_region_year_v3_incl_biomass.csv")

usable_excl = v3_excl.dropna(subset=["d_log_emissions", "dii_regional_composite"])
usable_incl = v3_incl.dropna(subset=["d_log_emissions", "dii_regional_composite"])
print(f"v3 excl_biomass (SAME pollutant definition as the country-level analysis, per the brief): "
      f"n={len(usable_excl)}, {usable_excl['NUTS_ID'].nunique()} regions, "
      f"{usable_excl['CNTR_CODE'].nunique()} countries, years={sorted(usable_excl['year'].unique())}")
print(f"v3 incl_biomass (broader CO2 definition, DEVIATION from convention, used only because "
      f"excl_biomass is unusably small): n={len(usable_incl)}, {usable_incl['NUTS_ID'].nunique()} regions, "
      f"{usable_incl['CNTR_CODE'].nunique()} countries, years={sorted(usable_incl['year'].unique())}")

print("\n--- v3 excl_biomass: n=15 is too small for any inference; reporting a bare correlation "
      "only, purely descriptive, NOT a regression result ---")
if len(usable_excl) >= 3:
    r, p = stats.pearsonr(usable_excl["dii_regional_composite"], usable_excl["d_log_emissions"])
    print(f"Pearson r={r:+.3f}, p={p:.3f}, n={len(usable_excl)} (descriptive only -- do not treat as a finding)")
    pd.DataFrame([{"n": len(usable_excl), "pearson_r": r, "p_value": p}]).to_csv(
        OUT / "phase_c_v3_excl_biomass_correlation.csv", index=False
    )

# ---------------------------------------------------------------------------
# CORRECTED per phase_c_review.md issue 2: cluster on COUNTRY (CNTR_CODE),
# not NUTS_ID. Regions within a country share the same national
# digitalization survey wave and policy/energy-price environment, so
# treating 58 regions as independent clusters when there are only 8
# countries understates the standard errors. Country is the correct
# clustering unit here, the same way it is everywhere else in this project.
# ---------------------------------------------------------------------------
print("\n--- v3 incl_biomass: n=97, but only G=8 COUNTRY clusters (corrected clustering level) "
      "-- reported as PROVISIONAL and, per the checks below, ultimately not usable ---")
run(usable_incl, "d_log_emissions ~ dii_regional_composite + C(year)",
    "dii_regional_composite", "CNTR_CODE", "C1 [PROVISIONAL] bare (composite level + year FE), clustered by COUNTRY", "item1")

usable_incl_ctrl = usable_incl.dropna(subset=["d_log_emissions", "dii_regional_composite"]).copy()
run(usable_incl_ctrl, "d_log_emissions ~ dii_regional_composite + C(year) + C(CNTR_CODE)",
    "dii_regional_composite", "CNTR_CODE", "C2 [PROVISIONAL] + country FE, clustered by COUNTRY", "item1")

# Robustness: restrict to the 43 rows whose composite is built from all 4
# available components (of the 5 total, only 4 are ever simultaneously
# available in any region-year -- see composite construction notes) --
# half the panel's regressor is a materially different measurement
# (1-3 components) from the other half; this checks whether that matters.
usable_incl_4comp = usable_incl[usable_incl["n_components"] == 4]
print(f"\n4-component-only robustness subsample: n={len(usable_incl_4comp)}")
if len(usable_incl_4comp) >= 10:
    run(usable_incl_4comp, "d_log_emissions ~ dii_regional_composite + C(year)",
        "dii_regional_composite", "CNTR_CODE", "C1b [PROVISIONAL] bare, 4-component-only subsample, clustered by COUNTRY", "item1")

# ---------------------------------------------------------------------------
# Leave-one-country-out on C1 (per phase_c_review.md issue 3) -- with only
# 8 country clusters, is the marginal association driven by one country?
# ---------------------------------------------------------------------------
print("\n--- Leave-one-country-out on C1 (region-clustered, matching the review's own check) ---")
loo_rows = []
for c in sorted(usable_incl["CNTR_CODE"].unique()):
    sub = usable_incl[usable_incl["CNTR_CODE"] != c]
    y, X = patsy.dmatrices("d_log_emissions ~ dii_regional_composite + C(year)", data=sub, return_type="dataframe")
    col_idx = list(X.columns).index("dii_regional_composite")
    beta, se, t_obs, G = t_stat(y.to_numpy().ravel(), X.to_numpy(), sub["NUTS_ID"].to_numpy(), col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    loo_rows.append({"dropped_country": c, "n": len(sub), "coef": beta, "p_naive_z_region_clustered": p_z})
loo_df = pd.DataFrame(loo_rows).sort_values("p_naive_z_region_clustered")
print(loo_df.to_string(index=False))
loo_df.to_csv(OUT / "phase_c_item1_leave_one_out.csv", index=False)
print(f"\nSpain is {(usable_incl['CNTR_CODE']=='ES').sum()} of {len(usable_incl)} rows "
      f"({(usable_incl['CNTR_CODE']=='ES').mean():.1%}) of the panel.")

# ---------------------------------------------------------------------------
# Biomass-inflation-by-country table (per phase_c_review.md issue 4): where
# BOTH "Carbon dioxide (CO2)" and "...excluding biomass" are reported for
# the same facility-year, how much does the incl_biomass figure inflate
# relative to excl_biomass, and does that inflation correlate with the
# regressor (digitalization)?
# ---------------------------------------------------------------------------
print("\n--- Biomass inflation ratio, by country (where both pollutant fields are reported) ---")
eprtr_all = pd.read_csv(RAW / "eprtr" / "F1_4_Air_Releases_Facilities.csv", low_memory=False)
incl = eprtr_all[eprtr_all["Pollutant"] == "Carbon dioxide (CO2)"][
    ["FacilityInspireId", "countryName", "reportingYear", "Releases"]
].rename(columns={"Releases": "co2_incl_biomass"})
excl = eprtr_all[
    eprtr_all["Pollutant"].str.contains("Carbon dioxide", case=False, na=False)
    & eprtr_all["Pollutant"].str.contains("excluding biomass", case=False, na=False)
][["FacilityInspireId", "countryName", "reportingYear", "Releases"]].rename(columns={"Releases": "co2_excl_biomass"})
both = incl.merge(excl, on=["FacilityInspireId", "countryName", "reportingYear"], how="inner")
both = both[both["co2_excl_biomass"] > 0]
both["ratio"] = both["co2_incl_biomass"] / both["co2_excl_biomass"]
ratio_by_country = both.groupby("countryName")["ratio"].median().sort_values(ascending=False)
print(ratio_by_country)
ratio_by_country.to_csv(OUT / "phase_c_biomass_inflation_ratio.csv")
panel_countries_full = {"Austria": "AT", "Bulgaria": "BG", "Denmark": "DK", "Spain": "ES",
                         "Croatia": "HR", "Hungary": "HU", "Romania": "RO", "Slovenia": "SI"}
known_biogenic = set(both["countryName"].unique()) & set(panel_countries_full.keys())
print(f"\nOf the 8 panel countries, {len(known_biogenic)} have ANY facility reporting both pollutant "
      f"fields (known biogenic share): {sorted(panel_countries_full[c] for c in known_biogenic)}")
print(f"The other {8 - len(known_biogenic)} panel countries have an UNKNOWN biogenic share: "
      f"{sorted(set(panel_countries_full.values()) - {panel_countries_full[c] for c in known_biogenic})}")

results_c1 = pd.DataFrame([r for r in all_results if r["item"] == "item1"])
results_c1.to_csv(OUT / "phase_c_item1_results.csv", index=False)

# headline scatter for item 1
fig, ax = plt.subplots(figsize=(7, 5.5))
ax.axhline(0, color="#999999", linewidth=1, linestyle="--")
ax.scatter(usable_incl["dii_regional_composite"], usable_incl["d_log_emissions"], s=20, alpha=0.6, color="#4c72b0")
ax.set_xlabel("Regional digitalization composite (z-score mean, incl_biomass CO2 sample)")
ax.set_ylabel("Region-year log change in CO2 (E-PRTR, incl. biomass)")
ax.set_title(f"Item 1 (PROVISIONAL, unreviewed): NUTS2 region-year, n={len(usable_incl)}")
fig.tight_layout()
fig.savefig(OUT / "phase_c_item1_scatter.png", dpi=150)
plt.close(fig)

# ===========================================================================
# ITEM 2: emissions intensity (verified emissions / industrial value-added)
# ===========================================================================
print("\n" + "=" * 90)
print("ITEM 2: emissions intensity outcome, v2a and v2b (both cuts)")
print("=" * 90)

va_abs = pd.read_csv(RAW / "eurostat" / "industry_value_added_absolute.csv")
va_abs = va_abs.rename(columns={"geo": "country_code", "time": "year", "value": "industry_va_meur"})[
    ["country_code", "year", "industry_va_meur"]
]
va_abs = va_abs.sort_values(["country_code", "year"])
va_abs["log_va"] = np.log(va_abs["industry_va_meur"].clip(lower=1))
va_abs["d_log_va"] = va_abs.groupby("country_code")["log_va"].diff()

v2a = pd.read_csv(OUT / "phase_b_working_v2a.csv")
v2a = v2a.merge(va_abs[["country_code", "year", "industry_va_meur", "d_log_va"]], on=["country_code", "year"], how="left")
v2a["d_log_emissions_intensity"] = v2a["d_log_emissions"] - v2a["d_log_va"]

v2b_full = pd.read_csv(OUT / "phase_b_working_v2b_full.csv")
v2b_excl = pd.read_csv(OUT / "phase_b_working_v2b_excl.csv")
v2b_full = v2b_full.merge(va_abs[["country_code", "year", "industry_va_meur", "d_log_va"]], on=["country_code", "year"], how="left")
v2b_excl = v2b_excl.merge(va_abs[["country_code", "year", "industry_va_meur", "d_log_va"]], on=["country_code", "year"], how="left")
v2b_full["d_log_emissions_intensity"] = v2b_full["d_log_emissions"] - v2b_full["d_log_va"]
v2b_excl["d_log_emissions_intensity"] = v2b_excl["d_log_emissions"] - v2b_excl["d_log_va"]

print(f"v2a rows with a valid emissions-intensity outcome: "
      f"{v2a.dropna(subset=['d_log_emissions_intensity', 'dii_high_share_manufacturing']).shape[0]} of "
      f"{v2a.dropna(subset=['d_log_emissions', 'dii_high_share_manufacturing']).shape[0]} with the raw outcome")

# --- v2a: bare and +controls, intensity outcome vs raw outcome side by side ---
usable_a_int = v2a.dropna(subset=["d_log_emissions_intensity", "dii_high_share_manufacturing"])
run(usable_a_int, "d_log_emissions_intensity ~ dii_high_share_manufacturing + C(year)",
    "dii_high_share_manufacturing", "country_code", "D1 v2a bare, INTENSITY outcome", "item2")
usable_a_int_ctrl = usable_a_int.dropna(subset=["d_log_gdp_per_capita", "energy_shock_exposure", "accession_2004plus"])
run(usable_a_int_ctrl,
    "d_log_emissions_intensity ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "D2 v2a +controls, INTENSITY outcome", "item2")
# for direct comparison, the raw-outcome equivalents on the SAME (intensity-
# restricted) sample
run(usable_a_int, "d_log_emissions ~ dii_high_share_manufacturing + C(year)",
    "dii_high_share_manufacturing", "country_code", "D1r v2a bare, RAW outcome (same sample as D1)", "item2")
run(usable_a_int_ctrl,
    "d_log_emissions ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "D2r v2a +controls, RAW outcome (same sample as D2)", "item2")

for cut_label, panel in [("full (incl. combustion)", v2b_full), ("excl-combustion", v2b_excl)]:
    usable_b_int = panel.dropna(subset=["d_log_emissions_intensity", "dii_high_share"])
    run(usable_b_int, "d_log_emissions_intensity ~ dii_high_share + C(year) + C(ets_activity_code)",
        "dii_high_share", "country_code", f"D3 v2b bare, INTENSITY outcome [{cut_label}]", "item2")
    usable_b_int_ctrl = usable_b_int.dropna(subset=["d_log_gdp_per_capita", "energy_shock_exposure", "accession_2004plus"])
    run(usable_b_int_ctrl,
        "d_log_emissions_intensity ~ dii_high_share + C(year) + C(ets_activity_code) + d_log_gdp_per_capita "
        "+ accession_2004plus + energy_shock_exposure",
        "dii_high_share", "country_code", f"D4 v2b +controls, INTENSITY outcome [{cut_label}]", "item2")
    run(usable_b_int, "d_log_emissions ~ dii_high_share + C(year) + C(ets_activity_code)",
        "dii_high_share", "country_code", f"D3r v2b bare, RAW outcome (same sample as D3) [{cut_label}]", "item2")
    run(usable_b_int_ctrl,
        "d_log_emissions ~ dii_high_share + C(year) + C(ets_activity_code) + d_log_gdp_per_capita "
        "+ accession_2004plus + energy_shock_exposure",
        "dii_high_share", "country_code", f"D4r v2b +controls, RAW outcome (same sample as D4) [{cut_label}]", "item2")

results_item2 = pd.DataFrame([r for r in all_results if r["item"] == "item2"])
results_item2.to_csv(OUT / "phase_c_item2_results.csv", index=False)

# ===========================================================================
# ITEM 3: EIBIS large-firm-only cross-check (EIBIS-only, DII has no size split)
# ===========================================================================
print("\n" + "=" * 90)
print("ITEM 3: EIBIS firm-size split (EIBIS-only -- DII's isoc_e_diin2 has only "
      "size_emp='GE10', no further breakdown, confirmed against the live API)")
print("=" * 90)

eib = pd.read_csv(RAW / "eibis" / "eibis_aggregate.csv")
eib = eib[~eib["country"].isin(["EU", "US"])]
eib_digital = eib[(eib["sector"] == "ALL") & (eib["indicator"] == "Implementation of digital technologies")]
print("EIBIS 'size' categories available:", sorted(eib["size"].unique()))

# base panel: same EU-ETS "20-99" country total used throughout, merged
# with EIBIS digital_multi at each size cut
eu = pd.read_csv(RAW / "eu_ets" / "eu-ets.csv")
eu = eu[eu["year"].str.fullmatch(r"\d{4}")].copy()
eu["year"] = eu["year"].astype(int)
ets_total = eu[(eu["main_activity_code"] == "20-99") & (eu["citl_information"] == "2. Verified emissions")].copy()
ets_total = ets_total.rename(columns={"value": "verified_emissions_t"})[["country_code", "year", "verified_emissions_t"]]
non_country = {"Innovation fund", "Modernisation Fund", "NER 300 auctions", "RRF"}
ets_total = ets_total[~ets_total["country_code"].isin(non_country)]
ets_total["country_code"] = ets_total["country_code"].replace({"GR": "EL"})
ets_total = ets_total.sort_values(["country_code", "year"])
ets_total["log_emissions"] = np.log(ets_total["verified_emissions_t"].clip(lower=1))
ets_total["d_log_emissions"] = ets_total.groupby("country_code")["log_emissions"].diff()
ets_total_overlap = ets_total[ets_total["year"].isin([2023, 2024, 2025])]

# ---------------------------------------------------------------------------
# CORRECTED per phase_c_review.md issue 1: the original comparison was
# ALL-firms on 27 countries vs. Large-firms on 15 countries -- not
# apples-to-apples. The missing cell is ALL-firms on the SAME 15 countries
# that report a Large-firm breakdown. Built and reported alongside the
# other two so the "is this about firm size, or about which countries
# report a size split" question can actually be answered.
# ---------------------------------------------------------------------------
sub_all = eib_digital[eib_digital["size"] == "ALL"][["country", "survey_wave", "Multiple technologies"]].dropna()
sub_all = sub_all.rename(columns={"country": "country_code", "survey_wave": "year", "Multiple technologies": "digital_multi_all"})
sub_large = eib_digital[eib_digital["size"] == "Large"][["country", "survey_wave", "Multiple technologies"]].dropna()
sub_large = sub_large.rename(columns={"country": "country_code", "survey_wave": "year", "Multiple technologies": "digital_multi_large"})

countries_with_large = sorted(sub_large["country_code"].unique())
print(f"\n{len(countries_with_large)} countries report a Large-firm breakdown for all 3 years: {countries_with_large}")

merged_all_27 = ets_total_overlap.merge(sub_all, on=["country_code", "year"], how="inner").dropna(
    subset=["d_log_emissions", "digital_multi_all"])
run(merged_all_27, "d_log_emissions ~ digital_multi_all + C(year)", "digital_multi_all", "country_code",
    "E1a ALL firms, 27 countries (original baseline)", "item3")

merged_all_15 = merged_all_27[merged_all_27["country_code"].isin(countries_with_large)]
run(merged_all_15, "d_log_emissions ~ digital_multi_all + C(year)", "digital_multi_all", "country_code",
    "E1b ALL firms, SAME 15 countries -- the correct like-for-like comparison", "item3")

merged_large_15 = ets_total_overlap.merge(sub_large, on=["country_code", "year"], how="inner").dropna(
    subset=["d_log_emissions", "digital_multi_large"])
run(merged_large_15, "d_log_emissions ~ digital_multi_large + C(year)", "digital_multi_large", "country_code",
    "E1c Large firms, 15 countries", "item3")

# corr(Large, ALL) on the 15-country overlap -- is there independent
# firm-size information here at all?
corr_df = sub_all.merge(sub_large, on=["country_code", "year"], how="inner")
r_size, p_size = stats.pearsonr(corr_df["digital_multi_all"], corr_df["digital_multi_large"])
print(f"\ncorr(digital_multi ALL, digital_multi Large) on the {len(corr_df)}-row 15-country overlap: "
      f"r={r_size:.3f} (p={p_size:.4f}) -- near-collinear if close to 1")
pd.DataFrame([{"n": len(corr_df), "corr_all_large": r_size}]).to_csv(OUT / "phase_c_item3_all_large_correlation.csv", index=False)

# ---------------------------------------------------------------------------
# What actually distinguishes the 15-country subset: leave-one-out (per
# review issue 1, matching the rigor applied to every other fragile result
# in this project) and a composition comparison (GDP, ETS emissions mass)
# against the 12 countries NOT in the subset.
# ---------------------------------------------------------------------------
print("\n--- Leave-one-country-out on E1c (Large firms, 15 countries) ---")
loo3_rows = []
for c in sorted(merged_large_15["country_code"].unique()):
    sub = merged_large_15[merged_large_15["country_code"] != c]
    y, X = patsy.dmatrices("d_log_emissions ~ digital_multi_large + C(year)", data=sub, return_type="dataframe")
    col_idx = list(X.columns).index("digital_multi_large")
    beta, se, t_obs, G = t_stat(y.to_numpy().ravel(), X.to_numpy(), sub["country_code"].to_numpy(), col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    loo3_rows.append({"dropped_country": c, "n": len(sub), "coef": beta, "p_naive_z": p_z})
loo3_df = pd.DataFrame(loo3_rows).sort_values("p_naive_z", ascending=False)
print(loo3_df.to_string(index=False))
loo3_df.to_csv(OUT / "phase_c_item3_leave_one_out.csv", index=False)

print("\n--- Subset composition: the 15 large-firm-reporting countries vs. the other 12 ---")
gdp = pd.read_csv(RAW / "eurostat" / "gdp_per_capita.csv")
gdp2024 = gdp[(gdp["time"] == 2024)].rename(columns={"geo": "country_code", "value": "gdp_per_capita_2024"})[["country_code", "gdp_per_capita_2024"]]
ets_2024 = ets_total[ets_total["year"] == 2024][["country_code", "verified_emissions_t"]].rename(
    columns={"verified_emissions_t": "ets_emissions_2024_t"})
# Use the 27-country EIBIS-covered universe (merged_all_27's own country
# set) as the comparison base, NOT the full 30-geography EU-ETS reporting
# universe (which also includes IS/NO/XI -- EEA/UK geographies EIBIS does
# not survey at all and that were never part of either firm-size cut).
all_27_countries = sorted(merged_all_27["country_code"].unique())
comp = pd.DataFrame({"country_code": all_27_countries})
comp["in_large_subset"] = comp["country_code"].isin(countries_with_large)
comp = comp.merge(gdp2024, on="country_code", how="left").merge(ets_2024, on="country_code", how="left")
comp_summary = comp.groupby("in_large_subset").agg(
    n_countries=("country_code", "count"),
    median_gdp_per_capita=("gdp_per_capita_2024", "median"),
    median_ets_emissions_mt=("ets_emissions_2024_t", lambda s: s.median() / 1e6),
    total_ets_emissions_mt=("ets_emissions_2024_t", lambda s: s.sum() / 1e6),
)
print(comp_summary)
total_mass_all = comp["ets_emissions_2024_t"].sum()
mass_in = comp.loc[comp["in_large_subset"], "ets_emissions_2024_t"].sum()
print(f"Share of total 2024 ETS emissions mass carried by the 15-country subset: {mass_in / total_mass_all:.1%}")
comp_summary.to_csv(OUT / "phase_c_item3_subset_composition.csv")

results_item3 = pd.DataFrame([r for r in all_results if r["item"] == "item3"])
results_item3.to_csv(OUT / "phase_c_item3_results.csv", index=False)

print(f"\nAll Phase C outputs written to {OUT}")
