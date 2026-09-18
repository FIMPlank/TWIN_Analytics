"""US extension: does digitalization intensity predict verified emissions
change at the state/county level? Mirrors the small-cluster-robust
inference machinery of analysis/phase_b_analysis.py (naive cluster z,
t(G-1), and a restricted-null Rademacher wild cluster bootstrap), adapted
to this panel's own structure. See analysis/us_extension/panel_qc.md for
data construction, coverage, and the headline substitution (BLS QCEW tech-
sector employment share in place of the blocked Census ABS technology
module -- and see panel_qc.md Sec.1 for why this substitute cannot fully
carry the hypothesis, quantified there and repeated below).

**Revision note (round 2, post-review):** `analysis/us_extension/review.md`
found a blocking data bug (a silent NaN->0 conversion in the county-level
emissions aggregation, fixed upstream in `build_panel.py`) and three
overclaimed headline statements ("every p above 0.59", "cleaner null than
the EU's", "no stable sign"), all now corrected below. Winsorization,
a PETRO_NG-excluded cut, a first-differenced regressor spec, a
territory-excluded cut, and a leave-one-state-out check (all flagged as
missing by the review) are added as first-class rows, not limitations.

Outcome: `d_log_emissions` (year-over-year change in log GHGRP direct-
emitter CO2e, aggregated to state or county), identical construction to
the EU panels for comparability. `d_log_emissions_excl_petro_ng` is an
alternate outcome excluding Subpart W (Petroleum and Natural Gas Systems,
reported at basin/operator level -- see panel_qc.md Sec.2b).

Regressor: `tech_emp_share` (QCEW NAICS 51 + 5415 employment / total
private employment), entered as a level in the headline specs and as a
first difference (`tech_emp_share_diff`) in the S7-style robustness spec.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import patsy
from scipy import stats

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

BASE_SEED = 20260917
N_BOOT = 1999
WINSOR_PCT = 0.01  # 1st/99th percentile

# ---------------------------------------------------------------------------
# Small-cluster-robust OLS machinery (naive cluster z, t(G-1), wild cluster
# bootstrap) -- ported from analysis/phase_b_analysis.py, unchanged logic.
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


def fit_report(df, formula, target_col, cluster_col, model_id, seed_offset, n_boot=N_BOOT, verbose=True):
    y, X = patsy.dmatrices(formula, data=df, return_type="dataframe")
    col_idx = list(X.columns).index(target_col)
    y = y.to_numpy().ravel()
    Xm = X.to_numpy()
    groups = df.loc[X.index, cluster_col].to_numpy()
    n = len(y)
    beta, se, t_obs, G = t_stat(y, Xm, groups, col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    p_t = 2 * (1 - stats.t.cdf(np.abs(t_obs), df=G - 1))
    tcrit = stats.t.ppf(0.975, df=G - 1)
    ci_lo, ci_hi = beta - tcrit * se, beta + tcrit * se
    if n_boot:
        _, _, _, p_wild, _ = wild_cluster_bootstrap_p(y, Xm, groups, col_idx, n_boot, BASE_SEED + seed_offset)
    else:
        p_wild = np.nan
    row = {
        "model": model_id, "target": target_col, "n": n, "G_clusters": G,
        "coef": beta, "se_cluster": se, "t_stat": t_obs, "ci_lo": ci_lo, "ci_hi": ci_hi,
        "p_naive_z": p_z, "p_t_Gminus1": p_t, "p_wild_bootstrap": p_wild,
    }
    if verbose:
        print(f"{model_id:45s} n={n:5d} G={G:3d} coef={beta:+.4f} [{ci_lo:+.3f},{ci_hi:+.3f}]  "
              f"p(z)={p_z:.4f}  p(t)={p_t:.4f}  p(wild)={p_wild if n_boot else float('nan'):.4f}")
    return row


results = []
_seed_counter = [0]


def run(df, formula, target_col, cluster_col, model_id, n_boot=N_BOOT):
    _seed_counter[0] += 1
    row = fit_report(df, formula, target_col, cluster_col, model_id, _seed_counter[0], n_boot=n_boot)
    results.append(row)
    return row


def add_lag_lead(df, key_cols, value_col, out_prefix):
    base = df[key_cols + ["year", value_col]].drop_duplicates(subset=key_cols + ["year"])
    lag = base.rename(columns={value_col: f"{out_prefix}_lag", "year": "year_lag_src"})
    lag["year"] = lag["year_lag_src"] + 1
    lead = base.rename(columns={value_col: f"{out_prefix}_lead", "year": "year_lead_src"})
    lead["year"] = lead["year_lead_src"] - 1
    out = df.merge(lag[key_cols + ["year", f"{out_prefix}_lag"]], on=key_cols + ["year"], how="left")
    out = out.merge(lead[key_cols + ["year", f"{out_prefix}_lead"]], on=key_cols + ["year"], how="left")
    return out


def winsorize(s: pd.Series, pct: float = WINSOR_PCT) -> pd.Series:
    lo, hi = s.quantile(pct), s.quantile(1 - pct)
    return s.clip(lo, hi)


# ---------------------------------------------------------------------------
# 1. Load panels
# ---------------------------------------------------------------------------
state = pd.read_csv(OUT / "panel_state_year_us.csv", dtype={"state_fips": str})
county = pd.read_csv(OUT / "panel_county_year_us.csv", dtype={"county_fips": str, "state_fips": str})

state = add_lag_lead(state, ["state_fips"], "tech_emp_share", "tech")
county = add_lag_lead(county, ["county_fips"], "tech_emp_share", "tech")

state_usable = state.dropna(subset=["d_log_emissions", "tech_emp_share"]).copy()
county_usable = county.dropna(subset=["d_log_emissions", "tech_emp_share"]).copy()

# Winsorized outcome, computed on each usable estimation sample (1st/99th pct).
state_usable["d_log_emissions_w"] = winsorize(state_usable["d_log_emissions"])
county_usable["d_log_emissions_w"] = winsorize(county_usable["d_log_emissions"])

print(f"State panel usable rows: {len(state_usable)} ({state_usable['state_fips'].nunique()} states, "
      f"{state_usable['year'].min()}-{state_usable['year'].max()})")
print(f"County panel usable rows: {len(county_usable)} ({county_usable['county_fips'].nunique()} counties, "
      f"{county_usable['year'].min()}-{county_usable['year'].max()})")

# ---------------------------------------------------------------------------
# 2. Descriptive correlations
# ---------------------------------------------------------------------------
print("\n--- Descriptive correlations (raw, no FE) ---")
r_state = state_usable[["d_log_emissions", "tech_emp_share"]].corr().iloc[0, 1]
print(f"State-year: corr(d_log_emissions, tech_emp_share) = {r_state:.4f}, n={len(state_usable)}")
r_county = county_usable[["d_log_emissions", "tech_emp_share"]].corr().iloc[0, 1]
print(f"County-year: corr(d_log_emissions, tech_emp_share) = {r_county:.4f}, n={len(county_usable)}")

# --- B2 correlations (review): tech_emp_share vs. how INDUSTRIAL an area
# is. Computed on the 2023 cross-section (most recent, least missing).
print("\n--- B2 check: is tech_emp_share an inverse index of industrial intensity? ---")
xs = state.dropna(subset=["tech_emp_share", "total_co2e", "emp_total"])
xs = xs[xs["year"] == 2023].copy()
xs["log_co2e_per_emp"] = np.log(xs["total_co2e"] / xs["emp_total"])
xs["log_emp_total"] = np.log(xs["emp_total"])
xs["facilities_per_10k_emp"] = xs["n_facilities"] / (xs["emp_total"] / 10000)
b2_state = {
    "vs_log_co2e_per_employee": xs[["tech_emp_share", "log_co2e_per_emp"]].corr().iloc[0, 1],
    "vs_log_private_employment": xs[["tech_emp_share", "log_emp_total"]].corr().iloc[0, 1],
    "vs_facilities_per_10k_emp": xs[["tech_emp_share", "facilities_per_10k_emp"]].corr().iloc[0, 1],
}
print("State (2023 cross-section, n=%d):" % len(xs), b2_state)
top8 = xs.sort_values("tech_emp_share", ascending=False).head(8)["state_fips"].tolist()
bot8 = xs.sort_values("tech_emp_share", ascending=True).head(8)["state_fips"].tolist()
print(f"  Top-8 tech_emp_share state_fips: {top8}")
print(f"  Bottom-8 tech_emp_share state_fips: {bot8}")

xc = county.dropna(subset=["tech_emp_share", "total_co2e", "emp_total"])
xc = xc[(xc["year"] == 2023) & (xc["emp_total"] > 0) & (xc["total_co2e"] > 0)].copy()
xc["log_co2e_per_emp"] = np.log(xc["total_co2e"] / xc["emp_total"])
b2_county = xc[["tech_emp_share", "log_co2e_per_emp"]].corr().iloc[0, 1]
print(f"County (2023 cross-section, n={len(xc)}): vs_log_co2e_per_employee = {b2_county:.4f}")

pd.DataFrame([
    {"level": "state", "vs": "log_co2e_per_employee", "corr": b2_state["vs_log_co2e_per_employee"]},
    {"level": "state", "vs": "log_private_employment", "corr": b2_state["vs_log_private_employment"]},
    {"level": "state", "vs": "facilities_per_10k_emp", "corr": b2_state["vs_facilities_per_10k_emp"]},
    {"level": "county", "vs": "log_co2e_per_employee", "corr": b2_county},
]).to_csv(OUT / "us_b2_proxy_validity_correlations.csv", index=False)

# ---------------------------------------------------------------------------
# 3. Headline regressions -- state panel
# ---------------------------------------------------------------------------
print("\n--- State-year panel (cluster = state) ---")
run(state_usable, "d_log_emissions ~ tech_emp_share + C(year)", "tech_emp_share", "state_fips", "S1 bare (+ year FE)")
run(state_usable, "d_log_emissions_w ~ tech_emp_share + C(year)", "tech_emp_share", "state_fips", "S1w winsorized outcome (1/99)")
run(state_usable, "d_log_emissions ~ tech_emp_share + np.log(n_facilities) + C(year)", "tech_emp_share", "state_fips", "S2 + log(n_facilities) control")

state_diff = state_usable.dropna(subset=["tech_emp_share_diff"])
run(state_diff, "d_log_emissions ~ tech_emp_share_diff + C(year)", "tech_emp_share_diff", "state_fips", "S7 differenced regressor")

# S5: exclude PR, VI, DC (territories + non-state federal district).
state_50 = state_usable[~state_usable["state_fips"].isin(["72", "78", "11"])]
run(state_50, "d_log_emissions ~ tech_emp_share + C(year)", "tech_emp_share", "state_fips", "S5 excl. PR+VI+DC")

# S6: state FE, to show the state panel is ~98% cross-sectional and adding
# state FE (i.e. asking only about within-state variation) makes the
# regressor's already-thin within-state variance uninformative.
run(state_usable, "d_log_emissions ~ tech_emp_share + C(year) + C(state_fips)", "tech_emp_share", "state_fips", "S6 + state FE (within-state only)")

matched_state = state_usable.dropna(subset=["tech_lag", "tech_lead"])
print(f"Matched lag/lead sample (state): n={len(matched_state)}")
run(matched_state, "d_log_emissions ~ tech_lag + C(year)", "tech_lag", "state_fips", "S3 REAL: lagged tech share")
run(matched_state, "d_log_emissions ~ tech_lead + C(year)", "tech_lead", "state_fips", "S4 PLACEBO: lead tech share")

# Leave-one-state-out on the headline bare spec (S1). t(G-1) only (no wild
# bootstrap per drop -- 53 reruns x 1999 reps each is not worth the cost
# when the review's own p_t-based check already establishes no single-state
# dominance; matches the level of rigor the EU project used for its own
# leave-one-out checks in analysis/analysis.py).
print("\n--- Leave-one-state-out (S1 spec, t(G-1) only) ---")
loo_rows = []
for drop_state in sorted(state_usable["state_fips"].unique()):
    sub = state_usable[state_usable["state_fips"] != drop_state]
    if sub["state_fips"].nunique() < 6:
        continue
    row = fit_report(sub, "d_log_emissions ~ tech_emp_share + C(year)", "tech_emp_share", "state_fips",
                      f"S1 drop {drop_state}", 0, n_boot=0, verbose=False)
    row["dropped_state_fips"] = drop_state
    loo_rows.append(row)
loo_df = pd.DataFrame(loo_rows)
loo_df.to_csv(OUT / "us_state_leave_one_out.csv", index=False)
print(f"LOO coef range: [{loo_df['coef'].min():+.4f}, {loo_df['coef'].max():+.4f}], "
      f"sign flips: {(np.sign(loo_df['coef']) != np.sign(loo_df['coef'].iloc[0])).sum()}, "
      f"min p_t: {loo_df['p_t_Gminus1'].min():.4f} (dropping {loo_df.loc[loo_df['p_t_Gminus1'].idxmin(), 'dropped_state_fips']})")

# ---------------------------------------------------------------------------
# 4. Headline regressions -- county panel
# ---------------------------------------------------------------------------
print("\n--- County-year panel (cluster = state, state FE) ---")
run(county_usable, "d_log_emissions ~ tech_emp_share + C(year) + C(state_fips)", "tech_emp_share", "state_fips", "C1 bare (+ year FE + state FE)")
run(county_usable, "d_log_emissions_w ~ tech_emp_share + C(year) + C(state_fips)", "tech_emp_share", "state_fips", "C1w winsorized outcome (1/99)")
run(county_usable, "d_log_emissions ~ tech_emp_share + np.log(n_facilities) + C(year) + C(state_fips)", "tech_emp_share", "state_fips", "C2 + log(n_facilities) control")

county_diff = county_usable.dropna(subset=["tech_emp_share_diff"])
run(county_diff, "d_log_emissions ~ tech_emp_share_diff + C(year) + C(state_fips)", "tech_emp_share_diff", "state_fips", "C7 differenced regressor")

# S2-equivalent for county: exclude Subpart W (PETRO_NG), and combine with
# winsorization -- the review's "most suggestive result anywhere" cut.
county_petro = county.dropna(subset=["d_log_emissions_excl_petro_ng", "tech_emp_share"]).copy()
county_petro["d_log_emissions_excl_petro_ng_w"] = winsorize(county_petro["d_log_emissions_excl_petro_ng"])
run(county_petro, "d_log_emissions_excl_petro_ng ~ tech_emp_share + C(year) + C(state_fips)", "tech_emp_share", "state_fips", "C5 excl. PETRO_NG")
run(county_petro, "d_log_emissions_excl_petro_ng_w ~ tech_emp_share + C(year) + C(state_fips)", "tech_emp_share", "state_fips", "C6 excl. PETRO_NG + winsorized")

matched_county = county_usable.dropna(subset=["tech_lag", "tech_lead"])
print(f"Matched lag/lead sample (county): n={len(matched_county)}")
run(matched_county, "d_log_emissions ~ tech_lag + C(year) + C(state_fips)", "tech_lag", "state_fips", "C3 REAL: lagged tech share")
run(matched_county, "d_log_emissions ~ tech_lead + C(year) + C(state_fips)", "tech_lead", "state_fips", "C4 PLACEBO: lead tech share")

# n_facilities >= 2 robustness (kept from round 1 -- review confirmed this
# specific cut barely moves the coefficient; winsorization is what matters).
county_multi = county_usable[county_usable["n_facilities"] >= 2].copy()
run(county_multi, "d_log_emissions ~ tech_emp_share + C(year) + C(state_fips)", "tech_emp_share", "state_fips", "C1b n_facilities>=2")

# Leave-one-state-out for the county panel's headline spec.
print("\n--- Leave-one-state-out (C1 spec, t(G-1) only) ---")
loo_rows_c = []
for drop_state in sorted(county_usable["state_fips"].unique()):
    sub = county_usable[county_usable["state_fips"] != drop_state]
    if sub["state_fips"].nunique() < 6:
        continue
    row = fit_report(sub, "d_log_emissions ~ tech_emp_share + C(year) + C(state_fips)", "tech_emp_share", "state_fips",
                      f"C1 drop {drop_state}", 0, n_boot=0, verbose=False)
    row["dropped_state_fips"] = drop_state
    loo_rows_c.append(row)
loo_df_c = pd.DataFrame(loo_rows_c)
loo_df_c.to_csv(OUT / "us_county_leave_one_out.csv", index=False)
print(f"LOO coef range: [{loo_df_c['coef'].min():+.4f}, {loo_df_c['coef'].max():+.4f}], "
      f"sign flips: {(np.sign(loo_df_c['coef']) != np.sign(loo_df_c['coef'].iloc[0])).sum()}, "
      f"min p_t: {loo_df_c['p_t_Gminus1'].min():.4f} (dropping {loo_df_c.loc[loo_df_c['p_t_Gminus1'].idxmin(), 'dropped_state_fips']})")

# ---------------------------------------------------------------------------
# 5. Minimum detectable effect (S4 in review) -- state headline spec.
#    MDE at 80% power, two-sided alpha=0.05: se * (t_{0.975,G-1} + t_{0.80,G-1})
# ---------------------------------------------------------------------------
s1_row = [r for r in results if r["model"] == "S1 bare (+ year FE)"][0]
G = s1_row["G_clusters"]
se = s1_row["se_cluster"]
mde = se * (stats.t.ppf(0.975, G - 1) + stats.t.ppf(0.80, G - 1))
sd_tech = state_usable["tech_emp_share"].std()
mean_decline = -state_usable["d_log_emissions"].mean()
print(f"\n--- MDE (state S1 spec) ---")
print(f"SD(tech_emp_share) = {sd_tech:.4f}; 1-SD effect on d_log_emissions = {s1_row['coef']*sd_tech:+.4f} "
      f"(95% CI [{s1_row['ci_lo']*sd_tech:+.4f}, {s1_row['ci_hi']*sd_tech:+.4f}])")
print(f"MDE at 80% power (coefficient units) = {mde:.4f}; as a 1-SD effect = {mde*sd_tech:.4f}")
print(f"Sample mean decline rate = {mean_decline:.4f} (i.e. {mean_decline*100:.2f} pp/yr)")
print(f"MDE as share of mean decline rate = {(mde*sd_tech)/mean_decline:.1%}")

# ---------------------------------------------------------------------------
# 6. Save results table
# ---------------------------------------------------------------------------
results_df = pd.DataFrame(results)
results_df.to_csv(OUT / "us_regression_results.csv", index=False)
print(f"\nSaved {len(results_df)} model rows to {OUT / 'us_regression_results.csv'}")

desc = pd.DataFrame({
    "panel": ["state-year", "county-year"],
    "n_usable": [len(state_usable), len(county_usable)],
    "n_units": [state_usable["state_fips"].nunique(), county_usable["county_fips"].nunique()],
    "year_min": [state_usable["year"].min() if len(state_usable) else None, county_usable["year"].min() if len(county_usable) else None],
    "year_max": [state_usable["year"].max() if len(state_usable) else None, county_usable["year"].max() if len(county_usable) else None],
})
desc.to_csv(OUT / "us_panel_descriptives.csv", index=False)
print(desc)
