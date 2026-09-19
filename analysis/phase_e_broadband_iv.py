"""
Phase E: is broadband-infrastructure rollout a usable instrument for DII?
Feasibility study, first stage FIRST, with a pre-declared gate (see section D).
Usage: python analysis/phase_e_broadband_iv.py      (helpers: phase_e_lib.py)
"""
import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy import stats as st
from phase_e_lib import *

pd.set_option("display.width", 220, "display.max_columns", 40, "display.max_rows", 200)
SEED = 20260501
NB = 1999
Y_VA, Y_EM, DII = "d_log_va", "d_log_emissions", "dii_high_share_manufacturing"

v, bb = build_panel()

# ---------------------------------------------------------------- A. data audit
t = pd.read_csv(RAW / "eurostat" / "broadband_coverage_technology.csv")
s = pd.read_csv(RAW / "eurostat" / "broadband_coverage_speed.csv")
r = pd.read_csv(RAW / "eurostat" / "broadband_household_access_regional.csv")
aud = []
for nm, df, col in [("isoc_cbs (speed)", s, "inet_spd"), ("isoc_cbt (technology)", t, "inet_tec")]:
    g = df.groupby(col).agg(n_cells=("value", "size"), n_countries=("geo", "nunique"),
                            first_year=("time", "min"), last_year=("time", "max"))
    g["dataset"] = nm
    aud.append(g.reset_index().rename(columns={col: "series"}))
aud = pd.concat(aud)
aud.to_csv(OUT / "phase_e_data_audit.csv", index=False)
print("Countries in speed:", s.geo.nunique(), "| technology:", t.geo.nunique(),
      "| rural (DEG3) cells:", (t.terrtypo == "DEG3").sum())
print("isoc_r_broad_h: units", sorted(r.unit.unique()), "geo units", r.geo.nunique(), "years", r.time.min(), r.time.max())

# ---------------------------------------------------------------- B. instruments
def loo_mean(bb, col):
    p = bb.pivot(index="year", columns="country_code", values=col)
    ssum = p.sum(axis=1, min_count=1)
    cnt = p.count(axis=1)
    out = []
    for cc in p.columns:
        m = (ssum - p[cc].fillna(0)) / (cnt - p[cc].notna().astype(int))
        out.append(pd.DataFrame({"year": m.index, "country_code": cc, col + "_loo": m.values}))
    return pd.concat(out)

base13 = bb[bb.year == 2013].set_index("country_code")
d = v.copy()
SHOCKS = {"FTTP": "FTTP_TOTAL", "G100": "MBPS_GT100"}
for k, c in SHOCKS.items():
    d = d.merge(loo_mean(bb, c).rename(columns={c + "_loo": f"sh_{k}"}), on=["country_code", "year"], how="left")
BASES = {"NGA": "NGA_TOTAL", "VDSL": "VDSL_TOTAL", "DOCSIS": "DOCSIS3_0_TOTAL", "DSL": "DSL_TOTAL", "G100": "MBPS_GT100"}
for k, c in BASES.items():
    d["b_" + k] = d.country_code.map(base13[c])
# (removed: 'non-fibre NGA' = NGA - FTTP. NGA is a union of VDSL/DOCSIS/FTTP, so the subtraction is wrong where
#  fibre and cable overlap (e.g. LT 2013: NGA=FTTP=48.7, cable 42.8) and needed a fabricated fillna(0) for CY.)
# sensitivity: missing DOCSIS 3.0 (EL, IT only, no cable network) -> 0.  Primary DOCSIS keeps NaN.
d["b_DOCSISz"] = d["b_DOCSIS"].where(~d.country_code.isin(["EL", "IT"]), 0.0)
BKEYS = ["NGA", "VDSL", "DOCSIS", "DOCSISz", "DSL", "G100"]
for b in BKEYS:
    for sk in SHOCKS:
        d[f"Z_{b}x{sk}"] = d["b_" + b] / 100 * d[f"sh_{sk}"] / 100
