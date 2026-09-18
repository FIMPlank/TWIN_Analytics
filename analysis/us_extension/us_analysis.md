# US extension: does digitalization intensity predict verified emissions
change at state/county level?

Reproducible from `analysis/us_extension/us_analysis.py`, which loads the
panels documented in `panel_qc.md`
(`output/panel_state_year_us.csv`, `output/panel_county_year_us.csv`).
**Read `panel_qc.md` first** — in particular §1 (the Census API is
blocked; the regressor here is BLS QCEW tech-sector employment share,
which §1 now shows is empirically close to an *inverse* index of
industrial intensity, not just "a different construct") and §2/§5 (the
GHGRP supplier-sector filter and the missingness-bug fix that this
report's headline numbers depend on).

**Revision note (round 2, post-Reviewer):** `analysis/us_extension/review.md`
found this report's original headline overclaimed in three ways — "every
p-value is above 0.59," "cleaner null than the EU's," and "no stable
sign" — and one blocking data bug (§5 of `panel_qc.md`). Corrected:
proper winsorization added; the level specifications are **consistently
negative**, not sign-unstable (the earlier "unstable sign" claim mixed
level and lag/lead specs together, which is the wrong comparison); the
regressor is empirically anti-correlated with industrial intensity
(r=-0.59, `panel_qc.md` §1) — the single most important framing fact,
carried through every claim below.

**Revision note (round 3, post-Reviewer round 2): the round-2 edit
introduced its own bug — the pre-existing biogenic-CO2 exclusion filter
was accidentally deleted, so every round-2 headline number below silently
included biogenic CO2.** Restored in `build_panel.py` (see `panel_qc.md`
§3, §5); every table in this document is regenerated on the corrected,
biogenic-excluded panel. Two secondary corrections from the same review
round: (a) the round-2 "true minimum p-value is 0.089" claim is itself
superseded — the corrected minimum, on the properly-restored panel, is
**0.125** (independently cross-checked against a Reviewer reimplementation
at 0.128 — the two are within ordinary wild-bootstrap seed variation of
each other); (b) the −0.024 vs. an earlier-cited −0.109 discrepancy
flagged in round 2 is resolved: **neither number was right**. The round-2
missingness fix (§5 of `panel_qc.md`) turned out to be a mathematical
no-op for `d_log_emissions` (it only ever changed `total_co2e` in ways
that were already producing `NaN`, not `0`, downstream); the actual
mover, both times, was the biogenic filter. The corrected county bare
coefficient is **−0.056** (round 3), close to the very first
(pre-any-fix) draft's −0.054 — the missingness fix was a real latent
defect worth having, but never actually changed this report's headline
number. A `.diff()` year-contiguity guard was also added (`panel_qc.md`
§5) after both this build and an independent Reviewer reconstruction were
separately found to have, at different points, let a `.diff()` span a
missing-row year gap and manufacture a spurious multi-year "annual"
change.

## Purpose

The EU side of this project (`analysis/phase_b_analysis.md`) found **no
significant relationship** between digitalization intensity and verified
emissions change, across 11 years, two independent EU digitalization
measures, country and sector-country panels, and rigorous small-cluster
inference. This extension asks whether the same null shows up in the US,
using EPA GHGRP facility emissions and BLS QCEW tech-sector employment as
a free, keyless, live US panel.

## The central limitation, stated before any result

**This is not a clean test of H1.** `panel_qc.md` §1 quantifies what
round 1 of this report only described qualitatively: `tech_emp_share`
correlates at **r=-0.592** (state level, 2023, round-3 biogenic-excluded
figure) with log(CO2e per private employee) — i.e. it is close to an
inverse index of how industrial a
state's economy is. The 2023 top-8 states by `tech_emp_share` (DC, WA,
VA, CO, CA, MA, MD, UT) and bottom-8 (MS, LA, AR, WY, IN, VI, DE, OK) are
close to disjoint from each other on industrial intensity. The
hypothesized channel runs through industrial/manufacturing firms
adopting digital tools; this regressor instead marks *how little* of a
state's economy is industrial in the first place. **A null result below
is therefore closer to "tech-hub states and heavy-industrial states are
different places" (true, uninteresting, nearly mechanical) than to "no
relationship between digitalization and emissions" (the actual
question).** Every result in this document should be read through that
lens — this is reported as a coverage/feasibility exercise for building a
free-data US panel, not as a genuine test of the EU comparison.

