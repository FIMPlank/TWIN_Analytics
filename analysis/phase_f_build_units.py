"""Phase F: assemble regional units (NUTS2 / NUTS3) with predetermined patent stocks,
covariates, outcomes and the NUTS-vintage stability QC. Uses phase_f_build.py helpers."""
import numpy as np
import pandas as pd

from phase_f_build import (ES, ROOT, BASE_YEAR, Y0, ACC, EU15, load_vintage_map, map_code,
                           load_patents, stock, load_gva, wide, is_unallocated)


def national_deflator_growth(y0, y1):
    """Annual log growth of the national B-E GVA deflator (CP_MNAC / CLV20_MNAC), y0 -> y1, x100."""
    n = pd.read_csv(ES / "national_gva_nac.csv")
    n = n[n.nace_r2 == "B-E"]
    cp = n[n.unit == "CP_MNAC"].pivot(index="geo", columns="time", values="value")
    cl = n[n.unit == "CLV20_MNAC"].pivot(index="geo", columns="time", values="value")
    d = cp / cl
    return 100 * (np.log(d[y1]) - np.log(d[y0])) / (y1 - y0)


def fill_missing_regional_pop(pop, popc):
    """Eurostat's NUTS3 population has gaps (Romania: no NUTS3 values 2002-2011). Fallback,
    disclosed in phase_f_patents.md: for a region with observed shares in years a<t<b, interpolate the
    region's share of the national population linearly between a and b and multiply by the national
    population in t. Only fills interior gaps (both a and b observed); nothing is extrapolated."""
    pop = pop.copy()
    nat = popc.reindex(columns=pop.columns)
    ctry = pop.index.str[:2]
    share = pop.div(nat.reindex(ctry).to_numpy() * 0 + nat.reindex(ctry).to_numpy())
    filled = 0
    for i, g in enumerate(pop.index):
        sh = share.loc[g]
        if sh.isna().any() and sh.notna().sum() >= 2:
            yrs = np.array(sh.index, float)
            ok = sh.notna().to_numpy()
            lo, hi = yrs[ok].min(), yrs[ok].max()
            inside = (~ok) & (yrs > lo) & (yrs < hi)
            interp = np.interp(yrs, yrs[ok], sh.to_numpy()[ok])
            for j in np.flatnonzero(inside):
                nv = nat.loc[g[:2], pop.columns[j]] if g[:2] in nat.index else np.nan
                if not np.isnan(nv):
                    pop.iloc[i, j] = interp[j] * nv
                    filled += 1
    pop.attrs["n_filled"] = filled
    return pop


