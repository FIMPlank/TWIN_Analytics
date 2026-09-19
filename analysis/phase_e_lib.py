"""Shared helpers for Phase E: data build + cluster-robust OLS/2SLS."""
import numpy as np, pandas as pd, patsy
from scipy import stats
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT.parent / "data" / "raw"
OUT = ROOT / "output"


def contiguous_diff(df, col, by="country_code"):
    """First difference only where previous row is exactly year-1 (guards gaps). NOTE: verified a no-op on
    industry_value_added_absolute.csv (no year gaps) -- kept only as a safeguard."""
    df = df.sort_values([by, "year"])
    d = df.groupby(by)[col].diff()
    gap = df.groupby(by)["year"].diff()
    return d.where(gap == 1)


def build_panel():
    v = pd.read_csv(OUT / "phase_b_working_v2a.csv")
    base = pd.read_csv(OUT / "panel_country_year_v2.csv")
    va = pd.read_csv(RAW / "eurostat" / "industry_value_added_absolute.csv")
    va = va.rename(columns={"geo": "country_code", "time": "year", "value": "va"})[["country_code", "year", "va"]]
    va = va.sort_values(["country_code", "year"])
    va["log_va"] = np.log(va["va"].clip(lower=1))
    va["d_log_va"] = contiguous_diff(va, "log_va")
    v = v.merge(va[["country_code", "year", "d_log_va"]], on=["country_code", "year"], how="left")
    v = v.sort_values(["country_code", "year"]).reset_index(drop=True)
    v["d_log_emissions_chk"] = contiguous_diff(v, "log_emissions")
    v["d_log_gdp_chk"] = v["d_log_gdp_per_capita"]
    # broadband
    t = pd.read_csv(RAW / "eurostat" / "broadband_coverage_technology.csv")
    s = pd.read_csv(RAW / "eurostat" / "broadband_coverage_speed.csv")
    tt = t.pivot_table(index=["geo", "time"], columns=["inet_tec", "terrtypo"], values="value")
    tt.columns = [f"{a}_{b}" for a, b in tt.columns]
    ss = s.pivot_table(index=["geo", "time"], columns="inet_spd", values="value")
    bb = tt.join(ss, how="outer").reset_index().rename(columns={"geo": "country_code", "time": "year"})
    return v, bb


# ---------------- estimators ----------------
def _cr_meat(X, u, g):
    k = X.shape[1]
    meat = np.zeros((k, k))
    for gg in np.unique(g):
        m = g == gg
        s = X[m].T @ u[m]
        meat += np.outer(s, s)
    return meat


def design(df, y, endog, instr, exog_formula):
    """Return arrays y, D (endog), Z (excluded instr), W (exog incl const), groups"""
    cols = [y, endog] + list(instr)
    d = df.dropna(subset=cols).copy()
    W = patsy.dmatrix(exog_formula, d, return_type="dataframe")
    d = d.loc[W.index]
    return (d[y].to_numpy(float), d[endog].to_numpy(float), d[list(instr)].to_numpy(float),
            W.to_numpy(float), d["country_code"].to_numpy(), d)


def ols_cr(y, X, g, j):
    n, k = X.shape
    b = np.linalg.solve(X.T @ X, X.T @ y)
    u = y - X @ b
    bread = np.linalg.inv(X.T @ X)
    G = len(np.unique(g))
    V = (G / (G - 1)) * ((n - 1) / (n - k)) * bread @ _cr_meat(X, u, g) @ bread
    return b[j], np.sqrt(V[j, j]), G


