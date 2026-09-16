"""
First-pass analysis: does digitalization intensity (EIBIS, country-year)
predict verified emissions trends (EU ETS, country-year)?

Reproducible from data/raw/. Writes tables to analysis/output/ and prints a
summary to stdout. See analysis/first_pass_analysis.md for the write-up.
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "analysis" / "output"
OUT.mkdir(parents=True, exist_ok=True)

pd.set_option("display.width", 140)

# ---------------------------------------------------------------------------
# 1. EU ETS verified emissions, country x year
# ---------------------------------------------------------------------------
eu = pd.read_csv(RAW / "eu_ets" / "eu-ets.csv")

# keep only genuine calendar years (drop "Total Nth trading period" rows)
eu = eu[eu["year"].str.fullmatch(r"\d{4}")].copy()
eu["year"] = eu["year"].astype(int)

# "2. Verified emissions" is the independently-audited metric.
# main_activity_code == "20-99" is *already* the country total across all
# stationary installations (20 = combustion, 21-99 = all other industrial
# activities); it is itself a rollup, so it must not be added to its own
# components when summing -- but taken alone it IS the correct country-year
# total, so we select it directly rather than re-summing the components.
ets = eu[
    (eu["main_activity_code"] == "20-99")
    & (eu["citl_information"] == "2. Verified emissions")
].copy()
ets = ets.rename(columns={"value": "verified_emissions_t"})[
    ["country_code", "year", "verified_emissions_t"]
]

# Drop non-country aggregate/fund rows that show up in country_code
non_country = {"Innovation fund", "Modernisation Fund", "NER 300 auctions", "RRF"}
ets = ets[~ets["country_code"].isin(non_country)]

# Country-code reconciliation EU ETS -> EIBIS convention
# EU ETS uses "GR" for Greece; EIBIS (and EU official code list) uses "EL".
# EU ETS additionally carries UK ("GB"), Northern Ireland ("XI"), and EEA/EFTA
# members (NO, IS, LI) that are not covered by EIBIS at all -- those rows
# simply won't find an EIBIS match and drop out of the merged panel below.
ets["country_code"] = ets["country_code"].replace({"GR": "EL"})

ets = ets.sort_values(["country_code", "year"])
ets["log_emissions"] = np.log(ets["verified_emissions_t"].clip(lower=1))
ets["d_log_emissions"] = ets.groupby("country_code")["log_emissions"].diff()
ets["pct_change_emissions"] = ets.groupby("country_code")["verified_emissions_t"].pct_change()

ets.to_csv(OUT / "eu_ets_country_year_verified_emissions.csv", index=False)

print("=== EU ETS country-year verified-emissions panel ===")
print(f"rows: {len(ets)}, countries: {ets['country_code'].nunique()}, "
      f"years: {ets['year'].min()}-{ets['year'].max()}")
print(ets["country_code"].unique())

# ---------------------------------------------------------------------------
# 2. EIBIS digitalization + climate module, country x year (ALL sector/size)
# ---------------------------------------------------------------------------
eib = pd.read_csv(RAW / "eibis" / "eibis_aggregate.csv")
# EIBIS carries "EU" (aggregate) and "US" rows alongside the 27 member states.
# These have no counterpart in the EU-ETS country panel so they drop out of the
# inner merge anyway, but filter them explicitly rather than relying on that.
eib = eib[~eib["country"].isin(["EU", "US"])]
eib_all = eib[(eib["sector"] == "ALL") & (eib["size"] == "ALL")].copy()

wide = {}
specs = [
    ("Implementation of digital technologies", "Multiple technologies", "digital_multi"),
    ("Implementation of digital technologies", "Single technology", "digital_single"),
    ("Share of firms using generative AI tools", "Share of firms using generative AI tools", "genai_share"),
    ("Climate change targets for own GHG emissions", "Climate change targets for own GHG emissions", "climate_target_share"),
    ("Impact of climate change - Physical risk", "A major impact", "physical_risk_major"),
    ("Impact of climate change - Risks associated with the transition to a net zero economy over the next five years", "A risk", "transition_risk_share"),
    ("Investment plans to tackle climate change impact", "Already invested", "already_invested_climate"),
]
for indicator, col, newname in specs:
    sub = eib_all[eib_all["indicator"] == indicator][["country", "survey_wave", col]].dropna()
    sub = sub.rename(columns={"survey_wave": "year", col: newname})
    wide[newname] = sub

eibis_panel = wide["digital_multi"][["country", "year", "digital_multi"]]
for name, df in wide.items():
    if name == "digital_multi":
        continue
    eibis_panel = eibis_panel.merge(df[["country", "year", name]], on=["country", "year"], how="outer")

eibis_panel["digital_any"] = eibis_panel[["digital_multi", "digital_single"]].sum(axis=1, min_count=2)
eibis_panel = eibis_panel.rename(columns={"country": "country_code"})
eibis_panel.to_csv(OUT / "eibis_country_year_panel.csv", index=False)

print("\n=== EIBIS country-year panel (ALL sector, ALL size) ===")
print(f"rows: {len(eibis_panel)}, countries: {eibis_panel['country_code'].nunique()}, "
      f"years: {sorted(eibis_panel['year'].unique())}")

# ---------------------------------------------------------------------------
# 3. E-PRTR national air releases, country x year (secondary/robustness outcome)
# ---------------------------------------------------------------------------
eprtr = pd.read_csv(RAW / "eprtr" / "F1_1_Air_Releases_National.csv")
co2 = eprtr[eprtr["Pollutant"].str.contains("Carbon dioxide", case=False, na=False)].copy()
# there are two CO2 lines in E-PRTR: "excluding biomass" and possibly "(total)" -- keep excl. biomass,
# the standard fossil/industrial CO2 metric, consistent with EU ETS scope
co2 = co2[co2["Pollutant"].str.contains("excluding biomass", case=False, na=False)]
co2 = co2.rename(columns={"countryName": "country_name", "reportingYear": "year", "Releases": "co2_eprtr"})
co2 = co2.groupby(["country_name", "year"], as_index=False)["co2_eprtr"].sum()

# map full country names -> EU official 2-letter codes (EIBIS/EU-ETS convention)
NAME_TO_CODE = {
    "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR", "Cyprus": "CY",
    "Czechia": "CZ", "Czech Republic": "CZ", "Denmark": "DK", "Estonia": "EE", "Finland": "FI",
    "France": "FR", "Germany": "DE", "Greece": "EL", "Hungary": "HU", "Ireland": "IE",
    "Italy": "IT", "Latvia": "LV", "Lithuania": "LT", "Luxembourg": "LU", "Malta": "MT",
    "Netherlands": "NL", "Poland": "PL", "Portugal": "PT", "Romania": "RO", "Slovakia": "SK",
    "Slovenia": "SI", "Spain": "ES", "Sweden": "SE", "United Kingdom": "UK", "Norway": "NO",
    "Iceland": "IS", "Liechtenstein": "LI", "Serbia": "RS", "Switzerland": "CH",
}
co2["country_code"] = co2["country_name"].map(NAME_TO_CODE)
co2 = co2.dropna(subset=["country_code"])
co2 = co2.sort_values(["country_code", "year"])
co2["log_co2"] = np.log(co2["co2_eprtr"].clip(lower=1))
co2["d_log_co2"] = co2.groupby("country_code")["log_co2"].diff()
co2.to_csv(OUT / "eprtr_country_year_co2.csv", index=False)

print("\n=== E-PRTR country-year CO2 (excl. biomass) panel ===")
print(f"rows: {len(co2)}, countries: {co2['country_code'].nunique()}, "
      f"years: {co2['year'].min()}-{co2['year'].max()}")

# ---------------------------------------------------------------------------
# 4. Merge: EIBIS digitalization (year t) -> EU ETS verified-emissions change (year t)
#    EIBIS waves are conducted mid-year (roughly June-Sept); we treat the wave
#    year as contemporaneous with same-calendar-year emissions changes, which
#    is the most defensible timing given EIBIS is a single annual cross-section
#    with no finer time resolution.
# ---------------------------------------------------------------------------
panel = ets.merge(eibis_panel, on=["country_code", "year"], how="inner")
panel = panel.dropna(subset=["d_log_emissions", "digital_multi"])
panel.to_csv(OUT / "merged_analysis_panel.csv", index=False)

print("\n=== Merged EU-ETS x EIBIS analysis panel ===")
print(f"rows: {len(panel)}, countries: {panel['country_code'].nunique()}, "
      f"years: {sorted(panel['year'].unique())}")
print(panel[["country_code", "year", "verified_emissions_t", "d_log_emissions",
             "digital_multi", "genai_share", "climate_target_share"]].to_string())

# also merge in E-PRTR CO2 change as an alternative outcome
panel_eprtr = co2.merge(eibis_panel, on=["country_code", "year"], how="inner")
panel_eprtr = panel_eprtr.dropna(subset=["d_log_co2", "digital_multi"])
panel_eprtr.to_csv(OUT / "merged_analysis_panel_eprtr.csv", index=False)
print(f"\nE-PRTR merged panel rows: {len(panel_eprtr)}, "
      f"countries: {panel_eprtr['country_code'].nunique()}")

# ---------------------------------------------------------------------------
# 5. Descriptive / correlation analysis
# ---------------------------------------------------------------------------
print("\n=== Descriptive statistics (merged EU-ETS panel) ===")
desc = panel[["d_log_emissions", "digital_multi", "digital_any", "genai_share",
              "climate_target_share"]].describe()
print(desc)
desc.to_csv(OUT / "descriptives.csv")

from scipy import stats

print("\n=== Pairwise correlations with d_log_emissions (verified-emissions YoY log change) ===")
corr_rows = []
for var in ["digital_multi", "digital_any", "genai_share", "climate_target_share"]:
    sub = panel.dropna(subset=[var, "d_log_emissions"])
    r, p = stats.pearsonr(sub[var], sub["d_log_emissions"])
    corr_rows.append({"variable": var, "n": len(sub), "pearson_r": r, "p_value": p})
    print(f"{var:25s} n={len(sub):3d}  r={r:+.3f}  p={p:.3f}")
corr_df = pd.DataFrame(corr_rows)
corr_df.to_csv(OUT / "correlations.csv", index=False)

# ---------------------------------------------------------------------------
# 6. Regressions
# ---------------------------------------------------------------------------
results_log = []

def run_and_log(name, model):
    print(f"\n--- {name} ---")
    print(model.summary())
    results_log.append((name, model.summary().as_text()))
    return model

# NOTE on standard errors: the panel is 27 countries x 3 years, so the three
# observations per country are not independent. HC1 (heteroskedasticity-robust
# but not cluster-robust) treats all 81 rows as independent and overstates
# precision. Every model below is therefore fit BOTH with HC1 and with SEs
# clustered by country_code, and the clustered version is the one used in the
# write-up and headline table; HC1 is kept alongside only to show how much of
# the apparent significance was coming from ignoring the panel structure.

# Model 1: pooled OLS, no fixed effects -- reported both ways
m1_hc1 = run_and_log(
    "Model 1 (HC1, NOT the preferred SE): pooled OLS  d_log_emissions ~ digital_multi",
    smf.ols("d_log_emissions ~ digital_multi", data=panel).fit(cov_type="HC1"),
)
m1 = run_and_log(
    "Model 1 (country-clustered SE -- headline): pooled OLS  d_log_emissions ~ digital_multi",
    smf.ols("d_log_emissions ~ digital_multi", data=panel).fit(
        cov_type="cluster", cov_kwds={"groups": panel["country_code"]}
    ),
)

# Model 2: add generative-AI share and climate-target share as covariates.
# genai_share is populated for 2025 only, so this model collapses to a single
# cross-section (n=27, one obs/country) -- clustering has no meaning here since
# there is exactly one observation per cluster, so HC1 is the correct/only
# choice for this one model.
m2 = run_and_log(
    "Model 2: pooled OLS (single cross-section, n=27)  "
    "d_log_emissions ~ digital_multi + genai_share + climate_target_share",
    smf.ols(
        "d_log_emissions ~ digital_multi + genai_share + climate_target_share",
        data=panel,
    ).fit(cov_type="HC1"),
)

# Model 3: year fixed effects, country-clustered SEs (absorbs EU-wide shocks
# like the 2022-23 energy-price crisis and common ETS cap tightening)
m3 = run_and_log(
    "Model 3: OLS + year FE, country-clustered SE  d_log_emissions ~ digital_multi + C(year)",
    smf.ols("d_log_emissions ~ digital_multi + C(year)", data=panel).fit(
        cov_type="cluster", cov_kwds={"groups": panel["country_code"]}
    ),
)

# --- Secondary / appendix specifications (NOT headline) -------------------
# Model 4: country + year fixed effects (two-way FE). Demoted to secondary
# because country FE absorb the great majority of digital_multi's variance
# (see variance decomposition below) -- with only 3 years, this model is
# barely testing the hypothesis at all, mostly regressing emissions changes
# on within-country EIBIS survey noise. Reported with country-clustered SEs
# for consistency with Model 3 (HC1 previously understated the SE here).
try:
    m4 = run_and_log(
        "Model 4 (APPENDIX -- country FE + year FE, country-clustered SE): "
        "d_log_emissions ~ digital_multi + C(country_code) + C(year)",
        smf.ols(
            "d_log_emissions ~ digital_multi + C(country_code) + C(year)", data=panel
        ).fit(cov_type="cluster", cov_kwds={"groups": panel["country_code"]}),
    )
except Exception as e:
    print("Model 4 failed:", e)

# Model 5: robustness on E-PRTR CO2 outcome instead of EU ETS. Demoted to
# appendix -- n=17 across only ~10 country clusters, cluster-robust inference
# is not meaningful at that cluster count; kept only as a directional check.
m5 = run_and_log(
    "Model 5 (APPENDIX / uninformative -- E-PRTR CO2 robustness check, n=17, ~10 clusters): "
    "d_log_co2 ~ digital_multi + C(year)",
    smf.ols("d_log_co2 ~ digital_multi + C(year)", data=panel_eprtr).fit(
        cov_type="cluster", cov_kwds={"groups": panel_eprtr["country_code"]}
    ),
)

# ---------------------------------------------------------------------------
# 6b. Fragility checks: leave-one-out (Bulgaria) on Model 1
#     Run on the naive HC1 spec (the one that showed p<0.05) to demonstrate
#     that its apparent significance is not even robust to dropping a single
#     observation -- a second, independent way the p=0.047 result fails,
#     layered on top of the clustering result above.
# ---------------------------------------------------------------------------
print("\n=== Leave-one-out fragility check on Model 1 (HC1, the naive spec that showed p<0.05) ===")
loo_rows = []

def fit_m1_hc1(df, label):
    mod = smf.ols("d_log_emissions ~ digital_multi", data=df).fit(cov_type="HC1")
    coef = mod.params["digital_multi"]
    p = mod.pvalues["digital_multi"]
    loo_rows.append({"sample": label, "n": len(df), "coef": coef, "p_value": p})
    print(f"{label:32s} n={len(df):3d}  coef={coef:+.3f}  p={p:.3f}")
    return mod

fit_m1_hc1(panel, "Full sample")
fit_m1_hc1(panel[~((panel["country_code"] == "BG") & (panel["year"] == 2025))],
           "Drop BG-2025 only")
fit_m1_hc1(panel[panel["country_code"] != "BG"], "Drop Bulgaria entirely")
loo_df = pd.DataFrame(loo_rows)
loo_df.to_csv(OUT / "leave_one_out_model1.csv", index=False)

# ---------------------------------------------------------------------------
# 6c. Variance decomposition of digital_multi (why two-way FE is uninformative)
# ---------------------------------------------------------------------------
print("\n=== Variance decomposition of digital_multi (between vs within country) ===")
grp = panel.groupby("country_code")["digital_multi"]
country_means = grp.transform("mean")
between_sd = country_means.std()
within_sd = (panel["digital_multi"] - country_means).groupby(panel["country_code"]).std().mean()
resid_share = (within_sd / between_sd) ** 2
print(f"Between-country SD: {between_sd:.3f}")
print(f"Mean within-country SD: {within_sd:.3f}")
print(f"Residual (within-country) variance share left for country-FE models: {resid_share:.1%}")
pd.DataFrame([{
    "between_country_sd": between_sd,
    "mean_within_country_sd": within_sd,
    "within_over_between_sq": resid_share,
}]).to_csv(OUT / "variance_decomposition.csv", index=False)

# ---------------------------------------------------------------------------
# 7. Diagnostics: VIF (Model 2), influence (Model 3), residual normality
# ---------------------------------------------------------------------------
from statsmodels.stats.outliers_influence import variance_inflation_factor

print("\n=== Multicollinearity check (Model 2 regressors) ===")
X2 = panel[["digital_multi", "genai_share", "climate_target_share"]].dropna()
X2c = sm.add_constant(X2)
vif_rows = []
for i, col in enumerate(X2c.columns):
    vif = variance_inflation_factor(X2c.values, i)
    vif_rows.append({"variable": col, "VIF": vif})
    print(f"{col:25s} VIF={vif:.2f}")
pd.DataFrame(vif_rows).to_csv(OUT / "vif_model2.csv", index=False)

print("\n=== Influence diagnostics (Model 3) ===")
infl = m3.get_influence()
cooks_d = infl.cooks_distance[0]
panel_m3 = panel.dropna(subset=["digital_multi", "d_log_emissions"]).reset_index(drop=True)
infl_df = panel_m3[["country_code", "year", "d_log_emissions", "digital_multi"]].copy()
infl_df["cooks_d"] = cooks_d
infl_df = infl_df.sort_values("cooks_d", ascending=False)
print(infl_df.head(10).to_string())
infl_df.to_csv(OUT / "influence_model3.csv", index=False)
n = len(panel_m3)
thresh = 4 / n
flagged = infl_df[infl_df["cooks_d"] > thresh]
print(f"\nObservations exceeding Cook's D > 4/n ({thresh:.3f}): {len(flagged)} of {n}")

resid = m3.resid
sw_stat, sw_p = stats.shapiro(resid)
print(f"\nShapiro-Wilk normality test on Model 3 residuals: W={sw_stat:.3f}, p={sw_p:.3f}")

with open(OUT / "regression_summaries.txt", "w", encoding="utf-8") as f:
    for name, text in results_log:
        f.write(f"{'='*90}\n{name}\n{'='*90}\n{text}\n\n")
    f.write(f"\nShapiro-Wilk on Model 3 residuals: W={sw_stat:.4f}, p={sw_p:.4f}\n")
    f.write(f"Cook's D flagged ({thresh:.3f} threshold): {len(flagged)} / {n} observations\n")
    f.write("\nLeave-one-out (Model 1, HC1 SE -- the naive spec that showed p<0.05):\n")
    f.write(loo_df.to_string(index=False) + "\n")
    f.write("\nVariance decomposition of digital_multi:\n")
    f.write(f"between-country SD={between_sd:.4f}, mean within-country SD={within_sd:.4f}, "
            f"within/between share={resid_share:.1%}\n")

# ---------------------------------------------------------------------------
# 8. Headline figure: country-level scatter, digitalization vs. cumulative
#    verified-emissions change, with fitted line + 95% CI band.
#    This collapses the 3-year panel to one point per country (mean
#    digital_multi over 2023-2025 on x; cumulative log-change in verified
#    emissions from 2022 to 2025 on y) -- the same cross-sectional collapse
#    the correlation table implicitly represents, and the most honest single
#    picture of "is there a visible relationship at all."
# ---------------------------------------------------------------------------
print("\n=== Building headline scatter figure ===")
cum = ets[ets["year"].isin([2022, 2025])].pivot(
    index="country_code", columns="year", values="verified_emissions_t"
)
cum = cum.dropna(subset=[2022, 2025])
cum["cum_d_log_emissions"] = np.log(cum[2025]) - np.log(cum[2022])

country_digital = panel.groupby("country_code")["digital_multi"].mean().rename("mean_digital_multi")
scatter_df = cum[["cum_d_log_emissions"]].join(country_digital, how="inner").reset_index()
scatter_df.to_csv(OUT / "scatter_country_level.csv", index=False)

r_scatter, p_scatter = stats.pearsonr(scatter_df["mean_digital_multi"], scatter_df["cum_d_log_emissions"])
print(f"Cross-sectional collapse (n={len(scatter_df)}): r={r_scatter:+.3f}, p={p_scatter:.3f}")

fit = smf.ols("cum_d_log_emissions ~ mean_digital_multi", data=scatter_df).fit()
x_grid = np.linspace(scatter_df["mean_digital_multi"].min(), scatter_df["mean_digital_multi"].max(), 100)
pred = fit.get_prediction(pd.DataFrame({"mean_digital_multi": x_grid}))
pred_summary = pred.summary_frame(alpha=0.05)

fig, ax = plt.subplots(figsize=(7.5, 5.5))
ax.axhline(0, color="#999999", linewidth=1, linestyle="--", zorder=1)
ax.fill_between(x_grid, pred_summary["mean_ci_lower"], pred_summary["mean_ci_upper"],
                 color="#4c72b0", alpha=0.18, zorder=2, label="95% CI (fitted line)")
ax.plot(x_grid, pred_summary["mean"], color="#4c72b0", linewidth=2, zorder=3, label="Fitted line")
ax.scatter(scatter_df["mean_digital_multi"], scatter_df["cum_d_log_emissions"],
           color="#333333", s=36, zorder=4)

bg_row = scatter_df[scatter_df["country_code"] == "BG"]
if not bg_row.empty:
    ax.annotate("BG", (bg_row["mean_digital_multi"].values[0], bg_row["cum_d_log_emissions"].values[0]),
                textcoords="offset points", xytext=(6, 6), fontsize=9, color="#c0392b", fontweight="bold")

ax.set_xlabel("Mean share of firms using multiple digital technologies (2023-2025 EIBIS)")
ax.set_ylabel("Cumulative log change in verified emissions, 2022->2025 (EU ETS)")
ax.set_title(
    f"Digitalization vs. verified-emissions change, {len(scatter_df)} countries\n"
    f"r={r_scatter:+.2f}, p={p_scatter:.3f} -- confidence band covers zero"
)
ax.legend(loc="best", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "scatter_digital_vs_emissions_change.png", dpi=150)
plt.close(fig)

print(f"\nAll outputs written to {OUT}")
