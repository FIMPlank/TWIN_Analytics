"""
Extension analysis: covariates, broader EIBIS indicators, and a
block-permutation robustness check, building on
analysis/first_pass_analysis.md and analysis/analysis.py.

Self-contained: rebuilds the EU-ETS x EIBIS panel from data/raw/ directly
(same logic as analysis.py) rather than depending on analysis.py's output
files being fresh, then adds:

  1. Eurostat country-year covariates (GDP per capita, industry
     value-added share, industrial electricity price) as controls on the
     headline models.
  2. Two additional EIBIS climate/energy-investment indicators (added to
     scripts/download_eibis_aggregate.py and re-fetched) as alternative
     predictors alongside digital_multi.
  3. A block-permutation test (permuting whole country series of
     digital_multi across countries) as a small-sample-appropriate
     alternative to asymptotic cluster-robust inference.
  4. A confirmation note on the EIBIS pre-2023 coverage gap (checked
     directly against the EIB API, not just the already-fetched CSV --
     see analysis/extension_analysis.md for the one-sentence result).

Run `python analysis/analysis.py` first if you want the first-pass output
files refreshed too; this script does not depend on them, only on
data/raw/.

Usage:
    python analysis/extension_analysis.py
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "analysis" / "output"
OUT.mkdir(parents=True, exist_ok=True)

pd.set_option("display.width", 140)
RNG = np.random.default_rng(20250916)

# ---------------------------------------------------------------------------
# 0. Rebuild the base EU-ETS x EIBIS panel (same logic as analysis.py)
# ---------------------------------------------------------------------------
eu = pd.read_csv(RAW / "eu_ets" / "eu-ets.csv")
eu = eu[eu["year"].str.fullmatch(r"\d{4}")].copy()
eu["year"] = eu["year"].astype(int)
ets = eu[
    (eu["main_activity_code"] == "20-99")
    & (eu["citl_information"] == "2. Verified emissions")
].copy()
ets = ets.rename(columns={"value": "verified_emissions_t"})[
    ["country_code", "year", "verified_emissions_t"]
]
non_country = {"Innovation fund", "Modernisation Fund", "NER 300 auctions", "RRF"}
ets = ets[~ets["country_code"].isin(non_country)]
ets["country_code"] = ets["country_code"].replace({"GR": "EL"})
ets = ets.sort_values(["country_code", "year"])
ets["log_emissions"] = np.log(ets["verified_emissions_t"].clip(lower=1))
ets["d_log_emissions"] = ets.groupby("country_code")["log_emissions"].diff()

eib = pd.read_csv(RAW / "eibis" / "eibis_aggregate.csv")
eib = eib[~eib["country"].isin(["EU", "US"])]
eib_all = eib[(eib["sector"] == "ALL") & (eib["size"] == "ALL")].copy()

specs = [
    ("Implementation of digital technologies", "Multiple technologies", "digital_multi"),
    ("Implementation of digital technologies", "Single technology", "digital_single"),
    ("Share of firms using generative AI tools", "Share of firms using generative AI tools", "genai_share"),
    ("Climate change targets for own GHG emissions", "Climate change targets for own GHG emissions", "climate_target_share"),
    # New for this extension (see scripts/download_eibis_aggregate.py):
    ("Proportion of investment directed towards measures to improve energy efficiency",
     "Proportion of investment directed towards measures to improve energy efficiency",
     "energy_efficiency_invest_share"),
    ("Share of firms investing in measures to improve energy efficiency",
     "Share of firms investing in measures to improve energy efficiency",
     "energy_efficiency_firms_share"),
]
wide = {}
for indicator, col, newname in specs:
    sub = eib_all[eib_all["indicator"] == indicator][["country", "survey_wave", col]].dropna()
    sub = sub.rename(columns={"survey_wave": "year", col: newname})
    wide[newname] = sub

eibis_panel = wide["digital_multi"][["country", "year", "digital_multi"]]
for name, df in wide.items():
    if name == "digital_multi":
        continue
    eibis_panel = eibis_panel.merge(df[["country", "year", name]], on=["country", "year"], how="outer")
eibis_panel = eibis_panel.rename(columns={"country": "country_code"})

panel = ets.merge(eibis_panel, on=["country_code", "year"], how="inner")
panel = panel.dropna(subset=["d_log_emissions", "digital_multi"])

print("=== Base panel (rebuilt) ===")
print(f"rows: {len(panel)}, countries: {panel['country_code'].nunique()}, "
      f"years: {sorted(panel['year'].unique())}")

# ---------------------------------------------------------------------------
# 1. Eurostat covariates: GDP per capita, industry value-added share,
#    industrial electricity price
# ---------------------------------------------------------------------------
gdp = pd.read_csv(RAW / "eurostat" / "gdp_per_capita.csv")
gdp = gdp.rename(columns={"geo": "country_code", "time": "year", "value": "gdp_per_capita"})
gdp = gdp[["country_code", "year", "gdp_per_capita"]]

ind = pd.read_csv(RAW / "eurostat" / "industry_value_added_share.csv")
ind = ind.rename(columns={"geo": "country_code", "time": "year", "value": "industry_va_share"})
ind = ind[["country_code", "year", "industry_va_share"]]

elec = pd.read_csv(RAW / "eurostat" / "industrial_electricity_price.csv")
# semi-annual (YYYY-S1 / YYYY-S2) -> annual average
elec["year"] = elec["time"].str.split("-").str[0].astype(int)
elec = elec.groupby(["geo", "year"], as_index=False)["value"].mean()
elec = elec.rename(columns={"geo": "country_code", "value": "electricity_price"})

print(f"\nEurostat coverage: GDP {gdp['country_code'].nunique()} geos, "
      f"industry share {ind['country_code'].nunique()} geos, "
      f"electricity price {elec['country_code'].nunique()} geos")

panel_x = panel.merge(gdp, on=["country_code", "year"], how="left")
panel_x = panel_x.merge(ind, on=["country_code", "year"], how="left")
panel_x = panel_x.merge(elec, on=["country_code", "year"], how="left")
panel_x["log_gdp_per_capita"] = np.log(panel_x["gdp_per_capita"])

missing_covariates = panel_x[
    panel_x[["gdp_per_capita", "industry_va_share", "electricity_price"]].isna().any(axis=1)
][["country_code", "year"]]
print(f"\nRows missing >=1 Eurostat covariate after merge: {len(missing_covariates)} of {len(panel_x)}")
if len(missing_covariates):
    print(missing_covariates.to_string(index=False))

panel_x.to_csv(OUT / "extension_panel_with_covariates.csv", index=False)

# ---------------------------------------------------------------------------
# 1b. Re-run headline models with GDP / industry-structure / energy-price
#     controls added, to test whether digital_multi was proxying for "rich"
#     or "less industrial"
# ---------------------------------------------------------------------------
panel_ctrl = panel_x.dropna(
    subset=["digital_multi", "d_log_emissions", "log_gdp_per_capita",
            "industry_va_share", "electricity_price"]
)
print(f"\n=== Controlled-model estimation sample: n={len(panel_ctrl)}, "
      f"countries={panel_ctrl['country_code'].nunique()} ===")

results_log = []

def run_and_log(name, model):
    print(f"\n--- {name} ---")
    print(model.summary())
    results_log.append((name, model.summary().as_text()))
    return model

m1b_bare = run_and_log(
    "Model 1b (bare, for comparison -- same spec as first_pass_analysis.md Model 1b): "
    "d_log_emissions ~ digital_multi, country-clustered SE, same estimation sample as controlled models",
    smf.ols("d_log_emissions ~ digital_multi", data=panel_ctrl).fit(
        cov_type="cluster", cov_kwds={"groups": panel_ctrl["country_code"]}
    ),
)

m1b_ctrl = run_and_log(
    "Model 1c: d_log_emissions ~ digital_multi + log_gdp_per_capita + industry_va_share "
    "+ electricity_price, country-clustered SE",
    smf.ols(
        "d_log_emissions ~ digital_multi + log_gdp_per_capita + industry_va_share + electricity_price",
        data=panel_ctrl,
    ).fit(cov_type="cluster", cov_kwds={"groups": panel_ctrl["country_code"]}),
)

m3_bare = run_and_log(
    "Model 3 (bare, for comparison): d_log_emissions ~ digital_multi + C(year), "
    "country-clustered SE, same estimation sample as controlled models",
    smf.ols("d_log_emissions ~ digital_multi + C(year)", data=panel_ctrl).fit(
        cov_type="cluster", cov_kwds={"groups": panel_ctrl["country_code"]}
    ),
)

m3_ctrl = run_and_log(
    "Model 3c: d_log_emissions ~ digital_multi + C(year) + log_gdp_per_capita "
    "+ industry_va_share + electricity_price, country-clustered SE",
    smf.ols(
        "d_log_emissions ~ digital_multi + C(year) + log_gdp_per_capita + industry_va_share + electricity_price",
        data=panel_ctrl,
    ).fit(cov_type="cluster", cov_kwds={"groups": panel_ctrl["country_code"]}),
)

ctrl_summary = pd.DataFrame([
    {"model": "1b bare (n={})".format(len(panel_ctrl)), "coef": m1b_bare.params["digital_multi"],
     "se": m1b_bare.bse["digital_multi"], "p": m1b_bare.pvalues["digital_multi"], "r2": m1b_bare.rsquared},
    {"model": "1c + GDP/industry/energy controls (LEVELS -- see caveat below)", "coef": m1b_ctrl.params["digital_multi"],
     "se": m1b_ctrl.bse["digital_multi"], "p": m1b_ctrl.pvalues["digital_multi"], "r2": m1b_ctrl.rsquared},
    {"model": "3 bare, year FE (n={})".format(len(panel_ctrl)), "coef": m3_bare.params["digital_multi"],
     "se": m3_bare.bse["digital_multi"], "p": m3_bare.pvalues["digital_multi"], "r2": m3_bare.rsquared},
    {"model": "3c + year FE + controls (LEVELS -- see caveat below)", "coef": m3_ctrl.params["digital_multi"],
     "se": m3_ctrl.bse["digital_multi"], "p": m3_ctrl.pvalues["digital_multi"], "r2": m3_ctrl.rsquared},
])
print("\n=== Summary: does digital_multi survive GDP/industry/energy-price controls? (LEVELS spec, n=74) ===")
print(ctrl_summary.to_string(index=False))
print(
    "\nCAVEAT (see section 1c below): the outcome d_log_emissions is a CHANGE, "
    "but these controls enter as contemporaneous LEVELS -- a specification "
    "mismatch that turns out to drive the whole result. Do not read the p=0.0006 "
    "/ p=0.0008 above as reliable; see the levels-vs-changes-vs-lagged comparison "
    "and corrected small-cluster inference immediately below before drawing any "
    "conclusion."
)
ctrl_summary.to_csv(OUT / "extension_covariate_models.csv", index=False)

# ---------------------------------------------------------------------------
# 1c. Levels vs. changes vs. lagged controls, on an IDENTICAL fixed sample
#     ------------------------------------------------------------------
#     The levels specification above conditions on contemporaneous
#     industry-value-added share and electricity price -- both of which
#     plausibly respond to the SAME shocks that move emissions in the same
#     year (a bad-controls problem: when industrial output contracts,
#     industry's value-added share falls AND emissions fall together). The
#     outcome itself is a first difference (d_log_emissions); controls that
#     are not are not a like-for-like comparison. This section re-estimates
#     with (a) controls as year-over-year CHANGES, matching the outcome, and
#     (b) controls LAGGED one year (t-1, pre-determined before the emissions
#     change being explained) -- and holds the ESTIMATION SAMPLE FIXED across
#     all four specs (bare / levels / changes / lagged) so differences in the
#     coefficient/p-value reflect the specification choice alone, not sample
#     composition.
#
#     Building the lag/change controls requires each country-year's PRIOR
#     year's covariate values. Because EIBIS digitalization coverage starts
#     in 2023 (see item 4), 2023's own lag falls in 2022 -- a year with
#     visibly thinner electricity-price coverage (34 vs ~40+ geos; see
#     scripts/download_eurostat.py). Rather than mix "some countries have a
#     2022 baseline, some don't" into the comparison, the fixed sample below
#     is restricted to 2024-2025 (dropping 2023 uniformly from ALL FOUR
#     specs), so every spec is fit on the exact same balanced 2-year x
#     25-country panel.
# ---------------------------------------------------------------------------
print("\n=== 1c. Levels vs. changes vs. lagged controls (identical fixed sample) ===")

gdp_by_y = gdp.set_index(["country_code", "year"])["gdp_per_capita"]
ind_by_y = ind.set_index(["country_code", "year"])["industry_va_share"]
elec_by_y = elec.set_index(["country_code", "year"])["electricity_price"]

base_ce = panel[["country_code", "year", "d_log_emissions", "digital_multi"]].dropna().copy()
base_ce["log_gdp_per_capita"] = base_ce.apply(
    lambda r: np.log(gdp_by_y.get((r["country_code"], r["year"]), np.nan)), axis=1)
base_ce["industry_va_share"] = base_ce.apply(
    lambda r: ind_by_y.get((r["country_code"], r["year"]), np.nan), axis=1)
base_ce["electricity_price"] = base_ce.apply(
    lambda r: elec_by_y.get((r["country_code"], r["year"]), np.nan), axis=1)
base_ce["log_gdp_per_capita_lag"] = base_ce.apply(
    lambda r: np.log(gdp_by_y.get((r["country_code"], r["year"] - 1), np.nan)), axis=1)
base_ce["industry_va_share_lag"] = base_ce.apply(
    lambda r: ind_by_y.get((r["country_code"], r["year"] - 1), np.nan), axis=1)
base_ce["electricity_price_lag"] = base_ce.apply(
    lambda r: elec_by_y.get((r["country_code"], r["year"] - 1), np.nan), axis=1)
base_ce["d_log_gdp"] = base_ce["log_gdp_per_capita"] - base_ce["log_gdp_per_capita_lag"]
base_ce["d_industry_va_share"] = base_ce["industry_va_share"] - base_ce["industry_va_share_lag"]
base_ce["d_electricity_price"] = base_ce["electricity_price"] - base_ce["electricity_price_lag"]

need_all = ["log_gdp_per_capita", "industry_va_share", "electricity_price",
            "log_gdp_per_capita_lag", "industry_va_share_lag", "electricity_price_lag",
            "d_log_gdp", "d_industry_va_share", "d_electricity_price"]
fixed = base_ce.dropna(subset=["digital_multi", "d_log_emissions"] + need_all).copy()
fixed_24_25 = fixed[fixed["year"].isin([2024, 2025])].reset_index(drop=True)
fixed_24_25.to_csv(OUT / "extension_levels_changes_lagged_sample.csv", index=False)
print(f"Fixed comparison sample: n={len(fixed_24_25)}, "
      f"countries={fixed_24_25['country_code'].nunique()}, years={sorted(fixed_24_25['year'].unique())}")

SPEC_FORMULAS = {
    "bare": "d_log_emissions ~ digital_multi",
    "levels": "d_log_emissions ~ digital_multi + log_gdp_per_capita + industry_va_share + electricity_price",
    "changes": "d_log_emissions ~ digital_multi + d_log_gdp + d_industry_va_share + d_electricity_price",
    "lagged": "d_log_emissions ~ digital_multi + log_gdp_per_capita_lag + industry_va_share_lag + electricity_price_lag",
}

spec_rows = []
spec_models = {}
for label, formula in SPEC_FORMULAS.items():
    m = smf.ols(formula, data=fixed_24_25).fit(
        cov_type="cluster", cov_kwds={"groups": fixed_24_25["country_code"]}
    )
    spec_models[label] = m
    spec_rows.append({
        "spec": label, "n": len(fixed_24_25), "coef": m.params["digital_multi"],
        "se": m.bse["digital_multi"], "p_asymptotic_z": m.pvalues["digital_multi"], "r2": m.rsquared,
    })
    print(f"{label:10s} n={len(fixed_24_25):3d}  coef={m.params['digital_multi']:+.4f}  "
          f"p(asymptotic z)={m.pvalues['digital_multi']:.4f}")
spec_df = pd.DataFrame(spec_rows)
spec_df.to_csv(OUT / "extension_levels_vs_changes_vs_lagged.csv", index=False)

print(
    "\nInterpretation: the ENTIRE apparent significance of the levels spec is a "
    "consequence of measuring the controls in levels against a differenced "
    "outcome. Slow-moving level controls on a first-differenced outcome behave "
    "like partial country fixed effects -- they absorb cross-country trend-level "
    "variation and change what identifies digital_multi, which is why the "
    "coefficient grows rather than shrinks. That is a mechanical artifact of the "
    "specification, not evidence the association survived a confound. Controls "
    "as changes (matching the outcome's own differencing) make the result "
    "indistinguishable from noise; lagged (pre-determined, before the emissions "
    "change occurs) is the defensible middle ground, since it avoids "
    "conditioning on a contemporaneous consequence of the same shock that moves "
    "emissions (industrial output contracts -> industry value-added share AND "
    "electricity demand AND emissions all move together in the same year -- a "
    "textbook bad-control problem for the levels spec)."
)

# ---------------------------------------------------------------------------
# 1d. Small-cluster-corrected inference on the LAGGED spec (the chosen
#     defensible primary) and the LEVELS spec (for contrast), pooled and with
#     year FE. statsmodels' cov_type="cluster" reports a z-based p-value with
#     no small-cluster correction; with ~25 clusters that is anticonservative.
#     Two corrections: (a) a t(G-1) reference distribution instead of z on the
#     same cluster-robust SE, and (b) a wild cluster bootstrap (restricted
#     null, Rademacher weights), which is the standard small-G-appropriate
#     method (Cameron, Gelbach & Miller 2008) and makes no distributional
#     assumption beyond exchangeability of cluster-level shocks under the null.
# ---------------------------------------------------------------------------
print("\n=== 1d. Small-cluster-corrected inference (t(G-1) and wild cluster bootstrap) ===")


def build_xy(df, y_col, x_cols):
    y = df[y_col].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(df))] + [df[c].to_numpy(dtype=float) for c in x_cols])
    return y, X


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


def wild_cluster_bootstrap_p(y, X, groups, col_idx, n_boot, rng):
    """Restricted (null-imposed) wild cluster bootstrap, Rademacher weights."""
    beta_obs, se_obs, t_obs, G = t_stat(y, X, groups, col_idx)
    X_r = np.delete(X, col_idx, axis=1)
    beta_r, resid_r = ols_fit(y, X_r)
    fitted_r = y - resid_r
    uniq = np.unique(groups)
    group_pos = {g: (groups == g) for g in uniq}
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


N_BOOT = 4999
# Fixed, explicit per-spec seeds -- NOT Python's built-in hash(), which is
# randomized per process (PYTHONHASHSEED) unless disabled, and would silently
# change the wild-bootstrap p-value on every re-run without changing anything
# else about the result. Using a plain enumerated offset off a single fixed
# base seed makes every number in this section byte-for-byte reproducible.
WILD_BOOT_BASE_SEED = 12345
inference_rows = []
spec_fe_combos = [
    (spec_label, x_cols, fe_label, extra)
    for spec_label, x_cols in [
        ("levels", ["digital_multi", "log_gdp_per_capita", "industry_va_share", "electricity_price"]),
        ("lagged", ["digital_multi", "log_gdp_per_capita_lag", "industry_va_share_lag", "electricity_price_lag"]),
    ]
    for fe_label, extra in [("pooled", None), ("+year FE", "year")]
]
for combo_idx, (spec_label, x_cols, fe_label, extra) in enumerate(spec_fe_combos):
    df = fixed_24_25.copy()
    x_cols_use = list(x_cols)
    if extra == "year":
        df["year_2025"] = (df["year"] == 2025).astype(float)
        x_cols_use = x_cols_use + ["year_2025"]
    y, X = build_xy(df, "d_log_emissions", x_cols_use)
    groups = df["country_code"].to_numpy()
    col_idx = 1  # digital_multi is always the first regressor after the constant
    beta_obs, se_obs, t_obs, G = t_stat(y, X, groups, col_idx)
    p_z = 2 * (1 - stats.norm.cdf(np.abs(t_obs)))
    p_t = 2 * (1 - stats.t.cdf(np.abs(t_obs), df=G - 1))
    rng_boot = np.random.default_rng(WILD_BOOT_BASE_SEED + combo_idx)
    _, _, _, p_wild, _ = wild_cluster_bootstrap_p(y, X, groups, col_idx, N_BOOT, rng_boot)
    inference_rows.append({
        "spec": f"{spec_label} {fe_label}", "n": len(df), "G_clusters": G,
        "coef": beta_obs, "se_cluster": se_obs, "t_stat": t_obs,
        "p_asymptotic_z": p_z, "p_t_G_minus_1": p_t, "p_wild_bootstrap": p_wild,
    })
    print(f"{spec_label:8s} {fe_label:9s} n={len(df):3d} G={G:2d}  coef={beta_obs:+.4f}  "
          f"p(z)={p_z:.4f}  p(t,G-1)={p_t:.4f}  p(wild boot, {N_BOOT} reps)={p_wild:.4f}")

inference_df = pd.DataFrame(inference_rows)
inference_df.to_csv(OUT / "extension_small_cluster_inference.csv", index=False)
print(
    "\nHeadline correction: statsmodels' default cluster-robust p-value is "
    "z-based and has no small-cluster correction. With ~25 country clusters "
    "this is meaningfully anticonservative. The wild cluster bootstrap "
    "(restricted null, Rademacher weights) is the appropriate small-G method "
    "and is reported as the real p-value above, not the z-based figure."
)

# ---------------------------------------------------------------------------
# 1e. Block-permutation test applied to the controlled specs (levels AND
#     lagged, pooled AND +year FE), for consistency with how every other
#     result in this project is now treated under small-cluster-appropriate
#     inference. Same country-block-shuffle logic as the bare-model
#     permutation test below (digital_multi's whole 2-year country block is
#     reassigned to another country; the controls stay fixed and correctly
#     matched to their own country/year, since only digital_multi's identity
#     is being tested against the null of "no effect beyond the controls").
# ---------------------------------------------------------------------------
print("\n=== 1e. Block-permutation test on the controlled specs ===")

N_PERM_CTRL = 5000
RNG_CTRL = np.random.default_rng(20250917)
countries_ctrl = sorted(fixed_24_25["country_code"].unique())
years_ctrl = sorted(fixed_24_25["year"].unique())
# fixed_24_25 is NOT a fully balanced 25-country x 2-year grid (n=48, not 50),
# so build the country-block shuffle via a keyed lookup/merge rather than a
# pivot-and-flatten, which silently assumes a balanced grid and breaks (or
# worse, silently misaligns) when it isn't one.
digital_lookup = fixed_24_25[["country_code", "year", "digital_multi"]].drop_duplicates()
digital_lookup = digital_lookup.rename(columns={"country_code": "donor_country", "digital_multi": "digital_multi_donor"})

perm_ctrl_rows = []
for spec_label, x_cols in [
    ("levels", ["log_gdp_per_capita", "industry_va_share", "electricity_price"]),
    ("lagged", ["log_gdp_per_capita_lag", "industry_va_share_lag", "electricity_price_lag"]),
]:
    for fe_label, formula_extra in [("pooled", ""), ("+year FE", " + C(year)")]:
        formula = f"d_log_emissions ~ digital_multi + {' + '.join(x_cols)}{formula_extra}"
        observed_coef = smf.ols(formula, data=fixed_24_25).fit().params["digital_multi"]
        perm_coefs = np.empty(N_PERM_CTRL)
        for i in range(N_PERM_CTRL):
            shuffled_cols = RNG_CTRL.permutation(countries_ctrl)
            mapping = dict(zip(countries_ctrl, shuffled_cols))
            df = fixed_24_25.drop(columns=["digital_multi"]).copy()
            df["donor_country"] = df["country_code"].map(mapping)
            df = df.merge(digital_lookup, on=["donor_country", "year"], how="left")
            df = df.rename(columns={"digital_multi_donor": "digital_multi"}).dropna(subset=["digital_multi"])
            perm_coefs[i] = smf.ols(formula, data=df).fit().params["digital_multi"]
        p_perm = float(np.mean(np.abs(perm_coefs) >= np.abs(observed_coef)))
        perm_ctrl_rows.append({
            "spec": f"{spec_label} {fe_label}", "observed_coef": observed_coef,
            "permutation_p": p_perm, "n_permutations": N_PERM_CTRL,
        })
        print(f"{spec_label:8s} {fe_label:9s}  observed coef={observed_coef:+.4f}  "
              f"permutation p ({N_PERM_CTRL} reps)={p_perm:.4f}")

perm_ctrl_df = pd.DataFrame(perm_ctrl_rows)
perm_ctrl_df.to_csv(OUT / "extension_permutation_controlled_specs.csv", index=False)

# ---------------------------------------------------------------------------
# 1f. Leave-one-country-out: is this another Bulgaria-style single-country
#     artifact? Run on the original levels spec (Model 1c, n=74, all 3 years)
#     since that is the specification the coordinator asked to stress-test,
#     and separately flag Ireland (measurement-error risk: GDP and industrial
#     value-added share are both inflated by multinational profit-shifting
#     with little matching physical/ETS footprint).
# ---------------------------------------------------------------------------
print("\n=== 1f. Leave-one-country-out (original levels spec, n=74, all 3 years) ===")
loo_ctrl_rows = []
formula_levels = "d_log_emissions ~ digital_multi + log_gdp_per_capita + industry_va_share + electricity_price"
for c in sorted(panel_ctrl["country_code"].unique()):
    df = panel_ctrl[panel_ctrl["country_code"] != c]
    m = smf.ols(formula_levels, data=df).fit(cov_type="cluster", cov_kwds={"groups": df["country_code"]})
    loo_ctrl_rows.append({
        "dropped_country": c, "n": len(df), "coef": m.params["digital_multi"],
        "p": m.pvalues["digital_multi"],
    })
loo_ctrl_df = pd.DataFrame(loo_ctrl_rows).sort_values("p", ascending=False)
print(loo_ctrl_df.to_string(index=False))
print(f"\nMax p across all 26 leave-one-country-out runs: {loo_ctrl_df['p'].max():.4f}  "
      f"(dropped: {loo_ctrl_df.iloc[0]['dropped_country']})")
print(f"Min coefficient: {loo_ctrl_df['coef'].min():.4f}")
ie_row = loo_ctrl_df[loo_ctrl_df["dropped_country"] == "IE"]
print(f"Dropping Ireland specifically: coef={ie_row['coef'].values[0]:+.4f}, p={ie_row['p'].values[0]:.4f} "
      "(Ireland's GDP and industry-value-added-share figures are both inflated by multinational "
      "profit-shifting/contract-manufacturing booked there with little matching ETS footprint -- "
      "dropping it does not weaken the result, it strengthens it, so this measurement-error risk "
      "is not what is driving the levels-spec finding)")
loo_ctrl_df.to_csv(OUT / "extension_leave_one_out_controlled.csv", index=False)

# ---------------------------------------------------------------------------
# 1g. Effect-size sanity check: is the implied magnitude plausible?
# ---------------------------------------------------------------------------
print("\n=== 1g. Effect-size sanity check ===")
sd_digital = fixed_24_25["digital_multi"].std()
mean_outcome = fixed_24_25["d_log_emissions"].mean()
lagged_pooled_coef = inference_df.loc[
    (inference_df["spec"] == "lagged pooled"), "coef"
].values[0]
implied_pp = sd_digital * lagged_pooled_coef * 100
print(f"SD(digital_multi) on the fixed sample = {sd_digital:.4f}")
print(f"Sample mean d_log_emissions = {mean_outcome:+.4f} ({mean_outcome*100:+.1f}%)")
print(f"Lagged-spec (pooled) coefficient = {lagged_pooled_coef:+.4f}")
print(f"Implied effect of +1 SD digitalization = {implied_pp:+.2f} percentage points of annual emissions growth")
print(
    f"For context, that is roughly {abs(implied_pp / (mean_outcome*100)):.0%} of the sample's own average "
    "annual emissions decline -- a large effect for a three-year country-level survey share to be "
    "carrying, and itself a reason for caution regardless of the p-value: implausibly large point "
    "estimates on a short panel are a classic symptom of residual confounding, not a reason for more "
    "confidence in the estimate."
)
with open(OUT / "extension_effect_size_note.txt", "w", encoding="utf-8") as f:
    f.write(f"SD(digital_multi) = {sd_digital:.4f}\n")
    f.write(f"Sample mean d_log_emissions = {mean_outcome:+.4f} ({mean_outcome*100:+.1f}%)\n")
    f.write(f"Lagged-spec (pooled) coefficient = {lagged_pooled_coef:+.4f}\n")
    f.write(f"Implied effect of +1 SD digitalization = {implied_pp:+.2f} percentage points\n")

# ---------------------------------------------------------------------------
# 2. Broadened EIBIS indicators: energy-efficiency investment measures as
#    alternative predictors, tested alone and alongside digital_multi
# ---------------------------------------------------------------------------
print("\n=== New EIBIS indicators: correlation with d_log_emissions ===")
new_ind_corr = []
for var in ["energy_efficiency_invest_share", "energy_efficiency_firms_share"]:
    sub = panel_x.dropna(subset=[var, "d_log_emissions"])
    r, p = stats.pearsonr(sub[var], sub["d_log_emissions"])
    new_ind_corr.append({"variable": var, "n": len(sub), "pearson_r": r, "p_value": p})
    print(f"{var:35s} n={len(sub):3d}  r={r:+.3f}  p={p:.3f}")
pd.DataFrame(new_ind_corr).to_csv(OUT / "extension_new_indicator_correlations.csv", index=False)

panel_ee = panel_x.dropna(subset=["digital_multi", "energy_efficiency_invest_share", "d_log_emissions"])
m_ee_alone = run_and_log(
    "Model E1: d_log_emissions ~ energy_efficiency_invest_share alone, country-clustered SE",
    smf.ols("d_log_emissions ~ energy_efficiency_invest_share", data=panel_ee).fit(
        cov_type="cluster", cov_kwds={"groups": panel_ee["country_code"]}
    ),
)
m_ee_with_digital = run_and_log(
    "Model E2: d_log_emissions ~ digital_multi + energy_efficiency_invest_share, country-clustered SE "
    "(does energy-investment intensity add anything beyond digitalization, or vice versa?)",
    smf.ols("d_log_emissions ~ digital_multi + energy_efficiency_invest_share", data=panel_ee).fit(
        cov_type="cluster", cov_kwds={"groups": panel_ee["country_code"]}
    ),
)

# ---------------------------------------------------------------------------
# 3. Block-permutation test: shuffle whole country-series of digital_multi
#    across countries (preserving each country's own 3-year pattern), rebuild
#    the panel, refit Model 1b (pooled) and Model 3 (year FE), and see where
#    the true coefficient falls in the resulting null distribution. This
#    avoids relying on asymptotic cluster-robust inference with only 27
#    clusters.
# ---------------------------------------------------------------------------
print("\n=== Block-permutation test (permute digital_multi across whole countries) ===")

perm_base = panel[["country_code", "year", "d_log_emissions", "digital_multi"]].dropna().copy()
countries_arr = sorted(perm_base["country_code"].unique())

# Wide country x year matrix of digital_multi (one row per country -- its own
# 3-year block, kept intact) and the matching outcome matrix, both indexed
# the same way so a column-label shuffle on the digital matrix reassigns
# whole country blocks without touching each country's own year-to-year
# pattern or its own outcome series.
digital_wide = perm_base.pivot(index="year", columns="country_code", values="digital_multi")[countries_arr]
outcome_wide = perm_base.pivot(index="year", columns="country_code", values="d_log_emissions")[countries_arr]
years_arr = digital_wide.index.tolist()

N_PERM = 5000


def fit_coef(df, formula):
    return smf.ols(formula, data=df).fit().params["digital_multi"]


observed_m1 = fit_coef(perm_base, "d_log_emissions ~ digital_multi")
observed_m3 = fit_coef(perm_base, "d_log_emissions ~ digital_multi + C(year)")

perm_coefs_m1 = np.empty(N_PERM)
perm_coefs_m3 = np.empty(N_PERM)

for i in range(N_PERM):
    shuffled_cols = RNG.permutation(countries_arr)
    # relabel the digital_multi matrix's columns with a shuffled country
    # order, so each real country (outcome_wide's own column) is paired with
    # another country's whole digital_multi block, own within-country
    # year-to-year structure intact
    digital_perm = digital_wide.copy()
    digital_perm.columns = shuffled_cols
    digital_perm = digital_perm[countries_arr]

    df = pd.DataFrame({
        "year": np.tile(years_arr, len(countries_arr)),
        "country_code": np.repeat(countries_arr, len(years_arr)),
        "d_log_emissions": outcome_wide.to_numpy().flatten(order="F"),
        "digital_multi": digital_perm.to_numpy().flatten(order="F"),
    }).dropna(subset=["digital_multi", "d_log_emissions"])

    perm_coefs_m1[i] = fit_coef(df, "d_log_emissions ~ digital_multi")
    perm_coefs_m3[i] = fit_coef(df, "d_log_emissions ~ digital_multi + C(year)")

perm_p_m1 = np.mean(np.abs(perm_coefs_m1) >= np.abs(observed_m1))
perm_p_m3 = np.mean(np.abs(perm_coefs_m3) >= np.abs(observed_m3))

print(f"Model 1 (pooled): observed coef={observed_m1:+.4f}  "
      f"permutation p={perm_p_m1:.4f}  (asymptotic clustered p=0.114, from first_pass_analysis.md)")
print(f"Model 3 (year FE): observed coef={observed_m3:+.4f}  "
      f"permutation p={perm_p_m3:.4f}  (asymptotic clustered p=0.216, from first_pass_analysis.md)")

perm_summary = pd.DataFrame([
    {"model": "Model 1 pooled", "observed_coef": observed_m1, "permutation_p": perm_p_m1,
     "asymptotic_clustered_p": 0.114, "n_permutations": N_PERM},
    {"model": "Model 3 year FE", "observed_coef": observed_m3, "permutation_p": perm_p_m3,
     "asymptotic_clustered_p": 0.216, "n_permutations": N_PERM},
])
perm_summary.to_csv(OUT / "extension_permutation_test.csv", index=False)

# permutation-null histogram figure
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
for ax, coefs, obs, title, p in [
    (axes[0], perm_coefs_m1, observed_m1, "Model 1 (pooled)", perm_p_m1),
    (axes[1], perm_coefs_m3, observed_m3, "Model 3 (year FE)", perm_p_m3),
]:
    ax.hist(coefs, bins=40, color="#999999", alpha=0.7, label="Permutation null")
    ax.axvline(obs, color="#c0392b", linewidth=2, label=f"Observed ({obs:+.3f})")
    ax.axvline(-obs, color="#c0392b", linewidth=1, linestyle="--", alpha=0.6)
    ax.set_title(f"{title}\npermutation p={p:.3f}")
    ax.set_xlabel("Coefficient on digital_multi (country-shuffled null)")
    ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(OUT / "extension_permutation_histograms.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# 4. EIBIS pre-2023 coverage gap: confirmed directly against the API
#    (see analysis/extension_analysis.md for the write-up; this block just
#    re-verifies against whatever is currently in the fetched CSV, which
#    is consistent with the direct API check already performed).
# ---------------------------------------------------------------------------
digital_wave_coverage = (
    eib_all[eib_all["indicator"] == "Implementation of digital technologies"]
    .groupby("survey_wave")["Multiple technologies"]
    .apply(lambda s: s.notna().sum())
)
print("\n=== EIBIS 'Implementation of digital technologies' non-null count by wave (sector=ALL,size=ALL) ===")
print(digital_wave_coverage)
digital_wave_coverage.to_csv(OUT / "extension_eibis_coverage_check.csv")

with open(OUT / "extension_regression_summaries.txt", "w", encoding="utf-8") as f:
    for name, text in results_log:
        f.write(f"{'='*90}\n{name}\n{'='*90}\n{text}\n\n")
    f.write("\nBlock-permutation test:\n")
    f.write(perm_summary.to_string(index=False) + "\n")

print(f"\nAll extension outputs written to {OUT}")