def build_units(level, pop_tol=0.05, lenient=False):
    """Return (units DataFrame, qc dict). level in {'NUTS2','NUTS3'}.
    Units carry NUTS-2016/2021 codes and are kept only if stable across vintages
    (see load_vintage_map + population-ratio check)."""
    maps = load_vintage_map()
    pat = load_patents()
    geos = pd.read_csv(ES / "patents_geo_list.csv")
    g5 = [g for g in geos.geo if len(g) == 5 and not is_unallocated(g)]
    mp = pd.DataFrame({"geo10": g5})
    mp[["code", "flag"]] = [map_code(c, maps) for c in g5]
    gva = load_gva()
    gvaset = set(gva.geo)
    mp["in_gva"] = mp.code.isin(gvaset)

    # boundary-stability check: patent-side population (NR / per-million-inhabitants, Eurostat's own
    # denominator on NUTS-2010 boundaries) vs GVA-side population (NUTS-2021 boundaries).
    a = pd.read_csv(ES / "patents_regional_total.csv")
    b = pd.read_csv(ES / "patents_regional_total_per_mhab.csv")
    x = a.merge(b, on=["geo", "time"], suffixes=("_nr", "_p"))
    x["pimp"] = x.value_nr / x.value_p * 1e3   # thousand persons
    pop = pd.read_csv(ES / "regional_population_nuts3.csv")
    popc = pop[pop.geo.str.len() == 2].pivot(index="geo", columns="time", values="value")
    pop = pop[pop.geo.str.len() == 5].pivot(index="geo", columns="time", values="value")
    pop = fill_missing_regional_pop(pop, popc)
    yrs = list(range(2000, 2005))
    imp = x[x.time.isin(yrs)].pivot_table(index="geo", columns="time", values="pimp").median(axis=1)
    pop_new3 = pop[yrs].median(axis=1)
    mp = mp.merge(imp.rename("pop_imp").reset_index().rename(columns={"geo": "geo10"}), on="geo10", how="left")
    mp["pop_new"] = mp.code.map(pop_new3)
    mp["pop_ratio"] = mp.pop_imp / mp.pop_new
    mp["pop_bad"] = ((mp.pop_ratio - 1).abs() > pop_tol).fillna(False)
    mp["o2"] = mp.geo10.str[:4]                              # NUTS-2010 parent
    mp["n2"] = np.where(mp.flag, mp.geo10.str[:4], mp.code.str[:4])   # NUTS2 key on the new vintage

    qc = {}
    if level == "NUTS3":
        ok = mp.in_gva & ~mp.flag & ~mp.pop_bad
        keep = mp[ok].copy()
        keep["unit"] = keep.code
        qc = dict(n_patent_regions=len(mp), n_in_gva=int(mp.in_gva.sum()), n_flagged=int(mp.flag.sum()),
                  n_pop_bad=int(mp.pop_bad.sum()), n_kept=len(keep))
    else:
        gch = {}
        for c in sorted(gvaset):
            gch.setdefault(c[:4], set()).add(c)
        pch = mp.groupby("n2").code.apply(set).to_dict()
        # each new-vintage NUTS2 n: patent-side NUTS2 population = sum over the 2010 parents o whose
        # children ALL map to n (otherwise the parent was cut across NUTS2 lines -> unvalidated)
        o_targets = mp.groupby("o2").n2.apply(set).to_dict()
        rows = []
        for n2 in sorted(set(gch) | set(pch)):
            sub = mp[mp.n2 == n2]
            os_ = sorted(set(sub.o2))
            clean = all(o_targets[o] == {n2} for o in os_)
            pat_pop = sum(imp.get(o, np.nan) for o in os_) if (os_ and clean) else np.nan
            new_pop = pop_new3.reindex(sorted(gch.get(n2, []))).sum(min_count=1) if n2 in gch else np.nan
            pr = pat_pop / new_pop if new_pop and not np.isnan(pat_pop) else np.nan
            same = (n2 in gch) and (n2 in pch) and gch[n2] == pch[n2]
            rows.append(dict(n2=n2, same_children=same, anyflag=bool(sub.flag.any()), pop_ratio=pr,
                             pop_bad=(not np.isnan(pr)) and abs(pr - 1) > pop_tol,
                             pop_unvalidated=np.isnan(pr), n_pat_children=len(sub),
                             n_gva_children=len(gch.get(n2, []))))
        st = pd.DataFrame(rows)
        st["stable_strict"] = st.same_children & ~st.anyflag & ~st.pop_bad
        # lenient: reorganisations of NUTS3 *inside* a NUTS2 are tolerated when the NUTS2 population
        # (validated against Eurostat's patent-side denominator) is unchanged within tolerance.
        st["stable_lenient"] = (st.n_pat_children > 0) & (st.n_gva_children > 0) & st.pop_ratio.notna() & ~st.pop_bad
        st["stable"] = st.stable_lenient if lenient else st.stable_strict
        keep_n2 = set(st[st.stable].n2)
        keep = mp[mp.n2.isin(keep_n2)].copy()
        keep["unit"] = keep.n2
        qc = dict(n_nuts2_patent_side=int((st.n_pat_children > 0).sum()), n_nuts2_gva_side=int((st.n_gva_children > 0).sum()),
                  n_same_children=int(st.same_children.sum()), n_stable_strict=int(st.stable_strict.sum()),
                  n_stable_lenient=int(st.stable_lenient.sum()), n_pop_bad=int(st.pop_bad.sum()),
                  n_flag=int(st.anyflag.sum()))
        qc["stability_table"] = st

    pt = pat.merge(keep[["geo10", "unit"]], left_on="geo", right_on="geo10")
    cols = [c for c in pat.columns if c not in ("geo", "time")]
    pt = pt.drop(columns=["geo", "geo10"]).groupby(["unit", "time"], as_index=False)[cols].sum().rename(columns={"unit": "geo"})
    series = ["dig_core", "dig_broad", "nondig", "nondig_broad", "total", "mech_chem"]
    U = pd.DataFrame(index=sorted(keep.unit.unique()))
    for s in series:
        for d, nm in [(0.10, "d10"), (0.15, "d15"), (0.20, "d20"), (None, "cum")]:
            U[f"S_{s}_{nm}"] = stock(pt, s, d, Y0, BASE_YEAR)
            U[f"S99_{s}_{nm}"] = stock(pt, s, d, Y0, 1999)
        U[f"SP_{s}_d15"] = stock(pt, s, 0.15, 2005, 2012)   # placebo: LATER window only

    if level == "NUTS3":
        umap = keep.set_index("code").unit
    else:   # GVA-side aggregation uses ALL new-vintage NUTS3 children of each retained NUTS2
        umap = pd.Series({c: c[:4] for c in gvaset if c[:4] in keep_n2})

    def agg(df):
        d = df.loc[df.index.intersection(umap.index)]
        key = umap.reindex(d.index)
        return d.groupby(key).sum(min_count=1).where(d.notna().groupby(key).all())

    ind = agg(wide(gva, "CP_MNAC", "B-E"))
    man = agg(wide(gva, "CP_MNAC", "C"))
    tot = agg(wide(gva, "CP_MNAC", "TOTAL"))
    ind_eur = agg(wide(gva, "CP_MEUR", "B-E"))
    tot_eur = agg(wide(gva, "CP_MEUR", "TOTAL"))
    popu = agg(pop)
    emp = pd.read_csv(ES / "regional_employment_nuts3.csv")
    emp = emp[(emp.geo.str.len() == 5) & (emp.nace_r2 == "TOTAL") & (emp.wstatus == "EMP")].pivot(
        index="geo", columns="time", values="value")
    empu = agg(emp)
    U["country"] = [u[:2] for u in U.index]
    U["group"] = np.where(U.country.isin(ACC), "ACC", np.where(U.country.isin(EU15), "EU15", "OTHER"))
    U["pop04"] = popu[2004]
    U["emp04"] = empu[2004]
    U["gva_tot04_eur"] = tot_eur[2004]
    U["gva_ind04_eur"] = ind_eur[2004]
    U["ln_gvapc04"] = np.log(1e6 * U.gva_tot04_eur / (1e3 * U.pop04))
    U["ind_share04"] = U.gva_ind04_eur / U.gva_tot04_eur
    U["ln_pop04"] = np.log(U.pop04)
    U["ln_gvapc00"] = np.log(1e6 * tot_eur[2000] / (1e3 * popu[2000]))
    U["ind_share00"] = ind_eur[2000] / tot_eur[2000]

    def lg(df, y0, y1):
        return 100 * (np.log(df[y1].where(df[y1] > 0)) - np.log(df[y0].where(df[y0] > 0))) / (y1 - y0)

    U["g_ind"] = lg(ind, 2005, 2019)            # nominal, national currency, %/yr
    U["defl"] = U.country.map(national_deflator_growth(2005, 2019))
    U["g_ind_real"] = U.g_ind - U.defl          # minus national B-E deflator (only matters without country FE)
    m3 = lambda df, ys: df[ys].mean(axis=1, skipna=False)
    U["g_ind_smooth"] = 100 * (np.log(m3(ind, [2017, 2018, 2019])) - np.log(m3(ind, [2004, 2005, 2006]))) / 13
    U["g_man"] = lg(man, 2005, 2019)
    U["g_tot"] = lg(tot, 2005, 2019)
    U["g_ind_0512"] = lg(ind, 2005, 2012)
    U["g_ind_1219"] = lg(ind, 2012, 2019)
    U["g_ind_0004"] = lg(ind, 2000, 2004)       # placebo window
    U["g_ind_0004_real"] = U.g_ind_0004 - U.country.map(national_deflator_growth(2000, 2004))
    U["g_tot_0004"] = lg(tot, 2000, 2004)
    U.index.name = "unit"
    qc["mapping"] = mp
    return U.reset_index(), qc
