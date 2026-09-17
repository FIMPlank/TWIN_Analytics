# Panel v2 QC report

**Phase A only — data engineering, no regressions.** This report documents
the coverage, quality, and known limitations of two new panels built from
Eurostat's Digital Intensity Index (DII), intended to replace EIBIS as the
digitalization measure once a Reviewer signs off on the panel itself
(Phase B). Reproducible from `analysis/panel_v2/build_panel.py`, which
depends on:

- `data/raw/eurostat/digital_intensity_index.csv` (new — `scripts/download_eurostat_dii.py`)
- `data/raw/eurostat/energy_import_dependency.csv` (new — `scripts/download_eurostat_energy_dependency.py`)
- `data/raw/eurostat/gdp_per_capita.csv` (existing — `scripts/download_eurostat.py`)
- `data/raw/eu_ets/eu-ets.csv` (existing — `scripts/download_eu_ets.py`)
- `data/raw/eibis/eibis_aggregate.csv` (existing — `scripts/download_eibis_aggregate.py`)

Outputs: `analysis/output/panel_country_year_v2.csv` (panel v2a),
`analysis/output/panel_sector_country_year_v2.csv` (panel v2b),
`analysis/output/panel_sector_country_year_v2_excl_combustion.csv` (v2b
minus its weakest-mapped sector — see §2), `analysis/output/panel_v2_dii_long.csv`
(the version-resolved DII series underlying both), and
`analysis/output/panel_v2b_crosswalk_emissions_weighted.csv` (the table in
§2).

**Revision note:** this version fixes two issues a review pass
(`analysis/panel_v2/panel_qc_review.md`) found in the first draft: (1) a
silent `fillna(0)` bug that treated a Eurostat-suppressed HI or VHI cell as
a definitional zero rather than a genuinely missing value, biasing 290 of
what were then 311 usable v2a rows and 782 of what were then 884 usable v2b
rows toward zero (see §5 for corrected counts); and (2) the crosswalk
confidence table was presented unweighted, which hid that 61.5% of panel
v2b's emissions mass sits on its single lowest-confidence mapping (§2). Both
are fixed below. The rest of the original report — the DII version mapping,
the coverage-gap finding, the Norway outlier, the 100%-cell explanation, and
the source-file substitution — was independently re-verified and is
unchanged.

## Headline: does the DII actually buy 11 years, as hoped?

**Partially, and unevenly.** The country-year panel (v2a) genuinely gets a
usable **2015-2025 window (11 years, 29 countries)** using DII's
manufacturing-wide (`nace_r2='C'`) series — a real improvement over EIBIS's
2023-2025. But the sector-level panel (v2b) does **not** get 11 years
uniformly: of the 7 ETS activities mapped to a DII sector, only 2
(**pig iron/steel** via `C24_C25`, **paper/cardboard** via `C16-C18`) have
DII data back to 2015. The other 5 (**combustion of fuels, refining of
mineral oil, cement clinker, lime/dolomite, bulk chemicals**) only have DII
data from **2021 onward** — their finer NACE codes (`C19`, `C20`, `C22_C23`,
`D35`) simply do not exist in this dataset before 2021, confirmed by
querying the live API directly, not assumed.

**Second, equally important headline (new in this revision): even within
the years and countries panel v2b does cover, its emissions mass is
concentrated almost entirely on the one sector mapping rated weakest.**
See §2 — this is not a footnote, it should be read before anything else in
this document if you are about to run Phase B on panel v2b.

## 1. DII methodology-version break — verified against the live API