def first_stage(y, D, Z, W, g):
    """Cluster-robust first stage (CR1). If k > G the cluster meat is rank-deficient: F is then
    optimistic and flagged reliable=False.  returns F (Wald/q, CR1), p (F(q,G-1)), partial R2, coefs."""
    X = np.column_stack([Z, W])
    n, k = X.shape
    q = Z.shape[1]
    b = np.linalg.solve(X.T @ X, X.T @ D)
    u = D - X @ b
    bread = np.linalg.inv(X.T @ X)
    G = len(np.unique(g))
    V = (G / (G - 1)) * ((n - 1) / (n - k)) * bread @ _cr_meat(X, u, g) @ bread
    bz, Vz = b[:q], V[:q, :q]
    F = float(bz @ np.linalg.solve(Vz, bz) / q)
    p = 1 - stats.f.cdf(F, q, G - 1)
    # partial R2
    bw = np.linalg.solve(W.T @ W, W.T @ D)
    rw = D - W @ bw
    pr2 = 1 - (u @ u) / (rw @ rw)
    return dict(F=F, p_F=p, partial_R2=pr2, coef=bz, se=np.sqrt(np.diag(Vz)), n=n, G=G, k=k, reliable=bool(k <= G))


def tsls(y, D, Z, W, g):
    """2SLS with one endogenous regressor; CR1 cluster vcov. returns beta, se, G"""
    X = np.column_stack([D, W])
    Zf = np.column_stack([Z, W])
    P = Zf @ np.linalg.solve(Zf.T @ Zf, Zf.T)
    Xh = P @ X
    b = np.linalg.solve(Xh.T @ X, Xh.T @ y)
    u = y - X @ b
    n, k = X.shape
    bread = np.linalg.inv(Xh.T @ Xh)
    G = len(np.unique(g))
    V = (G / (G - 1)) * ((n - 1) / (n - k)) * bread @ _cr_meat(Xh, u, g) @ bread
    return b[0], np.sqrt(V[0, 0]), G


def wild_p_restricted(y, X, g, j, n_boot, seed):
    """Wild cluster restricted bootstrap p-value (Rademacher) for coefficient j in OLS y~X."""
    b, se, G = ols_cr(y, X, g, j)
    t_obs = b / se
    Xr = np.delete(X, j, axis=1)
    br = np.linalg.solve(Xr.T @ Xr, Xr.T @ y)
    fr = Xr @ br
    rr = y - fr
    uniq = np.unique(g)
    idx = [np.where(g == u)[0] for u in uniq]
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n_boot):
        w = rng.choice([-1.0, 1.0], size=G)
        wv = np.empty(len(y))
        for i, ix in enumerate(idx):
            wv[ix] = w[i]
        ys = fr + rr * wv
        bb, ss, _ = ols_cr(ys, X, g, j)
        cnt += abs(bb / ss) >= abs(t_obs)
    return (cnt + 1) / (n_boot + 1)


def ar_test(y, D, Z, W, g, beta0):
    """Anderson-Rubin: regress y - beta0*D on Z,W; cluster Wald test on Z. returns F, p_F(q,G-1)"""
    yy = y - beta0 * D
    X = np.column_stack([Z, W])
    n, k = X.shape
    q = Z.shape[1]
    b = np.linalg.solve(X.T @ X, X.T @ yy)
    u = yy - X @ b
    bread = np.linalg.inv(X.T @ X)
    G = len(np.unique(g))
    V = (G / (G - 1)) * ((n - 1) / (n - k)) * bread @ _cr_meat(X, u, g) @ bread
    F = float(b[:q] @ np.linalg.solve(V[:q, :q], b[:q]) / q)
    return F, 1 - stats.f.cdf(F, q, G - 1)


def ar_ci(y, D, Z, W, g, grid, alpha=0.05):
    ok = [bt for bt in grid if ar_test(y, D, Z, W, g, bt)[1] > alpha]
    if not ok:
        return "empty", None, None
    lo, hi = min(ok), max(ok)
    bounded = lo > grid[0] and hi < grid[-1]
    # contiguity check
    idx = [i for i, bt in enumerate(grid) if bt in set(ok)]
    contiguous = (idx[-1] - idx[0] + 1) == len(idx)
    return ("bounded" if bounded and contiguous else ("unbounded/disjoint" )), lo, hi
