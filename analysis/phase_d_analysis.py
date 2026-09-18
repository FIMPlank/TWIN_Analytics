"""
Phase D: two refinements that don't require EIBIS firm microdata.

Item 1 (priority): an EU Cohesion Policy digital-investment (ICT, Thematic
  Objective 02) event-study / DiD -- the first attempt at anything beyond
  purely observational regression in this project. Funding disbursement
  timing is administratively/politically driven, not (in principle) set by
  a region's own emissions trajectory -- a plausible-not-certain
  quasi-experimental source of variation, treated with appropriate caution
  throughout (see analysis/phase_d_analysis.md for the exogeneity
  discussion).

Item 2: energy intensity (industrial energy consumption / industrial
  value-added) as a more proximate outcome than emissions change or
  emissions/VA intensity -- digitalization -> energy use is one fewer
  causal step removed than digitalization -> emissions.

Same standard as every prior phase: small-cluster-robust inference (naive
z, t(G-1), wild cluster bootstrap) from the start, never a naive p-value
alone; leave-one-out / confound checks where the design allows; explicit,
hedged interpretation.

Usage:
    python analysis/phase_d_analysis.py
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
BASE_SEED = 20260301
N_BOOT = 1999

# ---------------------------------------------------------------------------
# Small-cluster-robust OLS machinery (same as phase_b/c_analysis.py)
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
    else:
        _, _, _, p_wild, _ = wild_cluster_bootstrap_p(y, Xm, groups, col_idx, n_boot, BASE_SEED + seed_offset)
    row = {
        "model": model_id, "target": target_col, "n": n, "G_clusters": G,
        "coef": beta, "se_cluster": se, "t_stat": t_obs,
        "p_naive_z": p_z, "p_t_Gminus1": p_t, "p_wild_bootstrap": p_wild,
    }
    pw_str = f"{p_wild:.4f}" if not np.isnan(p_wild) else "n/a"
    print(f"{model_id:60s} target={target_col:20s} n={n:4d} G={G:3d} "
          f"coef={beta:+.4f}  p(z)={p_z:.4f}  p(t)={p_t:.4f}  p(wild)={pw_str}")
    return row


all_results = []
_seed_counter = [0]


def run(df, formula, target_col, cluster_col, model_id, tag):
    _seed_counter[0] += 1
    row = fit_report(df, formula, target_col, cluster_col, model_id, _seed_counter[0])
    row["item"] = tag
    all_results.append(row)
    return row


# ---------------------------------------------------------------------------
# 0. EU-ETS country total verified emissions, full history (2005-2025) --
#    same "20-99" construction used throughout this project.
# ---------------------------------------------------------------------------
eu = pd.read_csv(RAW / "eu_ets" / "eu-ets.csv")
eu = eu[eu["year"].str.fullmatch(r"\d{4}")].copy()
eu["year"] = eu["year"].astype(int)
ets_total = eu[(eu["main_activity_code"] == "20-99") & (eu["citl_information"] == "2. Verified emissions")].copy()
ets_total = ets_total.rename(columns={"value": "verified_emissions_t"})[["country_code", "year", "verified_emissions_t"]]
non_country = {"Innovation fund", "Modernisation Fund", "NER 300 auctions", "RRF"}
ets_total = ets_total[~ets_total["country_code"].isin(non_country)]
ets_total["country_code"] = ets_total["country_code"].replace({"GR": "EL", "GB": "UK"})
ets_total = ets_total.sort_values(["country_code", "year"])
ets_total["log_emissions"] = np.log(ets_total["verified_emissions_t"].clip(lower=1))
ets_total["d_log_emissions"] = ets_total.groupby("country_code")["log_emissions"].diff()

# ===========================================================================
# ITEM 1: EU Cohesion digital-funding event study / DiD
# ===========================================================================
print("=" * 90)
print("ITEM 1: EU Cohesion Policy digital-investment (TO2/ICT) event study")
print("=" * 90)

funding = pd.read_csv(RAW / "cohesion" / "digital_investment_2014_2020.csv")
funding["year"] = funding["year"].astype(int)
funding["country_code"] = funding["ms"].replace({"GR": "EL"})
# sum across programmes within country-year (safe: dimension_type is fixed
# to "Thematic Objective", a single non-overlapping cut per programme -- see
# scripts/download_cohesion_digital_funding.py docstring)
funding_cy = funding.groupby(["country_code", "year"], as_index=False)["eu_elig_expenditure_declared_fin_data_notional"].sum()
funding_cy = funding_cy.rename(columns={"eu_elig_expenditure_declared_fin_data_notional": "cum_digital_expenditure"})
funding_cy = funding_cy.sort_values(["country_code", "year"])

print(f"Countries with any recorded TO2 (digital/ICT) expenditure: {sorted(funding_cy['country_code'].unique())}")
print(f"Years: {sorted(funding_cy['year'].unique())}")

# annual disbursement flow (year-over-year first difference of the
# cumulative declared-expenditure figure -- confirmed monotonic non-decreasing
# for 20/21 countries, see download script docstring)
funding_cy["flow"] = funding_cy.groupby("country_code")["cum_digital_expenditure"].diff()
first_year_mask = funding_cy.groupby("country_code").cumcount() == 0
funding_cy.loc[first_year_mask, "flow"] = funding_cy.loc[first_year_mask, "cum_digital_expenditure"]

# Countries with essentially zero funding throughout (DE, IE) -- excluded,
# there is no "event" to study for them.
final_cum = funding_cy.groupby("country_code")["cum_digital_expenditure"].transform("max")
always_zero = funding_cy.groupby("country_code")["cum_digital_expenditure"].max()
always_zero_countries = always_zero[always_zero < 1].index.tolist()
print(f"Countries with ~zero recorded TO2 expenditure throughout (excluded): {always_zero_countries}")
funding_cy = funding_cy[~funding_cy["country_code"].isin(always_zero_countries)]

# ---------------------------------------------------------------------------
# Event-timing definition: for each country, the "onset year" is the first
# year (within the observed 2016-2023 window) in which CUMULATIVE digital
# expenditure reaches at least 50% of that country's eventual (2023)
# cumulative total -- i.e. "the year disbursement crossed its own halfway
# point". This was chosen over two alternatives that were checked and
# rejected:
#   - "first nonzero year": ~10 of 21 countries already have nonzero
#     cumulative expenditure in 2016 (the first observed year), which is
#     LEFT-CENSORED (the 2014-2020 programme technically starts in 2014;
#     true onset for these countries is unknown, <=2016) and would give no
#     observable pre-period for half the sample.
#   - "peak annual disbursement-flow year": checked and rejected -- 9 of 21
#     countries peak in 2023, the LAST observed year, which is a mechanical
#     artifact of most countries' spending still accelerating at the end of
#     the data window (and, more importantly, of end-of-programming-period
#     "N+3" spending-deadline closeout dynamics), not a meaningful "big push"
#     date.
# The halfway-point definition still leaves left-censored countries with no
# usable pre-period (their halfway point is reached immediately); these are
# identified and handled explicitly below, not silently included.
# ---------------------------------------------------------------------------
onset_rows = []
for c, g in funding_cy.groupby("country_code"):
    g = g.sort_values("year")
    final = g["cum_digital_expenditure"].iloc[-1]
    if final <= 0:
        continue
    frac = g["cum_digital_expenditure"] / final
    over = g[frac >= 0.5]
    onset_year = int(over["year"].min()) if len(over) else np.nan
    left_censored = g["cum_digital_expenditure"].iloc[0] > 0  # already spending in first observed year
    onset_rows.append({"country_code": c, "onset_year": onset_year, "left_censored_2016": left_censored,
                        "final_cum_expenditure_eur": final})
onset_df = pd.DataFrame(onset_rows).sort_values("onset_year")
print("\nOnset-year distribution (first year cumulative digital expenditure crosses 50% of its 2023 total):")
print(onset_df.to_string(index=False))
onset_df.to_csv(OUT / "phase_d_item1_onset_years.csv", index=False)

# ---------------------------------------------------------------------------
# Confound check: do "early onset" and "late onset" countries already differ
# systematically in their PRE-FUNDING emissions trend? If funding timing is
# truly administratively/politically driven rather than targeted at
# countries already on a particular trajectory, pre-onset trends should look
# similar across onset-timing groups. This is the project's version of a
# pre-trends / exogeneity sanity check for the design.
# ---------------------------------------------------------------------------
print("\n--- Confound check: pre-onset (2010 to onset_year-1) average d_log_emissions, "
      "early vs. late onset countries ---")
median_onset = onset_df["onset_year"].median()
onset_df["onset_group"] = np.where(onset_df["onset_year"] <= median_onset, "early", "late")
pretrend_rows = []
for _, row in onset_df.dropna(subset=["onset_year"]).iterrows():
    c, oy = row["country_code"], int(row["onset_year"])
    pre = ets_total[(ets_total["country_code"] == c) & (ets_total["year"] >= 2010) & (ets_total["year"] < oy)]
    pretrend_rows.append({"country_code": c, "onset_year": oy, "onset_group": row["onset_group"],
                           "mean_pre_onset_d_log_emissions": pre["d_log_emissions"].mean(), "n_pre_years": len(pre)})
pretrend_df = pd.DataFrame(pretrend_rows)
print(pretrend_df.groupby("onset_group")["mean_pre_onset_d_log_emissions"].agg(["mean", "std", "count"]))
pretrend_df.to_csv(OUT / "phase_d_item1_pretrend_check.csv", index=False)
t_pre, p_pre = stats.ttest_ind(
    pretrend_df.loc[pretrend_df["onset_group"] == "early", "mean_pre_onset_d_log_emissions"].dropna(),
    pretrend_df.loc[pretrend_df["onset_group"] == "late", "mean_pre_onset_d_log_emissions"].dropna(),
    equal_var=False,
)
print(f"Two-sample t-test, early vs. late onset pre-trend means: t={t_pre:.3f}, p={p_pre:.3f}")

# ---------------------------------------------------------------------------
# Event-study panel: merge onset year onto the FULL EU-ETS history
# (2005-2025 -- not limited to the 2016-2023 funding-data window, since the
# OUTCOME has much longer history and leads/lags can extend beyond it).
# ---------------------------------------------------------------------------
event_panel = ets_total.merge(onset_df[["country_code", "onset_year", "left_censored_2016"]],
                               on="country_code", how="inner")
event_panel = event_panel.dropna(subset=["onset_year", "d_log_emissions"])
event_panel["event_time"] = event_panel["year"] - event_panel["onset_year"]

# window: -5 to +3 (post-window limited by how recently most countries'
# onset years fall -- 2023 for the latest, giving only +1/+2 of outcome data)
WINDOW = range(-5, 4)
event_panel_w = event_panel[event_panel["event_time"].isin(WINDOW)].copy()
print(f"\nEvent-study panel: n={len(event_panel_w)}, {event_panel_w['country_code'].nunique()} countries, "
      f"event_time range used: {sorted(event_panel_w['event_time'].unique())}")
print("Observations per event_time:")
print(event_panel_w["event_time"].value_counts().sort_index())

# leave out left-censored countries for the LEAD (pre-period) coefficients'
# credibility -- they have no genuine pre-onset data, though they still
# contribute post-period observations. Flagged, not silently included as
# equally informative.
print(f"\nLeft-censored-in-2016 countries (no genuine pre-onset period observed): "
      f"{sorted(onset_df.loc[onset_df['left_censored_2016'], 'country_code'])}")

event_panel_w["event_time_int"] = event_panel_w["event_time"].astype(int)
event_panel_w["et_cat"] = pd.Categorical(event_panel_w["event_time_int"])

# NOTE on calendar-year effects: with staggered onset (2018-2023) but only
# 18 countries observed in a FIXED, balanced -5..+3 event window, including
# full C(country_code) + C(year) + C(event_time) dummies together is exactly
# collinear (several calendar years in the resulting ~2013-2026 span are
# only ever visited by one or two countries in this restricted 9-row-per-
# country subsample, so the year dummy for that year cannot be told apart
# from that country's own dummy plus the event-time dummy it pairs with --
# a `numpy.linalg.LinAlgError: Singular matrix`, confirmed by first trying
# the naive 3-way-FE spec and having it fail exactly this way).
#
# Fix: absorb calendar-year (EU-wide) shocks OUTSIDE the restricted event
# window, using the FULL EU-ETS panel (all ~30 countries, 2005-2025) to
# compute each calendar year's average d_log_emissions, then work with the
# year-demeaned outcome inside the event-time regression (country FE +
# event-time dummies only, no separate C(year)). NOTE (per
# phase_d_review.md issue 6): this is an EXTERNAL year-mean subtraction,
# NOT a Frisch-Waugh-Lovell partialling-out -- FWL partials out effects
# estimated WITHIN the estimation sample, with an orthogonality guarantee
# by construction; this estimates year means from a different, larger
# sample (the full ~30-country panel, which includes 11 countries absent
# from the event study), so the year adjustment is not guaranteed
# orthogonal to the event-study residuals, and the year means are
# generated regressors whose own estimation uncertainty is not propagated
# into the reported standard errors (second-order here, with ~30
# countries contributing to each year's mean, but not exactly zero).
year_avg_full = ets_total.groupby("year")["d_log_emissions"].transform("mean")
ets_total_yr = ets_total.assign(year_avg_d_log_emissions=year_avg_full)
event_panel_w = event_panel_w.merge(
    ets_total_yr[["country_code", "year", "year_avg_d_log_emissions"]], on=["country_code", "year"], how="left"
)
event_panel_w["d_log_emissions_yr_demeaned"] = (
    event_panel_w["d_log_emissions"] - event_panel_w["year_avg_d_log_emissions"]
)

# Full event-study regression: dummy per event-time bucket (reference = -1),
# country FE, on the year-demeaned outcome, clustered by country.
formula_event = (
    "d_log_emissions_yr_demeaned ~ C(et_cat, Treatment(reference=-1)) + C(country_code)"
)
y, X = patsy.dmatrices(formula_event, data=event_panel_w, return_type="dataframe")
groups = event_panel_w["country_code"].to_numpy()
event_coef_rows = []
for col in X.columns:
    if "et_cat" not in col:
        continue
    et_val = int(col.split("T.")[-1].rstrip("]"))
    col_idx = list(X.columns).index(col)
    beta, se, t_obs, G = t_stat(y.to_numpy().ravel(), X.to_numpy(), groups, col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    event_coef_rows.append({"event_time": et_val, "coef": beta, "se": se, "p_naive_z": p_z, "G": G})
event_coef_df = pd.DataFrame(event_coef_rows).sort_values("event_time")
print("\n--- Event-study coefficients (reference: event_time = -1), naive-z SE (see wild-bootstrap "
      "summary DiD below for the headline inference) ---")
print(event_coef_df.to_string(index=False))
event_coef_df.to_csv(OUT / "phase_d_item1_event_study_coefs.csv", index=False)

pre_coefs = event_coef_df[event_coef_df["event_time"] < -1]
print(f"\nPre-trend (lead) coefficients jointly: mean={pre_coefs['coef'].mean():+.4f}, "
      f"max |coef|={pre_coefs['coef'].abs().max():.4f}, "
      f"{(pre_coefs['p_naive_z'] < 0.05).sum()} of {len(pre_coefs)} individually significant at naive p<0.05")

# headline figure
fig, ax = plt.subplots(figsize=(8, 5.5))
ax.axhline(0, color="#999999", linewidth=1, linestyle="--")
ax.axvline(-0.5, color="#c0392b", linewidth=1, linestyle=":")
ax.errorbar(event_coef_df["event_time"], event_coef_df["coef"], yerr=1.96 * event_coef_df["se"],
            fmt="o-", color="#4c72b0", capsize=3)
ax.set_xlabel("Event time (years relative to funding-disbursement onset)")
ax.set_ylabel("Coefficient on d_log_emissions (rel. to event_time = -1)")
ax.set_title("Item 1: event study around digital-funding disbursement onset\n"
              "(naive-z 95% CI shown; dashed red line = treatment onset)")
fig.tight_layout()
fig.savefig(OUT / "phase_d_item1_event_study.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# Summary two-group DiD (the headline number, with full small-cluster
# inference): Post = 1 for event_time >= 0.
# ---------------------------------------------------------------------------
print("\n--- Summary DiD: Post + country FE, on the SAME year-demeaned outcome as the event study "
      "(consistent treatment of calendar-year effects; also avoids the same near-collinearity risk) ---")
event_panel_w["post"] = (event_panel_w["event_time"] >= 0).astype(float)
run(event_panel_w, "d_log_emissions_yr_demeaned ~ post + C(country_code)", "post", "country_code",
    "F1 summary DiD: post-onset indicator, full window [-5,+3]", "item1")

# robustness: excluding left-censored countries entirely (cleaner pre-period)
event_panel_clean = event_panel_w[~event_panel_w["left_censored_2016"]]
if event_panel_clean["country_code"].nunique() >= 6:
    run(event_panel_clean, "d_log_emissions_yr_demeaned ~ post + C(country_code)", "post", "country_code",
        "F2 summary DiD: excluding left-censored-in-2016 countries", "item1")

results_item1 = pd.DataFrame([r for r in all_results if r["item"] == "item1"])
results_item1.to_csv(OUT / "phase_d_item1_results.csv", index=False)

# ===========================================================================
# ITEM 2: energy intensity as outcome
# ===========================================================================
print("\n" + "=" * 90)
print("ITEM 2: energy intensity (industrial energy consumption / industrial value-added)")
print("=" * 90)

energy = pd.read_csv(RAW / "eurostat" / "industrial_energy_consumption.csv")
energy = energy.rename(columns={"geo": "country_code", "time": "year", "value": "energy_ktoe"})[
    ["country_code", "year", "energy_ktoe"]
]
energy["country_code"] = energy["country_code"].replace({"EL": "EL"})  # already EL, no-op, documented for clarity
energy = energy.sort_values(["country_code", "year"])
energy["log_energy"] = np.log(energy["energy_ktoe"].clip(lower=0.01))
energy["d_log_energy"] = energy.groupby("country_code")["log_energy"].diff()

va_abs = pd.read_csv(RAW / "eurostat" / "industry_value_added_absolute.csv")
va_abs = va_abs.rename(columns={"geo": "country_code", "time": "year", "value": "industry_va_meur"})[
    ["country_code", "year", "industry_va_meur"]
]
va_abs = va_abs.sort_values(["country_code", "year"])
va_abs["log_va"] = np.log(va_abs["industry_va_meur"].clip(lower=1))
va_abs["d_log_va"] = va_abs.groupby("country_code")["log_va"].diff()

v2a = pd.read_csv(OUT / "phase_b_working_v2a.csv")
v2a = v2a.merge(energy[["country_code", "year", "energy_ktoe", "d_log_energy"]], on=["country_code", "year"], how="left")
v2a = v2a.merge(va_abs[["country_code", "year", "d_log_va"]], on=["country_code", "year"], how="left")
v2a["d_log_energy_intensity"] = v2a["d_log_energy"] - v2a["d_log_va"]

print(f"v2a rows with a valid energy-intensity outcome and DII: "
      f"{v2a.dropna(subset=['d_log_energy_intensity', 'dii_high_share_manufacturing']).shape[0]}")

usable_energy = v2a.dropna(subset=["d_log_energy_intensity", "dii_high_share_manufacturing"])
run(usable_energy, "d_log_energy_intensity ~ dii_high_share_manufacturing + C(year)",
    "dii_high_share_manufacturing", "country_code", "G1 bare, ENERGY-INTENSITY outcome", "item2")
usable_energy_ctrl = usable_energy.dropna(subset=["d_log_gdp_per_capita", "energy_shock_exposure", "accession_2004plus"])
run(usable_energy_ctrl,
    "d_log_energy_intensity ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "G2 +controls, ENERGY-INTENSITY outcome", "item2")

# raw energy consumption change (not intensity) -- does DII move energy use
# at all, before even normalizing by output?
usable_raw_energy = v2a.dropna(subset=["d_log_energy", "dii_high_share_manufacturing"])
run(usable_raw_energy, "d_log_energy ~ dii_high_share_manufacturing + C(year)",
    "dii_high_share_manufacturing", "country_code", "G3 bare, RAW ENERGY CONSUMPTION change outcome", "item2")
usable_raw_energy_ctrl = usable_raw_energy.dropna(subset=["d_log_gdp_per_capita", "energy_shock_exposure", "accession_2004plus"])
run(usable_raw_energy_ctrl,
    "d_log_energy ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "G4 +controls, RAW ENERGY CONSUMPTION change outcome", "item2")

# for direct comparison: raw emissions and emissions-intensity outcomes on
# the SAME sample as G1/G2 (matching Phase C's side-by-side-on-identical-
# sample discipline)
run(usable_energy, "d_log_emissions ~ dii_high_share_manufacturing + C(year)",
    "dii_high_share_manufacturing", "country_code", "G1r bare, RAW EMISSIONS outcome (same sample as G1)", "item2")
run(usable_energy_ctrl,
    "d_log_emissions ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "G2r +controls, RAW EMISSIONS outcome (same sample as G2)", "item2")

# ---------------------------------------------------------------------------
# G2 is the first wild-bootstrap-significant coefficient in this project.
# Before reporting it, apply the same scrutiny every other marginal/
# significant result in Phases A-D has received:
#   (a) mechanism decomposition -- energy intensity = energy / value-added,
#       so which of the two components is actually moving with DII?
#   (b) leave-one-out across all countries (is this another Bulgaria/Spain
#       single-country artifact?)
#   (c) control decomposition (which single control drives the result?)
# ---------------------------------------------------------------------------
print("\n--- Mechanism decomposition: does DII move value-added, energy, both, or neither? ---")
run(usable_energy_ctrl,
    "d_log_va ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "G5 +controls, VALUE-ADDED growth outcome", "item2")
run(usable_energy_ctrl,
    "d_log_energy ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
    "+ accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "G6 +controls, ENERGY (level, not intensity) outcome", "item2")

# ---------------------------------------------------------------------------
# CORRECTED per phase_d_review.md issue 1: leave-one-out belongs on G5
# (value-added growth), the regression the write-up actually calls the real
# finding -- NOT on G2 (energy intensity), which is a mechanical
# consequence of G5, not the finding itself. Running the robustness check
# on the wrong regression was a bug (the claim happened to be true of G2
# too, but was never actually verified for G5 until now).
# ---------------------------------------------------------------------------
print("\n--- Leave-one-out on G5 (VALUE-ADDED growth, +controls) across all 28 countries "
      "-- the regression that actually carries the finding ---")
loo_rows = []
formula_g5 = ("d_log_va ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita "
              "+ accession_2004plus + energy_shock_exposure")
for c in sorted(usable_energy_ctrl["country_code"].unique()):
    sub = usable_energy_ctrl[usable_energy_ctrl["country_code"] != c]
    y, X = patsy.dmatrices(formula_g5, data=sub, return_type="dataframe")
    col_idx = list(X.columns).index("dii_high_share_manufacturing")
    beta, se, t_obs, G = t_stat(y.to_numpy().ravel(), X.to_numpy(), sub["country_code"].to_numpy(), col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    p_t = 2 * (1 - stats.t.cdf(np.abs(t_obs), df=G - 1))
    loo_rows.append({"dropped_country": c, "n": len(sub), "coef": beta, "p_naive_z": p_z, "p_t_Gminus1": p_t})
loo_df = pd.DataFrame(loo_rows).sort_values("p_naive_z", ascending=False)
print(loo_df.to_string(index=False))
loo_df.to_csv(OUT / "phase_d_item2_leave_one_out.csv", index=False)
print(f"\nMax leave-one-out p-value (G5): {loo_df['p_naive_z'].max():.4f} (dropping {loo_df.iloc[0]['dropped_country']}), "
      f"coefficient range {loo_df['coef'].min():+.4f} to {loo_df['coef'].max():+.4f}")

# confirmatory wild-bootstrap re-estimate on the single worst-case (highest
# naive-z p) leave-one-out sample
worst_country = loo_df.iloc[0]["dropped_country"]
sub_worst = usable_energy_ctrl[usable_energy_ctrl["country_code"] != worst_country]
run(sub_worst, formula_g5, "dii_high_share_manufacturing", "country_code",
    f"G5-LOO-worst-case: drop {worst_country}, wild-bootstrap re-estimate", "item2")

# ---------------------------------------------------------------------------
# PLACEBO / TIMING TEST (per phase_d_review.md issue 2 -- the decisive
# check the first draft did not run): does LAGGED digitalization (t-1,
# pre-determined) predict this year's value-added growth better than LEAD
# (future, t+1) digitalization "predicts" it? If lead performs as well or
# better than lag, that is the signature of reverse causality or a shared
# trend, not of digitalization driving growth. Built on the identical
# matched sample for both (same fix applied to the country-level placebo
# test in Phase B/C: lag and lead must be evaluated on the same rows, not
# each spec's own independently-dropped-NA sample).
# ---------------------------------------------------------------------------
print("\n--- PLACEBO/TIMING TEST: does lead DII predict PAST value-added growth "
      "as well as lag DII predicts FUTURE growth? ---")
dii_lookup = v2a[["country_code", "year", "dii_high_share_manufacturing"]].dropna().drop_duplicates()
lag_lookup = dii_lookup.rename(columns={"dii_high_share_manufacturing": "dii_lag", "year": "year_lag_src"})
lag_lookup["year"] = lag_lookup["year_lag_src"] + 1
lead_lookup = dii_lookup.rename(columns={"dii_high_share_manufacturing": "dii_lead", "year": "year_lead_src"})
lead_lookup["year"] = lead_lookup["year_lead_src"] - 1

# usable_energy_ctrl inherits dii_lag/dii_lead columns from
# phase_b_working_v2a.csv (Phase B's own country-level placebo construction,
# a DIFFERENT lag/lead pairing than the one built here) -- drop them first so
# the merge below doesn't silently rename its own dii_lag/dii_lead into
# dii_lag_x/dii_lag_y and get missed by the dropna() that follows.
placebo_input = usable_energy_ctrl.drop(columns=["dii_lag", "dii_lead"], errors="ignore")
placebo_base = placebo_input.merge(lag_lookup[["country_code", "year", "dii_lag"]], on=["country_code", "year"], how="left")
placebo_base = placebo_base.merge(lead_lookup[["country_code", "year", "dii_lead"]], on=["country_code", "year"], how="left")
placebo_matched = placebo_base.dropna(subset=["dii_lag", "dii_lead"])
print(f"Matched lag/lead sample: n={len(placebo_matched)}, {placebo_matched['country_code'].nunique()} countries")

run(placebo_matched,
    "d_log_va ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita + accession_2004plus + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "H1 CONTEMPORANEOUS DII, matched placebo sample", "item2")
run(placebo_matched,
    "d_log_va ~ dii_lag + C(year) + d_log_gdp_per_capita + accession_2004plus + energy_shock_exposure",
    "dii_lag", "country_code", "H2 REAL: lagged DII (t-1), matched placebo sample", "item2")
run(placebo_matched,
    "d_log_va ~ dii_lead + C(year) + d_log_gdp_per_capita + accession_2004plus + energy_shock_exposure",
    "dii_lead", "country_code", "H3 PLACEBO: lead DII (t+1), matched placebo sample", "item2")

# ---------------------------------------------------------------------------
# ACCESSION-COHORT CONCENTRATION CHECK (per phase_d_review.md issue 3): is
# this the same convergence-economics pattern Phase C found driving the
# v2b sign flip? Split the sample by accession_2004plus and re-estimate G5
# in each subgroup, plus the interaction term.
# ---------------------------------------------------------------------------
print("\n--- Accession-cohort concentration: is the value-added effect a convergence pattern? ---")
eu15 = usable_energy_ctrl[usable_energy_ctrl["accession_2004plus"] == 0]
accession = usable_energy_ctrl[usable_energy_ctrl["accession_2004plus"] == 1]
run(eu15, "d_log_va ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "H4 EU-15 only", "item2")
run(accession, "d_log_va ~ dii_high_share_manufacturing + C(year) + d_log_gdp_per_capita + energy_shock_exposure",
    "dii_high_share_manufacturing", "country_code", "H5 Accession 2004+ only", "item2")
run(usable_energy_ctrl,
    "d_log_va ~ dii_high_share_manufacturing * accession_2004plus + C(year) + d_log_gdp_per_capita + energy_shock_exposure",
    "dii_high_share_manufacturing:accession_2004plus", "country_code", "H6 interaction term (DII x accession)", "item2")

print("\n--- Control decomposition: which single control drives G2's significance? ---")
decomp_rows = []
for label, extra in [
    ("bare", ""), ("+GDP growth only", "+ d_log_gdp_per_capita"),
    ("+energy-shock exposure only", "+ energy_shock_exposure"),
    ("+accession cohort only", "+ accession_2004plus"),
    ("+all three", "+ d_log_gdp_per_capita + accession_2004plus + energy_shock_exposure"),
]:
    f = f"d_log_energy_intensity ~ dii_high_share_manufacturing + C(year) {extra}"
    y, X = patsy.dmatrices(f, data=usable_energy_ctrl, return_type="dataframe")
    col_idx = list(X.columns).index("dii_high_share_manufacturing")
    beta, se, t_obs, G = t_stat(y.to_numpy().ravel(), X.to_numpy(), usable_energy_ctrl["country_code"].to_numpy(), col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    decomp_rows.append({"spec": label, "coef": beta, "p_naive_z": p_z, "n": len(usable_energy_ctrl)})
    print(f"{label:30s} coef={beta:+.4f}  p(z)={p_z:.4f}")
decomp_df = pd.DataFrame(decomp_rows)
decomp_df.to_csv(OUT / "phase_d_item2_control_decomposition.csv", index=False)

results_item2 = pd.DataFrame([r for r in all_results if r["item"] == "item2"])
results_item2.to_csv(OUT / "phase_d_item2_results.csv", index=False)

print(f"\nAll Phase D outputs written to {OUT}")
