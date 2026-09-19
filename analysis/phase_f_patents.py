"""Phase F: predetermined patent-stock design for the digitalization -> industrial-growth
question, plus a descriptive country-level look at verified EU-ETS emissions.

Reproduce (needs data/raw/eurostat/{patents_*,regional_*,national_gva_nac}.csv and data/raw/geo/*):
    python scripts/download_eurostat_patents.py
    python scripts/download_eurostat_regional_gva.py
    python analysis/phase_f_patents.py | tee analysis/output/phase_f_log.txt

See analysis/phase_f_patents.md for the write-up. Inference for every claim-carrying number:
country-clustered CR1 SE, t(G-1) p-value and wild cluster bootstrap-t (Rademacher, null imposed,
fixed seeds; full enumeration when G <= 12). Naive z p-values are printed only for comparison.
"""
import sys
import itertools
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phase_f_build import ES, OUT, ROOT, EU27, EU15, ACC, BASE_YEAR, load_patents, stock  # noqa: E402
from phase_f_build_units import build_units  # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 40)
SEED = 20260919
NB = 4999          # bootstrap draws (non-headline)
NB_HEAD = 9999     # headline

# =====================================================================================
# 0. Inference machinery
# =====================================================================================


def within(a, groups):
    a = np.asarray(a, float)
    out = a.copy()
    for g in np.unique(groups):
        m = groups == g
        out[m] = a[m] - a[m].mean(axis=0)
    return out


def cr1(X, u, gidx, G):
    n, k = X.shape
    bread = np.linalg.inv(X.T @ X)
    S = np.zeros((G, k))
    np.add.at(S, gidx, X * u[:, None])
    meat = S.T @ S
    dfc = (G / (G - 1)) * ((n - 1) / (n - k))
    return dfc * bread @ meat @ bread


def wild_p(y, X, gidx, G, t_idx, t_obs, B, seed, webb=False):
    """Wild cluster bootstrap-t, restricted (null imposed), Rademacher weights."""
    n, k = X.shape
    Xr = np.delete(X, t_idx, axis=1)
    if Xr.shape[1] > 0:
        br = np.linalg.lstsq(Xr, y, rcond=None)[0]
        fit = Xr @ br
    else:
        fit = np.zeros(n)
    res = y - fit
    P = np.linalg.solve(X.T @ X, X.T)          # k x n
    bread = np.linalg.inv(X.T @ X)
    dfc = (G / (G - 1)) * ((n - 1) / (n - k))
    if webb:   # Webb 6-point weights (better behaved than Rademacher when G is small / clusters unbalanced)
        vals = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])
        W = np.random.default_rng(seed + 7).choice(vals, size=(B, G))
    elif G <= 12:
        W = np.array(list(itertools.product([-1.0, 1.0], repeat=G)))
    else:
        W = np.random.default_rng(seed).choice([-1.0, 1.0], size=(B, G))
    tb = np.empty(len(W))
    order = np.argsort(gidx, kind="stable")
    gs = gidx[order]
    starts = np.r_[0, np.flatnonzero(np.diff(gs)) + 1]
    Xo = X[order]
    for i0 in range(0, len(W), 1000):
        Wc = W[i0:i0 + 1000]
        Ys = fit[None, :] + res[None, :] * Wc[:, gidx]         # b x n
        beta = Ys @ P.T                                         # b x k
        U = Ys - beta @ X.T
        Uo = U[:, order]
        S = np.stack([np.add.reduceat(Uo * Xo[:, j][None, :], starts, axis=1) for j in range(k)], axis=2)  # b x G x k
        meat = np.einsum("bgk,bgl->bkl", S, S)
        V = dfc * np.einsum("ik,bkl,lj->bij", bread, meat, bread)
        tb[i0:i0 + 1000] = beta[:, t_idx] / np.sqrt(V[:, t_idx, t_idx])
    return float(np.mean(np.abs(tb) >= np.abs(t_obs) - 1e-12)), len(W)


