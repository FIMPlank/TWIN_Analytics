"""Phase F data build: predetermined digital-patent stocks + regional outcomes.
Imported by phase_f_patents.py (kept separate so the QC is inspectable)."""
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ES = RAW / "eurostat"
OUT = ROOT / "analysis" / "output"

DIGITAL_CORE = ["G06", "G11", "H03", "H04"]
DIGITAL_BROAD = DIGITAL_CORE + ["H01", "G05", "G08", "G09"]
BASE_YEAR = 2004
Y0, Y1 = 1977, 2012

EU15 = {"AT", "BE", "DE", "DK", "EL", "ES", "FI", "FR", "IE", "IT", "LU", "NL", "PT", "SE", "UK"}
ACC = {"CZ", "EE", "CY", "LV", "LT", "HU", "MT", "PL", "SI", "SK", "BG", "RO", "HR"}
EU27 = (EU15 - {"UK"}) | ACC


def is_unallocated(g):
    s = g[2:]
    return set(s) <= {"Z"} or set(s) <= {"X"}


# ---------------------------------------------------------------- NUTS vintage
def load_vintage_map():
    """Patents sit on NUTS 2010 codes; GVA/pop on NUTS 2021. Chain 2010->2013->2016 with
    Eurostat's correspondence tables (data/raw/geo). Only pure recodes are followed; any
    NUTS3 that was merged/split/boundary-shifted is FLAGGED (boundary not comparable).
    The 2016->2021 step has no downloadable table (404); it is handled by code-set
    comparison + the population-ratio check in phase_f_patents.py."""
    t1 = pd.read_excel(ROOT / "data/raw/geo/nuts_corr_2010_2013.xls", sheet_name="Correspondence NUTS-3")
    t1.columns = ["old", "new", "label", "change", "expl"]
    t2 = pd.read_excel(ROOT / "data/raw/geo/nuts_corr_2013_2016.xlsx", sheet_name="Correspondence NUTS-3")
    t2.columns = ["old", "new", "label", "change", "expl"]
    rec1 = t1[t1.change.isin(["Code change", "Code, name change"]) & t1.old.notna() & t1.new.notna()]
    map1 = dict(zip(rec1.old, rec1.new))
    flag1 = set(t1[t1.old.notna() & t1.change.isin(["Boundary shift", "Merged", "Split"])].old)
    rec2 = t2[(t2.change == "recoded") & t2.old.notna() & t2.new.notna()]
    map2 = dict(zip(rec2.old, rec2.new))
    flag2 = set(t2[t2.old.notna() & (t2.change != "recoded")].old)
    return map1, flag1, map2, flag2


def map_code(c, maps):
    map1, flag1, map2, flag2 = maps
    flagged = c in flag1
    c13 = map1.get(c, c)
    flagged |= c13 in flag2
    c16 = map2.get(c13, c13)
    return c16, flagged


# ---------------------------------------------------------------- patents
def load_patents():
    """Return long DataFrame geo(2010 code) x year: total, dig_core, dig_broad, and geo list."""
    ipc = pd.read_csv(ES / "patents_regional_ipc.csv")
    ipc = ipc[ipc.geo.str.len() == 5]
    w = ipc.pivot_table(index=["geo", "time"], columns="ipc", values="value", aggfunc="sum")
    geos = pd.read_csv(ES / "patents_geo_list.csv")
    g5 = [g for g in geos.geo if len(g) == 5]
    idx = pd.MultiIndex.from_product([g5, range(Y0, Y1 + 1)], names=["geo", "time"])
    w = w.reindex(idx).fillna(0.0)   # absent cell = no patent in Eurostat's sparse cube
    out = pd.DataFrame(index=w.index)
    out["total"] = w["IPC"]
    out["dig_core"] = w[DIGITAL_CORE].sum(axis=1)
    out["dig_broad"] = w[DIGITAL_BROAD].sum(axis=1)
    for s in "ABCDEFGH":
        out["sec_" + s] = w[s]
    out["nondig"] = (out["total"] - out["dig_core"]).clip(lower=0)
    out["nondig_broad"] = (out["total"] - out["dig_broad"]).clip(lower=0)
    out["mech_chem"] = w[["B", "C", "F"]].sum(axis=1)     # non-ICT industrial technology fields
    return out.reset_index()


def stock(df, col, delta, start, end):
    """Perpetual inventory S_t = (1-d) S_{t-1} + P_t over start..end; d=None -> cumulative sum.
    Patents before `start` are ignored (initial stock 0); stock at `end` returned per geo."""
    p = df[(df.time >= start) & (df.time <= end)].pivot(index="geo", columns="time", values=col).fillna(0.0)
    d = 0.0 if delta is None else delta
    s = np.zeros(len(p))
    for y in range(start, end + 1):
        s = (1 - d) * s + p[y].to_numpy()
    return pd.Series(s, index=p.index)


# ---------------------------------------------------------------- outcomes
def load_gva():
    g = pd.read_csv(ES / "regional_gva_nuts3.csv")
    g = g[g.geo.str.len() == 5]
    return g


def wide(g, unit, nace):
    x = g[(g.unit == unit) & (g.nace_r2 == nace)]
    return x.pivot(index="geo", columns="time", values="value")