# rural-gap and lagged-coverage candidates (time-varying, NOT predetermined)
bb2 = bb.sort_values(["country_code", "year"]).copy()
bb2["gap_NGA"] = bb2["NGA_TOTAL"] - bb2["NGA_DEG3"]
lag = bb2.groupby("country_code")["MBPS_GT100"].shift(2)
okc = bb2.groupby("country_code")["year"].shift(2) == bb2["year"] - 2
bb2["lag2_G100"] = lag.where(okc)
d = d.merge(bb2[["country_code", "year", "gap_NGA", "lag2_G100"]], on=["country_code", "year"], how="left")
d["Z_ruralgap_NGA"] = -d["gap_NGA"]
d["Z_lag2_G100"] = d["lag2_G100"]
d["gdp13"] = np.log(d.country_code.map(v[v.year == 2013].set_index("country_code").gdp_per_capita))
d["gdp13_x_sh"] = d["gdp13"] * d["sh_FTTP"] / 100
d["eu15"] = (d.accession_2004plus == 0).astype(int)

CTRL = "C(year)+d_log_gdp_per_capita+accession_2004plus+energy_shock_exposure"   # = Phase D G5 controls
CTRL_SUB = "C(year)+d_log_gdp_per_capita+energy_shock_exposure"                   # accession dummy constant within subsample
SPECS = {
    "S1 Phase-D controls": lambda sub: CTRL_SUB if sub != "all" else CTRL,
    "S2 +GDPpc2013 x EU-FTTP shock": lambda sub: (CTRL_SUB if sub != "all" else CTRL) + "+gdp13_x_sh",
    "S3 +GDPpc2013 x year FE": lambda sub: (CTRL_SUB if sub != "all" else CTRL) + "+gdp13:C(year)",
}
SPECS_FE = {  # textbook shift-share first stage: country FE + year FE (accession dummy absorbed by country FE)
    "S4 country FE + year FE": lambda sub: "C(year)+C(country_code)+d_log_gdp_per_capita+energy_shock_exposure",
    "S5 country FE + year FE + GDPpc2013 x year FE": lambda sub: "C(year)+C(country_code)+d_log_gdp_per_capita+energy_shock_exposure+gdp13:C(year)",
}
ALLSPECS = {**SPECS, **SPECS_FE}
SAMPLES = {"all": d, "EU15": d[d.eu15 == 1], "ACC2004+": d[d.eu15 == 0]}


def rows_for(sub, z):
    """Complete cases: both outcomes, DII, controls, instrument -> same rows for VA and emissions, OLS/FS/RF/IV."""
    need = [Y_VA, Y_EM, DII, "d_log_gdp_per_capita", "energy_shock_exposure", "gdp13", z]
    return sub.dropna(subset=need)

# ---------------------------------------------------------------- C. first stages: all candidates
cands = [c for c in d.columns if c.startswith("Z_")]
fs_rows = []
for z in cands:
    for sname, samp in SAMPLES.items():
        for spec, ff in {**SPECS, **(SPECS_FE if sname == "all" else {})}.items():
            sub = rows_for(samp, z)
            if sub.country_code.nunique() < 8:
                continue
            y, D, Z, W, g, dd = design(sub, Y_VA, DII, [z], ff(sname))
            f = first_stage(y, D, Z, W, g)
            fs_rows.append(dict(instrument=z, sample=sname, spec=spec, n=f["n"], G=f["G"], F_cluster=f["F"],
                                p_F=f["p_F"], partial_R2=f["partial_R2"], fs_coef=f["coef"][0], fs_se=f["se"][0], k=f["k"], cr1_reliable=f["reliable"]))
fs = pd.DataFrame(fs_rows)
fs.to_csv(OUT / "phase_e_first_stage_all_candidates.csv", index=False)
print("\n=== FIRST STAGE F (cluster-robust CR1, F(1,G-1) reference; single instrument => KP rk-F equals this) ===")
print(fs.pivot_table(index="instrument", columns=["sample", "spec"], values="F_cluster").round(1).to_string())
print("\nCells with k > G (CR1 covariance rank-deficient -> F optimistic, UNRELIABLE):")
print(fs[~fs.cr1_reliable][["sample", "spec", "n", "G", "k"]].drop_duplicates(["sample", "spec"]).to_string(index=False))
print("\nSample sizes (n, G) per candidate, full sample:")
print(fs[(fs["sample"] == "all") & fs.spec.str.startswith("S1")][["instrument", "n", "G", "partial_R2", "fs_coef"]].round(3).to_string(index=False))