`isoc_e_diin2`'s `indic_is` dimension carries **four incompatible
versions** of the Digital Intensity Index (v1 = `E_DI_*`, v2 = `E_DI2_*`,
v3 = `E_DI3_*`, v4 = `E_DI4_*`), and only one version is populated per year
— **except 2018, which has both v1 and v2**. Directly querying non-null
coverage by year and version (not assumed from Eurostat's documentation)
gives:

| Version | Years populated |
|---|---|
| v1 (`E_DI_*`) | 2015, 2016, 2017, 2018, 2019 |
| v2 (`E_DI2_*`) | 2018, 2020 |
| v3 (`E_DI3_*`) | 2021, 2023, 2025 |
| v4 (`E_DI4_*`) | 2022, 2024 |

**From 2021 onward the live version alternates every single year** (odd
years = v3, even years = v4) — a genuine, non-obvious property of the
source data confirmed empirically, not an assumption. `build_panel.py`
resolves this with an explicit `VERSION_IN_FORCE` mapping: v1 for
2015-2019 (using v1's own value for 2018 rather than v2's, to keep
2015-2019 on one continuous version), v2 for its unique year 2020, then v3/
v4 alternating from 2021. This was verified to apply identically across
every NACE sector queried — the version-in-force mapping is dataset-wide,
not sector-specific. Independently re-confirmed in review: matches cell for
cell.

**Consequence for Phase B, now made inspectable rather than left as prose:**
both output panels carry a per-row boolean column,
`dii_version_break_vs_prior_year`, computed from whether a row's own year
sits on a different DII methodology version than the immediately preceding
calendar year (True also when the preceding year predates DII entirely,
i.e. no same-methodology comparison is possible at all). **On the usable
rows, this flag is `True` for 188 of 290 v2a rows (64.8%) and 621 of 782
v2b rows (79.4%).** In other words: for the large majority of usable
observations, a first-differenced digitalization regressor built from this
panel would be crossing a methodology boundary. This is a first-order
design constraint for Phase B, not a footnote — whoever runs the next round
should read the column, not assume differencing is safe by default.

## 2. NACE-ETS sector crosswalk, and why the unweighted table is misleading

**Important deviation from the literal brief, documented here:**
`data/raw/eu_ets/eu-ets-sector-emissions.csv` (the file named in the task
brief) is an **EU-wide total by sector × year only — it has no country
column** (3 columns: `sector`, `year`, `emissions_mt`). It cannot support a
country × sector × year panel. Panel v2b is instead built from
`data/raw/eu_ets/eu-ets.csv` (country_code × main_activity_code × year),
filtered to the same 8 `main_activity_code` values that
`eu-ets-sector-emissions.csv` itself aggregates from.

| ETS code | ETS activity | DII `nace_r2` | Confidence | Note |
|---|---|---|---|---|
| 21 | Refining of mineral oil | `C19` | **High** | Clean 1:1 — NACE C19 ("coke and refined petroleum products") is essentially the same activity as the ETS category. |
| 42 | Production of bulk chemicals | `C20` | **Medium-high** | NACE C20 ("chemicals and chemical products") is broader than ETS's narrower "bulk chemicals by cracking/reforming/oxidation" definition, but it's the closest available NACE aggregate and the populations overlap heavily. |
| 24 | Production of pig iron or steel | `C24_C25` | **Medium** | DII only offers `C24_C25` combined ("basic metals" + "fabricated metal products"). ETS's steel activity sits inside C24 alone; C25 (fabricated metal products) dilutes the match. |
| 29 | Production of cement clinker | `C22_C23` | **Low-medium** | DII's finest available cut is `C22_C23` (rubber & plastic products + other non-metallic mineral products combined). Cement clinker sits inside C23 alone; C22 is unrelated and comparable in size. |
| 30 | Production of lime, or calcination of dolomite/magnesite | `C22_C23` | **Low-medium** | Same DII cell and caveat as cement clinker. |
| 36 | Production of paper or cardboard | `C16-C18` | **Medium** | DII's finest available cut is `C16-C18` (wood products + paper + printing combined). Paper (C17) is one of three sub-industries in this cell. |
| 20 | Combustion of fuels | `D35` | **Low** | **Conceptual mismatch, not just granularity**: ETS "Combustion of fuels" is a *process* occurring across many industries (any large combustion installation, wherever it sits organizationally), while DII's `D35` is an *enterprise classification* (electricity/gas/steam utilities only). Most combustion-activity ETS emissions actually come from installations inside chemical plants, refineries, steel mills etc. that are not themselves NACE D35 enterprises. `dii_high_share` for this row measures utility-sector digitalization; `d_log_emissions` measures combustion emissions economy-wide — different populations, correlation unknown. |
| 10 | Aviation | — | **No match** | No DII NACE breakdown exists for air transport specifically. Excluded from panel v2b entirely. |

**ETS activity `50` is also entirely excluded and unmentioned in the table
above by design, not oversight:** it is 90.4 Mt in 2024 (8.7% of
stationary-installation ETS emissions) but the *source data itself*
(`eu-ets.csv`) gives it a blank/unlabeled `main_activity_name` ("50", no
description) — unlike Aviation, there is no real-world activity to even
attempt a NACE mapping for.

### The emissions-weighted picture (new in this revision)

The table above is honest row-by-row but **unweighted** — a reader counts
"1 high, 2 medium-ish, 3 low-ish, 1 unmapped" and reasonably concludes the
panel is a mixed bag. Weighting by each sector's actual emissions mass
(2024, among usable v2b rows — i.e. rows where a DII match exists) tells a
different story:

| ETS activity | Confidence | 2024 Mt | Share of v2b mass |
|---|---|---|---|
| **20 Combustion of fuels** | **low** | 457.4 | **61.5%** |
| 24 Pig iron/steel | medium | 88.1 | 11.9% |
| 29 Cement clinker | low-medium | 75.3 | 10.1% |
| 21 Refining | high | 66.4 | 8.9% |
| 42 Bulk chemicals | medium-high | 25.0 | 3.4% |
| 30 Lime/dolomite | low-medium | 17.8 | 2.4% |
| 36 Paper/cardboard | medium | 13.1 | 1.8% |

**By confidence tier: low = 61.5%, low-medium = 12.5%, medium = 13.6%,
medium-high = 3.4%, high = 8.9%. Combining low + low-medium = 74.0% of the
panel's emissions mass; high + medium-high = only 12.3%.**

**The single mapping rated weakest carries essentially two-thirds of the
whole panel.** This is not a mixed bag of varying quality — it is a panel
dominated by the one relationship (utility-sector enterprise digitalization
vs. economy-wide combustion emissions) that has the clearest conceptual
reason to be unreliable. Activity 20 alone is 57.0% of *all* EU ETS
stationary emissions in 2024 (588.9 of 1,033.5 Mt) — this is not a niche
cell that happened to get a bad mapping, it is the largest ETS activity by
construction, and it is also the one DII covers worst conceptually.

**Two Phase-B-ready cuts are provided, deliberately without a
recommendation on which to use:**

- `analysis/output/panel_sector_country_year_v2.csv` — the full 7-sector
  panel, including ETS activity 20.
- `analysis/output/panel_sector_country_year_v2_excl_combustion.csv` — the
  same panel with ETS activity 20 dropped (2,785 of the original 3,421
  rows remain).

**Phase-B instruction, not a decision made here:** any regression run on
panel v2b should report results **from both cuts side by side**, not pool
without sector fixed effects, and not silently pick one cut and hide the
other. If the full panel is used, the weighted-mass table above should
travel with any result, since a pooled coefficient on the full panel is,
by construction, mostly a statement about the combustion/D35 relationship
whether or not that is what a reader would assume.

## 3. Panel v2a's own scope mismatch: manufacturing DII vs. total ETS emissions

A related, one-level-up version of the same problem exists in panel v2a.
`ets_total` (the outcome) is `main_activity_code == "20-99"` — **all**
stationary ETS installations, including combustion (≈57% of the total).
`dii_high_share_manufacturing` (`nace_r2 == 'C'`) covers manufacturing
enterprises only — it does not include combustion/utility installations
(NACE D35) at all. So v2a regresses a change in *total* ETS emissions on a
digitalization measure that structurally does not cover the majority of
what it is explaining. This is a defensible country-level *proxy* choice
(manufacturing digitalization standing in for overall industrial
digitalization), but it is a real scope mismatch that should be stated,
not assumed away.

An alternative column, **`dii_high_share_c_or_d35`**, is provided: a simple
(unweighted, enterprise-count-blind) average of the `C` and `D35` shares
where both exist, widening coverage toward the combustion/utility side —
but it is a cruder blend of two different enterprise populations, not a
proper weighted aggregate, and is offered as an alternative to compare
against, not a fix. It is non-missing for 291 of 636 v2a rows (`D35`
coverage is thinner than `C`'s: 2021-2025 only, same as the sector table in
§1).

**Also worth remembering (per review): DII covers only enterprises with
≥10 employees** (`size_emp == 'GE10'`, the only breakdown this dataset
offers) — it is not a population-wide digitalization measure, and
micro-enterprises are excluded by construction from every DII column in
both panels.

## 4. Panel v2a: country × year

- **Nominal source range:** EU ETS verified emissions available
  2005-2025; DII (`nace_r2='C'`, manufacturing) available 2015-2025.
- **Rows with both `d_log_emissions` and `dii_high_share_manufacturing`
  non-missing: 290 rows, 29 countries, 2015-2025 (11 years)** — corrected
  from 311 after the HI/VHI missingness fix (§5).
- **Countries with zero DII coverage at all:** Iceland (IS), Liechtenstein
  (LI), Northern Ireland (XI). Norway (NO) *is* covered.
- **Secondary/robustness column, not discarded:** `eibis_digital_multi`
  populated for its native 2023-2025 window only (87.3% missing over the
  full panel — expected, matches `first_pass_analysis.md`).
- **Missingness by column** (share of all 636 country-year rows,
  2005-2025, after the fix):

  | Column | Missing share |
  |---|---|
  | `d_log_emissions` | 5.0% |
  | `dii_high_share_manufacturing` | 54.4% (up from 51.1% pre-fix — the extra ~3pp is genuinely-suppressed cells that were wrongly non-missing before) |
  | `dii_high_share_d35` | 86.6% |
  | `dii_high_share_c_or_d35` | 54.2% |
  | `eibis_digital_multi` | 87.3% |
  | `d_log_gdp_per_capita` | 7.9% |
  | `energy_import_dependency_pct` | 10.1% |

## 5. Panel v2b: country × ETS-sector × year

- **3,421 total rows** (32 countries × 7 mapped sectors × up to 21 years,
  unbalanced).
- **782 rows with both `d_log_emissions` and `dii_high_share`
  non-missing** — corrected from 884 after the HI/VHI missingness fix (down
  102 rows, exactly matching the review's estimate).
- **Usable rows by sector × year** (country count with both variables
  present, post-fix):

  | ETS activity | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
  |---|---|---|---|---|---|---|---|---|---|---|---|
  | 20 Combustion of fuels | 0 | 0 | 0 | 0 | 0 | 0 | 19 | 16 | 16 | 17 | 17 |
  | 21 Refining of mineral oil | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 4 | 10 | 12 | 9 |
  | 24 Pig iron or steel | 22 | 22 | 23 | 23 | 21 | 21 | 22 | 20 | 20 | 19 | 18 |
  | 29 Cement clinker | 0 | 0 | 0 | 0 | 0 | 0 | 17 | 16 | 17 | 20 | 18 |
  | 30 Lime/dolomite | 0 | 0 | 0 | 0 | 0 | 0 | 16 | 15 | 15 | 17 | 16 |
  | 36 Paper or cardboard | 19 | 19 | 20 | 17 | 16 | 17 | 20 | 18 | 18 | 20 | 20 |
  | 42 Bulk chemicals | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 8 | 10 | 11 | 11 |

  Coverage dropped meaningfully in several sector-year cells after the fix
  (e.g. refining 2022 fell to 4 countries) — the HI/VHI suppression the fix
  now correctly respects concentrates exactly in these small, niche-sector
  cells, as expected. **This table should be read together with §2's
  emissions-weighted confidence table, not in isolation**: sectors with the
  thinnest country coverage here (refining, bulk chemicals) are not the
  ones carrying the panel's emissions mass — combustion is, and it has
  comparatively good coverage (16-19 countries/year) but the weakest
  conceptual mapping.

## 6. Fixing the HI/VHI missingness bug — what changed and why

**Fix 1, applied in `build_panel.py`:** `dii_high_share` is now computed as
`(HI + VHI).sum(axis=1, min_count=2) / 100`, which is `NaN` whenever
*either* HI or VHI is missing, not only when both are. The prior
`fillna(0) + fillna(0)` treated a Eurostat confidentiality suppression
(small underlying enterprise population, value withheld) as a definitional
zero — concrete examples confirmed against the live API by the review pass
(e.g. Germany, `C19`, 2022: HI=57.63 reported, VHI suppressed; the old code
recorded a share of 0.576 when the true share is unknown but at least
0.576, not "57.6% and that's the whole story"). The review found affected
cells had a mean recorded share of 0.120 vs. 0.259 for unaffected cells —
a systematic downward bias, not random noise, concentrated in exactly the
small-population sectors and countries this report already flags as noisy
elsewhere.

**Confirmed row counts changed by the fix:**

| | before | after | rows lost |
|---|---|---|---|
| Panel v2a usable rows | 311 | 290 | 21 |
| Panel v2b usable rows | 884 | 782 | 102 |

Both match the review's estimates exactly (21/311, 102/884). No attempt was
made to recover or impute the suppressed values — they are genuinely
missing information, not a value that can be reconstructed from what's
available in this dataset.

## 7. Descriptive statistics for the new variables (post-fix)

**Panel v2a (usable rows, n=290):**

| Variable | n | mean | SD | min | max |
|---|---|---|---|---|---|
| `dii_high_share_manufacturing` | 290 | 0.229 | 0.136 | 0.010 | 0.656 |
| `d_log_gdp_per_capita` | 284 | 0.021 | 0.035 | -0.121 | 0.211 |
| `energy_import_dependency_pct` | 262 | 31.1 | 133.2 | -682.1 | 103.1 |
| `d_log_emissions` | 290 | -0.053 | 0.113 | -0.623 | 0.243 |

**Panel v2b (usable rows, n=782):**

| Variable | n | mean | SD | min | max |
|---|---|---|---|---|---|
| `dii_high_share` | 782 | 0.277 | 0.227 | 0.000 | 1.000 |
| `d_log_gdp_per_capita` | 772 | 0.022 | 0.031 | -0.121 | 0.142 |
| `energy_import_dependency_pct` | 671 | 16.0 | 157.7 | -682.1 | 96.3 |
| `d_log_emissions` | 782 | -0.071 | 0.449 | -5.836 | 3.532 |

Note the v2a minimum for `dii_high_share_manufacturing` moved from 0.000
(pre-fix) to 0.010 (post-fix) — direct evidence that at least one of the
old reported zeros was manufactured by the bug rather than observed. The
v2b minimum remains 0.000; those are independently confirmed to be cells
where both HI and VHI are genuinely reported (non-suppressed) as zero, not
an artifact.

Full unchanged descriptive material from the first draft (Norway's -682%
energy-import-dependency outlier, real and stable across years 2017-2024;
the 100%-`dii_high_share` cells in niche sectors, confirmed to have both HI
and VHI genuinely present and summing to 100, not a symptom of the
missingness bug) — see the original discussion, re-verified by the review
and unchanged here.

## 8. EU accession cohort lookup

Hardcoded mapping (`EU_ACCESSION_COHORT` in `build_panel.py`), attached to
both panels as `eu_accession_cohort`:

| Cohort | Countries | n |
|---|---|---|
| EU-15 | AT, BE, DE, DK, EL, ES, FI, FR, IE, IT, LU, NL, PT, SE, UK | 15 |
| 2004 | CZ, EE, CY, LV, LT, HU, MT, PL, SK, SI | 10 |
| 2007 | BG, RO | 2 |
| 2013 | HR | 1 |

Four geographies have no accession cohort (`NaN`, by design): Iceland,
Liechtenstein, Norway (EEA/EFTA, never EU members) and Northern Ireland
(`XI`, a UK sub-code). UK is coded EU-15 by its historical accession-era
cohort even though it has since left the EU — flag this if Phase B
interprets the cohort variable as current EU membership rather than
historical accession wave.

## 9. Files

- `scripts/download_eurostat_dii.py`, `scripts/download_eurostat_energy_dependency.py`
  — fetch scripts, both added to `scripts/download_all.py`.
- `data/raw/eurostat/digital_intensity_index.csv` — raw long-format DII
  pull (all 4 versions, HI/VHI only, 7 NACE sectors), 2,809 rows.
- `data/raw/eurostat/energy_import_dependency.csv` — raw energy import
  dependency, siec=TOTAL, 814 rows.
- `analysis/panel_v2/build_panel.py` — builds both panels, the
  excl-combustion cut, and the emissions-weighted crosswalk table.
- `analysis/output/panel_country_year_v2.csv` — panel v2a, 636 rows.
- `analysis/output/panel_sector_country_year_v2.csv` — panel v2b, 3,421
  rows (full 7-sector set).
- `analysis/output/panel_sector_country_year_v2_excl_combustion.csv` —
  panel v2b with ETS activity 20 dropped, 2,785 rows.
- `analysis/output/panel_v2_dii_long.csv` — version-resolved DII series
  underlying both panels.
- `analysis/output/panel_v2b_crosswalk_emissions_weighted.csv` — the
  emissions-weighted confidence table in §2.

## What this QC report does NOT do

- **No regressions.** Per the brief, this is Phase A only.
- **No claim about whether DII will show a different result than EIBIS
  did.** That is the Phase-B question this panel is being built to
  support.
- **No decision on whether ETS activity 20 (combustion) should be
  included in Phase B.** Both cuts are provided; the choice, and the
  obligation to report both side by side if the full panel is used, is
  left to whoever runs Phase B, informed by the emissions-weighted table
  in §2.
- **No resolution of the version-break problem** — quantified via the new
  `dii_version_break_vs_prior_year` column (§1), but not resolved; that
  remains a Phase-B modeling choice.
