# US extension: panel QC report

**Phase A discipline, EU-style: data engineering and coverage documented
before any regression is interpreted.** This report covers the two new US
panels (state x year, county x year) built to test whether the EU's null
digitalization-emissions finding (see `analysis/phase_b_analysis.md`) is
EU/ETS-specific or a more general fact. Reproducible from
`analysis/us_extension/build_panel.py`, which depends on:

- `data/raw/epa_ghgrp/facilities.csv`, `emissions.csv`, `sector_lookup.csv`
  (new — `scripts/download_epa_ghgrp.py`)
- `data/raw/bls_qcew/qcew_tech_industries_2015_2023.csv` (new —
  `scripts/download_bls_qcew_tech.py`)

Outputs: `output/panel_state_year_us.csv` (756 rows, 54 states/
territories, 2010-2023), `output/panel_county_year_us.csv` (27,955 rows,
2,112 counties, 2010-2023).

**Revision note (round 2, post-Reviewer):** a Reviewer pass
(`analysis/us_extension/review.md`) independently re-derived every number
in this report and in `us_analysis.md`, confirmed the supplier-sector
catch (§2) and the Census refusal (§1) as correct, ran a leave-one-state-
out check this report had omitted (no single-state artifact in either
direction), and found one blocking bug and one blocking framing error,
both fixed then: (1) a silent NaN→0 conversion in the county-emissions
aggregation (§5) that understated 15.8% of direct-emitter facility-years
by a *growing* amount over time (0% in 2010-2012, 28.5% by 2023); (2) the
BLS QCEW substitute regressor is not just "a different construct" from
EIBIS/DII, it is empirically **anti-correlated** with how industrial a
state's economy is (r=-0.59 with log CO2e per employee) — quantified in
§1 below.

**Revision note (round 3, post-Reviewer round 2):** the round-2 edit that
added the missingness fix **accidentally deleted the pre-existing
biogenic-CO2 exclusion filter** (`BIOGENIC_GAS_ID` and its surrounding
comments survived, the actual filter line did not) — the round-2
delivered panels silently included biogenic CO2 (4.67% of direct-emitter
mass, concentrated non-randomly in pulp/paper and biomass-co-firing
facilities) despite this report's §3 and the code's own docstring both
still claiming it was excluded. **This is exactly the failure mode the
supplier catch (§2) was praised for avoiding — a panel that looks
entirely plausible while silently measuring something other than what it
says — and it happened here on the very next edit.** Restored in §3/§5
below, with an assertion added to `build_panel.py` so this specific
filter cannot silently vanish again. A second, related bug was chased
down in the same round: a naive `.diff()` on a unit's emissions series
spans whatever gap sits between consecutive *rows*, not consecutive
*calendar years* — a unit missing a whole year's row (not just a NaN
value) gets a multi-year change mislabeled as one year. Both this
build and an independent Reviewer reconstruction had, at different
points, produced spurious multi-year jumps this way; both are now
guarded against (§5).

## Headline: this build required two real substitutions relative to the
task brief, both found only by querying the live APIs, not from
documentation

1. **The Census ABS technology module (the brief's intended
   digitalization measure) is blocked without a Census API key that this
   pipeline does not obtain on its own.** See §1.
2. **Two-thirds of raw GHGRP-reported CO2e is NOT facility emissions at
   all — it's upstream fuel-supply accounting that would badly distort
   the panel if left in.** See §2. This is the single most important
   *data* finding in this report and is fixed in the panel as delivered,
   not left as a caveat.
3. **The substitute regressor (§1) cannot carry the hypothesis it is
   standing in for** — it is close to an inverse index of industrial
   intensity, the population the hypothesis is actually about. This is
   the single most important *framing* fact in the whole exercise: it
   means every null result downstream is close to uninformative about the
   original digitalization-emissions question, not just imprecise.

Both are documented in full in the relevant script's module docstring
(`scripts/download_census_abs_tech.py`, `scripts/download_epa_ghgrp.py` /
`build_panel.py`) as well as here.

## 1. Census ABS technology module — blocked, substituted with BLS QCEW