def reg(df, y, xs, target, fe=True, cluster="country", B=NB, seed_tag=0, boot=True, equal_country_weight=False):
    """OLS with optional country FE (within transform; countries with a single unit dropped).
    Returns dict with coef, cluster SE, t, p_z (naive), p_t(G-1), p_wild, n, G."""
    d = df[[y] + xs + [cluster]].dropna().copy()
    if fe:
        cnt = d.groupby(cluster)[y].transform("size")
        d = d[cnt >= 2]
    groups = d[cluster].to_numpy()
    yy = d[y].to_numpy(float)
    XX = d[xs].to_numpy(float)
    if fe:
        yy = within(yy, groups)
        XX = within(XX, groups)
    else:
        XX = np.column_stack([np.ones(len(d)), XX])
    if equal_country_weight:   # weights constant within country -> weighted within-transform == plain demeaning
        cnt_c = pd.Series(groups).map(pd.Series(groups).value_counts()).to_numpy(float)
        sw = np.sqrt(1.0 / cnt_c)
        yy = yy * sw
        XX = XX * sw[:, None]
    names = (["const"] if not fe else []) + xs
    t_idx = names.index(target)
    uq, gidx = np.unique(groups, return_inverse=True)
    G = len(uq)
    n = len(d)
    beta = np.linalg.lstsq(XX, yy, rcond=None)[0]
    u = yy - XX @ beta
    V = cr1(XX, u, gidx, G)
    se = float(np.sqrt(V[t_idx, t_idx]))
    t = float(beta[t_idx] / se)
    # effective number of clusters for the target coefficient (Carter et al. 2017 spirit):
    # w_g = share of cluster g in the target's leverage (x~'x~) and in the score variance (S_g^2)
    xt = XX[:, t_idx]
    Zo = np.delete(XX, t_idx, axis=1)
    xt = xt - Zo @ np.linalg.lstsq(Zo, xt, rcond=None)[0] if Zo.shape[1] else xt
    lev = np.bincount(gidx, weights=xt ** 2, minlength=G)
    sc = np.bincount(gidx, weights=xt * u, minlength=G) ** 2
    lev_w, sc_w = lev / lev.sum(), sc / sc.sum()
    out = dict(y=y, target=target, n=n, G=G, G_eff_leverage=float(1 / (lev_w ** 2).sum()),
               G_eff_score=float(1 / (sc_w ** 2).sum()), top_cluster=str(uq[int(sc_w.argmax())]),
               top_cluster_score_share=float(sc_w.max()),
               mde_80=float((stats.t.ppf(.975, G - 1) + 0.8416) * se), coef=float(beta[t_idx]), se=se, t=t,
               p_naive_z=float(2 * (1 - stats.norm.cdf(abs(t)))),
               p_t_Gm1=float(2 * (1 - stats.t.cdf(abs(t), G - 1))),
               ci_lo=float(beta[t_idx] - stats.t.ppf(.975, G - 1) * se),
               ci_hi=float(beta[t_idx] + stats.t.ppf(.975, G - 1) * se),
               sd_within_x=float(XX[:, t_idx].std(ddof=0)))
    if boot and G >= 5:
        out["p_wild"], out["n_wild_draws"] = wild_p(yy, XX, gidx, G, t_idx, t, B, SEED + seed_tag)
        out["p_webb"] = wild_p(yy, XX, gidx, G, t_idx, t, B, SEED + seed_tag, webb=True)[0]
    else:
        out["p_wild"], out["n_wild_draws"], out["p_webb"] = np.nan, 0, np.nan
    return out


RESULTS = []


def run(tag, sample, df, y, xs, target, **kw):
    r = reg(df, y, xs, target, **kw)
    r.update(tag=tag, sample=sample, xs="+".join(xs))
    RESULTS.append(r)
    pw = f"{r['p_wild']:.3f}" if not np.isnan(r["p_wild"]) else "  n/a"
    print(f"  {tag:58s} n={r['n']:4d} G={r['G']:2d} b={r['coef']:+.3f} se={r['se']:.3f} "
          f"p_z={r['p_naive_z']:.3f} p_t={r['p_t_Gm1']:.3f} p_wild={pw} p_webb={r['p_webb']:.3f} "
          f"G*={r['G_eff_score']:.1f}/{r['G_eff_leverage']:.1f} top={r['top_cluster']}({r['top_cluster_score_share']:.2f})")
    return r


# =====================================================================================
# 1. Variable construction
# =====================================================================================


def xvar(U, series, delta="d15", norm="pop", tr="asinh", prefix="S"):
    S = U[f"{prefix}_{series}_{delta}"]
    den = {"pop": U.pop04 / 1e3, "emp": U.emp04 / 1e3, "gva": U.gva_tot04_eur / 1e3}[norm]   # -> per million
    v = S / den
    return np.arcsinh(v) if tr == "asinh" else np.log1p(v)


def add_vars(U):
    U = U.copy()
    for sname, ser in [("dig", "dig_core"), ("nondig", "nondig"), ("total", "total"), ("digb", "dig_broad"),
                       ("nondigb", "nondig_broad"), ("mechchem", "mech_chem")]:
        U[f"x_{sname}"] = xvar(U, ser)
    U["x_tilt"] = U.x_dig - U.x_nondig     # digital minus non-digital
    U["x_sum"] = U.x_dig + U.x_nondig
    U["acc"] = (U.group == "ACC").astype(float)
    U["x_dig_acc"] = U.x_dig * U.acc
    U["x_nondig_acc"] = U.x_nondig * U.acc
    return U


CTRL = ["ln_gvapc04", "ind_share04"]


def qc_units(name, U, qc):
    print(f"\n--- QC {name} ---")
    print({k: v for k, v in qc.items() if k not in ("mapping", "stability_table")})
    e = U[U.group != "OTHER"]
    print("units by country (EU27):", e.groupby("country").size().to_dict())
    print("non-EU27 units present in raw build (dropped from analysis):", sorted(set(U[U.group == "OTHER"].country)))
    print("EU27 countries with no unit:", sorted(EU27 - set(e.country)))
    for c in ["S_dig_core_d15", "S_nondig_d15", "S_total_d15"]:
        z = (e[c] == 0).mean()
        print(f"  share of units with ZERO {c}: {z:.3f}")
    print(f"  corr(x_dig, x_nondig) = {e[['x_dig','x_nondig']].corr().iloc[0,1]:.3f}")
    print(f"  missing outcome g_ind: {e.g_ind.isna().sum()} of {len(e)};  missing controls: {e[CTRL].isna().any(axis=1).sum()}")


# =====================================================================================
# 2. Patent-panel QC (global)
# =====================================================================================