# ---------------------------------------------------------------- D. PRE-DECLARED GATE
# A candidate proceeds to a headline second stage only if F_cluster >= 10 in the development-robust spec S3
# (GDPpc-2013 x year FE + Phase-D controls) in the full sample AND in EU-15 alone.
gate = fs[fs.spec.str.startswith("S3")].pivot_table(index="instrument", columns="sample", values="F_cluster")
gate["pass_gate"] = (gate["all"] >= 10) & (gate["EU15"] >= 10)   # NB EU15/S3 has k>G: even a "pass" there would be unreliable
print("\n=== GATE: F>=10 in S3 for BOTH full sample and EU-15 ===")
print(gate.round(1).to_string())
gate.to_csv(OUT / "phase_e_gate.csv")
n_pass = int(gate.pass_gate.sum())
print("Candidates passing gate:", n_pass, "of", len(gate))

# ---------------------------------------------------------------- first-stage wild-cluster bootstrap p for PRIM (robust to k>G)
PRIM = "Z_NGAxFTTP"   # highest S1 F among predetermined-baseline candidates (selected ON F => optimistic)
wrows = []
for sname, samp in SAMPLES.items():
    for spec, ff in {**SPECS, **(SPECS_FE if sname == "all" else {})}.items():
        sub = rows_for(samp, PRIM)
        y, D, Z, W, g, dd = design(sub, Y_VA, DII, [PRIM], ff(sname))
        f = first_stage(y, D, Z, W, g)
        pw = wild_p_restricted(D, np.column_stack([Z, W]), g, 0, NB, SEED + 7)
        wrows.append(dict(sample=sname, spec=spec, n=f["n"], G=f["G"], k=f["k"], F_CR1=f["F"], p_CR1=f["p_F"],
                          p_wild_first_stage=pw, cr1_reliable=f["reliable"]))
wfs = pd.DataFrame(wrows)
wfs.to_csv(OUT / "phase_e_first_stage_wild_bootstrap.csv", index=False)
print("\n=== First-stage inference for", PRIM, ": CR1 F vs wild-cluster bootstrap p (same coefficient) ===")
print(wfs.round(4).to_string(index=False))

# ---------------------------------------------------------------- E. exclusion diagnostics
cs = d[d.year == 2013].drop_duplicates("country_code").set_index("country_code")
cs = cs[cs.index.isin(d[d[DII].notna()].country_code.unique())]
diag = []
for b in ["b_NGA", "b_DOCSIS", "b_VDSL", "b_G100"]:
    x = cs[[b, "gdp13", "eu15"]].dropna()
    m1 = sm.OLS(x[b], sm.add_constant(x[["gdp13"]])).fit()
    m2 = sm.OLS(x[b], sm.add_constant(x[["gdp13", "eu15"]])).fit()
    diag.append(dict(baseline=b, n=len(x), corr_gdp13=x[b].corr(x["gdp13"]), R2_on_gdp13=m1.rsquared,
                     R2_on_gdp13_eu15=m2.rsquared, mean_EU15=x[x.eu15 == 1][b].mean(), mean_ACC=x[x.eu15 == 0][b].mean()))
diag = pd.DataFrame(diag)
print("\n=== E1: baseline (2013) coverage vs development level (cross-section of sample countries) ===")
print(diag.round(2).to_string())
diag.to_csv(OUT / "phase_e_baseline_vs_development.csv", index=False)