The task brief describes the Census Data API as free and keyless. **That
is no longer true, verified directly against the live API on 2026-09-17,
not assumed from old documentation.** Every `api.census.gov/data/...`
*data* query (`get=...`), for every dataset tested — including the 2020
Decennial Census, which historically needed no key at all — returns an
HTML "Missing Key" or "Invalid Key" error page instead of JSON. This
reproduces identically for `absmcb` (the intended 2020-2023 technology
module) and `abstcb` (the 2018 one-off). A web search independently
confirms Census's own current developer documentation states all data
queries now require a key. Dataset *metadata* endpoints
(`/variables.json`) are unaffected and were used to confirm both datasets
exist and to resolve the `BUSCHAR`/`QDESC` code structure — only the
actual row-returning queries are gated.

**This pipeline deliberately does not obtain a key on its own** — that
requires submitting a name and email to Census's signup form, which is
outside this pipeline's remit without the pipeline owner's explicit
say-so. `scripts/download_census_abs_tech.py` is fully built and correct
(BUSCHAR/QDESC resolution, state and county geography, `*_S`
reliability-flag columns preserved) and will run end-to-end the moment a
free key (https://api.census.gov/data/key_signup.html) is set as
`CENSUS_API_KEY`. **As delivered, this script has not pulled any Census
technology-adoption data — that entire line of the intended analysis is
open, not attempted-and-failed.**

**Substitution used instead: BLS QCEW "digital economy" employment
share**, via `scripts/download_bls_qcew_tech.py` — free, keyless, live and
working. This is a **structural/compositional** proxy (the share of a
county's or state's *private-sector employment* sitting in NAICS 51
"Information" + NAICS 5415 "Computer systems design"), not an
**adoption-intensity** proxy (whether businesses in *any* sector use
cloud/AI/robotics — the EIBIS/DII construct, and what Census ABS
technology module would have measured).

**Quantified (added in round 2, per Reviewer B2): this is not just "a
different construct that happens to share a word" — it is empirically
close to an *inverse* index of how industrial a state's economy is,**
i.e. it points the wrong way relative to the population the hypothesis is
actually about (industrial/manufacturing firms adopting digital tools).
On the 2023 state cross-section:

| `tech_emp_share` correlated against | state (n=53) | county (n=1,702) |
|---|---|---|
| log(CO2e per private employee) (round-3, biogenic-excluded) | **-0.592** | -0.263 |
| log(private employment) | +0.374 | — |
| GHGRP facilities per 10k private employees | -0.392 | — |

The 2023 top-8 states by `tech_emp_share` are **DC, WA, VA, CO, CA, MA,
MD, UT**; the bottom-8 are **MS, LA, AR, WY, IN, VI, DE, OK**. Wyoming and
Mississippi are heavy-industrial, low-tech-employment-share states;
DC/CA/WA/MA are the reverse. **Tech-hub states and heavy-industrial
states are close to disjoint populations in this data.** This matters a
great deal for interpretation: the hypothesized channel runs through
industrial firms adopting digital tools, but high values of this
regressor mark places with comparatively *few* such firms. A null result
built on this regressor is therefore close to **uninformative** about the
original hypothesis — it could just as easily mean "a state is rarely
both a tech hub and an industrial hub" (true, uninteresting, mechanical)
as "digitalization doesn't affect industrial emissions" (the actual
question). **This report is downgraded accordingly: `us_analysis.md`
should be read as a coverage/feasibility exercise for a US panel using
free data, not as a test of H1 that this regressor can actually carry.**
A genuine Census ABS technology-module pull remains the thing that would
close this gap (§1 above).

Two further QCEW-specific findings, found only by inspecting a raw
singlefile:

- **`own_code=0`** ("Total covered", all ownership combined — the
  natural first guess) returns essentially **zero rows for any detailed
  NAICS industry**, only for the grand total (`industry_code=10`). A
  first pull using it produced a tech-share column that was silently
  100% missing. Fixed by switching to **`own_code=5`** ("Private
  ownership") throughout, which is well-populated and is the right
  population anyway (software/data-processing/computer-design firms are
  almost entirely private-sector).
- **`industry_code=5112`** (software publishers specifically) returns
  **zero rows at any geography** in the bulk annual singlefile — not one
  of the aggregation levels BLS publishes there. Dropped from the
  regressor; NAICS 51 (which contains 5112) and 5415 still capture the
  intended construct.

## 2. GHGRP "Supplier" sectors — the US analog of the EU's `20-99`
double-count trap

**Filtering emissions to `sector_type == 'E'` (direct emitters) drops
55.8% of raw reported CO2e mass** (4.353e10 of 9.856e10 t CO2e kept,
2010-2023, across all gas types before the biogenic exclusion below).
GHGRP's `PUB_DIM_SECTOR` table classifies each of its 16 reporting
sectors as `E` (direct Emitter), `S` (fuel/gas Supplier), or `I` (CO2
Injection). **The two single largest sectors in the raw, unfiltered
emissions table are BOTH suppliers**: "Petroleum Product Suppliers"
(Subpart MM, 3.89e10 t CO2e) and "Natural Gas and NGL Suppliers" (Subpart
NN, 1.55e10 t CO2e) — together larger than "Power Plants," the largest
true direct-emitter sector (2.63e10 t). These report the **potential**
CO2e content of fuel *supplied into commerce* — an upstream, national-
accounting quantity attributed to wherever the supplier's corporate
reporting entity sits, not the facility-level combustion/process
emissions that constitute EU ETS's "verified emissions" concept. Left
unfiltered, a handful of refinery product-terminal and gas-processing-hub
facilities would dominate any county/state aggregate by construction,
unrelated to that area's actual industrial emissions profile. **Fixed in
`build_panel.py`: emissions are filtered to `sector_type == 'E'` before
any aggregation**, cross-checked against `facilities.facility_types`
(which independently carries an explicit "Supplier" vs. "Direct Emitter"
text tag, agreeing with the sector-level classification). `sector_type
== 'I'` (CO2 Injection, well under 1% of the unfiltered total) is
excluded on the same logic — injected CO2 is not an atmospheric emission.

This is flagged as the single most important QC finding in this report
because an unfiltered pull would have looked completely plausible (large
numbers, full state/county/year coverage, no errors) while measuring
something structurally different from what the brief, and the EU
comparison, require.

**§2b, added in round 2 (Reviewer S2): the `sector_type == 'E'` filter is
correct on the emissions-*concept* axis but one direct-emitter sector has
a *geography* problem of the same species.** `PETRO_NG` (Subpart W,
"Petroleum and Natural Gas Systems") is 9.0% of the final outcome mass
and is reported at basin/operator level for onshore production and
gathering-and-boosting activity — i.e. a whole multi-county upstream
basin can be booked to a single reporting county, the same "upstream
aggregate attributed to wherever the reporting entity sits" error type as
the supplier catch above, one level down within the direct-emitter set.
This is NOT reclassified as a supplier (it is correctly a direct emitter
conceptually) but its geographic attribution is weaker than the other
`E` sectors. `us_analysis.py` reports a `PETRO_NG`-excluded cut
(`d_log_emissions_excl_petro_ng`) alongside the full-panel outcome, the
same side-by-side discipline `phase_b_analysis.md` uses for v2b's
combustion-included/excluded cuts.

## 3. Biogenic CO2 exclusion

GHGRP's `gas_id=8` ("Biogenic CO2") is reported and excluded from
`total_co2e` for the same reason `analysis/first_pass_analysis.md`
excludes E-PRTR's biomass CO2 in the EU panels — treated as part of the
natural carbon cycle under standard US GHG-inventory convention, not a
netted-out emission. 9,051 of 346,683 raw emission rows (2.6%) carry
`gas_id=8`.

**Round-3 correction: this filter was accidentally deleted during the
round-2 missingness-bug edit (see the revision note above) and the
round-2 delivered panels silently included biogenic CO2.** Independently
verified by a Reviewer reconstruction: rebuilding with vs. without the
filter matched the round-2 published county panel **exactly** to the
WITH-biogenic version (27,955/27,955 rows identical), not the documented
without-biogenic one. Biogenic CO2 is **4.67% of direct-emitter mass**,
concentrated specifically in pulp/paper and biomass-co-firing power
plants — sectorally and geographically non-random, and trending over the
period, so it would have contaminated `d_log_emissions` non-uniformly
rather than adding flat noise. **The filter is restored in this round**
(`em = em[em["gas_id"] != BIOGENIC_GAS_ID]`, immediately followed by an
`assert` that no `gas_id == 8` rows remain in the aggregation input, so
this exact failure cannot silently recur). All downstream numbers in this
report and in `us_analysis.md` reflect the corrected, biogenic-excluded
panel.

## 4. GHGRP year coverage: 2010-2023, not 2010-2025

Confirmed against the live API, not assumed: querying `year/2024` or
`year/2025` on `PUB_FACTS_SECTOR_GHG_EMISSION` returns **zero rows** —
facility-level GHGRP data is not yet published past 2023 (reporting lag).
This means the EPA side of this panel tops out one to two years earlier
than the EU ETS series used elsewhere in this repo (which runs through
2025). Number of unique reporting facilities per year rises steadily from
6,764 (2010) to 11,235 (2023) — expected, reflecting GHGRP's phased
rollout across subparts, not treated as a break requiring correction.

## 5. The `groupby().sum()` missingness bug (Reviewer B3, blocking, fixed)
and what the 1,174 "zero" cells actually are

**A first draft of this build had a real, blocking bug, caught by
Reviewer round 1: `co2e_emission` was summed per facility-year with a
bare `.sum()`, which silently returns `0.0` (not `NaN`) when every
underlying row in a group is `NaN`, rather than propagating the
missingness.** This affected **15.8% of direct-emitter facility-years
(20,186 of 127,511)**, and — the more important detail — the share is
**not stationary: it rises monotonically from 0% in 2010-2012 to 28.5%
by 2023** (9.1% at 2015, the first analysis year), because later years
have more facilities with partially-reported GHGRP subparts. This is the
same *class* of bug the EU review caught in panel_v2's Eurostat DII
HI/VHI aggregation (a `fillna(0)` treating suppression as a definitional
zero) — found independently here rather than missed twice.

**Fix, applied at both aggregation levels** (facility-year, and again at
county/state-year — a plain `.sum()` at the *second* level would have
silently reintroduced the identical bug even after fixing the first,
since summing a group that is entirely `NaN` returns `0.0` by default at
every level, not just the first one summed): both use
`.sum(min_count=1)`, which returns `NaN` only when *every* value in the
group is missing, and sums normally (skipping missing values) otherwise.

**What this means for the "1,174 zero-`total_co2e`" county-years
originally described in this section (round 1) as "facilities that filed
but had no fossil/process emissions to declare":** that description was
**wrong**. Recomputed with the fix: **1,110 of those 1,174 (94.5%) are
actually county-years where every reporting facility's emissions were
missing, not genuinely reported as zero** — the fix now correctly labels
them `NaN`, not `0`. Only **64 county-years (0.2% of the panel)** are
genuine reported zeros. The corrected breakdown:

| | before fix (round 1, wrong) | after fix (round 2) |
|---|---|---|
| county-years with `total_co2e == 0` | 1,174 | 64 (genuine) |
| county-years with `total_co2e` missing (`NaN`) | 0 | 1,110 (newly, correctly, missing) |

`log(0)` remains undefined and is set to `NaN` (not `-inf`) for the 64
genuine-zero cells, as in round 1 — that part of the original fix was
correct and is unchanged.

**Note on a residual, more subtle form of the same issue, not fully
fixed:** a county-year with, say, 3 real facilities and 1 whose own data
is missing still sums only the 3 real facilities (`min_count=1` fixes the
*all-missing* case, not partial coverage) — this understates the true
county total by an unknown, time-varying amount whenever coverage is
partial, and is **not** corrected here (there is no way to correct it
without imputing the missing facility's emissions, which this build does
not attempt). This is disclosed as a residual limitation, not silently
left as "fixed."

**Round-3 correction: this fix, while a real latent defect worth fixing,
turned out to be a mathematical no-op for `d_log_emissions` itself.** All
1,110 newly-`NaN` `total_co2e` cells already produced `log(0)` → `NaN`
under the pre-existing `.where(total_co2e > 0)` guard, regardless of
whether the input was `0.0` (the bug) or `NaN` (the fix) — a
Reviewer-independent reconstruction confirmed `d_log_emissions` differs
on **zero rows** between the buggy and fixed versions, and the county
bare-model coefficient is bit-identical (−0.054) either way. **The
headline-number movement seen across rounds traces entirely to the
biogenic-CO2 filter deletion (§3), not to this fix.** The fix is retained
regardless, because it protects `total_co2e` in levels (and any future
use of that column on its own, outside a log-difference), not because it
turned out to move this report's headline result.

**A second, related bug surfaced while chasing the above down: a plain
`.diff()` on a unit's `log_emissions` series spans whatever gap sits
between consecutive dataframe *rows*, not consecutive *calendar years*.**
A unit that is missing a whole (unit, year) row — not just a `NaN` value
within an existing row — silently gets a multi-year change mislabeled as
a one-year change. Both this build (in an earlier draft) and an
independent Reviewer reconstruction (which dropped `NaN` rows before
aggregating, opening year gaps) fell into this at different points;
`_finalize_emissions_panel` in `build_panel.py` now computes each row's
year-over-year gap explicitly and sets `d_log_emissions` to `NaN`
whenever that gap isn't exactly 1, regardless of which implementation
step produced the gap. This affects a small number of rows (13 in the
county panel's headline outcome, 8 in the PETRO_NG-excluded variant) but
is exactly the kind of guard that matters most in the rows it does
affect, since they are disproportionately high-leverage.

## 6. BLS QCEW disclosure suppression

QCEW's own overall suppression rate (`disclosure_code` populated) across
the raw tech-industry pull is **18.2%**, concentrated almost entirely at
the county level (18.5% of county-level rows vs. 0.07% of state-level
rows — essentially unsuppressed) and rising sharply with industry
granularity: **0.8%** suppressed for the total-employment denominator
(`industry_code=10`), **20.7%** for NAICS 51, and **35.9%** for the
narrower NAICS 5415. This is the expected pattern (thinner cells suppress
more) and is handled the same way panel_v2 handles Eurostat DII
suppression after its own review-driven fix: suppressed cells are set to
`NaN`, never silently treated as zero.

## 7. Coverage and missingness — state panel

- **756 state-year rows, 54 states/territories** (50 states + DC + a few
  territories/regions carried in GHGRP's own `state` field), 2010-2023.
- **`d_log_emissions` missing for 7.1%** of rows (each state's first
  observed year, plus any single-year reporting gaps).
- **`tech_emp_share` missing for 36.9%** of rows — almost entirely
  mechanical: QCEW is only pulled for 2015-2023 (matching GHGRP's own
  max year, see §4), so **every state-year before 2015 is missing by
  construction**, roughly 5 of 14 years (35.7%), consistent with the
  observed rate.
- **Usable rows (both variables non-missing): 477**, 53 states,
  2015-2023 (9 years) — the state panel's actual usable window.

| Variable | n | mean | SD | min | max |
|---|---|---|---|---|---|
| `tech_emp_share` | 477 | 0.0351 | 0.0148 | 0.0081 | 0.0937 |
| `d_log_emissions` (round-3, biogenic-excluded) | 702 (of 756) | -0.0236 | 0.1188 | -1.246 | 0.832 |
| `total_co2e` (t, round-3, biogenic-excluded) | 756 | 5.33e7 | 6.38e7 | 1.04e5 | 4.43e8 |
| `n_facilities` | 756 | 157 | 184 | 3 | 1,482 |

Missingness shares (`d_log_emissions` 7.1%, `tech_emp_share` 36.9%) are
unaffected by either the §5 missingness fix or the §3 biogenic-filter
restoration at the state level (large-enough aggregation that no
state-year ends up all-missing). The state-level descriptive numbers
above are, after restoring the biogenic filter, numerically identical to
the very first (pre-any-fix) draft's table — independent confirmation
that neither the missingness fix nor the diff-contiguity guard moves
anything at the state level; only the biogenic filter does, and only
at the county level (§8).

## 8. Coverage and missingness — county panel

- **27,955 county-year rows, 2,112 counties**, 2010-2023.
- **`d_log_emissions` missing for 12.0%** of rows (first-year gaps, the
  zero/missing `total_co2e` cells from §5, and — new in round 3 — the
  small number of rows spanning a year gap != 1, per the `.diff()` guard
  also added in §5).
- **`tech_emp_share` missing for 42.6%** — pre-2015 mechanical gap (§7)
  plus genuine QCEW county-level disclosure suppression (§6) stacking on
  top, hence the higher rate than the state panel's 36.9%.
- **Usable rows (both variables non-missing): 15,030**, 1,865 counties,
  2015-2023 (down 7 from round 2's 15,037 — exactly the rows the new
  `.diff()` year-contiguity guard correctly nulls out within the usable
  window; the missingness fix itself, per §5's round-3 correction,
  changes zero rows).

| Variable | n | mean | SD | min | max |
|---|---|---|---|---|---|
| `tech_emp_share` | 16,052 | 0.0178 | 0.0183 | 0.0002 | 0.258 |
| `d_log_emissions` (round-3, biogenic-excluded, diff-guarded) | 24,609 | -0.0113 | 0.4860 | -11.41 | 13.53 |
| `total_co2e` (t, round-3, biogenic-excluded) | 26,845 | 1.50e6 | 3.54e6 | 0 | 7.15e7 |
| `n_facilities` | 27,955 | 4.24 | 7.99 | 1 | 303 |

**Extreme `d_log_emissions` outliers, corrected characterization (round
2, Reviewer S1): the "concentrated almost entirely in single-facility
county-years" claim in round 1 was true only at a very high threshold and
does not hold at the threshold that actually drives OLS leverage.** At
`|d_log_emissions| > 5` (37 county-years in the round-3 corrected data),
a majority are single-facility, so the round-1 claim is directionally
fine *there*. But at the more consequential `|d_log_emissions| > 1`
threshold (778 county-years), a large share are NOT single-facility and
survive the `n_facilities >= 2` cut entirely — meaning that cut, used in
round 1 as the sole outlier treatment, leaves most high-leverage cells
untouched. Residual SD is far higher in thin cells than thick ones
(single-facility cells are much noisier than 20+-facility cells), a
standard heteroskedastic-leverage pattern. **Round 2 fix, unchanged by
round 3: `us_analysis.py` reports 1st/99th-percentile winsorization of
`d_log_emissions` as a headline row (not a skipped limitation), alongside
— not instead of — the `n_facilities >= 2` cut.** This is analogous to
(though a different mechanism from) the EU project's Norway energy-
import-dependency outlier — flagged and handled, not silently left in.

## 9. Geography note

State/county FIPS are taken directly from GHGRP's own `county_fips`
field, with `state_fips` derived as its first two characters — no
separate crosswalk was needed (one genuine advantage of GHGRP's facility
file over the EU project's E-PRTR facility file, which required real
geocoding work).

**7.8% of raw facility-years (10,628 of 136,005) have a missing/malformed
`county_fips` and are dropped before aggregation — round 2 correction
(Reviewer S3): this drop is geographically non-random and time-trending,
not "mostly housekeeping" as round 1 described it.** Independently
re-verified: dropped facility-years concentrate heavily in oil-and-gas
states — **TX (4,024), LA (1,569), OK (770), CO (761), CA (520)** — and
the annual drop count rises steeply, from **53 in 2010 to 1,352 in
2023**, tracking GHGRP's growing Subpart W (onshore production,
gathering & boosting, offshore) reporting volume, which structurally
lacks a single-county assignment (a well pad or gathering system spans
multiple counties or is offshore). **Net effect: this panel systematically
and increasingly under-represents oil-and-gas-producing states' emissions
at the county level**, a real and growing coverage gap, not neutral
housekeeping. It does not bias the *state*-level panel the same way
(state assignment is more often recoverable even when county is not,
though this was not separately re-verified) and is disclosed here rather
than only in the aggregate 7.8% headline figure.

**State panel composition (round 2 correction, Reviewer S5): "53
states" undersells what the cluster set actually is.** The panel's 54
raw units are the 50 states + DC + Guam + Puerto Rico + US Virgin
Islands; Guam drops out of the *usable* (both-variables-non-missing)
sample for lack of QCEW coverage, leaving the reported "53" clusters as
**50 states + DC + PR + VI**, not 53 states. PR and VI in particular are
thin clusters (a handful of GHGRP facilities each). `us_analysis.py`
reports a `PR+VI+DC`-excluded cut (leaving exactly the 50 states) as a
named robustness row rather than only in this footnote.

## What this report does NOT do

- **No causal claim, no regression interpretation** — that is
  `us_analysis.md`'s job, built on top of the panels documented here.
- **No resolution of the Census API block.** A free key would let
  `scripts/download_census_abs_tech.py` run as originally scoped and
  would give a genuinely comparable adoption-intensity measure; that
  remains open, not attempted-and-abandoned.
- **No claim that the QCEW substitute is a good proxy, only that it is
  the best free, live, keyless option found.** Its conceptual distance
  from EIBIS/DII (structural composition vs. adoption intensity) is the
  single largest source of non-comparability with the EU results and
  should travel with every result built on it.
