"""
Phase C, item 1: build panel v3 (NUTS2 region x year), the regional
digitalization/emissions panel described in the Phase C brief. Data
engineering only -- QC diagnostics are printed and saved; regressions on
this panel happen in analysis/phase_c_analysis.py and are explicitly
labelled provisional/pending Reviewer sign-off, following the same
"data first, checked, then models" discipline as Phase A/B (compressed
into one round here, as instructed).

Inputs:
  - data/raw/eprtr/F1_4_Air_Releases_Facilities.csv (E-PRTR facility-level
    air releases, incl. Longitude/Latitude -- fetched directly, same file
    scripts/download_eprtr.py --all would produce; gitignored, not
    committed, ~72MB)
  - data/raw/geo/nuts2_2021.geojson (NUTS2021 region polygons, EPSG:4326 --
    scripts/download_nuts2_boundaries.py; gitignored, not committed, ~18MB)
  - data/raw/eurostat/dii_regional_components.csv (5 regional
    digitalization survey components -- scripts/download_eurostat_dii_regional.py)

Outputs:
  - analysis/output/phase_c_panel_region_year_v3.csv
  - analysis/output/phase_c_facility_geocoding.csv (one row per unique
    facility, with its assigned NUTS2 region, for independent inspection)
  - Printed QC diagnostics (coverage, geocoding match rate, composite
    construction) -- consumed into analysis/phase_c_analysis.md

Usage:
    python analysis/phase_c_build_panel.py
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "analysis" / "output"
OUT.mkdir(parents=True, exist_ok=True)

pd.set_option("display.width", 160)

# ---------------------------------------------------------------------------
# 1. Geocode E-PRTR facilities to NUTS2 regions via point-in-polygon
#
#    Two pollutant definitions are built, both documented and both kept
#    (never silently picking one):
#      - "excl_biomass": Carbon dioxide (CO2) excluding biomass -- the SAME
#        pollutant definition already used and validated in the country-
#        level analysis (analysis/analysis.py, analysis/extension_analysis.py),
#        per the Phase C brief's explicit instruction. Only 15 countries
#        report this specific variant at facility level (checked below),
#        which turns out to make the resulting region panel too small to
#        analyze (see QC section 4).
#      - "incl_biomass": Carbon dioxide (CO2) (Eurostat/E-PRTR's plain,
#        undifferentiated CO2 field, which INCLUDES biogenic CO2 that the
#        excl_biomass variant and EU ETS itself both exclude). Reported at
#        32 countries / ~3,600 facilities -- a genuinely usable sample size.
#        This is a DEVIATION from the country-level convention, built and
#        reported ONLY because the instructed definition turned out to be
#        unusable; every result built on it is flagged as not directly
#        comparable to panel v1/v2's fossil-only emissions figures.
# ---------------------------------------------------------------------------
print("=== 1. Geocoding E-PRTR facilities to NUTS2 regions ===")

eprtr = pd.read_csv(RAW / "eprtr" / "F1_4_Air_Releases_Facilities.csv", low_memory=False)

POLLUTANT_DEFS = {
    "excl_biomass": eprtr["Pollutant"].str.contains("Carbon dioxide", case=False, na=False)
                     & eprtr["Pollutant"].str.contains("excluding biomass", case=False, na=False),
    "incl_biomass": eprtr["Pollutant"] == "Carbon dioxide (CO2)",
}

geocoded_frames = {}
region_year_frames = {}

for pollutant_label, mask in POLLUTANT_DEFS.items():
    print(f"\n--- Pollutant definition: {pollutant_label} ---")
    co2 = eprtr[mask].copy()
    print(f"E-PRTR facility-year rows: {len(co2)}")
    print(f"Countries reporting this pollutant at facility level ({co2['countryName'].nunique()}): "
          f"{sorted(co2['countryName'].unique())}")
    print(f"Years available: {sorted(co2['reportingYear'].unique())}")

    facilities = co2[["FacilityInspireId", "facilityName", "countryName", "Longitude", "Latitude"]].drop_duplicates(
        subset=["FacilityInspireId", "Longitude", "Latitude"]
    )
    print(f"Unique facilities to geocode: {len(facilities)}")

    nuts2 = gpd.read_file(RAW / "geo" / "nuts2_2021.geojson")[["NUTS_ID", "CNTR_CODE", "geometry"]]
    fac_gdf = gpd.GeoDataFrame(
        facilities,
        geometry=gpd.points_from_xy(facilities["Longitude"], facilities["Latitude"]),
        crs="EPSG:4326",
    )
    matched = gpd.sjoin(fac_gdf, nuts2, how="left", predicate="within")
    # a handful of points can fail an exact "within" (e.g. sitting exactly on
    # a coastline/border vertex due to floating-point coordinate precision)
    # -- for those, fall back to nearest-polygon assignment rather than
    # dropping them silently.
    unmatched_mask = matched["NUTS_ID"].isna()
    n_unmatched_within = unmatched_mask.sum()
    if n_unmatched_within:
        print(f"{n_unmatched_within} facilities did not fall exactly `within` any NUTS2 polygon "
              f"(likely coastline/border precision) -- reassigning via nearest polygon")
        unmatched_gdf = fac_gdf[unmatched_mask]
        nearest = gpd.sjoin_nearest(unmatched_gdf, nuts2, how="left")
        nearest = nearest[~nearest.index.duplicated(keep="first")]
        matched.loc[unmatched_mask, "NUTS_ID"] = nearest["NUTS_ID"].reindex(matched.loc[unmatched_mask].index).values
        matched.loc[unmatched_mask, "CNTR_CODE"] = nearest["CNTR_CODE"].reindex(matched.loc[unmatched_mask].index).values

    still_unmatched = matched["NUTS_ID"].isna().sum()
    print(f"Facilities with NO NUTS2 assignment after nearest-polygon fallback: {still_unmatched} "
          f"of {len(matched)} ({still_unmatched / len(matched):.1%})")

    facility_geocoded = matched[["FacilityInspireId", "facilityName", "countryName", "Longitude", "Latitude", "NUTS_ID", "CNTR_CODE"]].copy()
    facility_geocoded["pollutant_def"] = pollutant_label
    facility_geocoded.to_csv(OUT / f"phase_c_facility_geocoding_{pollutant_label}.csv", index=False)

    # sanity check: country implied by the facility's own countryName field
    # vs. the country implied by its geocoded NUTS2 region's CNTR_CODE -- a
    # mismatch would indicate a geocoding error (e.g. a coordinate typo
    # putting a facility in the wrong country entirely), not just the wrong
    # region within the right country.
    COUNTRY_NAME_TO_ISO = {
        "Austria": "AT", "Belgium": "BE", "Bulgaria": "BG", "Croatia": "HR", "Cyprus": "CY",
        "Czechia": "CZ", "Denmark": "DK", "Estonia": "EE", "Finland": "FI", "France": "FR",
        "Germany": "DE", "Greece": "EL", "Hungary": "HU", "Iceland": "IS", "Ireland": "IE",
        "Italy": "IT", "Latvia": "LV", "Lithuania": "LT", "Luxembourg": "LU", "Malta": "MT",
        "Netherlands": "NL", "Norway": "NO", "Poland": "PL", "Portugal": "PT", "Romania": "RO",
        "Serbia": "RS", "Slovakia": "SK", "Slovenia": "SI", "Spain": "ES", "Sweden": "SE",
        "Switzerland": "CH", "United Kingdom": "UK",
    }
    facility_geocoded["expected_iso"] = facility_geocoded["countryName"].map(COUNTRY_NAME_TO_ISO)
    facility_geocoded["geocoded_iso"] = facility_geocoded["CNTR_CODE"]
    country_mismatch = facility_geocoded[
        facility_geocoded["NUTS_ID"].notna()
        & (facility_geocoded["expected_iso"] != facility_geocoded["geocoded_iso"])
    ].copy()
    print(f"Facilities where the geocoded country disagrees with E-PRTR's own reported country: "
          f"{len(country_mismatch)} of {facility_geocoded['NUTS_ID'].notna().sum()} geocoded facilities")
    if len(country_mismatch):
        # Coordinate-plausibility check: continental Europe's land mass sits
        # roughly between 34N-71N latitude. A mismatch with an implausible
        # latitude (e.g. a truncated leading digit, like 55.33 -> 5.33) is a
        # SOURCE DATA CORRUPTION, not an offshore point-in-polygon limitation
        # -- a different defect class that a "these are all offshore
        # platforms" summary would misclassify. Both categories are excluded
        # from the aggregated panel either way (the mismatch filter below
        # doesn't care why), but the two are worth telling apart for anyone
        # extending this pipeline to other years/pollutants.
        country_mismatch["likely_cause"] = np.where(
            (country_mismatch["Latitude"] < 34) | (country_mismatch["Latitude"] > 71),
            "coordinate corruption (implausible latitude for Europe)",
            "offshore / coastal point-in-polygon limitation",
        )
        print(country_mismatch[["facilityName", "countryName", "expected_iso", "geocoded_iso",
                                 "Longitude", "Latitude", "likely_cause"]].to_string())
        print(country_mismatch["likely_cause"].value_counts().to_string())

    geocoded_frames[pollutant_label] = facility_geocoded

    # -----------------------------------------------------------------------
    # Aggregate facility-level CO2 to NUTS2 region x year (this pollutant def)
    # -----------------------------------------------------------------------
    co2_geo = co2.merge(
        facility_geocoded[["FacilityInspireId", "Longitude", "Latitude", "NUTS_ID", "expected_iso", "geocoded_iso"]],
        on=["FacilityInspireId", "Longitude", "Latitude"], how="left"
    )
    n_no_region = co2_geo["NUTS_ID"].isna().sum()
    print(f"Facility-year rows with no NUTS2 region assigned (dropped from the region panel): "
          f"{n_no_region} of {len(co2_geo)}")
    co2_geo = co2_geo.dropna(subset=["NUTS_ID"])

    # Drop facility-year rows whose geocoded country disagrees with E-PRTR's
    # own reported country -- overwhelmingly offshore oil/gas platforms (the
    # North Sea has no NUTS2 land region to contain them, so a
    # nearest-polygon fallback can assign them to whichever country's
    # coastline happens to be closest, which is not necessarily the
    # reporting/operating country). Including these would put emissions in
    # the wrong country's region-year total, not just a debatable region
    # within the right country -- these rows are excluded rather than kept
    # with a wrong assignment.
    n_country_mismatch_rows = (co2_geo["expected_iso"] != co2_geo["geocoded_iso"]).sum()
    print(f"Facility-year rows dropped for country-mismatched geocoding "
          f"(mostly offshore platforms -- see facility_geocoding CSV): {n_country_mismatch_rows}")
    co2_geo = co2_geo[co2_geo["expected_iso"] == co2_geo["geocoded_iso"]]

    region_year = co2_geo.groupby(["NUTS_ID", "reportingYear"], as_index=False)["Releases"].sum()
    region_year = region_year.rename(columns={"reportingYear": "year", "Releases": "co2_region_t"})
    region_year = region_year.sort_values(["NUTS_ID", "year"])
    region_year["log_emissions"] = np.log(region_year["co2_region_t"].clip(lower=1))
    region_year["d_log_emissions"] = region_year.groupby("NUTS_ID")["log_emissions"].diff()

    print(f"Region-year panel ({pollutant_label}): {len(region_year)} rows, "
          f"{region_year['NUTS_ID'].nunique()} regions, years={sorted(region_year['year'].unique())}")
    region_year_frames[pollutant_label] = region_year

# ---------------------------------------------------------------------------
# 3. Regional digitalization composite from the 5 survey components
#    ------------------------------------------------------------
#    Each component is on its own scale/coverage; the composite is the
#    MEAN OF Z-SCORED (standardized within its own available sample)
#    component values for a given region-year, averaged over however many
#    of the 5 components actually have data for that region-year (NOT
#    requiring all 5 -- coverage differs sharply by dataset, see
#    scripts/download_eurostat_dii_regional.py). This is a simple,
#    transparent, and reproducible composite -- not a validated index, and
#    explicitly documented as such throughout.
# ---------------------------------------------------------------------------
print("\n=== 3. Regional digitalization composite ===")
dii_reg = pd.read_csv(RAW / "eurostat" / "dii_regional_components.csv")
dii_reg = dii_reg.rename(columns={"geo": "NUTS_ID", "time": "year"})

coverage_by_component = dii_reg.groupby("source_dataset")["year"].apply(lambda s: sorted(s.unique()))
print("Year coverage confirmed live, by component dataset:")
for ds, years in coverage_by_component.items():
    print(f"  {ds}: {years}")

dii_reg["z_value"] = dii_reg.groupby("source_dataset")["value"].transform(
    lambda s: (s - s.mean()) / s.std()
)
composite = dii_reg.groupby(["NUTS_ID", "year"], as_index=False).agg(
    dii_regional_composite=("z_value", "mean"),
    n_components=("z_value", "count"),
)
composite.to_csv(OUT / "phase_c_dii_regional_composite.csv", index=False)
print(f"\nComposite built for {len(composite)} region-year cells "
      f"({composite['NUTS_ID'].nunique()} regions, years={sorted(composite['year'].unique())})")
print("Distribution of how many of the 5 components each region-year's composite is averaged over:")
print(composite["n_components"].value_counts().sort_index())

# ---------------------------------------------------------------------------
# 4. Merge into panel v3 (region x year) -- built once per pollutant
#    definition, both saved, neither silently discarded.
# ---------------------------------------------------------------------------
for pollutant_label, region_year in region_year_frames.items():
    print(f"\n=== 4. Panel v3 ({pollutant_label}): region x year ===")
    panel_v3 = region_year.merge(composite, on=["NUTS_ID", "year"], how="outer")
    panel_v3["CNTR_CODE"] = panel_v3["NUTS_ID"].str[:2]
    panel_v3.to_csv(OUT / f"phase_c_panel_region_year_v3_{pollutant_label}.csv", index=False)

    print(f"Full panel v3 ({pollutant_label}, outer join): {len(panel_v3)} rows")
    usable_v3 = panel_v3.dropna(subset=["d_log_emissions", "dii_regional_composite"])
    print(f"Rows with BOTH d_log_emissions and dii_regional_composite non-missing "
          f"(the actual usable regression sample): {len(usable_v3)}")
    if len(usable_v3):
        print(f"  regions: {usable_v3['NUTS_ID'].nunique()}, years: {sorted(usable_v3['year'].unique())}, "
              f"countries: {sorted(usable_v3['CNTR_CODE'].unique())}")
        print("Usable rows by year:")
        print(usable_v3["year"].value_counts().sort_index())
        print("Usable rows by country:")
        print(usable_v3["CNTR_CODE"].value_counts())

print(f"\nOutputs written to {OUT}")
