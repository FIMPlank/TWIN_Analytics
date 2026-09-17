# Phase C: three EU refinements (NUTS2 regional panel, emissions intensity, firm-size split)

Reproducible from `analysis/phase_c_build_panel.py` (item 1's data
engineering — geocoding, composite construction) and
`analysis/phase_c_analysis.py` (all three items' regressions). New raw data
under `data/raw/eurostat/` (regional digitalization components, absolute
industrial value-added), `data/raw/geo/` (NUTS2 boundaries), and
`data/raw/eprtr/F1_4_Air_Releases_Facilities.csv` (facility-level E-PRTR,
gitignored, ~72MB — fetch via the URL documented in
`analysis/phase_c_build_panel.py`'s docstring or `download_eprtr.py --all`).
Builds on the Reviewer-approved Phase B panels (`analysis/phase_b_analysis.md`)
for items 2 and 3.

**Revision note:** this version corrects issues a review pass
(`analysis/phase_c_review.md`) found in items 1 and 3. **Item 1** was
clustered at the wrong level (region instead of country), is dominated by
a single country (Spain, 36% of rows) whose removal flips the p-value by
two orders of magnitude, and used a pollutant-definition substitution that
turns out to be a real confound (correlated with the digitalization
regressor via Nordic countries' heavy biomass use), not just added noise —
**item 1 is now reported as infeasible with current E-PRTR facility-level
coverage, not as a number**. **Item 3**'s large-firm-vs-all-firms
comparison was not apples-to-apples (15 countries vs. 27); on the correct
like-for-like comparison, the large-firm effect **disappears** — what was
actually detected is a pattern specific to a 15-country subset of large,
lower-income EU-ETS emitters, present regardless of firm-size cut, and
itself fragile to which country is dropped. The section is rewritten
around that finding under its correct label. **Item 2 required no
changes** — independently verified clean by the review.

## Headline

- **Item 1 (NUTS2 regional panel): infeasible with current data, not a
  result.** The panel technically works (geocoding is clean — see below),
  but three compounding problems mean no number from it should be reported
  as a finding: (a) the naive p=0.058-0.066 reported in the first draft
  used the wrong clustering level (58 regions; the panel only has 8
  independent country clusters) — correctly clustered, p=0.152-0.250,
  not close to significant; (b) the panel is dominated by one country
  (Spain, 36% of rows) whose removal *more than doubles* the coefficient
  and drops p to 0.003 — in the *opposite* direction from what correct
  clustering did, meaning the estimate is not just imprecise but
  structurally unstable; (c) the pollutant-definition substitution needed
  to get a usable sample size inflates Nordic countries' emissions
  figures by 2-6x relative to non-Nordic countries (Sweden 5.6x, Finland
  2.1x, most others ~1.0-1.3x) because of biomass energy use that
  independently correlates with those same countries' high digitalization
  — a confound baked into the outcome variable, not just added
  measurement noise. Full detail below; no regression coefficient from
  this panel is presented as a finding.
- **Item 2 (emissions intensity): unchanged, verified clean.** Switching
  the outcome from raw emissions change to emissions-per-unit-of-
  industrial-output does not produce a significant result anywhere, and
  if anything pulls the (already non-significant) v2a coefficient further
  toward zero (+0.069 raw → +0.030 intensity, bare; +0.081 → +0.015,
  controlled).
- **Item 3 (EIBIS firm-size split): the original framing was backwards.**
  The first draft compared large-firms (15 countries) against all-firms
  (27 countries) and reported the large-firm result as stronger — an
  apples-to-oranges comparison. On the correct like-for-like comparison
  (all-firms on the *same* 15 countries), **the all-firms coefficient is
  larger and closer to significance than the large-firm one** (+0.352,
  p=0.057 vs. +0.273, p=0.062), and the two firm-size measures correlate
  at r=0.952 — there is essentially no independent firm-size signal here.
  What is real is a **15-country subset pattern**: those countries are
  systematically the larger, lower-income EU-ETS emitters (median GDP
  €25,600 vs. €31,745; median 2024 ETS emissions 23.9 Mt vs. 6.6 Mt;
  83.6% of total 2024 ETS mass), and restricting to them produces a
  nominally-significant-ish positive coefficient regardless of which
  firm-size cut is used. It is also fragile — leave-one-out shows
  dropping Bulgaria alone cuts the coefficient by 45% (0.273 → 0.151) —
  so this is reported as a lead worth a dedicated future test, not a
  finding.

Across all three items, the project's overall conclusion is unchanged: no
digitalization-emissions relationship in this data survives correct,
small-cluster-robust inference and a full fragility check, at the country
level, the sector level, or (as far as current data can determine) the
regional level.

## Item 1: NUTS2 regional panel — infeasible with current data

### Data engineering (unaffected by the issues below — this part holds up)

**Digitalization side.** Eurostat has no regional Digital Intensity Index;
five separate NUTS2-region enterprise-survey components were fetched
instead (`scripts/download_eurostat_dii_regional.py`), one headline
indicator picked per dataset (closest to "any/overall adoption" in that
dataset):

| Component | Dataset | Indicator | Years (confirmed live) |
|---|---|---|---|
| AI use | `isoc_r_eb_ain2` | `E_AI_TANY` (any AI technology) | 2023, 2024, 2025 |
| Customer/supplier integration | `isoc_r_eb_icsn2` | `E_INV4S_AP` (automated-processing eInvoicing — closest available proxy) | **2023 only** |
| Internal process integration | `isoc_r_eb_iipn2` | `E_BSANY` (any ERP/CRM/BI software) | 2023, 2025 (**skips 2024**) |
| E-commerce sales | `isoc_r_ec_eseln2` | `E_AWSELL` (web sales — only indicator available) | 2023, 2024, 2025 |
| Data analytics | `isoc_r_eb_dan2` | `E_DA` (own or external data analytics) | 2025 only at `nace_r2='C'` |

**Composite:** each component z-scored within its own sample, then
averaged across whichever components have data for a region-year (never
requiring all five). Of 97 usable region-years, 43 average all 4
practically-available components (`icsn2`'s single year means it almost
never overlaps with the others), 49 average 2, and a handful average 1 or
3 — genuinely different measurements pooled into one column, flagged
throughout and checked as a robustness cut below.

**Emissions side — geocoding.** E-PRTR's facility-level file (72MB,
gitignored) has per-facility `Longitude`/`Latitude`. Facilities were
geocoded to NUTS2 regions via point-in-polygon (`geopandas.sjoin`,
`predicate="within"`) against Eurostat/GISCO's highest-resolution
NUTS2021 boundaries, with a nearest-polygon fallback for exact-`within`
failures. **The geocoding itself is excellent and holds up under
independent re-checking** (the review independently re-geocoded a
300-facility random sample and found 289/300 exact matches, zero false
positives — every non-match was a documented offshore-fallback case).

**Two geocoding-failure classes, correctly distinguished:**

| Cause | Count | Example |
|---|---|---|
| Offshore point-in-polygon limitation (North Sea platforms — no NUTS2 land polygon actually contains them) | 17 facilities | TOTAL E&P Danmark, INEOS E&P, Sleipner Vest, Statfjord, Armada |
| **Source-data coordinate corruption** (truncated latitude digit) | 1 facility | FJERNVARME FYN FYNSVÆRKET A/S (Denmark): latitude recorded as 5.33 instead of 55.33, geocoded to Sicily |

The single coordinate-corruption case was originally lumped in with the
offshore cases; it is a different defect class (bad source data, not a
geocoding-method limitation) and is now flagged separately, with a
latitude-plausibility check (facilities outside 34°N-71°N, implausible for
continental Europe, are flagged as likely corrupted rather than offshore)
added to the build script. Both classes are excluded from the aggregated
panel either way — this record only appears in 2015, outside the
2023-2024 analysis window, so it does not affect any number below — but
the distinction matters for anyone extending this pipeline to other years.

### Why no number from this panel is reported as a finding

**Problem 1 — wrong clustering level.** The first draft clustered
inference on `NUTS_ID` (58 region clusters). But regions within a country
share the same national digitalization survey wave, energy prices, and
carbon policy — the panel only has **8 independent country clusters**.
Reclustering correctly:

| Spec | Clustered by region (wrong) | Clustered by country (correct) |
|---|---|---|
| C1 bare | coef +0.099, p(wild)=0.066 | coef +0.099, **p(wild)=0.250** (p naive z=0.152) |
| C2 + country FE | coef −0.007, p(wild)=0.917 | coef −0.007, **p(wild)=0.922** (p naive z=0.934) |

At the correct clustering level, C1's marginal p-value — the closest any
model in this project came to significance in the first draft — is not
close to significant at all.

**Problem 2 — dominated by one country.** Spain alone is 35 of 97 rows
(36.1%) of the panel. Leave-one-country-out on C1 (all 8 countries,
region-clustered naive z, matching the review's own check):

| Dropped | n | coef | p (naive z, region-clustered) |
|---|---|---|---|
| **ES** | 62 | **+0.195** | **0.003** |
| SI | 93 | +0.099 | 0.059 |
| HR | 89 | +0.102 | 0.063 |
| RO | 89 | +0.100 | 0.078 |
| AT | 85 | +0.101 | 0.094 |
| DK | 87 | +0.091 | 0.109 |
| BG | 91 | +0.066 | 0.194 |
| HU | 83 | +0.061 | 0.228 |

Dropping Spain **doubles** the coefficient and drops p to 0.003 — in the
opposite direction from what correcting the clustering level did. The
estimate swings across two orders of magnitude in p-value depending on
which single country (of only 8) is present. This is not an imprecise
estimate that a bigger sample would sharpen — it is not a stable estimate
at all.

**Problem 3 — the pollutant substitution is a confound, not just noise.**
Only 15 countries report the "excluding biomass" CO2 field the country-
level analysis uses (n=15, unusable, as originally found). The broader
"Carbon dioxide (CO2)" field used to get a workable sample (n=97) is **not
neutral**: where both fields are reported for the same facility-year, the
broader field's inflation relative to the biomass-excluded figure is
sharply country-asymmetric:

| Country | Median inflation ratio (incl./excl. biomass) |
|---|---|
| **Sweden** | **5.61×** |
| **Finland** | **2.05×** |
| Denmark | 1.28× |
| Germany | 1.27× |
| Bulgaria, Slovenia | ~1.13× |
| Ireland, UK, Romania | ~1.03-1.07× |
| Cyprus, Czechia, Estonia, Norway, Malta, Netherlands | 1.00× |

Sweden and Finland — both heavy biomass-energy users *and* among the most
digitalized economies in the sample — have their emissions figures
inflated 2-6x by the pollutant substitution, while most other countries
are barely affected. **The measurement error correlates with the
regressor.** Worse, year-over-year *changes* in the substituted figure
partly reflect biomass-combustion swings (heating demand, forestry
cycles, renewable-energy policy) that have nothing to do with industrial
digitalization. Of the 8 countries in the usable panel, only 4 (BG, DK,
RO, SI) have a known biogenic share at all; the other 4 (AT, ES, HR, HU)
have an entirely unknown biogenic share, since they never report the
biomass-excluded field.

**Given all three problems, the coordinator's own framing applies
directly: 8 country clusters is too few to trust either the marginal C1
number or the null C2 number, before even reaching the confound problem.**
Restricting to the countries with a known biogenic share (BG, DK, RO, SI)
reduces to the original, already-established-as-unusable n=15 sample.
Attempting a different E-PRTR pollutant field would face the same 15-
country ceiling that motivated the substitution in the first place.
**Conclusion: the NUTS2 regional panel is infeasible to analyze with
current E-PRTR facility-level coverage.** This is reported honestly as a
null/infeasibility finding, not smoothed over — per the coordinator's own
framing, an 8-cluster panel producing no usable answer is neither
surprising nor a failure of the exercise.

**Robustness note (not decisive, included for completeness):** restricting
to the 43 region-years whose composite averages all 4 practically-
available components (removing the composite-heterogeneity concern) gives
coef=−0.021, p(wild)=0.986, G=6 — even less informative, with only 6
country clusters remaining. This does not rescue anything; it is
additional evidence that no cut of this panel currently supports a
trustworthy estimate.

## Item 2: emissions intensity as outcome

No changes from the previous draft — independently verified clean by the
review (units, the exact log-decomposition, the merge, and the headline
numbers all reproduce exactly).

**Data.** `nama_10_a10` re-fetched with `unit=CLV20_MEUR` (chain-linked
volumes, million EUR — the absolute level, not the percentage-of-economy
share already in the panel), `nace_r2='B-E'` (same industry aggregate used
throughout). Emissions intensity is constructed as `verified_emissions /
industry_va_meur`; since both are logged, `d_log(intensity) = d_log
(emissions) − d_log(industry_va)` — an exact decomposition (verified
numerically to 1e-9), not an approximation.

**Results, intensity vs. raw outcome, identical samples, side by side:**

| Model | Outcome | n | G | coef | p (naive z) | p (t, G−1) | **p (wild bootstrap)** |
|---|---|---|---|---|---|---|---|
| v2a bare | intensity | 284 | 28 | +0.030 | 0.682 | 0.685 | **0.720** |
| v2a bare | raw (same sample) | 284 | 28 | +0.069 | 0.321 | 0.330 | **0.345** |
| v2a +controls | intensity | 284 | 28 | +0.015 | 0.836 | 0.837 | **0.839** |
| v2a +controls | raw (same sample) | 284 | 28 | +0.081 | 0.263 | 0.272 | **0.295** |
| v2b bare, full | intensity | 772 | 28 | +0.050 | 0.700 | 0.703 | **0.756** |
| v2b bare, full | raw (same sample) | 772 | 28 | +0.085 | 0.452 | 0.458 | **0.510** |
| v2b +controls, full | intensity | 772 | 28 | −0.110 | 0.397 | 0.404 | **0.531** |
| v2b +controls, full | raw (same sample) | 772 | 28 | −0.069 | 0.543 | 0.548 | **0.640** |
| v2b bare, excl-combustion | intensity | 687 | 27 | +0.055 | 0.740 | 0.742 | **0.785** |
| v2b bare, excl-combustion | raw (same sample) | 687 | 27 | +0.084 | 0.571 | 0.576 | **0.611** |
| v2b +controls, excl-combustion | intensity | 687 | 27 | −0.138 | 0.409 | 0.416 | **0.541** |
| v2b +controls, excl-combustion | raw (same sample) | 687 | 27 | −0.097 | 0.520 | 0.526 | **0.639** |

**Nothing reaches significance under either outcome.** v2a's positive
coefficient shrinks toward zero under intensity; v2b's controlled-spec
negative coefficient grows somewhat larger under intensity on both cuts,
remaining non-significant throughout. This item does not surface a masked
effect, nor does it show the Phase B null was an artifact of not
accounting for output-driven emissions growth.

## Item 3: EIBIS firm-size split — reframed

**The original comparison was not apples-to-apples.** The first draft
compared the `Large`-firm EIBIS series (15 countries) against the
`ALL`-firms series (27 countries) and reported the large-firm coefficient
as larger and closer to significance. The missing comparison is
`ALL`-firms on the **same 15 countries** that report a large-firm
breakdown:

| Model | Firm-size cut | Countries | n | G | coef | p (naive z) | p (t, G−1) | **p (wild bootstrap)** |
|---|---|---|---|---|---|---|---|---|
| E1a | ALL | 27 (original baseline) | 81 | 27 | +0.178 | 0.216 | 0.228 | **0.271** |
| **E1b** | **ALL** | **same 15 as E1c** | **45** | **15** | **+0.352** | **0.036** | **0.054** | **0.057** |
| E1c | Large | 15 | 45 | 15 | +0.273 | 0.051 | 0.071 | **0.062** |

**On the correct, like-for-like comparison, all-firms performs *better*
than large-firms** — the coefficient falls from +0.352 to +0.273 and the
wild-bootstrap p rises from 0.057 to 0.062 when switching from all-firms
to large-firms only. The earlier "1.5x larger, closer to significant"
claim held only against the mismatched 27-country baseline.

**Why:** `corr(digital_multi_ALL, digital_multi_Large)` on this 15-country
overlap is **r=0.952** — the two series are near-identical. There is
essentially no independent firm-size information available to detect a
firm-size-specific effect with, which is the mechanical reason large-firm
and all-firms land in almost the same place.

### What is actually there: a 15-country subset pattern, not a firm-size effect

The 15 countries that happen to report a large-firm EIBIS breakdown (AT,
BE, BG, DE, EL, ES, FR, HR, HU, IT, PL, PT, RO, SE, SI) are systematically
different from the other 12 (CY, CZ, DK, EE, FI, IE, LT, LU, LV, MT, NL,
SK) — and different in a direction that matters for this analysis:

| | 15-country subset | Other 12 |
|---|---|---|
| Median GDP per capita (2024) | €25,600 | €31,745 |
| Median 2024 ETS emissions | 23.9 Mt | 6.6 Mt |
| Share of total 2024 ETS emissions mass | **83.6%** | 16.4% |

This is the larger, lower-income, heavier-industrial-emitter half of the
EU. Restricting to this subset produces a nominally-significant-ish
positive coefficient **regardless of which firm-size cut is used**
(E1b and E1c both land around p=0.06) — a sample-composition pattern, not
a firm-size finding.

**It is also fragile, in the same way every other marginal result in this
project has turned out to be.** Leave-one-country-out on the large-firm
spec (E1c), all 15 clusters:

| Dropped | coef | p (naive z) |
|---|---|---|
| **BG** | **+0.151** | 0.063 |
| DE | +0.268 | 0.059 |
| HU | +0.293 | 0.056 |
| PT | +0.273 | 0.055 |
| ES | +0.283 | 0.055 |
| RO | +0.290 | 0.053 |
| IT | +0.273 | 0.050 |
| SI | +0.295 | 0.036 |
| EL | +0.317 | 0.032 |
| HR | +0.336 | 0.018 |
| FR | +0.282 | 0.139 (max p, dropping France) |

**Dropping Bulgaria alone cuts the coefficient by 45%** (0.273 → 0.151) —
the same country that drove the original, now-resolved EIBIS false
positive from the very first round of this project is again the single
most influential observation in a marginal result. This pattern is more
robust than that original false alarm (which died outright at p≈0.21 once
correctly clustered), but it is not clean, and should not be presented as
more than a lead.

**Bottom line for item 3:** the firm-size framing added nothing — DII has
no size breakdown to cross-check against in any case (confirmed:
`isoc_e_diin2`'s `size_emp` dimension is `GE10` only, no further
breakdown, checked against the live API), and EIBIS's own large-firm and
all-firms measures are too correlated to isolate a firm-size effect from a
country-composition effect. What is genuinely worth a dedicated future
test is whether the 15-country subset of larger, lower-income EU-ETS
emitters behaves differently from the rest of the EU — a real, specific,
but currently unconfirmed and Bulgaria-sensitive pattern.

## Combined read across items 1-3

Item 1 produces no usable number at all once its three compounding
problems (wrong clustering, single-country dominance, confounded pollutant
substitution) are addressed — reported as infeasible with current data,
not forced through to a headline figure. Item 2 confirms emissions
intensity does not change the Phase B picture. Item 3's apparent finding
(a large-firm effect) evaporates under a like-for-like comparison and is
replaced by a different, more specific, but still fragile lead (a
big-emitter/lower-income country subset pattern) that itself halves under
leave-one-out. None of the three refinements produces a robust, significant
result; the project's standing conclusion — no digitalization-emissions
relationship survives correct inference at any level of aggregation tried
so far — is unchanged and, if anything, further reinforced by how
consistently marginal results in this project have turned out to trace to
a single influential country once checked properly.

## Files

- `scripts/download_eurostat_dii_regional.py`, `scripts/download_nuts2_boundaries.py`,
  `scripts/download_eurostat_industry_va_absolute.py` — fetch scripts, all
  added to `scripts/download_all.py` (the large E-PRTR facility file is
  not — same pattern as the other large E-PRTR tables, needs
  `download_eprtr.py --all`).
- `data/raw/eurostat/dii_regional_components.csv`,
  `data/raw/eurostat/industry_value_added_absolute.csv` — Eurostat pulls.
- `data/raw/geo/nuts2_2021.geojson` — NUTS2021 boundaries (gitignored,
  ~18MB).
- `data/raw/eprtr/F1_4_Air_Releases_Facilities.csv` — facility-level
  E-PRTR (gitignored, ~72MB).
- `analysis/phase_c_build_panel.py` — item 1's geocoding and panel
  construction, now with the offshore-vs-corruption coordinate-
  plausibility check.
- `analysis/phase_c_analysis.py` — all three items' regressions, now
  including country-clustered inference, leave-one-out for items 1 and 3,
  the biomass-inflation-ratio table, and the like-for-like item-3
  comparison.
- `analysis/output/phase_c_panel_region_year_v3_excl_biomass.csv`,
  `phase_c_panel_region_year_v3_incl_biomass.csv` — panel v3, both
  pollutant definitions (kept for inspection; not used for a headline
  number).
- `analysis/output/phase_c_facility_geocoding_excl_biomass.csv`,
  `phase_c_facility_geocoding_incl_biomass.csv` — one row per unique
  facility with its assigned NUTS2 region and offshore/corruption
  classification.
- `analysis/output/phase_c_item1_leave_one_out.csv`,
  `phase_c_biomass_inflation_ratio.csv` — item 1's fragility and confound
  evidence.
- `analysis/output/phase_c_item2_results.csv` — item 2's full table.
- `analysis/output/phase_c_item3_all_large_correlation.csv`,
  `phase_c_item3_leave_one_out.csv`, `phase_c_item3_subset_composition.csv`
  — item 3's reframed evidence.

## What this analysis does NOT show

- It does **not** establish anything about a regional digitalization-
  emissions relationship — item 1 is reported as infeasible to analyze
  with current data, not as a null result with a number attached to it.
- It does **not** show emissions intensity was hiding an effect the raw
  outcome missed, or vice versa — neither outcome produces a significant
  result under any specification tested.
- It does **not** show a firm-size-specific digitalization effect — the
  apparent large-firm result in the first draft was an artifact of
  comparing mismatched country samples, and disappears on a like-for-like
  comparison.
- It does **not** confirm the big-emitter/lower-income-country subset
  pattern found in item 3 as real — it is a specific, worth-investigating
  lead, not an established finding, and is itself sensitive to dropping
  a single country (Bulgaria).
- It does **not** change the overall conclusion from Phase B: no
  digitalization-emissions relationship in this data survives correct,
  small-cluster-robust inference, at any level of aggregation this project
  has been able to test.