# E2 pre-period falsification: baseline coverage vs 2006-13 mean industrial VA growth (before DII exists)
va = pd.read_csv(RAW / "eurostat" / "industry_value_added_absolute.csv").rename(columns={"geo": "country_code", "time": "year", "value": "va"})
va = va.sort_values(["country_code", "year"]); va["lv"] = np.log(va.va.clip(lower=1)); va["dv"] = contiguous_diff(va, "lv")
prev = va[(va.year >= 2006) & (va.year <= 2013)].groupby("country_code").dv.agg(lambda x: x.mean() if x.count() >= 6 else np.nan)
cs["pre_va_growth_0613"] = prev.reindex(cs.index)
pre_rows = []
for b in ["b_NGA", "b_G100"]:
    x = cs[[b, "pre_va_growth_0613", "gdp13", "eu15"]].dropna()
    for nm, cols in [("bare", [b]), ("+eu15", [b, "eu15"]), ("+gdp13", [b, "gdp13"])]:
        m = sm.OLS(x["pre_va_growth_0613"], sm.add_constant(x[cols])).fit(cov_type="HC3")
        pre_rows.append(dict(baseline=b, spec=nm, n=len(x), coef_per_100pp=m.params[b] * 100, t_HC3=m.tvalues[b], p=m.pvalues[b]))
pre_df = pd.DataFrame(pre_rows)
print("\n=== E2: baseline coverage vs PRE-PERIOD (2006-13 mean) industrial VA growth (cross-country, HC3) ===")
print(pre_df.round(3).to_string())
pre_df.to_csv(OUT / "phase_e_preperiod_falsification.csv", index=False)

# ---------------------------------------------------------------- F. diagnostic-only 2SLS for PRIM (gate decides; NOT a headline)
def block(sname, z, spec, label):
    sub = rows_for(SAMPLES[sname], z)
    out = []
    ff = ALLSPECS[spec](sname)
    for yv in [Y_VA, Y_EM]:
        y, D, Z, W, g, dd = design(sub, yv, DII, [z], ff)
        Xo = np.column_stack([D, W])
        bo, so, G = ols_cr(y, Xo, g, 0)
        f = first_stage(y, D, Z, W, g)
        Xr = np.column_stack([Z, W])
        brf, srf, _ = ols_cr(y, Xr, g, 0)
        bi, si, _ = tsls(y, D, Z, W, g)
        pw_ols = wild_p_restricted(y, Xo, g, 0, NB, SEED)
        pw_rf = wild_p_restricted(y, Xr, g, 0, NB, SEED + 1)
        grid = list(np.round(np.arange(-3, 3.0001, 0.01), 3))
        kind, lo, hi = ar_ci(y, D, Z, W, g, grid)
        out.append(dict(label=label, outcome=yv, sample=sname, spec=spec, instrument=z, n=len(y), G=G,
                        FS_F=f["F"], FS_pR2=f["partial_R2"], k=f["k"], CR1_reliable=f["reliable"],
                        OLS=bo, OLS_se=so, OLS_p_t=2 * (1 - st.t.cdf(abs(bo / so), G - 1)), OLS_p_wild=pw_ols,
                        RF=brf, RF_se=srf, RF_p_t=2 * (1 - st.t.cdf(abs(brf / srf), G - 1)), RF_p_wild=pw_rf,
                        IV=bi, IV_se=si, IV_p_t=2 * (1 - st.t.cdf(abs(bi / si), G - 1)),
                        AR95_kind=kind, AR95_lo=lo, AR95_hi=hi))
    return out

diag_rows = []
if n_pass == 0:
    print("\nGATE FAILED for every candidate -> NO headline second stage. Diagnostic-only blocks for the highest-F "
          "candidate follow, to document WHY exclusion fails (RF, IV, AR set). These are not results.")
for sname in ["all", "EU15", "ACC2004+"]:
    for spec in (ALLSPECS if sname == "all" else SPECS):
        diag_rows += block(sname, PRIM, spec, "DIAGNOSTIC-ONLY (gate failed)" if n_pass == 0 else "candidate")
