# Review: US state/county extension

Rounds 1 and 2. **Round 2 (the current, post-fix check) is first; the
round 1 review is retained below as the record.**

Reviewer pass over `analysis/us_extension/panel_qc.md`,
`us_analysis.md`, `us_analysis.py`, `build_panel.py`,
`scripts/download_epa_ghgrp.py`, `scripts/download_bls_qcew_tech.py`,
`scripts/download_census_abs_tech.py`. Held to the bar set by the five
EU-side review rounds (`analysis/review.md`, `review_extension.md`,
`phase_b_review.md`, `phase_c_review.md`).

Everything below was re-derived independently: the Envirofacts and Census
APIs were queried directly, `build_panel.py` was re-run, and the
regressions were re-estimated with a **separately written** OLS /
cluster-robust / wild-cluster-bootstrap implementation rather than by
importing `us_analysis.py`'s machinery.

---

# ROUND 2 — final check (post-fix)

Re-read `us_analysis.md`, `panel_qc.md`, `build_panel.py`,
`us_analysis.py` after the round-2 fixes. Every number below was again
re-derived from raw data with my own code.

## Round 2 verdict

**Conditional go.** The interpretive work — the part that mattered most —
is done properly, and in places better than I asked for. B1 (ETS-cap) and
B2 (proxy validity) are fully and honestly addressed, the sign-stability
correction is right, and the report now reads as an appropriately scoped,
appropriately humble artifact. **But the B3 fix introduced a silent
regression that invalidates every number in both round-2 tables, and the
disclosed −0.024 vs −0.109 discrepancy has a concrete resolution that
neither of us had right.** Both are mechanical: one line of code and a
table regeneration.

### R1 (BLOCKING, new) — the biogenic-CO2 filter was deleted while fixing B3

`build_panel.py` line 86 still defines `BIOGENIC_GAS_ID = 8` and line 111
still carries the comment "Total CO2e per facility-year, excluding
biogenic CO2 (gas_id=8)" — but **the filter statement itself is gone**.
The old `em = em[em["gas_id"] != BIOGENIC_GAS_ID]` sat immediately above
the aggregation and was dropped when the `min_count=1` change and its
comment block were inserted. `BIOGENIC_GAS_ID` is now referenced nowhere
in executable code.

Not an inference — I rebuilt the panel both ways and matched against the
delivered CSVs:

| reconstruction | matches published county panel | matches published state panel |
|---|---|---|
| **with** biogenic (no gas_id filter) | **27,955 / 27,955** | **756 / 756** |
| without biogenic (as documented) | 20,939 / 27,955 | 110 / 756 |

Exact on both. The delivered data includes biogenic CO2. Biogenic is
4.67% of direct-emitter mass, concentrated in pulp & paper and
biomass-co-firing power plants — sectorally and geographically
non-random, and trending over the period, so it contaminates
`d_log_emissions` rather than adding uniform noise. Meanwhile
`build_panel.py`'s docstring point 1 and `panel_qc.md` §3 both still
assert the exclusion, so the documentation contradicts the delivered
data. This is the exact failure mode round 1 credited the supplier catch
for avoiding: a panel that looks entirely plausible while measuring
something other than what it says.

### R2 (BLOCKING, resolution) — the −0.024 vs −0.109 discrepancy: both numbers were wrong

Flagging this rather than force-fitting my number was the right call. But
the stated explanation — "aggregation-policy choice (how partial facility
coverage is handled)" — **is not the cause**, and partial coverage is in
fact handled *identically* by both implementations: `sum(min_count=1)`
and "drop the NaN facility-years, then sum" return the same total for any
county-year with some reporting and some missing facilities. There are
two separate errors:

**(a) The `min_count=1` fix, with rows retained, is a mathematical no-op
for the outcome.** It changes `total_co2e` from `0.0` to `NaN` on 1,110
all-missing county-years — but those cells already produced `log(0)` →
`NaN` under `.where(total > 0)`. Reconstructing both ways,
`d_log_emissions` differs on **exactly 0 rows**, and the regression is
bit-identical: coef −0.0541, se 0.1336, n 15,037 under both. So the
round-2 movement from −0.054 to −0.024 is **entirely** attributable to R1
(biogenic), not to the B3 fix.