## Method

Same small-cluster-robust machinery as `analysis/phase_b_analysis.py`:
naive cluster z, t(G−1), and a restricted-null Rademacher wild cluster
bootstrap (1,999 reps) — **wild-bootstrap p is authoritative**.
`tech_emp_share` enters as a level in the headline specs and as a first
difference in a dedicated robustness spec. State panel: year FE, cluster
by state. County panel: year FE + state FE, cluster by state. A matched
lag/lead placebo check is run on both panels on the identical sample
between specs. **New in round 2:** 1st/99th-percentile winsorization of
`d_log_emissions` as a headline row (not a skipped limitation), a
`PETRO_NG`-excluded outcome cut (Subpart W is reported at basin/operator
level — see `panel_qc.md` §2b), a first-differenced regressor spec, a
territory-excluded (PR+VI+DC dropped) cut, a within-state (state-FE) spec
that shows the state panel cannot speak to within-state variation, and a
leave-one-state-out check across all clusters in both panels. No
GDP-growth or energy-shock control is included (see Limitations).

## Headline result

**Still a null — no coefficient reaches conventional significance
anywhere.** The true minimum wild-bootstrap p-value across every
specification run is **0.125** (the first-differenced state regressor,
S7; independently cross-checked at 0.128 by the Reviewer's own
reimplementation), in the same general range as the EU's own minimum
(0.265, panel v2b's convergence interaction) — not obviously cleaner, not
obviously noisier. **Every contemporaneous-level specification's point
estimate is negative** (the hypothesized direction) except the
within-state-only spec (S6), which is flagged below as uninformative on
its own terms, not as evidence of instability.

### State-year panel (n=477, 53 clusters [50 states + DC + PR + VI],
2015-2023, cluster = state)

| Model | Target | n | G | coef | 95% CI (t,G−1) | p (naive z) | p (t, G−1) | **p (wild bootstrap)** |
|---|---|---|---|---|---|---|---|---|
| S1 bare (+ year FE) | `tech_emp_share` | 477 | 53 | −0.092 | [−0.442, +0.258] | 0.599 | 0.601 | **0.612** |
| S1w winsorized outcome (1/99) | `tech_emp_share` | 477 | 53 | −0.245 | [−0.616, +0.127] | 0.186 | 0.192 | **0.232** |
| S2 + log(n_facilities) | `tech_emp_share` | 477 | 53 | −0.092 | [−0.444, +0.259] | 0.598 | 0.601 | **0.596** |
| S7 differenced regressor | `tech_emp_share_diff` | 424 | 53 | −4.044 | [−9.911, +1.824] | 0.167 | 0.173 | **0.125** |
| S5 excl. PR+VI+DC (50 states only) | `tech_emp_share` | 450 | 50 | −0.165 | [−0.607, +0.278] | 0.455 | 0.458 | **0.460** |
| S6 + state FE (within-state only — see note) | `tech_emp_share` | 477 | 53 | +0.735 | [−2.192, +3.662] | 0.614 | 0.617 | **0.592** |
| S3 REAL: lagged, matched (n=371) | `tech_lag` | 371 | 53 | +0.139 | [−0.561, +0.840] | 0.690 | 0.692 | **0.891** |
| S4 PLACEBO: lead, matched (n=371) | `tech_lead` | 371 | 53 | −0.011 | [−0.564, +0.543] | 0.970 | 0.970 | **0.979** |

**S6 note:** only 2.2% of the variance of `tech_emp_share` in the state
panel is *within*-state (the panel is 98% cross-sectional — a state's
tech-employment share barely moves year to year). Adding state FE turns
the spec into a within-state-only test, and the resulting SE (1.46, vs.
0.156 without state FE) shows there is essentially no usable within-state
signal to test with — **S6's near-zero informativeness, not its flipped
sign, is the finding worth reporting.** The state panel's other headline
specs (S1, S1w, S2, S5, S7) are therefore a between-state comparison,
exactly the comparison most exposed to the industrial-composition
confound in the Central Limitation above.

**Leave-one-state-out (S1 spec):** coefficient ranges **−0.196 to −0.034**
across all 53 single-state drops, **zero sign flips**, minimum p(t,G−1)
= 0.266 (dropping Washington). No single state manufactures or conceals
this result.

### County-year panel (n=15,030, 1,865 counties, 2015-2023, cluster =
state, state FE)