dg = pd.DataFrame(diag_rows)
dg.to_csv(OUT / "phase_e_diagnostic_2sls.csv", index=False)
print("\n=== DIAGNOSTIC-ONLY: OLS / reduced form / IV for", PRIM, "(AR grid beta in [-3,3], step .01; ref F(1,G-1)) ===")
# IV_p_t is saved in the csv but deliberately not shown: Wald IV t is unreliable at these F/G
show = ["outcome", "sample", "spec", "n", "G", "k", "CR1_reliable", "FS_F", "OLS", "OLS_p_wild", "RF", "RF_p_wild", "IV", "AR95_kind", "AR95_lo", "AR95_hi"]
print(dg[show].round(3).to_string())

# ---------------------------------------------------------------- G. leave-one-country-out first stage of PRIM
loo = []
sub = rows_for(d, PRIM)
for c in sorted(sub.country_code.unique()):
    ss_ = sub[sub.country_code != c]
    for spec in ["S1 Phase-D controls", "S3 +GDPpc2013 x year FE"]:
        y, D, Z, W, g, dd = design(ss_, Y_VA, DII, [PRIM], SPECS[spec]("all"))
        f = first_stage(y, D, Z, W, g)
        brf, srf, _ = ols_cr(y, np.column_stack([Z, W]), g, 0)
        loo.append(dict(dropped=c, spec=spec, F=f["F"], fs_coef=f["coef"][0], RF_va=brf, RF_t=brf / srf))
loo = pd.DataFrame(loo)
loo.to_csv(OUT / "phase_e_leave_one_out_first_stage.csv", index=False)
print("\n=== Leave-one-country-out, first stage of", PRIM, "===")
print(loo.groupby("spec").agg(F_min=("F", "min"), F_med=("F", "median"), F_max=("F", "max"),
                               RFt_min=("RF_t", "min"), RFt_max=("RF_t", "max")).round(2).to_string())
for spec in loo.spec.unique():
    x = loo[loo.spec == spec].sort_values("F")
    print(spec, "| lowest-F drops:", list(zip(x.dropped.head(3), x.F.head(3).round(1))), "| highest:", list(zip(x.dropped.tail(2), x.F.tail(2).round(1))))

# ---------------------------------------------------------------- H. OLS reference
sub = rows_for(d, PRIM)
for yv in [Y_VA, Y_EM]:
    y, D, Z, W, g, dd = design(sub, yv, DII, [PRIM], CTRL)
    b, se, G = ols_cr(y, np.column_stack([D, W]), g, 0)
    print(f"OLS reference {yv}: coef={b:+.4f} se={se:.4f} n={len(y)} G={G} (Phase D G5 for VA: +0.0728 on its own n=257 sample)")

# ---------------------------------------------------------------- I. leave-one-out within EU-15 (the only sample where PRIM survives development controls)
loo15 = []
sub15 = rows_for(SAMPLES["EU15"], PRIM)
for c in sorted(sub15.country_code.unique()):
    ss_ = sub15[sub15.country_code != c]
    for spec in ["S1 Phase-D controls", "S3 +GDPpc2013 x year FE"]:
        y, D, Z, W, g, dd = design(ss_, Y_VA, DII, [PRIM], SPECS[spec]("EU15"))
        f = first_stage(y, D, Z, W, g)
        bi, si, G_ = tsls(y, D, Z, W, g)
        loo15.append(dict(dropped=c, spec=spec, F=f["F"], IV_va=bi, IV_se=si))
loo15 = pd.DataFrame(loo15)
loo15.to_csv(OUT / "phase_e_leave_one_out_eu15.csv", index=False)
print("\n=== Leave-one-out WITHIN EU-15 (first stage F and just-identified IV for VA growth) ===")
print(loo15.groupby("spec").agg(F_min=("F", "min"), F_med=("F", "median"), F_max=("F", "max"), IV_min=("IV_va", "min"), IV_max=("IV_va", "max")).round(3).to_string())
for spec in loo15.spec.unique():
    x = loo15[loo15.spec == spec].sort_values("F")
    print(spec, "| lowest-F drops:", list(zip(x.dropped.head(3), x.F.head(3).round(1))))
