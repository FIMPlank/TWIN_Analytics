"""
Phase B: regression analysis on the Reviewer-approved DII-based panels
(panel v2a, panel v2b full + excl-combustion cuts). See
analysis/panel_v2/panel_qc.md and panel_qc_review.md for the panel
construction and the three carried-forward constraints this script obeys
throughout:

  1. v2b is ALWAYS reported on both cuts (full incl. combustion,
     excl-combustion) side by side, always with sector fixed effects.
  2. DII never enters first-differenced -- 80% of usable rows sit on a DII
     methodology version-break (v3/v4 alternating annually from 2021), so a
     year-over-year change in DII conflates real change with a measurement
     artifact (round-one Eurostat-controls mistake, not repeated here).
     DII enters in LEVELS (contemporaneous or lagged), with year FE to
     absorb common trends.
  3. v2a's DII is manufacturing-only (nace_r2='C') but paired against ALL
     EU-ETS stationary emissions (which combustion, largely non-
     manufacturing, dominates) -- flagged explicitly wherever v2a results
     appear.

Also applied proactively (all three country-level review rounds' lessons,
baked in from the start rather than found again by a Reviewer):
  - Every headline model reports THREE p-values: naive cluster z, t(G-1),
    and a wild cluster bootstrap (restricted null, Rademacher weights) --
    never a naive p-value alone.
  - Controls (GDP growth, energy-shock exposure) enter as changes or
    pre-determined baselines, never as contemporaneous levels against a
    differenced outcome.
  - A placebo/timing (Granger-style) check: does FUTURE digitalization
    "predict" PAST emissions change? Run as a first-class check alongside
    the lagged ("real") specification, not an afterthought.
  - A convergence/catch-up control using the EU accession cohort already
    built into both panels.
  - Energy-shock exposure via country-level PRE-CRISIS energy import
    dependency, interacted with a crisis-period indicator (not just year FE,
    which only absorbs the EU-wide average shock).
  - v2a and v2b are reported as separate, parallel analyses, never forced
    into one model.
  - EIBIS's digital_multi carried through as a secondary cross-check on the
    2023-2025 overlap.

Usage:
    python analysis/phase_b_analysis.py
"""

import numpy as np
import pandas as pd
import patsy
import statsmodels.api as sm
import statsmodels.formula.api as smf
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
BASE_SEED = 20260101
N_BOOT = 1999  # wild cluster bootstrap reps per model -- kept modest (vs. 4999
               # in the country-level extension) because Phase B runs ~20
               # headline models; still >>enough for a 2-3 decimal p-value