**(b) My round-1 −0.109 was wrong, for a reason I flagged myself.** My
FIX1 dropped NaN facility-years *before* aggregation, which deletes 1,110
county-year rows, opens year gaps, and lets `.diff()` span them —
manufacturing 44 spurious multi-year "annual" changes (mean |Δlog| =
1.57, max 5.92) on thin counties. Those 44 high-leverage rows are the
whole of the −0.054 → −0.109 move. That is precisely the N1 year-gap
contamination I listed as nice-to-have in round 1 and then walked into.
**The row-retention approach is the correct one and mine was not**; that
should be recorded, and the `.diff()` contiguity guard (N1) is now worth
doing rather than deferring.

**The correct value is C1 bare = −0.054** — unchanged from round 1's
baseline. Which means **B3 was a real latent defect but never a
consequential one**: it never touched `d_log_emissions`. Fixing it is
still right (it protects `total_co2e` in levels and any future use), but
the round-2 text should stop describing it as a bug whose correction
moved the headline, because it did not.

Corrected headline numbers (independently derived; wild bootstrap, 1,999
reps):

| Spec | round-2 published (biogenic in) | **corrected** |
|---|---|---|
| S1 state bare | −0.091, p_w 0.568 | **−0.092, p_w 0.608** |
| S1w state winsorized | −0.248, p_w 0.163 | **−0.215, p_w 0.240** |
| S7 state differenced | −4.383, **p_w 0.089** | **−4.044, p_w 0.128** |
| S5 excl PR+VI+DC | −0.169, p_w 0.379 | **−0.164, p_w 0.454** |
| S6 + state FE | +0.237, p_w 0.855 | **+0.735, p_w 0.607** |
| C1 county bare | −0.024, p_w 0.859 | **−0.054, p_w 0.696** |
| C1w county winsorized | −0.081, p_w 0.409 | **−0.109, p_w 0.283** |
| C5 excl PETRO_NG | −0.024, p_w 0.832 | **−0.057, p_w 0.584** |
| C6 excl PETRO_NG + winsorized | −0.103, p_w 0.286 | **−0.126, p_w 0.203** |
| C7 county differenced | +1.052, p_w 0.190 | **+1.056, p_w 0.181** |
| C1b n_facilities≥2 | −0.011, p_w 0.933 | **−0.053, p_w 0.684** |
| LOO state (S1) | −0.157 to −0.036, 0 flips | **−0.196 to −0.034, 0 flips, min p(t) 0.266** |
| LOO county (C1) | −0.069 to +0.050, 3 flips | **−0.100 to +0.017, 2 flips, min p(t) 0.418** |

No conclusion changes. Every level spec stays negative, nothing
approaches significance, and the corrected minimum is **0.128** (S7), not
0.089 — so **Fix 2's specific claim does not survive**, though its
substance (the true minimum is ~0.13, not 0.59) does.

## Round 2: what I verified as correct

- **Fix 3 (sign stability) — confirmed, and stronger under correction.**
  "10 of 11 contemporaneous-level specs negative, S6 the exception"
  reproduces exactly on the corrected build (S1, S1w, S2, S5, C1, C1w,
  C2, C5, C6, C1b all negative; S6 +0.735, SE 1.459). Separating level
  specs from lag/lead specs rather than pooling them into an
  "unstable sign" claim is the right analytical move and is now argued
  explicitly rather than asserted.
