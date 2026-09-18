# Phase D: EU digital-funding event study, and energy intensity as a proximate mechanism

Reproducible from `analysis/phase_d_analysis.py`. New raw data:
`data/raw/cohesion/digital_investment_2014_2020.csv`
(`scripts/download_cohesion_digital_funding.py`) and
`data/raw/eurostat/industrial_energy_consumption.csv`
(`scripts/download_eurostat_energy_consumption.py`). Builds on the
Reviewer-approved Phase B panel (`analysis/phase_b_analysis.md`) for item
2's controls, and on the full EU-ETS country-year history (2005-2025,
same "20-99" construction used throughout this project) for item 1's
outcome.

**Revision note:** this version corrects issues a review pass
(`analysis/phase_d_review.md`) found in both items, plus one bug the
review itself did not catch. **A genuine country-code bug** — the EU-ETS
side of item 1 remapped `GR→EL` (matching this project's convention) but
never remapped `GB→UK` (the Cohesion funding data's own convention for the
United Kingdom) — silently dropped the UK from the entire event-study
panel, not just its pre-period, which is what produced the "12/18
left-censored" count the review computed against that buggy output. Fixed
at the source (`ets_total` now maps `GB→UK` like every other panel-
building script in this project); the UK is correctly included, and the
left-censoring count is **13 of 19** throughout (the review's own
independent count of the onset file, which turns out to be the right
number everywhere once the bug is fixed, not a different number for the
onset file versus the regression sample). **Item 1** is reframed, per the
review's Phase-C-infeasibility precedent, from "no effect found" to "this
design cannot answer the question" — 13 of 19 countries have no observable
pre-period, and the sharpest-estimated coefficient in the whole event
study is a significant pre-trend, not noise as the first draft claimed.
**Item 2** keeps its numbers (independently re-derived and confirmed by
the review) but corrects a leave-one-out run on the wrong regression, adds
the placebo/timing test and accession-cohort split the first draft did not
run, and reframes the entire finding around what those two checks show:
a robust correlation whose *direction* the data cannot establish.

## Headline

- **Item 2 (highest priority — read this first): a genuinely robust
  correlation between digitalization and industrial value-added growth —
  but the data cannot tell you which way it runs, and it concentrates in
  catch-up economies.** Unlike every other marginal result in this
  project (original EIBIS p=0.047, Eurostat-controls p=0.001, EIBIS
  large-firm p=0.06 — all of which dissolved under a single country's
  removal), this one **survives leave-one-out across all 28 countries**
  (maximum p=0.038, dropping Ireland; coefficient never changes sign,
  ranging +0.060 to +0.101). But a placebo/timing test **fails
  decisively**: *lead* (future) digitalization predicts this year's
  value-added growth at least as well as *lagged* (past) digitalization
  does (lead: coef=+0.075, wild-bootstrap p=0.031; lag: coef=+0.057,
  p=0.089) — the textbook signature of reverse causality or a shared
  underlying trend, not of digitalization driving growth. The association
  is also **2.4x larger in accession-wave (2004+) economies** than in the
  EU-15 (+0.118, p=0.053 vs. +0.050, p=0.061) — the same convergence-
  economics pattern Phase C found driving the sector-panel sign flip. The
  most parsimonious reading: digitalization and industrial growth move
  together because both are driven by a common catch-up/development
  process, not because either causes the other.
- **Item 1 (EU digital-funding event study): the design cannot answer the
  question it was built to ask.** 13 of 19 funded countries are
  left-censored (already receiving funding before the data window opens
  in 2016), leaving only 6 countries with any genuine pre-treatment
  period to identify off. Worse, the event-study coefficient with the
  **smallest standard error of the eight estimated** (SE=0.024, second-
  tightest after only the final post-period point) is a **significant,
  positive lead** five years before funding onset (coef=+0.051,
  p=0.030) — a real pre-trend signal in the study's single sharpest
  estimate, not a noisy edge effect as an earlier draft of this
  document claimed. Following the same precedent set for Phase C's
  regional panel: this is reported as **infeasible with the available
  funding-timing data**, not as evidence that funding has no effect on
  emissions trajectories.

## Item 2: energy intensity, value-added growth, and why the causal story doesn't hold

### The intensity finding, and the mechanism behind it (unchanged from the prior draft)

`ten00124` ("Final energy consumption by sector"), `nrg_bal='FC_IND_E'`
(industry), unit=KTOE — chosen over the more granular `nrg_d_indq_n` after
checking that the latter's own `nace_r2='TOTAL'` returns an empty value
set for every country (see `analysis/phase_d_analysis.py` docstring for
the full check). Energy intensity is `d_log(energy_intensity) =
d_log(industry_energy_ktoe) − d_log(industry_va_meur)`, an exact log
decomposition.

| Outcome | Spec | coef | p (naive z) | p (t, G−1) | **p (wild bootstrap)** |
|---|---|---|---|---|---|
| Energy intensity | bare | −0.045 | 0.180 | 0.191 | **0.214** |
| Energy intensity | +controls | −0.074 | 0.023 | 0.031 | **0.020** |
| Raw energy consumption | bare | −0.008 | 0.655 | 0.658 | **0.663** |
| Raw energy consumption | +controls | −0.001 | 0.967 | 0.968 | **0.960** |
| `d_log(industry value-added)` | +controls | +0.073 | 0.013 | 0.019 | **0.016** |
| `d_log(industry energy)` | +controls | −0.001 | 0.967 | 0.968 | **0.974** |

**This was never an energy-efficiency finding.** Raw energy consumption
shows no detectable association with digitalization (p=0.96-0.97 in every
spec); the significant energy-intensity result is a mechanical consequence
of digitalization tracking faster industrial **value-added growth**
(coef=+0.073, wild-bootstrap p=0.016), which dilutes the energy/output
ratio without any change in energy use itself.

### Robustness: leave-one-out on the regression that actually carries the finding

**Correction from the prior draft:** leave-one-out was previously run on
the energy-*intensity* regression (a downstream, mechanical consequence),
not on value-added growth (G5) — the regression the write-up actually
calls the real finding. Re-run on G5 directly, across all 28 country
clusters:

- **Maximum p-value: 0.038** (naive z, dropping Ireland), **0.048** under
  t(G−1) — confirmed with a full wild-cluster-bootstrap re-estimate on the
  drop-Ireland sample: **p=0.050**, consistent.
- Coefficient ranges **+0.060 to +0.101** across all 28 leave-one-out
  runs — never changes sign, never close to zero. (Full table:
  `analysis/output/phase_d_item2_leave_one_out.csv`.)

**This passes more cleanly than the mis-targeted check in the prior
draft did.** The robustness claim was directionally correct even when
tested on the wrong regression, but it had not actually been verified for
the regression that matters until now. It is not another Bulgaria/Spain-
style single-country artifact — nothing here depends on any one country.

### The placebo/timing test: this is where the causal story breaks

If digitalization drives industrial growth, lagged (pre-determined)
digitalization should predict *next* year's value-added growth better
than *future* digitalization can "predict" *this* year's — future values
cannot cause past outcomes. Both were built on the identical matched
sample (n=221, 28 countries — lag and lead must be evaluated on the same
rows, the same fix applied to every other placebo test in this project):

| Spec | coef | p (naive z) | p (t, G−1) | **p (wild bootstrap)** |
|---|---|---|---|---|
| Contemporaneous DII | +0.087 | 0.040 | 0.050 | **0.085** |
| REAL — lagged DII (t−1) | +0.057 | 0.092 | 0.103 | **0.089** |
| **PLACEBO — lead DII (t+1)** | **+0.075** | **0.030** | **0.039** | **0.031** |

**The placebo (lead) coefficient is larger and more significant than the
"real" (lagged) one.** Future digitalization tracks this year's
value-added growth *better* than past digitalization tracks next year's.
This is the textbook signature of reverse causality or a shared trend —
industrial growth and digitalization investment rising together for a
common reason — not of digitalization causing growth. **A placebo test
cannot establish that digitalization measurably precedes growth here; if
anything, the timing runs the other way.**

### The association concentrates in catch-up economies

Splitting on `accession_2004plus` — the same variable Phase C found
driving the v2b sector-panel sign flip:

| Sample | n | G | coef | p (naive z) | p (t, G−1) | **p (wild bootstrap)** |
|---|---|---|---|---|---|---|
| EU-15 only | 141 | 15 | +0.050 | 0.055 | 0.075 | **0.061** |
| Accession 2004+ only | 116 | 13 | **+0.118** | **0.022** | 0.041 | **0.053** |
| Interaction (DII × accession) | 257 | 28 | +0.094 | 0.168 | 0.179 | **0.230** |

The coefficient is **2.4x larger** in accession-wave economies, and only
that subset clears 5% under naive z on its own (EU-15 sits at 0.055-0.061
across methods). The interaction term itself is not significant, but at
G=28 with a cross-level interaction this test has the same limited power
already documented in Phase B and Phase C. **This needs no digitalization-
causes-growth channel at all**: catch-up economies plausibly digitalize
faster from a lower base *and* grow industrial output faster through
ordinary convergence, with development level as the shared driver —
exactly the pattern already identified in Phase C's `accession_2004plus`
finding, showing up again here in a different outcome variable.

### The honest characterization

Putting the three checks together: **digitalization intensity and
industrial value-added growth are robustly correlated across EU
countries** — this survives every fragility check applied to it, unlike
every prior marginal finding in this project. **But the association
concentrates in catch-up/accession economies, and a placebo/timing test
shows this is not a case where digitalization measurably precedes
growth** — future digitalization tracks past growth at least as well as
past digitalization tracks future growth. **The most parsimonious reading
is that both are driven by a common underlying convergence process
(catch-up economies growing and digitalizing together), not that
digitalization causes industrial growth.** This is a genuinely different
outcome from the four rounds of marginal, single-country-dependent false
alarms earlier in this project — the correlation itself is real and
well-established — but its correct interpretation is "robust correlation,
wrong (or at least unestablished) causal direction," not "digitalization
drives growth."

## Item 1: EU Cohesion digital-funding event study — data cannot answer the question

### What the funding data supports (unchanged findings, still checked not assumed)

Country-year granularity (NUTS2/3 checked and rejected as unreliable, see
`scripts/download_cohesion_digital_funding.py` docstring), Thematic
Objective 02 (ICT) declared expenditure, 21 of ~28 countries, 2016-2023,
cumulative values (annual flow derived by differencing). No RRF actuals
dataset exists on this platform (checked). Two countries (DE, IE) with
~zero recorded TO2 spending throughout excluded; 19 remain.

### Design (unchanged): onset defined as first year cumulative funding
crosses 50% of its own 2023 total, compared against two rejected
alternatives (first-nonzero: censored for most countries; peak-flow-year:
lands on 2023 for 9/21 countries via N+3 closeout dynamics, not a
meaningful policy date). Event window −5 to +3, merged onto the full
2005-2025 EU-ETS history. A genuine collinearity in the naive 3-way
(country + calendar-year + event-time) fixed-effects specification was
resolved by subtracting calendar-year means computed on the **full**
~30-country EU-ETS panel before the event-time regression — an **external
year-mean subtraction**, not (as an earlier draft called it) a
Frisch-Waugh-Lovell partialling-out: FWL guarantees orthogonality because
it estimates the partialled-out effect *within* the same sample; here the
year means come from a different, larger sample (11 countries outside the
event study contribute to them), so orthogonality is not guaranteed by
construction, and the year means' own estimation uncertainty is not
propagated into the reported standard errors (second-order with ~30
countries per year, but not exactly zero).

### Left-censoring: 13 of 19, confirmed after fixing a real bug

**A genuine country-code bug, not just a miscount, was found and fixed
while responding to this review.** The EU-ETS emissions data uses `GB`
for the United Kingdom; the Cohesion funding data uses `UK`. Every other
panel-building script in this project (`panel_v2/build_panel.py`, for
example) remaps `GB→UK`; this script's item-1 construction only remapped
`GR→EL`, silently dropping the UK from the merge entirely — not just its
pre-period, all of it. This produced the "12/18" figure the review
computed by checking the (buggy) output. **Fixed at the source**: with
`GB→UK` now applied, the UK is correctly retained (G=19, not 18), and the
left-censoring count is **13 of 19 everywhere** — the onset file and the
regression sample no longer disagree, because the discrepancy was the bug,
not a genuine onset-file-vs-regression-sample distinction.

| Onset year | Countries |
|---|---|
| 2018 | EE, UK |
| 2019 | SE, CZ, MT |
| 2020 | IT, CY, LT, LV, PT, ES |
| 2021 | FR, PL, HU |
| 2022 | RO, EL, SI |
| 2023 | HR, SK |

Left-censored (funding already positive in 2016, true onset unknown):
EE, UK, SE, IT, LT, LV, PT, FR, PL, HU, EL, SI, SK — **13 of 19**. Only
**6 countries (CZ, MT, CY, ES, RO, HR)** have a genuine observable
pre-period.

### The pre-trend problem: the sharpest estimate in the study is a significant lead

**Correction from the prior draft, which dismissed this incorrectly.** An
earlier version of this document discounted the significant
`event_time = −5` lead coefficient on the grounds that it "sits at the
window's edge where the fewest years of data contribute." Both halves of
that claim were checked and found wrong:

| Event time | Coefficient | SE | Naive-z p | Countries contributing |
|---|---|---|---|---|
| **−5** | **+0.051** | **0.024** | **0.030** | 19 (full support) |
| −4 | −0.013 | 0.040 | 0.749 | 19 |
| −3 | −0.019 | 0.036 | 0.594 | 19 |
| −2 | +0.025 | 0.031 | 0.426 | 19 |
| 0 | +0.010 | 0.029 | 0.739 | 19 |
| +1 | −0.034 | 0.036 | 0.333 | 19 |
| +2 | +0.009 | 0.039 | 0.810 | 19 |
| +3 | +0.035 | 0.023 | 0.121 | 16 |

`event_time = −5`'s standard error (0.024) is the **second-smallest of
all eight** event-time coefficients (only `+3`, at 0.023, is tighter), and
every event time from −5 to +2 draws on the full 19-country sample — there
is no support-thinness at the window's edge. **This is the single most
precisely estimated coefficient in the entire event study, and it is a
significant, positive pre-trend five years before funding onset.** The
"1 of 4 leads significant is roughly what chance alone would produce"
argument still has some force taken purely as a multiple-comparisons
point — but dismissing this specific coefficient on grounds of imprecision
or thin support was incorrect, and it happens to be the sharpest,
strongest-signed of the four.

This also resolves an apparent tension between two checks in this report:
the group-mean pre-trend test (early vs. late onset countries, 2010 to
onset_year−1, t=0.573, **p=0.576**) found no significant difference and
was previously described as "mildly reassuring." That test and the
significant lead are not contradictory — they test very different things
with very different power. The group t-test compares two 9-11-country
group means and could not detect a moderate difference even if one were
present; the event-time coefficient is a sharper, within-design test at
full sample support, and it flags. The weaker, null test should not have
been weighted above the sharper, positive one.

### Bottom line: this design cannot answer the question

With **13 of 19 countries left-censored** (no observable pre-period at
all) and the **single sharpest-estimated coefficient in the study
showing a significant pre-trend** in the 6 countries (plus whatever
identifying variation the left-censored countries contribute despite
having no "before"), neither specification below can support a causal
conclusion in either direction:

| Model | n | G | coef | p (naive z) | p (t, G−1) | **p (wild bootstrap)** |
|---|---|---|---|---|---|---|
| F1: full window, all 19 countries | 168 | 19 | −0.005 | 0.796 | 0.799 | **0.792** |
| F2: excluding left-censored countries (6 remain) | 53 | 6 | +0.041 | 0.334 | 0.378 | **0.449** |

F1's identifying variation comes overwhelmingly from countries whose
"before" is unobservable — a before/after design run mostly on
observations with no genuine "before." F2 restricts to the 6 clean
countries and has G=6, a cluster count this project has correctly treated
as untrustworthy everywhere else it has come up (Phase C's regional
panel, most directly). **Following the same precedent set for Phase C's
NUTS2 regional panel: this is reported as an infeasible design given the
available funding-timing data, not as a null finding about whether
digital funding affects emissions.** Neither F1's near-zero coefficient
nor F2's larger, differently-signed one should be read as evidence about
the true relationship — both come from specifications this project's own
standards (established in Phase C) treat as unable to support a
conclusion.

### On the exogeneity assumption

The underlying administrative argument for why funding timing might be
exogenous (programme adoption dates, absorption-capacity cycles, N+3
spending deadlines — not, on its face, a country's own emissions
trajectory) is still reasonable as a starting hypothesis, and nothing here
shows it is false. What this analysis shows is narrower: **even granting
the exogeneity assumption, this specific dataset's coverage window
(2016-2023, with most countries already mid-disbursement by its start)
cannot support the before/after comparison the design needs.** A dataset
starting earlier (ideally covering the true 2014 programme start) or a
design that does not require an observable pre-period for most of the
sample would be needed to actually test this question. One additional,
milder concern worth naming: onset timing correlates with programme scale
(larger-eventual-funding countries tend to cross their own halfway point
later, simply because there is more total funding to accumulate toward),
so "onset year" is not entirely independent of a country's funding
envelope — a look-ahead-by-construction feature of the halfway-point
definition, not a reason to prefer either rejected alternative, but worth
naming as a residual non-randomness in the timing variable.

## Combined read across items 1-2

Item 1 cannot answer its question with the data available — a genuine
data-coverage limitation (heavy left-censoring, confirmed by a real
country-code bug fix and a corrected precision analysis of the pre-trend
coefficient), reported honestly as infeasible rather than forced into a
null finding. Item 2 finds this project's most robust correlation to
date — one that survives every fragility check thrown at it — but a
placebo test shows the timing runs at least as much backward as forward,
and the effect concentrates in catch-up economies, pointing to a shared
convergence-economics driver rather than a causal digitalization-to-growth
channel. Read together with Phase C's `accession_2004plus` finding, a
consistent picture is emerging across two independent phases of this
project: wherever something in this data looks like it might be a
real effect, the leading alternative explanation is that both
digitalization and the outcome in question are driven by a common
economic-convergence process, not that digitalization is doing the
causal work.

## Files

- `scripts/download_cohesion_digital_funding.py`,
  `scripts/download_eurostat_energy_consumption.py` — fetch scripts, both
  added to `scripts/download_all.py`.
- `data/raw/cohesion/digital_investment_2014_2020.csv` — Cohesion Policy
  TO2 (ICT) expenditure, country x year.
- `data/raw/eurostat/industrial_energy_consumption.csv` — industry final
  energy consumption, country x year.
- `analysis/phase_d_analysis.py` — both items' full analysis, including
  the corrected `GB→UK` country-code mapping, the G5-targeted leave-one-out,
  the placebo/timing test, and the accession-cohort split.
- `analysis/output/phase_d_item1_onset_years.csv`,
  `phase_d_item1_pretrend_check.csv`, `phase_d_item1_event_study_coefs.csv`,
  `phase_d_item1_results.csv`, `phase_d_item1_event_study.png` — item 1's
  full evidence.
- `analysis/output/phase_d_item2_results.csv`,
  `phase_d_item2_leave_one_out.csv` (now targeting G5),
  `phase_d_item2_control_decomposition.csv` — item 2's full evidence,
  including the mechanism decomposition, leave-one-out, placebo test, and
  accession split.

## What this analysis does NOT show

- It does **not** establish that EU digital-funding disbursement causally
  affects (or fails to affect) verified emissions — the design cannot
  support a conclusion in either direction given how much of the sample
  is left-censored and the significant pre-trend in its most precise
  estimate. This is a statement about what the available data can
  support, not evidence that funding does or does not work.
- It does **not** show that digitalization causes faster industrial
  value-added growth. The correlation is real and robust, but a placebo
  test finds future digitalization tracks past growth at least as well as
  past digitalization tracks future growth — the data cannot establish
  the direction, and the most parsimonious explanation (a shared
  convergence/catch-up process) requires no causal channel from
  digitalization to growth at all.
- It does **not** show that digitalization improves energy efficiency —
  raw energy consumption shows no detectable association with DII in any
  specification; the energy-intensity result is fully explained by the
  (itself non-causally-established) value-added growth finding.
- It does **not** change the project's standing conclusion about verified
  emissions specifically: no digitalization-emissions relationship
  survives correct inference at any level of aggregation or research
  design tried across Phases A-D (country, sector, region, or
  funding-event timing). What item 2 adds is a robust *adjacent*
  correlation (value-added growth) with an unresolved, and on the
  evidence here probably non-causal, direction — not a reversal of the
  emissions null.