# ---------------------------------------------------------------------------
# Generic small-cluster-robust OLS fitting: naive cluster z, t(G-1), and a
# wild cluster bootstrap (restricted null, Rademacher weights) -- the same
# machinery built and validated in analysis/extension_analysis.py, ported
# here and generalized to arbitrary patsy formulas (so it works with year/
# sector fixed effects without hand-building dummy columns).
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
    """Fit `formula` by OLS on `df`, report coef/SE on `target_col` with
    three p-values (naive z, t(G-1), wild cluster bootstrap), clustering on
    `cluster_col`. Returns a dict row and prints a one-line summary."""
    y, X = patsy.dmatrices(formula, data=df, return_type="dataframe")
    col_idx = list(X.columns).index(target_col)
    y = y.to_numpy().ravel()
    Xm = X.to_numpy()
    groups = df.loc[X.index, cluster_col].to_numpy()
    n = len(y)
    beta, se, t_obs, G = t_stat(y, Xm, groups, col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    p_t = 2 * (1 - stats.t.cdf(np.abs(t_obs), df=G - 1))
    _, _, _, p_wild, _ = wild_cluster_bootstrap_p(y, Xm, groups, col_idx, n_boot, BASE_SEED + seed_offset)
    row = {
        "model": model_id, "target": target_col, "n": n, "G_clusters": G,
        "coef": beta, "se_cluster": se, "t_stat": t_obs,
        "p_naive_z": p_z, "p_t_Gminus1": p_t, "p_wild_bootstrap": p_wild,
    }
    print(f"{model_id:45s} target={target_col:35s} n={n:4d} G={G:3d} "
          f"coef={beta:+.4f}  p(z)={p_z:.4f}  p(t)={p_t:.4f}  p(wild,{n_boot})={p_wild:.4f}")
    return row

results = []
_seed_counter = [0]


def run(df, formula, target_col, cluster_col, model_id):
    _seed_counter[0] += 1
    row = fit_report(df, formula, target_col, cluster_col, model_id, _seed_counter[0])
    results.append(row)
    return row


# ---------------------------------------------------------------------------
# 1. Load panels (already validated -- see panel_qc.md / panel_qc_review.md)
# ---------------------------------------------------------------------------
v2a = pd.read_csv(ROOT.parent / "analysis" / "output" / "panel_country_year_v2.csv")
v2b_full = pd.read_csv(ROOT.parent / "analysis" / "output" / "panel_sector_country_year_v2.csv")
v2b_excl = pd.read_csv(ROOT.parent / "analysis" / "output" / "panel_sector_country_year_v2_excl_combustion.csv")

# ---------------------------------------------------------------------------
# 2. Build lag/lead DII (levels, never differenced) via explicit
#    (country[,sector], year) merges -- NOT positional .shift(), which would
#    misalign wherever a panel has a gap year for that country/sector.
# ---------------------------------------------------------------------------

def add_lag_lead(df, key_cols, value_col, out_prefix):
    base = df[key_cols + ["year", value_col]].drop_duplicates(subset=key_cols + ["year"])
    lag = base.rename(columns={value_col: f"{out_prefix}_lag", "year": "year_lag_src"})
    lag["year"] = lag["year_lag_src"] + 1
    lead = base.rename(columns={value_col: f"{out_prefix}_lead", "year": "year_lead_src"})
    lead["year"] = lead["year_lead_src"] - 1
    out = df.merge(lag[key_cols + ["year", f"{out_prefix}_lag"]], on=key_cols + ["year"], how="left")
    out = out.merge(lead[key_cols + ["year", f"{out_prefix}_lead"]], on=key_cols + ["year"], how="left")
    return out


v2a = add_lag_lead(v2a, ["country_code"], "dii_high_share_manufacturing", "dii")
v2b_full = add_lag_lead(v2b_full, ["country_code", "ets_activity_code"], "dii_high_share", "dii")
v2b_excl = add_lag_lead(v2b_excl, ["country_code", "ets_activity_code"], "dii_high_share", "dii")

# ---------------------------------------------------------------------------
# 3. Energy-shock exposure: country-level PRE-CRISIS (2021) energy import
#    dependency, interacted with a crisis-period indicator (2022-2023) --
#    i.e. "how exposed was this country to the shock, given where it stood
#    right before it hit", not a contemporaneous level (which would itself
#    be a bad control -- energy dependency in 2022 partly reflects the
#    crisis's own effect on trade flows) and not just year FE (which only
#    absorbs the EU-wide average shock, not country-differential exposure).
# ---------------------------------------------------------------------------

def add_energy_shock_exposure(df):
    baseline = df[df["year"] == 2021][["country_code", "energy_import_dependency_pct"]].drop_duplicates("country_code")
    baseline = baseline.rename(columns={"energy_import_dependency_pct": "energy_dep_2021_baseline"})
    out = df.merge(baseline, on="country_code", how="left")
    out["crisis_period"] = out["year"].isin([2022, 2023]).astype(float)
    out["energy_shock_exposure"] = out["energy_dep_2021_baseline"] * out["crisis_period"]
    return out


v2a = add_energy_shock_exposure(v2a)
v2b_full = add_energy_shock_exposure(v2b_full)
v2b_excl = add_energy_shock_exposure(v2b_excl)

# ---------------------------------------------------------------------------
# 4. Convergence/catch-up control: binary "accession_2004_or_later" (EU-15
#    baseline vs. 2004/2007/2013 accession waves) -- simpler than full
#    4-category dummies, which would cost too many degrees of freedom given
#    G~20-30 clusters.
# ---------------------------------------------------------------------------
for df in (v2a, v2b_full, v2b_excl):
    df["accession_2004plus"] = df["eu_accession_cohort"].isin(["2004", "2007", "2013"]).astype(float)

for df in (v2a, v2b_full, v2b_excl):
    df.to_csv(OUT / f"phase_b_working_{'v2a' if df is v2a else ('v2b_full' if df is v2b_full else 'v2b_excl')}.csv", index=False)

print(f"v2a: {len(v2a)} rows, {v2a['country_code'].nunique()} countries")
print(f"v2b full: {len(v2b_full)} rows; v2b excl-combustion: {len(v2b_excl)} rows")

# ===========================================================================
# PART A -- Panel v2a: country x year (SCOPE-MISMATCH REMINDER printed once
# and repeated in the write-up: dii_high_share_manufacturing covers
# manufacturing enterprises only, but d_log_emissions is ALL EU-ETS
# stationary emissions, which combustion -- largely non-manufacturing --
# dominates. Every v2a result below inherits this mismatch.)
# ===========================================================================
print("\n" + "=" * 90)
print("PART A: Panel v2a (country x year) -- DII is MANUFACTURING-ONLY, "
      "outcome is ALL stationary ETS emissions (scope mismatch, see panel_qc.md #3)")
print("=" * 90)

usable_a = v2a.dropna(subset=["d_log_emissions", "dii_high_share_manufacturing"]).copy()

# A1: bare, DII level + year FE
run(usable_a, "d_log_emissions ~ dii_high_share_manufacturing + C(year)",
    "dii_high_share_manufacturing", "country_code", "A1 bare (level + year FE)")

# A2: + controls (GDP growth [already a change], accession convergence
# control, energy-shock exposure) -- controls are changes/pre-determined
# baselines, never contemporaneous levels against the differenced outcome
a2_df = usable_a.dropna(subset=["d_log_gdp_per_capita", "energy_shock_exposure", "accession_2004plus"])
run(a2_df,
    "d_log_emissions ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "A2 +controls (GDP growth, accession, energy shock)")

# A2 DECOMPOSITION (per phase_b_review.md issue 2, run for v2a too as a
# direct comparison point against the v2b decomposition below): does
# accession_2004plus alone flip v2a's sign the way it does in v2b?
run(a2_df, "d_log_emissions ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita",
    "dii_high_share_manufacturing", "country_code", "A2d decomposition: bare + GDP growth only")
run(a2_df, "d_log_emissions ~ dii_high_share_manufacturing + C(year) + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "A2d decomposition: bare + energy-shock exposure only")
run(a2_df, "d_log_emissions ~ dii_high_share_manufacturing + C(year) + accession_2004plus",
    "dii_high_share_manufacturing", "country_code", "A2d decomposition: bare + accession_2004plus only")

# A2 ROBUSTNESS: energy_shock_exposure is built from raw 2021 energy-import
# dependency, which panel_qc.md flagged as having an extreme outlier
# (Norway, -682%). Phase A recommended winsorizing before using this
# variable in a regression; that recommendation was not acted on when A2
# was first built. Added here as an explicit robustness row, winsorizing
# energy_dep_2021_baseline at the 1st/99th percentile before building the
# interaction.
a2_wins_df = a2_df.copy()
lo, hi = a2_wins_df["energy_dep_2021_baseline"].quantile([0.01, 0.99])
a2_wins_df["energy_dep_2021_baseline_wins"] = a2_wins_df["energy_dep_2021_baseline"].clip(lo, hi)
a2_wins_df["energy_shock_exposure_wins"] = a2_wins_df["energy_dep_2021_baseline_wins"] * a2_wins_df["crisis_period"]
run(a2_wins_df,
    "d_log_emissions ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure_wins",
    "dii_high_share_manufacturing", "country_code",
    "A2 robustness: energy-shock exposure winsorized at 1/99pct (Norway outlier)")

# A3 (real) vs A4 (placebo/Granger): does LAGGED DII predict this year's
# emissions change (real, pre-determined), or does FUTURE (lead) DII
# "predict" it too (placebo -- if so, that's reverse causality/confounding,
# not a real effect).
#
# IMPORTANT (per phase_b_review.md issue 1): the lagged (A3) and lead (A4)
# specs must be run on the IDENTICAL set of rows for the comparison to be
# meaningful -- dropping each spec's own missing rows independently is NOT
# enough, because dii_lag is missing for each country's FIRST observed year
# and dii_lead is missing for each country's LAST observed year: two
# different, only partially overlapping sets of rows. Fitting each spec on
# "whatever survives its own dropna" can produce equal sample sizes (a
# coincidence, not evidence of comparability) while the actual row sets
# differ substantially. Both specs below are restricted to the common
# subsample where dii_lag AND dii_lead (and every control) are all
# simultaneously non-missing, so "real" and "placebo" are evaluated on
# exactly the same observations.
a34_common_df = usable_a.dropna(
    subset=["dii_lag", "dii_lead", "d_log_gdp_per_capita", "energy_shock_exposure", "accession_2004plus"]
)
run(a34_common_df,
    "d_log_emissions ~ dii_lag + C(year) + d_log_gdp_per_capita + accession_2004plus + energy_shock_exposure",
    "dii_lag", "country_code", "A3 REAL: lagged DII (t-1) + controls + year FE [matched lag/lead sample]")

run(a34_common_df,
    "d_log_emissions ~ dii_lead + C(year) + d_log_gdp_per_capita + accession_2004plus + energy_shock_exposure",
    "dii_lead", "country_code", "A4 PLACEBO: lead DII (t+1) + controls + year FE [matched lag/lead sample]")

# A5: convergence interaction -- does the DII effect differ for
# still-catching-up (2004/2007/2013 accession) countries vs. EU-15? And does
# the main DII effect survive once this is directly interacted rather than
# just added as a control?
a5_df = a2_df.copy()
run(a5_df,
    "d_log_emissions ~ dii_high_share_manufacturing * accession_2004plus + C(year) "
    "+ d_log_gdp_per_capita + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "A5 convergence interaction: DII x accession_2004plus (main effect)")
run(a5_df,
    "d_log_emissions ~ dii_high_share_manufacturing * accession_2004plus + C(year) "
    "+ d_log_gdp_per_capita + energy_shock_exposure",
    "dii_high_share_manufacturing:accession_2004plus", "country_code",
    "A5 convergence interaction: DII x accession_2004plus (interaction term)")

# ---------------------------------------------------------------------------
# A6: EIBIS cross-check on the 2023-2025 overlap. NOTE (per
# phase_b_review.md issue 3): DII and EIBIS are NOT independent
# measurements of digitalization -- they correlate strongly on this overlap
# sample (computed below and reported in the write-up), so their
# coefficients landing in a similar place is close to mechanical, not two
# separately-informative lines of evidence. This is reported as a
# measurement-consistency check, not "triangulation".
# ---------------------------------------------------------------------------
print("\n--- A6: EIBIS vs DII cross-check, 2023-2025 overlap only ---")
overlap = usable_a[usable_a["year"].isin([2023, 2024, 2025])].dropna(subset=["eibis_digital_multi"])
run(overlap, "d_log_emissions ~ dii_high_share_manufacturing + C(year)",
    "dii_high_share_manufacturing", "country_code", "A6a DII, 2023-2025 overlap sample")
run(overlap, "d_log_emissions ~ eibis_digital_multi + C(year)",
    "eibis_digital_multi", "country_code", "A6b EIBIS digital_multi, SAME 2023-2025 overlap sample")

dii_eibis_corr = overlap["dii_high_share_manufacturing"].corr(overlap["eibis_digital_multi"])
print(f"corr(DII, EIBIS) on the {len(overlap)}-row overlap sample: r={dii_eibis_corr:.3f} "
      f"-- NOT independent measurements (see A6 note above)")
pd.DataFrame([{"n": len(overlap), "corr_dii_eibis": dii_eibis_corr}]).to_csv(
    OUT / "phase_b_dii_eibis_correlation.csv", index=False)

results_a_df = pd.DataFrame(results)
results_a_df.to_csv(OUT / "phase_b_v2a_results.csv", index=False)

# ===========================================================================
# PART B -- Panel v2b: country x ETS-sector x year, BOTH cuts side by side,
# ALWAYS with sector fixed effects (carried-forward constraint #1). Never
# pool without C(ets_activity_code); never present only one cut.
# ===========================================================================
print("\n" + "=" * 90)
print("PART B: Panel v2b (country x ETS-sector x year) -- BOTH cuts, sector FE always")
print("=" * 90)

results_b = []


def run_b(df, formula, target_col, cluster_col, model_id, cut_label):
    _seed_counter[0] += 1
    row = fit_report(df, formula, target_col, cluster_col, f"{model_id} [{cut_label}]", _seed_counter[0])
    row["cut"] = cut_label
    row["model_base"] = model_id
    results_b.append(row)
    return row


for cut_label, panel in [("full (incl. combustion)", v2b_full), ("excl-combustion", v2b_excl)]:
    usable_b = panel.dropna(subset=["d_log_emissions", "dii_high_share"]).copy()

    # B1: bare, DII level + year FE + sector FE
    run_b(usable_b, "d_log_emissions ~ dii_high_share + C(year) + C(ets_activity_code)",
          "dii_high_share", "country_code", "B1 bare (level + year FE + sector FE)", cut_label)

    # B2: + controls
    b2_df = usable_b.dropna(subset=["d_log_gdp_per_capita", "energy_shock_exposure", "accession_2004plus"])
    run_b(b2_df,
          "d_log_emissions ~ dii_high_share + C(year) + C(ets_activity_code) + d_log_gdp_per_capita "
          "+ accession_2004plus + energy_shock_exposure",
          "dii_high_share", "country_code", "B2 +controls", cut_label)

    # B2 DECOMPOSITION (per phase_b_review.md issue 2): B1 (bare) is positive
    # and B2 (all controls) sign varies by cut -- rather than wave this off as
    # generic "instability", add each control to the bare+FE spec ONE AT A
    # TIME, on the identical b2_df sample, to identify which specific control
    # is responsible for any sign change.
    run_b(b2_df, "d_log_emissions ~ dii_high_share + C(year) + C(ets_activity_code) + d_log_gdp_per_capita",
          "dii_high_share", "country_code", "B2d decomposition: bare + GDP growth only", cut_label)
    run_b(b2_df, "d_log_emissions ~ dii_high_share + C(year) + C(ets_activity_code) + energy_shock_exposure",
          "dii_high_share", "country_code", "B2d decomposition: bare + energy-shock exposure only", cut_label)
    run_b(b2_df, "d_log_emissions ~ dii_high_share + C(year) + C(ets_activity_code) + accession_2004plus",
          "dii_high_share", "country_code", "B2d decomposition: bare + accession_2004plus only", cut_label)

    # B3 (real) vs B4 (placebo/Granger) -- run on the MATCHED lag/lead sample
    # (per phase_b_review.md issue 1 -- see the identical fix and rationale
    # for A3/A4 above), not on each spec's own independently-dropped-NA rows.
    b34_common_df = usable_b.dropna(
        subset=["dii_lag", "dii_lead", "d_log_gdp_per_capita", "energy_shock_exposure", "accession_2004plus"]
    )
    run_b(b34_common_df,
          "d_log_emissions ~ dii_lag + C(year) + C(ets_activity_code) + d_log_gdp_per_capita "
          "+ accession_2004plus + energy_shock_exposure",
          "dii_lag", "country_code", "B3 REAL: lagged DII (t-1) + controls [matched lag/lead sample]", cut_label)

    run_b(b34_common_df,
          "d_log_emissions ~ dii_lead + C(year) + C(ets_activity_code) + d_log_gdp_per_capita "
          "+ accession_2004plus + energy_shock_exposure",
          "dii_lead", "country_code", "B4 PLACEBO: lead DII (t+1) + controls [matched lag/lead sample]", cut_label)

    # B5: convergence interaction
    b5_df = b2_df.copy()
    run_b(b5_df,
          "d_log_emissions ~ dii_high_share * accession_2004plus + C(year) + C(ets_activity_code) "
          "+ d_log_gdp_per_capita + energy_shock_exposure",
          "dii_high_share", "country_code", "B5 convergence interaction (main effect)", cut_label)
    run_b(b5_df,
          "d_log_emissions ~ dii_high_share * accession_2004plus + C(year) + C(ets_activity_code) "
          "+ d_log_gdp_per_capita + energy_shock_exposure",
          "dii_high_share:accession_2004plus", "country_code", "B5 convergence interaction (interaction term)", cut_label)

results_b_df = pd.DataFrame(results_b)
results_b_df.to_csv(OUT / "phase_b_v2b_results.csv", index=False)

# ---------------------------------------------------------------------------
# 5. Headline forest plot: DII coefficient +/- t(G-1)-based 95% CI across
#    the key specifications, v2a and v2b (both cuts) shown together so
#    agreement/disagreement between the country-year and sector-country-year
#    panels is visible at a glance. CI uses the cluster-robust SE with a
#    t(G-1) critical value (a reasonable small-sample approximation); the
#    p-values driving any significance claim remain the wild-bootstrap ones
#    reported in the tables, not this plot's CI in isolation.
# ---------------------------------------------------------------------------
plot_rows = []
key_models_a = ["A1 bare (level + year FE)", "A2 +controls (GDP growth, accession, energy shock)",
                 "A3 REAL: lagged DII (t-1) + controls + year FE [matched lag/lead sample]",
                 "A4 PLACEBO: lead DII (t+1) + controls + year FE [matched lag/lead sample]"]
for m in key_models_a:
    r = results_a_df[results_a_df["model"] == m].iloc[0]
    plot_rows.append({"label": f"v2a: {m.split(':')[0].split('(')[0].strip()}", "coef": r["coef"],
                       "se": r["se_cluster"], "G": r["G_clusters"], "p_wild": r["p_wild_bootstrap"]})

key_models_b = ["B1 bare (level + year FE + sector FE)", "B2 +controls",
                "B3 REAL: lagged DII (t-1) + controls [matched lag/lead sample]",
                "B4 PLACEBO: lead DII (t+1) + controls [matched lag/lead sample]"]
for cut_label in ["full (incl. combustion)", "excl-combustion"]:
    for m in key_models_b:
        r = results_b_df[(results_b_df["model_base"] == m) & (results_b_df["cut"] == cut_label)].iloc[0]
        short_cut = "full" if "full" in cut_label else "excl-comb"
        plot_rows.append({"label": f"v2b ({short_cut}): {m.split(':')[0].split('(')[0].strip()}",
                           "coef": r["coef"], "se": r["se_cluster"], "G": r["G_clusters"], "p_wild": r["p_wild_bootstrap"]})

plot_df = pd.DataFrame(plot_rows)
plot_df["tcrit"] = plot_df["G"].apply(lambda g: stats.t.ppf(0.975, df=g - 1))
plot_df["ci_lo"] = plot_df["coef"] - plot_df["tcrit"] * plot_df["se"]
plot_df["ci_hi"] = plot_df["coef"] + plot_df["tcrit"] * plot_df["se"]
plot_df.to_csv(OUT / "phase_b_forest_plot_data.csv", index=False)

fig, ax = plt.subplots(figsize=(9, 7))
y_pos = np.arange(len(plot_df))[::-1]
ax.axvline(0, color="#999999", linewidth=1, linestyle="--", zorder=1)
colors = ["#4c72b0" if lbl.startswith("v2a") else ("#55a868" if "full" in lbl else "#c44e52") for lbl in plot_df["label"]]
for yi, (_, row), color in zip(y_pos, plot_df.iterrows(), colors):
    ax.errorbar(row["coef"], yi, xerr=[[row["coef"] - row["ci_lo"]], [row["ci_hi"] - row["coef"]]],
                fmt="o", color="black", ecolor=color, elinewidth=2, capsize=3, markersize=5, zorder=3)
ax.set_yticks(y_pos)
ax.set_yticklabels(plot_df["label"], fontsize=8)
ax.set_xlabel("Coefficient on DII (level) -- 95% CI (t(G-1)-based)")
ax.set_title("Phase B headline coefficients: v2a (blue), v2b full (green), v2b excl-combustion (red)\n"
             "None clear conventional significance under wild-bootstrap p-values (see tables)", fontsize=10)
fig.tight_layout()
fig.savefig(OUT / "phase_b_forest_plot.png", dpi=150)
plt.close(fig)

print(f"\nAll Phase B outputs written to {OUT}")