| Model | Target | n | G | coef | 95% CI (t,G−1) | p (naive z) | p (t, G−1) | **p (wild bootstrap)** |
|---|---|---|---|---|---|---|---|---|
| C1 bare (+ year FE + state FE) | `tech_emp_share` | 15,030 | 53 | −0.056 | [−0.324, +0.211] | 0.672 | 0.674 | **0.693** |
| C1w winsorized outcome (1/99) | `tech_emp_share` | 15,030 | 53 | −0.105 | [−0.280, +0.070] | 0.228 | 0.233 | **0.310** |
| C2 + log(n_facilities) | `tech_emp_share` | 15,030 | 53 | −0.055 | [−0.321, +0.212] | 0.681 | 0.682 | **0.697** |
| C7 differenced regressor | `tech_emp_share_diff` | 13,119 | 53 | +1.054 | [−0.454, +2.561] | 0.161 | 0.167 | **0.181** |
| C5 excl. PETRO_NG (Subpart W) | `tech_emp_share` | 13,809 | 53 | −0.058 | [−0.277, +0.162] | 0.599 | 0.601 | **0.611** |
| C6 excl. PETRO_NG + winsorized | `tech_emp_share` | 13,809 | 53 | −0.131 | [−0.306, +0.044] | 0.133 | 0.139 | **0.221** |
| C3 REAL: lagged, matched (n=11,301) | `tech_lag` | 11,301 | 53 | +0.046 | [−0.264, +0.356] | 0.766 | 0.768 | **0.772** |
| C4 PLACEBO: lead, matched (n=11,301) | `tech_lead` | 11,301 | 53 | +0.075 | [−0.208, +0.357] | 0.596 | 0.598 | **0.595** |
| C1b robustness: n_facilities≥2 | `tech_emp_share` | 11,116 | 52 | −0.053 | [−0.303, +0.198] | 0.674 | 0.676 | **0.695** |

**Leave-one-state-out (C1 spec):** coefficient ranges **−0.102 to
+0.015**, **1 of 53 sign flips** (a coefficient this close to zero flips
sign easily — this reflects how weak the estimate is, not a single-state
artifact inflating a real finding), minimum p(t,G−1) = 0.406 (dropping
Wyoming). No state comes close to manufacturing significance in either
direction.

### Corrected sign-stability statement