def patent_qc():
    print("\n" + "=" * 100 + "\nSECTION 1: PATENT PANEL QC\n" + "=" * 100)
    tot = pd.read_csv(ES / "patents_regional_total.csv")
    ipc = pd.read_csv(ES / "patents_regional_ipc.csv")
    geos = pd.read_csv(ES / "patents_geo_list.csv")
    print(f"geo dimension: {len(geos)} codes; NUTS3-length {int((geos.geo.str.len()==5).sum())}; "
          f"unallocated codes (ZZ/XX): {int(geos.geo.map(lambda g: len(g)==5 and set(g[2:])<={'Z'} or set(g[2:])<={'X'}).sum())}")
    t3 = tot[tot.geo.str.len() == 5]
    unall = t3.geo.map(lambda g: set(g[2:]) <= {"Z"} or set(g[2:]) <= {"X"})
    for y in [1990, 2000, 2004, 2008, 2012]:
        a = t3[t3.time == y]
        ua = unall[a.index]
        ctry = tot[(tot.geo.str.len() == 2) & (tot.time == y) & tot.geo.isin(EU27 | {"UK"})].value.sum()
        print(f"  {y}: EPO applications, NUTS3 rows all countries {a.value.sum():9.0f}; "
              f"unallocated (ZZ/XX) {a[ua].value.sum():7.0f}; EU27+UK country-total rows {ctry:9.0f}")
    print("  NOTE: 2011-2012 totals fall (49.7k in 2012 vs 59k in 2004): late-publication truncation; "
          "the baseline stock ends in 2004 so it is unaffected, the 2005-2012 PLACEBO stock is.")
    # IPC consistency: sections add up to the total => counting across classes is fractional, no double counting
    x = ipc[(ipc.time == 2004) & (ipc.geo.str.len() == 5)].pivot_table(index="geo", columns="ipc", values="value")
    secs = x[list("ABCDEFGH")].sum().sum()
    print(f"  IPC check 2004 NUTS3: sum of sections A-H = {secs:.0f} vs IPC total = {x['IPC'].sum():.0f} "
          f"(ratio {secs / x['IPC'].sum():.3f}) -> class counts are fractional; digital+non-digital = total by construction")
    d = x[["G06", "G11", "H03", "H04"]].sum().sum()
    print(f"  digital core (G06+G11+H03+H04) 2004 = {d:.0f} = {100*d/x['IPC'].sum():.1f}% of all EPO applications")
    P = load_patents()
    neg = (P.total - P.dig_core < -1e-6).sum()
    print(f"  cells with digital core > total (would be negative non-digital): {int(neg)} (clipped at 0)")
    # zero shares at NUTS3 for a cell-year and for the stock
    print(f"  NUTS3 x year cells with zero total patents: {100*(P.total==0).mean():.1f}%")
    yr = P[P.time.between(1990, 2004)].groupby("time")[["dig_core", "total"]].sum()
    print("  digital core share of all patents (pooled, all NUTS3): 1990 %.3f  1997 %.3f  2004 %.3f" % (
        yr.loc[1990].dig_core / yr.loc[1990].total, yr.loc[1997].dig_core / yr.loc[1997].total,
        yr.loc[2004].dig_core / yr.loc[2004].total))


# =====================================================================================
# 3. Main regional analysis for one sample
# =====================================================================================


