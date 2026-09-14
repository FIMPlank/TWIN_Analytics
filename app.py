"""Interactive exploration app for the TWIN Analytics datasets.

Free, local, runs entirely on your machine via Streamlit + Plotly.

Usage:
    pip install -r requirements.txt
    streamlit run app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent / "data" / "raw"

st.set_page_config(page_title="TWIN Analytics", layout="wide")
st.title("Twin Transformation: digitalization vs. verified emissions")
st.caption(
    "Explore the open-access datasets in `data/raw/`: EU ETS verified emissions (EUTL), "
    "the EIB Investment Survey (EIBIS), and the E-PRTR industrial emissions register."
)


@st.cache_data
def load_eu_ets():
    return pd.read_csv(DATA_DIR / "eu_ets" / "eu-ets.csv")


@st.cache_data
def load_eibis():
    return pd.read_csv(DATA_DIR / "eibis" / "eibis_aggregate.csv")


@st.cache_data
def load_eprtr(name):
    return pd.read_csv(DATA_DIR / "eprtr" / name)


tab_ets, tab_eibis, tab_eprtr = st.tabs(
    ["EU ETS verified emissions", "EIBIS digitalization & climate", "E-PRTR industrial emissions"]
)

# ---------------------------------------------------------------- EU ETS ---
with tab_ets:
    df = load_eu_ets()
    df = df[df["main_activity_code"] != "20-99"]  # drop the "all stationary" rollup
    metrics = sorted(df["citl_information"].unique())
    default_metric = "2. Verified emissions"
    metric = st.selectbox(
        "CITL information (metric)",
        metrics,
        index=metrics.index(default_metric) if default_metric in metrics else 0,
        key="ets_metric",
    )
    d = df[df["citl_information"] == metric]

    col1, col2 = st.columns(2)
    countries = col1.multiselect(
        "Countries (empty = all, aggregated)",
        sorted(d["country_code"].unique()),
        default=["DE", "FR", "PL", "IT", "ES"],
    )
    activities = col2.multiselect(
        "Main activities (empty = all)",
        sorted(d["main_activity_name"].unique()),
        default=[],
    )

    if countries:
        d = d[d["country_code"].isin(countries)]
    if activities:
        d = d[d["main_activity_name"].isin(activities)]

    group_by = "country_code" if countries else "main_activity_name"
    trend = d.groupby([group_by, "year"], as_index=False)["value"].sum()

    fig = px.line(
        trend, x="year", y="value", color=group_by, markers=True,
        labels={"value": metric, "year": "Year", group_by: group_by.replace("_", " ")},
    )
    fig.update_layout(hovermode="x unified", legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Raw data"):
        st.dataframe(d, use_container_width=True)

# ---------------------------------------------------------------- EIBIS ---
with tab_eibis:
    df = load_eibis()
    indicators = sorted(df["indicator"].unique())
    indicator = st.selectbox("Indicator", indicators, key="eibis_indicator")
    d = df[df["indicator"] == indicator].dropna(axis=1, how="all")

    value_cols = [
        c for c in d.columns
        if c not in ("country", "survey_wave", "sector", "size", "indicator")
    ]
    value_col = st.selectbox("Value column", value_cols, key="eibis_value")

    col1, col2, col3 = st.columns(3)
    wave = col1.selectbox("Survey wave", sorted(d["survey_wave"].unique(), reverse=True), key="eibis_wave")
    sector = col2.selectbox("Sector", sorted(d["sector"].unique()), index=sorted(d["sector"].unique()).index("ALL") if "ALL" in d["sector"].unique() else 0, key="eibis_sector")
    size = col3.selectbox("Firm size", sorted(d["size"].unique()), index=sorted(d["size"].unique()).index("ALL") if "ALL" in d["size"].unique() else 0, key="eibis_size")

    filtered = d[(d["survey_wave"] == wave) & (d["sector"] == sector) & (d["size"] == size)].dropna(subset=[value_col])
    filtered = filtered[~filtered["country"].isin(["EU", "US"])].sort_values(value_col, ascending=False)

    fig = px.bar(
        filtered, x="country", y=value_col,
        labels={value_col: indicator, "country": "Country"},
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**Compare two indicators (scatter)**")
    col1, col2 = st.columns(2)
    ind_x = col1.selectbox("X indicator", indicators, index=indicators.index(indicator), key="scatter_x")
    ind_y = col2.selectbox("Y indicator", indicators, index=min(1, len(indicators) - 1), key="scatter_y")

    def wave_country_values(ind, col=None):
        dd = df[(df["indicator"] == ind) & (df["survey_wave"] == wave) & (df["sector"] == sector) & (df["size"] == size)]
        dd = dd.dropna(axis=1, how="all")
        cols = [c for c in dd.columns if c not in ("country", "survey_wave", "sector", "size", "indicator")]
        if not cols:
            return pd.DataFrame(columns=["country", "value"])
        c = col if col in cols else cols[0]
        out = dd[["country", c]].dropna().rename(columns={c: "value"})
        return out

    x_df = wave_country_values(ind_x).rename(columns={"value": "x"})
    y_df = wave_country_values(ind_y).rename(columns={"value": "y"})
    merged = x_df.merge(y_df, on="country")
    merged = merged[~merged["country"].isin(["EU", "US"])]

    if merged.empty:
        st.info("No overlapping data for this combination — try a different wave/sector/size.")
    else:
        fig2 = px.scatter(
            merged, x="x", y="y", text="country",
            labels={"x": ind_x, "y": ind_y},
        )
        fig2.update_traces(textposition="top center")
        st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Raw data"):
        st.dataframe(filtered, use_container_width=True)

# ---------------------------------------------------------------- E-PRTR ---
with tab_eprtr:
    level = st.radio(
        "Aggregation level",
        ["National", "Sector", "Activity"],
        horizontal=True,
        key="eprtr_level",
    )
    file_map = {
        "National": ("F1_1_Air_Releases_National.csv", "countryName"),
        "Sector": ("F1_2_Air_Releases_Sector.csv", "EPRTR_SectorName"),
        "Activity": ("F1_3_Air_Releases_AnnexIActivity.csv", "EPRTRAnnexIMainActivity"),
    }
    filename, group_col = file_map[level]
    df = load_eprtr(filename)

    col1, col2 = st.columns(2)
    pollutants = sorted(df["Pollutant"].unique())
    default_pollutant = "Carbon dioxide (CO2)"
    pollutant = col1.selectbox(
        "Pollutant", pollutants,
        index=pollutants.index(default_pollutant) if default_pollutant in pollutants else 0,
        key="eprtr_pollutant",
    )
    year = col2.selectbox("Reporting year", sorted(df["reportingYear"].unique(), reverse=True), key="eprtr_year")

    d = df[(df["Pollutant"] == pollutant) & (df["reportingYear"] == year)]
    d = d.groupby(group_col, as_index=False)["Releases"].sum().sort_values("Releases", ascending=False)

    if len(d) <= 1:
        st.info("Only one row for this pollutant/year combination — try a different selection.")
    else:
        max_n = max(2, len(d))
        top_n = st.slider("Show top N", 1, max_n, min(12, max_n), key="eprtr_topn")
        d = d.head(top_n)
        d["Releases (t)"] = d["Releases"] / 1000

        fig = px.bar(
            d, x=group_col, y="Releases (t)",
            labels={group_col: level, "Releases (t)": f"{pollutant} (tonnes)"},
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Raw data"):
            st.dataframe(d, use_container_width=True)

st.divider()
st.caption(
    "Run `python scripts/download_all.py` to refresh the underlying data. "
    "Facility-level E-PRTR tables (48-305MB) are fetched separately with "
    "`python scripts/download_eprtr.py --all` and aren't loaded here by default."
)