Every **contemporaneous-level** specification (S1, S1w, S2, S5, C1, C1w,
C2, C5, C6, C1b) has a **negative** coefficient — the hypothesized
direction — with the single exception of S6, which is separately flagged
as an uninformative within-state-only test, not counted as a genuine sign
disagreement. The three **positive** coefficients in the tables (S3/C3
lagged, S4/C4 lead) come from the placebo-matched lag/lead specs, which
have the widest standard errors of any model here and are not
contemporaneous levels in the first place — comparing them to the level
specs as evidence of "instability" (round 1's framing) conflated two
different kinds of specification. **The honest statement: a consistently
negative but never-significant contemporaneous point estimate, roughly
2-4x larger once outliers are handled via winsorization or a
PETRO_NG-clean outcome, with the single lowest p-value (0.125) coming
from the differenced-regressor spec — still not significant at
conventional levels, and still subject to the Central Limitation above.**

### Minimum detectable effect (state S1 spec)

A null is a claim about statistical power, not just a p-value — this was
missing from round 1. SD(`tech_emp_share`) = 0.0148; the S1 point
estimate implies a 1-SD increase in tech-employment share associates with
a **−0.0014** change in `d_log_emissions` (95% CI **[−0.0065,
+0.0038]**), against a sample mean *decline* rate of **0.0288** (2.88
pp/yr). The minimum detectable effect at 80% power is **0.0074** per 1-SD
of the regressor — **about 26% of the average annual decline rate**. This
is a moderately informative null on its own terms (it rules out large
effects) but, per the Central Limitation, "informative about
`tech_emp_share`" and "informative about digitalization adoption" are not
the same claim.

## What was deleted, not softened

**Round 1 argued the US null was "some evidence against the hypothesis
that the EU null was an artifact of the ETS cap specifically swamping any
digitalization signal." This claim is deleted, not hedged, per the
Reviewer's B1 finding.** The inference requires this US test to have had
a real chance of detecting the effect in question. Given the Central
Limitation above, it did not — a null from a regressor that does not
measure the hypothesized treatment (industrial-firm digital adoption) is
consistent with *both* "the ETS cap was irrelevant to the EU null" and
"the ETS cap was doing all the work" equally. No amount of hedging fixes
an invalid logical step. What remains, and is defensible: **the null is
not unique to EU ETS data, EU digitalization measures, or the EU's
institutional setting** — a structurally different country, outcome
variable, and regressor construction all land on "no detectable
relationship," which is itself worth reporting. That is a narrower claim
than the deleted one, and it is the one this extension actually supports.

## Comparison to the EU finding

| | EU (panel v2a/v2b, DII) | US (this extension) |
|---|---|---|
| Outcome | EU ETS verified emissions, Δlog | GHGRP direct-emitter CO2e, Δlog |
| Digitalization measure | Adoption intensity (any sector) | Structural tech-sector employment share, **anti-correlated with industrial intensity (r=-0.59)** |
| Years | 2015-2025 | 2015-2023 |
| Units | 29 countries / 7 sectors × country | 50-53 states / 1,865 counties |
| Contemporaneous-level sign | Mixed (+ in v2a, sign-flips in v2b by control) | **Consistently negative** |
| Smallest wild-bootstrap p across all models | 0.265 (v2b B5 interaction) | **0.125** (S7, differenced) |
| **Verdict** | **Null** | **Null, but not a clean test of the same hypothesis** |

**Both are null. That comparison is real and is the one thing this
extension can support — not the ETS-cap inference (deleted above), and
not a claim that the two nulls are measuring the same underlying
relationship.** Given the Central Limitation, this table should not be
read as "the US replicates the EU's null under a comparable design" — it
is closer to "a differently-constructed, weaker test also failed to find
a relationship," which is a real but much more modest finding.

## Limitations

1. **The regressor cannot carry the hypothesis (restated, not new).**
   `tech_emp_share` is empirically anti-correlated with industrial
   intensity (`panel_qc.md` §1, r=-0.59). This is the single largest
   limitation of the whole exercise. A genuine Census ABS technology-
   module pull (blocked on a free API key this pipeline does not obtain
   on its own) remains the natural next step and would let this become an
   actual test of H1 rather than a coverage exercise.
2. **No GDP-growth or energy-shock control.** No free, keyless
   state/county source for either was identified in the time available
   (BEA's regional GDP API is also key-gated). Year fixed effects absorb
   common national trends but not state/county-specific shocks.
3. **Facility-level aggregation, not firm-level** — same caveat every EU
   report in this project repeats.
4. **GHGRP covers only large emitters**, like EU ETS — not an
   economy-wide emissions panel.
5. **9 usable years (2015-2023), shorter than the EU's 11 (2015-2025)** —
   GHGRP's own reporting lag, not a choice made for convenience.
6. **Residual understatement in partial-coverage county-years**
   (`panel_qc.md` §5): a county-year with some but not all facilities
   missing still sums only the reporting ones, understating the true
   total by an unknown amount. Not corrected (would require imputation);
   disclosed rather than silently left as fully fixed.
7. **No convergence/catch-up or region-specific interaction tested** —
   no obvious US analog to the EU's accession-cohort variable was
   operationalized in this round.
8. **The state panel is close to purely cross-sectional** (2.2%
   within-state variance in the regressor) — S6 above shows this
   directly; the county panel, where state FE does real work (91%
   within-county variance), is the better-identified of the two and
   should be weighted more heavily by any reader.

## What this analysis does NOT show

- It does **not** show that digitalization causes, or fails to cause,
  emissions changes in the US.
- It does **not** show that a properly-measured adoption-intensity
  regressor would produce the same null — that measure was never
  actually tested, only blocked (`panel_qc.md` §1).
- It does **not** license any claim about *why* the EU found a null (the
  deleted ETS-cap argument) — this design cannot discriminate between
  competing explanations of another study's null.
- It does **not** establish that the EU and US findings test the same
  underlying relationship — given the Central Limitation, they are best
  read as two separate, differently-flawed nulls that happen to point the
  same direction, not as a replication.
- It does **not** rule out a real relationship this data, or this
  regressor, is underpowered or structurally unable to detect. The
  minimum detectable effect (state panel) is about 26% of the average
  annual decline rate — moderately informative about `tech_emp_share`
  specifically, silent on adoption-intensity digitalization given the
  Central Limitation.