def regional_block(name, U, headline=False, seed_base=0):
    print("\n" + "=" * 100 + f"\nSECTION: REGIONAL RESULTS -- {name}\n" + "=" * 100)
    E = add_vars(U[U.group != "OTHER"])
    need = ["g_ind", "g_ind_real"] + CTRL + ["x_dig", "x_nondig", "x_total", "x_tilt", "x_sum", "x_mechchem",
                                            "x_digb", "x_nondigb", "acc"]
    S = E.dropna(subset=need).copy()
    cnt = S.groupby("country").size()
    dropped = cnt[cnt < 2].index.tolist()
    S = S[~S.country.isin(dropped)]
    print(f"  IDENTICAL analysis sample: {len(S)} units, {S.country.nunique()} countries "
          f"(EU15 {S[S.group=='EU15'].country.nunique()}, accession {S[S.group=='ACC'].country.nunique()}); "
          f"single-unit countries dropped: {dropped}")
    print("  units per country:", S.groupby("country").size().to_dict())
    S.to_csv(OUT / f"phase_f_sample_{name}.csv", index=False)
    B = NB_HEAD if headline else NB
    sb = seed_base
    print(" [A] country-FE regressions, y = industrial (B-E) GVA growth 2005-2019, %/yr")
    run("A1 FE: dig only", name, S, "g_ind", ["x_dig"], "x_dig", seed_tag=sb + 1, B=B)
    run("A2 FE: dig + controls", name, S, "g_ind", ["x_dig"] + CTRL, "x_dig", seed_tag=sb + 2, B=B)
    claim = run("A3 FE: dig + nondig + controls  [CLAIM]", name, S, "g_ind", ["x_dig", "x_nondig"] + CTRL, "x_dig",
                seed_tag=sb + 3, B=NB_HEAD)
    run("A3b FE: same, target = NON-digital", name, S, "g_ind", ["x_dig", "x_nondig"] + CTRL, "x_nondig", seed_tag=sb + 4, B=B)
    run("A4 FE: total patents + controls", name, S, "g_ind", ["x_total"] + CTRL, "x_total", seed_tag=sb + 5, B=B)
    run("A5 FE: tilt (dig-nondig) + sum + controls", name, S, "g_ind", ["x_tilt", "x_sum"] + CTRL, "x_tilt", seed_tag=sb + 6, B=B)
    print(" [A-w] same FE regressions, EQUAL total weight per country (limits Germany/France/Italy dominance)")
    run("Aw2 FE equal-country-weight: dig + controls", name, S, "g_ind", ["x_dig"] + CTRL, "x_dig", seed_tag=sb + 13, B=B, equal_country_weight=True)
    run("Aw3 FE equal-country-weight: dig + nondig + controls", name, S, "g_ind", ["x_dig", "x_nondig"] + CTRL, "x_dig", seed_tag=sb + 14, B=B, equal_country_weight=True)
    run("Aw4 FE equal-country-weight: total patents + controls", name, S, "g_ind", ["x_total"] + CTRL, "x_total", seed_tag=sb + 15, B=B, equal_country_weight=True)
    print(" [B] pooled (NO country FE), y = growth minus national B-E deflator")
    run("B1 pooled: dig + controls", name, S, "g_ind_real", ["x_dig"] + CTRL, "x_dig", fe=False, seed_tag=sb + 7, B=B)
    run("B2 pooled: dig + nondig + controls", name, S, "g_ind_real", ["x_dig", "x_nondig"] + CTRL, "x_dig", fe=False, seed_tag=sb + 8, B=B)
    run("B3 pooled: + accession dummy", name, S, "g_ind_real", ["x_dig", "x_nondig", "acc"] + CTRL, "x_dig", fe=False, seed_tag=sb + 9, B=B)
    print(" [C] accession split of the claim regression (own country FE in each subsample)")
    for gname in ["EU15", "ACC"]:
        sub = S[S.group == gname]
        run(f"C {gname} only: dig + nondig + controls", name, sub, "g_ind", ["x_dig", "x_nondig"] + CTRL, "x_dig", seed_tag=sb + 10, B=B)
    run("C interaction: dig x ACC (own-group slopes for dig & nondig)", name, S, "g_ind",
        ["x_dig", "x_dig_acc", "x_nondig", "x_nondig_acc"] + CTRL, "x_dig_acc", seed_tag=sb + 12, B=B)
    print(" [D] robustness of the claim regression (same sample S, same y unless noted)")
    Sx = S.copy()
    for dl in ["d10", "d20", "cum"]:
        Sx["xd"] = xvar(Sx, "dig_core", dl)
        Sx["xn"] = xvar(Sx, "nondig", dl)
        run(f"D depreciation {dl}", name, Sx, "g_ind", ["xd", "xn"] + CTRL, "xd", seed_tag=sb + 20, B=B)
    for nm in ["emp", "gva"]:
        Sx["xd"] = xvar(Sx, "dig_core", norm=nm)
        Sx["xn"] = xvar(Sx, "nondig", norm=nm)
        run(f"D normalised per {nm}", name, Sx, "g_ind", ["xd", "xn"] + CTRL, "xd", seed_tag=sb + 21, B=B)
    Sx["xd"] = xvar(Sx, "dig_core", tr="log1p")
    Sx["xn"] = xvar(Sx, "nondig", tr="log1p")
    run("D log1p instead of asinh", name, Sx, "g_ind", ["xd", "xn"] + CTRL, "xd", seed_tag=sb + 22, B=B)
    run("D broad digital (+H01,G05,G08,G09) vs matching non-digital", name, S, "g_ind", ["x_digb", "x_nondigb"] + CTRL, "x_digb", seed_tag=sb + 23, B=B)
    run("D comparison field = mech/chem (B,C,F sections) instead of non-digital", name, S, "g_ind", ["x_dig", "x_mechchem"] + CTRL, "x_dig", seed_tag=sb + 24, B=B)
    Sx["ln_pop"] = S.ln_pop04
    run("D + ln population control", name, S, "g_ind", ["x_dig", "x_nondig", "ln_pop04"] + CTRL, "x_dig", seed_tag=sb + 25, B=B)
    for yv, lab in [("g_ind_smooth", "3-yr endpoint averages"), ("g_man", "manufacturing (C) growth"),
                    ("g_tot", "TOTAL-economy GVA growth (specificity check)"), ("g_ind_0512", "growth 2005-2012 only"),
                    ("g_ind_1219", "growth 2012-2019 only")]:
        run(f"D outcome: {lab}", name, S, yv, ["x_dig", "x_nondig"] + CTRL, "x_dig", seed_tag=sb + 26, B=B)
    return S, claim


def loo(name, S, xs=("x_dig", "x_nondig"), target="x_dig", label="A3"):
    print(f"\n--- Leave-one-country-out on {label}: {'+'.join(xs)}, target {target} -- {name} ---")
    rows = []
    for c in sorted(S.country.unique()):
        sub = S[S.country != c]
        r = reg(sub, "g_ind", list(xs) + CTRL, target, B=NB, seed_tag=900)
        r.update(dropped=c, n_dropped_units=int((S.country == c).sum()))
        rows.append(r)
    L = pd.DataFrame(rows)[["dropped", "n_dropped_units", "n", "G", "coef", "se", "p_t_Gm1", "p_wild"]]
    print(L.round(4).to_string(index=False))
    print(f"  coef range [{L.coef.min():+.3f}, {L.coef.max():+.3f}]; p_wild<0.05 in {(L.p_wild<0.05).sum()}/{len(L)} runs; "
          f"p_t<0.05 in {(L.p_t_Gm1<0.05).sum()}/{len(L)} runs")
    L["sample"] = name
    L["regression"] = label
    return L