- **Fix 4 (B2) — confirmed and well-calibrated.** The r = −0.595
  correlation, the +0.374 / −0.392 companions, and both top-8/bottom-8
  state lists are in `panel_qc.md` §1 in a table with the interpretation
  spelled out, and restated in `us_analysis.md` as a "Central Limitation"
  section placed *before* any result rather than in a limitations
  appendix. My independent figure is −0.590 pooled vs. their −0.595 on
  the 2023 cross-section; same number. On calibration: close to right.
  Not over-corrected into nihilism — the residual claim they keep ("the
  null is not unique to EU ETS data, EU measures, or the EU's
  institutional setting") is genuinely supported and worth reporting, and
  the "coverage/feasibility exercise" framing is honest without making
  the work pointless. The one residual tension: a full EU comparison
  table is still presented under a framing that says the comparison
  cannot bear weight. It is explicitly caveated in place, so I would
  leave it — but a reader skimming tables will take more from it than the
  surrounding text licenses.
- **Fix 5 (ETS-cap) — confirmed deleted, not softened.** There is a
  dedicated "What was deleted, not softened" section that states the
  original claim, explains why the logical step is invalid at any
  confidence level, and names the narrower claim that survives. Exactly
  the right disposition.
- **Fix 6 additions — all six present and correctly specified.**
  Leave-one-state-out across all 53 clusters in both panels;
  PETRO_NG-excluded outcome (built as a parallel
  `total_co2e_excl_petro_ng` column with its own log/diff — clean, and
  the `is_petro_ng` flag merge is one row per facility-year with no
  fan-out, which I checked); first-differenced regressor; PR+VI+DC-
  excluded cut; within-state (S6) spec with the 2.2%-variance diagnostic;
  winsorized rows promoted into the headline tables; MDE and 95% CIs
  throughout. The "53 clusters [50 states + DC + PR + VI]" relabel is
  done. Only the *values* are affected by R1.

## Round 2: recommended next step

1. Restore `em = em[em["gas_id"] != BIOGENIC_GAS_ID]` in
   `load_facility_emissions()` and re-run `build_panel.py` then
   `us_analysis.py`. The corrected values above were derived
   independently and should match.
2. Replace "0.089" with the corrected minimum (0.128, S7) in the revision
   note, the headline, and the EU comparison table.
3. Rewrite the discrepancy disclosure using R2(a)/R2(b): the B3 fix is a
   no-op for `d_log_emissions`, the correct C1 is −0.054, and the
   reviewer's round-1 −0.109 was the artifact. Drop the description of B3
   as a bug whose fix moved the headline.
4. Add the `.diff()` year-contiguity guard (N1) — no longer cosmetic now
   that it is the documented cause of a real discrepancy.
5. Add a one-line assertion that `gas_id == 8` is absent from the
   aggregation input, so this particular filter cannot silently vanish
   again.

After that, this is ready to fold into the project as an honest, clearly
bounded US comparison point.

## Round 2 sign-off (post-fix verification)

**Cleared. Ready to commit as final.** Re-verified after the fixes:

- **Both guards present and correctly placed.** `build_panel.py:125-126`
  restores the filter with `assert (em["gas_id"] == BIOGENIC_GAS_ID).sum()
  == 0` immediately after it — this fires on exactly the regression that
  occurred (deletion of the filter line). `build_panel.py:216-231`
  computes a per-unit `year.diff()` and nulls any `d_log_emissions` whose
  row gap is not exactly 1, closing N1 generically rather than for one
  code path. (Minor, not worth acting on now: `assert` is stripped under
  `python -O`; an explicit raise would be marginally stronger.)
- **Biogenic exclusion verified exact**: the delivered panels match a
  biogenic-excluded rebuild on **756/756** state rows and
  **27,955/27,955** county rows.
- **Numbers reproduce.** C1 county bare −0.0564 (reported −0.056); n falls
  15,037 → 15,030, which is exactly the 7 gap-spanning usable rows
  identified as N1 in round 1 and accounts for the whole −0.054 → −0.056
  move. S1 −0.0917. S7 differenced −4.0436, p_wild 0.128 at my seed and
  0.117-0.131 across seeds, so the reported 0.125 is within seed variation
  as claimed. C1 winsorized −0.111, p_wild 0.273. B2 correlation −0.592,
  matching.
- **Nothing else drifted**: 477 usable state-years, 53 clusters,
  2015-2023 window, and the leave-one-state-out picture are all unchanged.

---

# ROUND 1 review (retained as record)

## Verdict

**No-go as currently framed. Close to a go on substance.** The panel
engineering is sound, the arithmetic reproduces exactly, and the
qualitative conclusion — no statistically significant relationship —
survives everything I threw at it. But two of the three claims that
carry the headline do not survive, and one of them is load-bearing for
the comparison to the EU:

1. **"Every single p-value ... is above 0.59" and "if anything, a cleaner
   null than the EU's" are not robust.** Applying the 1st/99th-percentile
   winsorization that `us_analysis.md` itself lists as skipped
   (Limitation 6), plus two data-quality fixes documented below, moves
   the county coefficient from −0.054 (p_wild=0.696) to **−0.152
   (p_t=0.085, p_wild=0.131)** and the state coefficient from −0.092
   (p_wild=0.608) to **−0.275 (p_wild=0.184)**. Still null — but the
   minimum p across the exercise is ~0.13, not 0.59, which is *the same
   neighbourhood as* the EU's 0.265, not cleaner than it. The "cleaner
   null" sentence has to go, and the winsorized specs have to be in the
   table rather than in the limitations list.
2. **"No stable sign" is not accurate.** Every contemporaneous level
   specification I ran — baseline, winsorized, NaN-fixed, Subpart-W-
   excluded, leave-one-state-out (53 of 53), territory-excluded — is
   negative, i.e. the hypothesized direction. The three positive
   coefficients cited as evidence of instability are all lag/lead specs,
   the ones with the widest SEs. The honest statement is "a consistently
   negative but never significant point estimate, of a magnitude that
   roughly triples once outliers are handled."
3. **The ETS-cap inference does not follow and should be cut** (not
   softened). See "Confirmed issues → B1".

Nothing here is a merge bug, a sign-convention error, or a spurious
significance. The direction of the problem is the *other* EU failure
mode — the Phase B "cleaner null" one: a null that is partly manufactured
by noise, stated more confidently than the evidence supports.

---

## Confirmed issues

### BLOCKING

**B1 — The "some evidence against the ETS-cap explanation" claim is not
supported by this design, and needs removing rather than hedging.**
`us_analysis.md` says the US null is "*some* evidence against the
hypothesis that the EU null was an artifact of the ETS cap specifically
swamping any digitalization signal." That inference requires the US test
to have had a real chance of detecting the effect. It did not, and the
report's own §1 caveat is the reason why. You cannot use an
uninformative test of X to discriminate between two competing
explanations of another study's null on X — a null from a regressor that
does not measure the hypothesized treatment is consistent with *both*
"the cap was irrelevant" and "the cap was doing it." The paragraph is
hedged in tone ("suggestive, not conclusive") but the logical step is
invalid at any confidence level. Delete the claim; the extension's
contribution is "the null is not unique to EU ETS data and measures,"
which is real and does not require the cap argument.

**B2 — The proxy is empirically anti-correlated with the population the
hypothesis is about, and the report never quantifies this.** The
structural-vs-adoption-intensity gap is disclosed repeatedly and
honestly (credit below), but always in the abstract. Measured, it is
worse than the prose implies:

| `tech_emp_share` vs. | state panel | county panel |
|---|---|---|
| log(CO2e per private employee) | **−0.590** | −0.258 |
| log(private employment) | +0.340 | +0.436 |
| GHGRP facilities per 10k employees | −0.379 | −0.136 |

The 2023 top-eight on `tech_emp_share` are DC, WA, VA, CO, CA, MA, MD,
UT; the bottom-eight are MS, LA, AR, WY, IN, VI, DE, OK. Wyoming reports
236 t CO2e per private employee, DC 0.31. This variable is, to a first
approximation, an inverse index of how industrial a state's economy is.
So the regressor and the outcome are generated by near-disjoint and
systematically *opposed* populations: the hypothesized channel runs
through industrial firms adopting digital tools, while high values of
the regressor mark areas that have comparatively few such firms. That is
not a "different construct that shares a word" — it is a construct
pointing the wrong way for the mechanism under test, and it means a null
here is close to uninformative about H1 rather than weakly informative.
These three correlations (or equivalent) belong in `panel_qc.md` §1, and
the framing in `us_analysis.md` needs to shift from "informative, but not
a strict replication" to "this measure cannot carry the hypothesis; it
is reported as a coverage/feasibility exercise pending a real
adoption-intensity measure." This is the single most important fix.

**B3 — `groupby().sum()` silently converts all-NaN facility-years to
zero, with a strong time trend.** `build_panel.py:113` aggregates
`co2e_emission` without `min_count`, so a facility-year whose emission
rows are all NULL becomes `0.0` rather than `NaN`. This affects
**20,186 of 127,511 direct-emitter facility-years (15.8%)**, and the
share is not stationary — it rises monotonically from 0% of reporting
facilities in 2010-2012 to **28.5% in 2023** (9.1% in 2015, the first
analysis year):

```
year  2013  2014  2015  2016  2017  2018  2019  2020  2021  2022  2023
 %     4.1   5.3   9.1  18.4  21.1  21.9  23.4  24.7  26.1  27.3  28.5
```

**23.8% of county-years mix zero-imputed and real facilities**, so their
totals are understated by a time-varying amount, feeding directly into
`d_log_emissions`. This is the same class of bug the EU review caught as
a silent `fillna(0)` on Eurostat DII — and `build_panel.py` gets it
*right* on the QCEW side (`min_count=1` at line 137) while missing it on
the emissions side. Note also that the 1,174 `total_co2e == 0`
county-years described in `panel_qc.md` §5 as facilities with "no
fossil/process emissions to declare" are in fact 1,110 county-years where
*every* facility is all-NULL, i.e. missing data, not declared zeros —
the log-NaN handling incidentally saves those cells, but the stated
interpretation is wrong. Fix is one argument; I verified it moves C1
from p_wild=0.696 to **0.402** (coef −0.054 → −0.109), so it is not
cosmetic.

### SHOULD-FIX

**S1 — Winsorization was skipped on an empirically false justification.**
Limitation 6 argues the `n_facilities >= 2` cut makes winsorization
unnecessary. It does not. The QC claim that extreme values are
"concentrated almost entirely in county-years with exactly 1 reporting
facility" holds only at the |Δlog| > 5 threshold (27 of 37). At the
thresholds that actually generate OLS leverage it breaks down: of 360
usable cells with |Δlog| > 1, only 44% are single-facility, and **200
survive the n≥2 cut**. Hence the cut barely moves the coefficient
(−0.054 → −0.053) while winsorizing nearly doubles it. The residual SD
is 0.67 in single-facility cells vs. 0.24 in 20+-facility cells, so this
is textbook heteroskedastic-leverage attenuation. Report winsorized 1/99
as a headline row, not a limitation.

**S2 — Subpart W geography is the supplier trap's second cousin, and it
was not caught.** The `sector_type == 'E'` filter is correct on the
emissions-concept axis (verified below), but `PETRO_NG` (Subpart W,
Petroleum and Natural Gas Systems) is 9.0% of the final outcome mass and
is reported at *basin* / operator level for onshore production, gathering
and boosting — a whole multi-county basin booked to one county. This is
the same error type the supplier catch fixed (an upstream aggregate
attributed to wherever the reporting entity sits), one level down.
Excluding `PETRO_NG` drops 182 counties and moves C1 winsorized to
p_wild=0.180, and combined with B3 to **coef −0.152, p_t=0.085,
p_wild=0.131** — the most suggestive result anywhere in the exercise.
Run it as a robustness cut, the way `phase_b_analysis.md` reports v2b
with and without combustion side by side.

**S3 — The county-FIPS drop is non-random and its composition is not
disclosed.** `panel_qc.md` §9 attributes the 7.8% drop to "mostly older
filings and a handful of offshore/tribal-land facilities." The actual
composition of the 10,628 dropped facility-years is W-ONSH (3,997),
C,W-OFFSH (1,309), W-GB (715), transmission pipelines, plus **2,589
plain "Direct Emitter" facilities**; by state it is TX 3,599, LA 1,542,
OK 768, CO 748, NM, ND. It is 2.98% of direct-emitter mass and the drop
count rises from 45 (2010) to 1,130 (2023). So the panel systematically
and increasingly excludes oil-and-gas-state emissions. Necessary given
no county assignment exists — but it should be described as a
geographically non-random, time-trending exclusion rather than as
housekeeping.

**S4 — No confidence intervals, no minimum detectable effect anywhere.**
A null is a claim about power and neither report states any. For the
state spec: SD(`tech_emp_share`) = 0.0148, so a 1-SD increase implies
−0.14 pp/yr with a 95% CI of [−0.65, +0.38] pp/yr, against a sample mean
decline of 2.88 pp/yr. MDE at 80% power ≈ 0.72 pp/yr per SD, i.e. the
test can only rule out effects larger than ~25% of the observed average
decline rate. That is a moderately informative null, and saying so is
stronger than leaving it implicit. The EU reports' "fails to detect, with
limited power to do so" language (a Phase B review correction) should be
carried over verbatim in spirit.

**S5 — "53 states" is 50 states + DC + Puerto Rico + US Virgin
Islands.** Reproduced: the panel's 54 units are the 50 states, DC, GU,
PR, VI; Guam drops out for lack of QCEW coverage, leaving 53. PR and VI
are in the regression as clusters with 4 and a handful of facilities.
Dropping PR+VI moves the state coefficient −0.092 → −0.120; dropping
DC too gives −0.165. Null either way, but the label is misleading and
the cut belongs in the robustness set.

**S6 — The state panel is 98% cross-sectional and this is not stated.**
Only 2.2% of the variance of `tech_emp_share` in the state panel is
within-state (91% is within-state in the county panel). With year FE and
no state FE, S1-S4 are effectively a between-state regression of growth
rates on levels — precisely the specification most exposed to the
confound quantified in B2. Adding state FE gives coef +0.735 (SE 1.459,
p_wild=0.607), i.e. uninformative, which is itself the finding worth
reporting: the state panel cannot speak to within-state variation at all.
The county panel, where state FE does real work, is the better-identified
of the two and should lead.

**S7 — The one specification closest to the hypothesis was not run.**
Entering the regressor first-differenced gives coef −4.04 (SE 2.92,
p_t=0.173, **p_wild=0.128**) — the largest-magnitude, lowest-p estimate
in the whole exercise, hypothesized sign. The levels-only choice is
justified by analogy to `panel_v2`'s DII vintage-break concern, but
`us_analysis.py`'s own docstring concedes "no version-break was found in
QCEW specifically," so the analogy does not transfer. Report the
differenced spec; it does not change the conclusion but it is the spec a
skeptical reader will ask for first.

### NICE-TO-HAVE

**N1 — `d_log_emissions` is computed with `.diff()` without checking year
contiguity**, so a unit with a reporting gap gets a multi-year change
labelled one-year. I checked: 0 affected rows in the state panel (it is
exactly balanced, 54 × 14 = 756), 13 in the county panel, 7 inside the
usable sample. Immaterial, but worth a guard since the EU panels have the
same pattern.

**N2 — The QCEW county filter (`~endswith("000")`) also retains 388 MSA
and 51 pseudo-county area codes.** Harmless — I confirmed **zero**
collisions with GHGRP `county_fips` — but it is an accidental
non-failure, not a designed one. Filter positively on 5-digit numeric
codes.

**N3 — Bootstrap p-values use `mean(|t*| >= |t|)` rather than
`(1 + #)/(1 + B)`.** Immaterial at these p-values; the EU code has the
same habit.

**N4 — State clustering is not mechanically conservative here.** In the
county panel, SE clustered by state (0.134) is *smaller* than clustered
by county (0.167). State is still the right level, but the report should
not lean on clustering choice as a conservativeness argument.

---

## What I verified and could not break

**The supplier-sector catch is real, correctly quantified, and correctly
applied — this is the best thing in the submission.** Queried
`PUB_DIM_SECTOR` live: exactly 16 sectors, `sector_type` ∈ {E, S, I},
and the local snapshot matches the live API row-for-row (346,683
emission rows, 136,005 facility rows). Independently recomputed:
`sector_type == 'E'` retains **44.17%** of raw reported CO2e, i.e. drops
**55.83%** — the report's "55.8%" and "4.353e10 of 9.856e10" are exact.
Petroleum Product Suppliers (38.9 Gt) and Natural Gas/NGL Suppliers
(15.5 Gt) are indeed the two largest sectors in the raw table, together
exceeding Power Plants (26.3 Gt). The filter is the right width on the
emissions-concept axis: Subparts MM/NN/OO/CO2-supply are fuel-content
accounting, QQ is import/export of pre-charged equipment, `I` is
injection — all correctly excluded; the nine `E` sectors are all
genuine facility-level combustion/process emitters. Left unfiltered this
would have produced a large, complete, entirely plausible panel
measuring the wrong thing. This is a genuine EU-`20-99`-class catch and
it was found by interrogating the data rather than the documentation.
(My one disagreement, S2, is about geography within `E`, not about the
filter itself.)

**The refusal to obtain a Census API key was correct and the diagnosis
is exactly right.** Verified independently: `api.census.gov/data/...`
data queries return an HTML "Missing Key" page — including
`2020/dec/pl`, which historically needed no key — while
`/variables.json` metadata endpoints still work. That is precisely the
asymmetry §1 describes, down to the detail used to confirm the datasets
exist. And signing up requires submitting a name and email that are not
the pipeline's to submit; declining and leaving the line of analysis
explicitly *open* rather than quietly attempted-and-failed is the right
call, correctly escalated to the owner. The distinction drawn in §1
between "blocked" and "tested and failed" is exactly the one that matters
for how the result should be read.

**The headline numbers reproduce exactly.** `build_panel.py` re-runs to
756 state-year rows / 54 units and 27,955 county-year rows / 2,112
counties; usable samples are 477 (53 states) and 15,037 (1,865
counties), 2015-2023, as claimed. My independent estimator reproduces all
nine reported models to four decimals on the coefficient and within ±0.02
on the wild-bootstrap p (S1 −0.0917, C1 −0.0541, C1b −0.0525 …), with
raw correlations −0.0109 and −0.0056. Matched lag/lead samples are
genuinely the *same rows* between the real and placebo specs (n=371,
n=11,301) — the mismatched-placebo error the EU review caught in Phase B
is not repeated here.

**The wild cluster bootstrap implementation is sound.** Resampling unit
is the correct cluster level (state), Rademacher weights are applied at
cluster level and broadcast correctly, the restricted null is imposed
properly (restricted fitted values + restricted residuals, unrestricted
design for the test statistic), designs are full rank (10 and 62
columns), and there are no degenerate or NaN replications. The bootstrap
t-distribution is well-behaved (SD ≈ 1.00, 2.5/97.5 quantiles −1.93/+1.95
for the state panel, −2.15/+2.17 for the county panel) and p is stable
across four seeds (±0.02) and at B = 9,999. No leakage. 1,999 reps is
adequate. I found nothing to fix.

**Panel construction is clean where the EU builds were not.** The
`PUB_DIM_FACILITY` duplicate collapse is safe — I checked all 136,005
facility-years and `county_fips`, `naics_code` and `state` vary across
duplicate rows in **zero** cases, so "spot-checked, not assumed" holds.
The emissions-to-facility merge matches 127,511 of 127,511 facility-years
with no left-only rows. `county_fips` is always exactly five characters
when present, so the `zfill(5)` is a harmless guard rather than a
silent truncation risk. No duplicate `(state, year)` or `(county, year)`
rows, no QCEW `(area, year, industry)` duplicates, so no fan-out
double-counting. The `own_code=0` and `industry_code=5112` findings in
the QCEW script are real and were found the only way they could be —
by inspecting a raw singlefile.

**No single-cluster dominance, in either direction.** This is the check
the EU process ran five times and the submission omits, so I ran it:
leave-one-state-out across all 53 clusters in both panels. State panel
coefficients range −0.196 to −0.034 (full sample −0.092), **zero sign
flips**, minimum p_t = 0.266 (dropping Washington). County panel: −0.100
to +0.017, minimum p_t = 0.418 (dropping Wyoming). No Bulgaria, no
Spain, no Norway — no single state manufactures the null and none
conceals a significant effect. The null is not fragile to unit
composition; it is fragile to *outlier treatment* (S1), which is a
different and more tractable problem.

---

## Recommended next step

One short revision round, then this is presentable — as a feasibility and
coverage exercise, not as a cross-country test of H1.

1. Apply **B3** (`min_count=1`) — one argument, ~15 minutes including a
   re-run.
2. Add three rows to both headline tables: **winsorized 1/99** (S1),
   **excl. `PETRO_NG`** (S2), **differenced regressor** (S7). Add
   **excl. PR+VI+DC** (S5) and **leave-one-state-out range** (my numbers
   above are reusable) to the robustness set.
3. Rewrite the headline: drop "every p above 0.59," drop "cleaner than
   the EU's," replace "no stable sign" with the consistently-negative
   statement, and add the CI/MDE sentences from **S4**.
4. Delete the ETS-cap paragraph (**B1**) and put the three correlations
   from **B2** into `panel_qc.md` §1, reframing the QCEW measure as
   unable to carry H1 rather than as an imperfect version of it.
5. Fix the §5 zero-cell interpretation and the §8/§9 characterizations
   (**B3**, **S3**), and relabel "53 states" (**S5**).

Then, and this is the real next step rather than a cleanup item: **the
Census ABS technology module is the analysis, and it is still
unattempted.** Everything above is scaffolding for a regressor that
cannot test the hypothesis. The pipeline is built and the block is a free
API key the owner can provision in minutes — that decision is worth one
line in a status note, and it converts this from a coverage exercise into
the cross-country replication the project actually wants. Failing that,
a state-level adoption-intensity measure from another source (BEA/NSF
business R&D, or industry-level IT capital shares apportioned to state
industrial composition) would be a better use of a round than any further
refinement of `tech_emp_share`.