def placebo(name, U):
    print("\n" + "=" * 100 + f"\nSECTION: FALSIFICATION / PLACEBO -- {name}\n" + "=" * 100)
    E = U[U.group != "OTHER"].copy()
    for sname, ser in [("dig", "dig_core"), ("nondig", "nondig")]:
        E[f"x99_{sname}"] = xvar(E, ser, prefix="S99")
        E[f"xP_{sname}"] = xvar(E, ser, delta="d15", prefix="SP")
        E[f"x04_{sname}"] = xvar(E, ser)
    P0 = ["ln_gvapc00", "ind_share00"]
    need = ["g_ind_0004"] + P0 + ["x99_dig", "x99_nondig", "xP_dig", "xP_nondig", "x04_dig", "x04_nondig"]
    S = E.dropna(subset=need)
    cnt = S.groupby("country").size()
    S = S[S.country.map(cnt) >= 2]
    print(f"  placebo sample (identical across P-specs): {len(S)} units, {S.country.nunique()} countries")
    print(f"  corr(stock through 1999, stock 2005-12 flow) digital: {S[['x99_dig','xP_dig']].corr().iloc[0,1]:.3f}; "
          f"non-digital: {S[['x99_nondig','xP_nondig']].corr().iloc[0,1]:.3f}")
    print("  y = industrial GVA growth 2000-2004 (4 yrs only -> noisy; nominal, FE absorbs the national deflator)")
    run("P0 FE: stock through 1999 (predetermined for 2000-04): dig", name, S, "g_ind_0004", ["x99_dig", "x99_nondig"] + P0, "x99_dig", seed_tag=1001)
    run("P1 FE: stock 2005-12 ONLY (future) : dig  [PLACEBO]", name, S, "g_ind_0004", ["xP_dig", "xP_nondig"] + P0, "xP_dig", seed_tag=1002)
    run("P2 FE: both windows in one model: dig(1999 stock)", name, S, "g_ind_0004", ["x99_dig", "xP_dig", "x99_nondig", "xP_nondig"] + P0, "x99_dig", seed_tag=1003)
    run("P2 FE: both windows in one model: dig(2005-12 flow)", name, S, "g_ind_0004", ["x99_dig", "xP_dig", "x99_nondig", "xP_nondig"] + P0, "xP_dig", seed_tag=1004)
    run("P3 FE: stock through 2004 (baseline of main design) on 2000-04 growth [overlaps]", name, S, "g_ind_0004", ["x04_dig", "x04_nondig"] + P0, "x04_dig", seed_tag=1005)
    run("P4 FE: total-economy growth 2000-04 on stock through 1999", name, S, "g_tot_0004", ["x99_dig", "x99_nondig"] + P0, "x99_dig", seed_tag=1006)
    return S


# =====================================================================================
# 4. Country-level ETS (descriptive)
# =====================================================================================


def ets_block():
    print("\n" + "=" * 100 + "\nSECTION: COUNTRY-LEVEL VERIFIED EU-ETS EMISSIONS (descriptive, N~22)\n" + "=" * 100)
    eu = pd.read_csv(ROOT / "data/raw/eu_ets/eu-ets.csv")
    eu = eu[(eu.citl_information == "2. Verified emissions") & (eu.main_activity_code.astype(str) == "20-99")]
    eu = eu[eu.year.astype(str).str.fullmatch(r"\d{4}")].copy()
    eu["year"] = eu.year.astype(int)
    eu["country"] = eu.country_code.replace({"GR": "EL", "GB": "UK"})
    E = eu.pivot_table(index="country", columns="year", values="value", aggfunc="sum")
    # patents: country-total rows (include unallocated regions) -> stock through 2004, delta 15%
    ipc = pd.read_csv(ES / "patents_regional_ipc.csv")
    ipc = ipc[ipc.geo.str.len() == 2]
    w = ipc.pivot_table(index=["geo", "time"], columns="ipc", values="value", aggfunc="sum")
    idx = pd.MultiIndex.from_product([sorted(set(ipc.geo)), range(1977, 2013)], names=["geo", "time"])
    w = w.reindex(idx).fillna(0.0)
    cp = pd.DataFrame({"total": w["IPC"], "dig_core": w[["G06", "G11", "H03", "H04"]].sum(axis=1)})
    cp["nondig"] = (cp.total - cp.dig_core).clip(lower=0)
    cp = cp.reset_index()
    C = pd.DataFrame(index=sorted(set(ipc.geo)))
    for s in ["dig_core", "nondig", "total"]:
        C[s] = stock(cp, s, 0.15, 1977, BASE_YEAR)
    pop = pd.read_csv(ES / "regional_population_nuts3.csv")
    pop = pop[(pop.geo.str.len() == 2) & (pop.time == 2004)].set_index("geo").value
    C["pop"] = pop
    gdp = pd.read_csv(ES / "gdp_per_capita.csv")
    gdp = gdp[gdp.time == 2004].set_index("geo").value
    C["ln_gdppc"] = np.log(gdp)
    C["x_dig"] = np.arcsinh(C.dig_core / (C["pop"] / 1e3))
    C["x_nondig"] = np.arcsinh(C.nondig / (C["pop"] / 1e3))
    C["acc"] = [1.0 if c in ACC else 0.0 for c in C.index]
    C = C[C.index.isin(EU27 | {"UK"})]
    # ---- country-level analogue of the regional claim: national B-E real growth 2005-19 (CLV20, national currency)
    nat = pd.read_csv(ES / "national_gva_nac.csv")
    cl = nat[(nat.nace_r2 == "B-E") & (nat.unit == "CLV20_MNAC")].pivot(index="geo", columns="time", values="value")
    cpB = nat[(nat.nace_r2 == "B-E") & (nat.unit == "CP_MNAC")].pivot(index="geo", columns="time", values="value")
    cpT = nat[(nat.nace_r2 == "TOTAL") & (nat.unit == "CP_MNAC")].pivot(index="geo", columns="time", values="value")
    C["g_ind_nat"] = (100 * (np.log(cl[2019]) - np.log(cl[2005])) / 14).reindex(C.index)
    C["ind_share04"] = (cpB[2004] / cpT[2004]).reindex(C.index)
    print("\n  --- country-level analogue: national industrial (B-E) real GVA growth 2005-2019, %/yr, on predetermined stock ---")
    cs = C[C.index.isin(EU27)].dropna(subset=["g_ind_nat", "x_dig", "x_nondig", "ln_gdppc", "ind_share04"])
    print(f"   N={len(cs)} EU27 countries; excluded: {sorted(EU27 - set(cs.index))}")
    crow = []
    for lab, xs in [("dig only", ["x_dig"]), ("dig + controls", ["x_dig", "ln_gdppc", "ind_share04"]),
                    ("dig + nondig + controls", ["x_dig", "x_nondig", "ln_gdppc", "ind_share04"]),
                    ("dig + nondig + controls + ACC dummy", ["x_dig", "x_nondig", "ln_gdppc", "ind_share04", "acc"])]:
        X = np.column_stack([np.ones(len(cs)), cs[xs].to_numpy(float)])
        yv = cs.g_ind_nat.to_numpy(float)
        Xi = np.linalg.inv(X.T @ X)
        bh = Xi @ X.T @ yv
        uh = yv - X @ bh
        h = np.einsum("ij,jk,ik->i", X, Xi, X)
        Xu = X.T * (uh / (1 - h))
        Vh = Xi @ (Xu @ Xu.T) @ Xi
        se = np.sqrt(Vh[1, 1]); tt = bh[1] / se
        pv = 2 * (1 - stats.t.cdf(abs(tt), len(cs) - X.shape[1]))
        lo = [np.linalg.lstsq(X[np.arange(len(cs)) != i], yv[np.arange(len(cs)) != i], rcond=None)[0][1] for i in range(len(cs))]
        print(f"   {lab:40s} b_dig={bh[1]:+.3f} HC3 se={se:.3f} p(t,N-k)={pv:.3f}  LOO range [{min(lo):+.3f}, {max(lo):+.3f}]")
        crow.append(dict(spec=lab, n=len(cs), coef=bh[1], se_hc3=se, p=pv, loo_min=min(lo), loo_max=max(lo)))
    pd.DataFrame(crow).to_csv(OUT / "phase_f_country_growth.csv", index=False)
    out = []
    for end in [2019, 2023]:
        C[f"dlnE_{end}"] = 100 * np.log(E[end] / E[2005]).reindex(C.index)
        sub = C.dropna(subset=[f"dlnE_{end}", "x_dig", "x_nondig", "pop", "ln_gdppc"])
        print(f"\n  outcome: 100*ln(verified ETS emissions {end} / 2005); N={len(sub)}; "
              f"excluded (missing 2005 or {end} ETS data, or no patent/pop data): {sorted(set(C.index) - set(sub.index))}")
        print("   NOTE: ETS scope changed in 2013 (new sectors/gases) and 2021 (UK exit) -> levels are not like-for-like.")
        rho, prho = stats.spearmanr(sub.x_dig, sub[f"dlnE_{end}"])
        print(f"   Spearman(dig stock pc, emissions change) = {rho:+.2f} (p={prho:.3f})")
        for lab, xs in [("dig only", ["x_dig"]), ("dig + nondig", ["x_dig", "x_nondig"]),
                        ("dig + nondig + ln GDPpc + ACC dummy", ["x_dig", "x_nondig", "ln_gdppc", "acc"])]:
            X = np.column_stack([np.ones(len(sub)), sub[xs].to_numpy(float)])
            yv = sub[f"dlnE_{end}"].to_numpy(float)
            bh = np.linalg.lstsq(X, yv, rcond=None)[0]
            uh = yv - X @ bh
            H = X @ np.linalg.inv(X.T @ X) @ X.T
            h = np.diag(H)
            Vh = np.linalg.inv(X.T @ X) @ (X.T * (uh / (1 - h))) @ (X.T * (uh / (1 - h))).T @ np.linalg.inv(X.T @ X)   # HC3
            se = np.sqrt(Vh[1, 1])
            tt = bh[1] / se
            pv = 2 * (1 - stats.t.cdf(abs(tt), len(sub) - X.shape[1]))
            # leave-one-out range of the dig coefficient
            loo_b = []
            for i in range(len(sub)):
                m = np.ones(len(sub), bool)
                m[i] = False
                loo_b.append(np.linalg.lstsq(X[m], yv[m], rcond=None)[0][1])
            print(f"   {lab:42s} b_dig={bh[1]:+7.2f} HC3 se={se:6.2f} p(t,N-k)={pv:.3f}  LOO range [{min(loo_b):+.1f}, {max(loo_b):+.1f}]")
            out.append(dict(window=f"2005-{end}", spec=lab, n=len(sub), coef=bh[1], se_hc3=se, p=pv,
                            loo_min=min(loo_b), loo_max=max(loo_b), spearman=rho))
    pd.DataFrame(out).to_csv(OUT / "phase_f_ets_country.csv", index=False)
    C.to_csv(OUT / "phase_f_ets_country_data.csv")
    return out


# =====================================================================================
# 5. Figure
# =====================================================================================


def figure(S2, S3, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def fwl(S):
        d = S[["g_ind", "x_dig", "x_nondig"] + CTRL + ["country", "group"]].dropna().copy()
        W = within(d[["g_ind", "x_dig", "x_nondig"] + CTRL].to_numpy(float), d.country.to_numpy())
        y, xd, Z = W[:, 0], W[:, 1], W[:, 2:]
        ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
        rx = xd - Z @ np.linalg.lstsq(Z, xd, rcond=None)[0]
        return d, rx, ry

    fig, ax = plt.subplots(1, 3, figsize=(15.5, 4.8), gridspec_kw=dict(width_ratios=[1, 1, 1.15]))
    col = {"EU15": "#2a6f97", "ACC": "#d1495b"}
    for a, S, lab in [(ax[0], S2, "NUTS2"), (ax[1], S3, "NUTS3")]:
        d, rx, ry = fwl(S)
        for g in ["EU15", "ACC"]:
            m = (d.group == g).to_numpy()
            a.scatter(rx[m], ry[m], s=14 if lab == "NUTS3" else 24, alpha=.55, c=col[g], label=g if g == "EU15" else "2004+ accession", lw=0)
        b = (rx @ ry) / (rx @ rx)
        xs = np.linspace(np.percentile(rx, 1), np.percentile(rx, 99), 10)
        a.plot(xs, b * xs, c="k", lw=1.6)
        a.set_xlim(np.percentile(rx, 0.5) - .1, np.percentile(rx, 99.5) + .1)
        a.set_ylim(np.percentile(ry, 0.5) - .5, np.percentile(ry, 99.5) + .5)
        r = [x for x in res if x["tag"].startswith("A3 FE") and x["sample"] == lab][0]
        a.set_title(f"{lab}: n={r['n']}, G={r['G']} countries\nslope {r['coef']:+.2f} (t(G-1) p={r['p_t_Gm1']:.2f}, wild p={r['p_wild']:.2f})", fontsize=10)
        a.set_xlabel("digital patent stock (asinh, per Mio inh.), residualised\non country FE, controls, non-digital stock")
        a.set_ylabel("industrial GVA growth 2005-19, %/yr, residualised")
        a.axhline(0, c="#999", lw=.5)
        a.legend(frameon=False, fontsize=8)
    # forest
    rows = [("A2 FE: dig + controls", "A2 dig + controls"), ("A3 FE: dig + nondig", "A3 CLAIM"),
            ("C EU15 only", "EU-15 only"), ("C ACC only", "2004+ only")]
    labs, ests, los, his, cols = [], [], [], [], []
    for lab in ["NUTS2", "NUTS3"]:
        for pref, nm in rows:
            r = [x for x in res if x["tag"].startswith(pref) and x["sample"] == lab][0]
            labs.append(f"{lab} {nm}")
            ests.append(r["coef"]); los.append(r["ci_lo"]); his.append(r["ci_hi"])
            cols.append("#2a6f97" if lab == "NUTS2" else "#6a994e")
    yy = np.arange(len(labs))[::-1]
    for y_, e, lo, hi, c in zip(yy, ests, los, his, cols):
        ax[2].plot([lo, hi], [y_, y_], c=c, lw=2)
        ax[2].scatter([e], [y_], c=c, s=30, zorder=3)
    ax[2].axvline(0, c="k", lw=.8)
    ax[2].set_yticks(yy)
    ax[2].set_yticklabels(labs, fontsize=8)
    ax[2].set_xlabel("coefficient on digital patent stock (pp/yr per unit asinh)\n95% CI, country-clustered t(G-1)")
    ax[2].set_title("Country-FE estimates: all CIs vs zero", fontsize=10)
    fig.suptitle("Phase F: predetermined (<=2004) digital patent stock vs regional industrial GVA growth 2005-2019, country fixed effects", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "phase_f_headline.png", dpi=150)
    plt.close(fig)


# =====================================================================================
# main
# =====================================================================================


def selection_qc(U2, U3):
    """Kept vs lost regions on the outcome: all EU27 NUTS3 in the GVA tables with a B-E growth figure."""
    from phase_f_build import wide, load_gva
    print("\n" + "=" * 100 + "\nSECTION 2b: SELECTION -- kept vs lost regions on the outcome\n" + "=" * 100)
    ind = wide(load_gva(), "CP_MNAC", "B-E")
    g = 100 * (np.log(ind[2019].where(ind[2019] > 0)) - np.log(ind[2005].where(ind[2005] > 0))) / 14
    d = pd.DataFrame({"g": g}).dropna()
    d["country"] = d.index.str[:2]
    d = d[d.country.isin(EU27)].copy()
    d["grp"] = np.where(d.country.isin(ACC), "ACC", "EU15")
    d["kept3"] = d.index.isin(U3.unit)
    d["kept2"] = d.index.str[:4].isin(U2.unit)
    for k in ["kept3", "kept2"]:
        print(f"  {k}: mean growth kept {d[d[k]].g.mean():.2f} (n={int(d[k].sum())}) vs lost {d[~d[k]].g.mean():.2f} (n={int((~d[k]).sum())}); "
              f"EU15 kept {d[d[k]&(d.grp=='EU15')].g.mean():.2f} lost {d[~d[k]&(d.grp=='EU15')].g.mean():.2f}; "
              f"ACC kept {d[d[k]&(d.grp=='ACC')].g.mean():.2f} lost {d[~d[k]&(d.grp=='ACC')].g.mean():.2f}")
    t = d.groupby(["country", "kept3"]).size().unstack(fill_value=0)
    print("  NUTS3 outcome regions by country (False=lost, True=kept):")
    print(t.T.to_string())
    d.to_csv(OUT / "phase_f_qc_selection.csv")


def main():
    patent_qc()
    U2, qc2 = build_units("NUTS2")
    U2l, qc2l = build_units("NUTS2", lenient=True)
    U3, qc3 = build_units("NUTS3")
    for nm, U, qc in [("NUTS2_strict", U2, qc2), ("NUTS2_lenient", U2l, qc2l), ("NUTS3", U3, qc3)]:
        U.to_csv(OUT / f"phase_f_units_{nm}.csv", index=False)
    qc2["stability_table"].to_csv(OUT / "phase_f_qc_nuts2_stability.csv", index=False)
    qc3["mapping"].to_csv(OUT / "phase_f_qc_nuts3_mapping.csv", index=False)
    print("\n" + "=" * 100 + "\nSECTION 2: NUTS-VINTAGE / MERGE QC\n" + "=" * 100)
    print("Patents sit on NUTS-2010 codes (verified: e.g. DE401.., DE80x = 18 MV districts, FR 2010 codes);")
    print("GVA/population/employment sit on NUTS-2021. Chain: 2010->2013->2016 (Eurostat correspondence tables,")
    print("pure recodes followed, merges/splits/boundary shifts FLAGGED) + a population-ratio check")
    print("(Eurostat's own patent-side denominator NR/P_MHAB vs 2021-vintage population, tolerance 5%).")
    print("2016->2021: no downloadable table (404); residual risk = code reuse with changed boundary,")
    print("caught only if it moves population > 5%.")
    m = qc3["mapping"]
    print("NUTS3:", {k: v for k, v in qc3.items() if k not in ("mapping", "stability_table")})
    ok = m.pop_ratio.dropna()
    print(f"  population-ratio distribution over matched NUTS3 (n={len(ok)}): median {ok.median():.3f}, "
          f"share within 2%: {(abs(ok-1)<.02).mean():.3f}, within 5%: {(abs(ok-1)<.05).mean():.3f}")
    for nm in ["NUTS2_strict"]:
        print("NUTS2:", {k: v for k, v in qc2.items() if k not in ("mapping", "stability_table")})
    print("NUTS2 lenient:", {k: v for k, v in qc2l.items() if k not in ("mapping", "stability_table")})
    ex = set(U2[U2.group != "OTHER"].country)
    print(f"  EU27 patent regions by country lost (NUTS3 stage): {(m[~m.in_gva | m.flag | m.pop_bad].groupby(m.geo10.str[:2]).size()).to_dict()}")
    for nm, U, qc in [("NUTS2_strict", U2, qc2), ("NUTS2_lenient", U2l, qc2l), ("NUTS3", U3, qc3)]:
        qc_units(nm, add_vars(U), qc)
    # patent coverage of retained units
    P = load_patents()
    allp = P[P.time <= BASE_YEAR].merge(m[["geo10", "code"]], left_on="geo", right_on="geo10")
    allp = allp[allp.geo.str[:2].isin(EU27)]
    tot_eu = allp.total.sum()
    for nm, U in [("NUTS2_strict", U2), ("NUTS3", U3)]:
        pass
    print(f"  EU27 patents 1977-2004 assigned to NUTS3 regions (excl. unallocated): {tot_eu:.0f}")
    allc = allp.groupby(allp.geo.str[:2])[["total", "dig_core"]].sum()
    cov = pd.DataFrame({"eu_total_pat_1977_2004": allc.total, "eu_dig_pat_1977_2004": allc.dig_core})
    for nm, U in [("nuts2_strict", U2), ("nuts3", U3)]:
        g = U.groupby("country")[["S_total_cum", "S_dig_core_cum"]].sum()
        cov[f"retained_share_total_{nm}"] = (g.S_total_cum / cov.eu_total_pat_1977_2004).reindex(cov.index).fillna(0)
        cov[f"retained_share_dig_{nm}"] = (g.S_dig_core_cum / cov.eu_dig_pat_1977_2004).reindex(cov.index).fillna(0)
    cov.to_csv(OUT / "phase_f_qc_coverage.csv")
    print(cov.round(3).to_string())
    for nm in ["nuts2_strict", "nuts3"]:
        print(f"  ==> share of all EU27 1977-2004 patents retained at {nm}: total {(cov[f'retained_share_total_{nm}']*cov.eu_total_pat_1977_2004).sum()/cov.eu_total_pat_1977_2004.sum():.3f}, "
              f"digital {(cov[f'retained_share_dig_{nm}']*cov.eu_dig_pat_1977_2004).sum()/cov.eu_dig_pat_1977_2004.sum():.3f}")
    print("  UK: patents exist but NO regional GVA in Eurostat's tables after Brexit -> UK regions cannot enter (all 139 NUTS3 lost).")

    selection_qc(U2, U3)
    print("\n" + "=" * 100 + "\nSECTION 3: MAIN REGRESSIONS\n" + "=" * 100)
    S2, c2 = regional_block("NUTS2", U2, headline=True, seed_base=0)
    S3, c3 = regional_block("NUTS3", U3, headline=True, seed_base=100)
    S2l, c2l = regional_block("NUTS2_lenient", U2l, headline=True, seed_base=200)
    L = pd.concat([loo("NUTS2", S2), loo("NUTS3", S3), loo("NUTS2_lenient", S2l),
                   loo("NUTS3", S3, ("x_dig",), "x_dig", "A2"), loo("NUTS3", S3, ("x_total",), "x_total", "A4"),
                   loo("NUTS2", S2, ("x_total",), "x_total", "A4")])
    L.to_csv(OUT / "phase_f_leave_one_out.csv", index=False)
    # accession LOO for the subgroup claims (NUTS3, where G is largest)
    print("\n--- LOO within the accession subsample, NUTS3 ---")
    Sa = S3[S3.group == "ACC"]
    for c in sorted(Sa.country.unique()):
        r = reg(Sa[Sa.country != c], "g_ind", ["x_dig", "x_nondig"] + CTRL, "x_dig", B=NB, seed_tag=950)
        print(f"   drop {c}: n={r['n']:4d} G={r['G']} b={r['coef']:+.3f} p_t={r['p_t_Gm1']:.3f} p_wild={r['p_wild']:.3f}")
    placebo("NUTS2", U2)
    placebo("NUTS3", U3)
    placebo("NUTS2_lenient", U2l)
    ets_block()
    pd.DataFrame(RESULTS).to_csv(OUT / "phase_f_results.csv", index=False)
    figure(S2, S3, RESULTS)
    print("\nDone. Outputs in analysis/output/phase_f_*")


if __name__ == "__main__":
    main()
