# Review of `analysis/phase_d_analysis.md`

Independent verification of both Phase-D items. Item 2 was re-derived from
scratch — raw Eurostat files up — rather than checked against the Researcher's
outputs, and then subjected to the two tests the report does not run.

---

## Verdict

| Item | Verdict |
|---|---|
| **1 — Funding event study** | **Needs rework of the framing.** The null is not wrong, but the design cannot support presenting it as a finding, and one factual claim used to dismiss a pre-trend violation is incorrect. |
| **2 — Energy intensity / value-added** | **The correlation is real and genuinely robust. The causal direction is not — it fails a placebo test decisively.** Reframe, do not discard. |

**Direct answer to the question posed:** the value-added-growth finding is
**not** the first real signal, but it is also **not** the same kind of failure
as the earlier false alarms. Those (EIBIS p=0.047, Eurostat-controls p=0.001,
large-firm p=0.06) were *statistical* artifacts — they dissolved under a single
country's removal or a like-for-like sample comparison. This one **survives
every fragility check I could throw at it**, including the one the report ran
on the wrong regression. What it fails is a *causal-direction* test: future
digitalization predicts past industrial growth better than past digitalization
predicts future growth. The association is robustly there; the story told about
it is not supported.

That is a meaningfully better outcome than the previous false alarms, and it
should be reported as such — but the report's current framing ("digitalization
is associated with faster industrial output growth," offered as "striking and
independently worth-flagging") reads as directional in a way the evidence does
not license.

---

## Confirmed issues

### 1. Item 2: the leave-one-out was run on the wrong regression — SHOULD-FIX
(claim is correct anyway)

The coordinator's suspicion is confirmed. `phase_d_analysis.py:451-452` defines
`formula_g2` — the **energy-intensity** outcome — and loops leave-one-out over
that. But the report's own argument is that the intensity result is *mechanical*
and the real finding is **G5, value-added growth**. So the headline robustness
claim ("survives leave-one-out across all 28 countries") was never tested on the
regression that actually carries the finding.

I ran it. **It passes — in fact more cleanly than G2:**

| | G2 (intensity, as tested) | **G5 (value-added, untested)** |
|---|---|---|
| Max leave-one-out p (naive z) | 0.056 (drop IE) | **0.038 (drop IE)** |
| Max p under t(G−1) | — | **0.048** |
| Coefficient range | −0.056 to −0.100 | **+0.060 to +0.101** |
| Sign flips | 0 | **0** |

So the claim stands, but it stood by luck rather than by test. Re-run the loop
on G5 and report those numbers instead — they are stronger, and they are the
ones that matter.

### 2. Item 2: the finding fails a placebo/timing test — BLOCKING for the
directional framing

This is the decisive result and the report does not run it. Constructing lag
(t−1) and lead (t+1) digitalization and fitting all three on the **identical
matched sample** (n=195, G=28, same controls):

| Spec | coef | p (naive z) | p (t, G−1) |
|---|---|---|---|
| Contemporaneous | +0.0949 | 0.036 | 0.046 |
| REAL — lagged DII (t−1) | +0.0643 | 0.050 | 0.060 |
| **PLACEBO — lead DII (t+1)** | **+0.0743** | **0.027** | **0.035** |

**Future digitalization "predicts" past industrial value-added growth better
than past digitalization predicts future growth** — larger coefficient, smaller
p-value. This is the textbook signature of a shared trend or reverse causality,
not of digitalization driving output.

It is also exactly the diagnostic this project already applied in Phase B,
where I flagged the same lead > lag pattern in the v2b panel. The tooling
exists in `phase_b_analysis.py`; it simply was not pointed at this finding.

The report's caveat paragraph does mention reverse causality as a generic
possibility (lines 311-315). That is not the same as running the test and
reporting that it failed. The honest statement is: *"a placebo test cannot
distinguish this from reverse causality or a common trend — future
digitalization tracks past growth at least as well as past digitalization
tracks future growth."*

### 3. Item 2: the association is concentrated in catch-up economies —
SHOULD-FIX

Splitting on `accession_2004plus` (the variable Phase C already identified as
driving the v2b sign flip):

| Sample | n | G | coef | p (naive z) | p (t, G−1) |
|---|---|---|---|---|---|
| All 28 | 257 | 28 | +0.121 | 0.001 | 0.003 |
| EU-15 only | 141 | 15 | **+0.050** | **0.055** | 0.075 |
| Accession 2004+ | 116 | 13 | **+0.118** | **0.022** | 0.041 |
| Interaction DII × accession | 257 | 28 | +0.094 | 0.168 | — |

The coefficient is **2.4× larger in accession-wave economies**, and only that
subset clears 5% on its own; EU-15 sits at p=0.055. The interaction is not
significant, but at G=28 that test has the same limited power already
documented in Phase B.

This is precisely the convergence-economics confound the coordinator asked
about, and it needs no causal channel: catch-up economies digitalize faster
(from a low base) *and* grow industrial output faster (convergence), with a
common driver — development level — generating the correlation. Combined with
issue 2, this is the most parsimonious reading of the whole result.

### 4. Item 1: the dismissal of the significant pre-trend is factually wrong —
BLOCKING

The report discounts the significant `event_time = −5` lead (+0.050, p=0.047)
on the grounds that it "sits at the window's edge where the fewest years of
data contribute" (lines 213-214). Both halves of that are incorrect:

- **It is among the most precisely estimated coefficients, not the least.** Its
  SE is **0.0250** — the second-smallest of the eight event-time coefficients
  (others run 0.0299–0.0421; only `+3` is tighter at 0.0224).
- **Support is not thinner there.** Reconstructing the event window, every
  event time from −5 to +2 draws on all 19 countries; only `+3` falls to 17.

So the single significant lead is the *sharpest* estimate in the study, it is
positive, and it says emissions growth was elevated five years before funding
onset. That is a pre-trend signal, and the stated reason for setting it aside
does not hold.

This also resolves the tension the coordinator identified: the group-mean
pre-trend test (early vs. late onset, p=0.383) and the significant lead are
**not** in contradiction — they are tests of very different power. The t-test
compares two group means across 8 vs. 10 countries and could not detect a
moderate difference; the event-time coefficient is a sharper, within-design
test, and it flags. Presenting the weaker, null test as "mildly reassuring"
while dismissing the sharper, positive one on incorrect grounds inverts the
evidential weight. The "1 in 4 leads significant is what chance would produce"
argument is fair on its own — keep that, drop the precision claim.

### 5. Item 1: left-censoring makes both specifications uninformative, and the
count is wrong — BLOCKING for framing

**Arithmetic:** the onset file contains **19** countries; the regression has
G=18 because the UK drops out (its pre-onset mean is `NaN`, `n_pre_years=0` in
`phase_d_item1_pretrend_check.csv`). So left-censoring in the estimation sample
is **12 of 18**, not the "13 of 18" stated in the headline and repeated three
times. 13 of 19 is right for the onset file; 12 of 18 for the regression.

**Substance, which matters more:** with only 6 of 18 countries having any
observable pre-period, F1's identifying variation comes overwhelmingly from
countries whose "before" is unobservable — a before/after design run mostly on
observations with no "before." F2 restricts to the 6 clean countries and has
G=6, which this project has correctly treated as untrustworthy everywhere else.

So **neither specification can support a conclusion**, which is the same
situation as Phase C item 1 — and that one was correctly reported as
*infeasible* rather than as a null. Here, F1 is still called "the headline
number" (line 217) and the item summary leads with "no detectable effect."
Those should be brought into line with the Phase C precedent: report the design
as unable to answer the question, not as having answered it in the negative.

To the report's credit, the exogeneity section (lines 232-253) is genuinely
well-hedged and explicitly declines to oversell the design as clean
identification — I checked for overclaiming and found none there. The problem
is confined to how the *result* is billed, not how the *assumption* is
discussed.

### 6. Item 1: the year-demeaning fix is legitimate but mischaracterized —
SHOULD-FIX

The collinearity diagnosis is correct and the fix is defensible: calendar-year
means are computed on the **full ~30-country** EU-ETS panel and subtracted
before the event-time regression (`phase_d_analysis.py:298-305`). Using an
external, larger panel to estimate year effects is a reasonable way around the
singularity — arguably better than dropping year effects.

But it is **not** "equivalent to a two-step Frisch-Waugh-Lovell partialling-out"
(lines 162-164). FWL partials out effects estimated *within* the estimation
sample; this estimates them from a different, larger sample that includes 11
countries absent from the event study. Two consequences worth a sentence: the
year adjustment is not orthogonal to the event-study residuals by construction
the way FWL guarantees, and the year means are generated regressors whose
estimation uncertainty is not propagated into the standard errors (second-order
here, with ~30 countries per year, but not zero). Describe it as what it is —
an external year adjustment — rather than as FWL.

### 7. Item 1: the onset definition has a look-ahead, correctly non-circular —
NICE-TO-HAVE

Defining onset as "first year cumulative funding reaches 50% of the country's
own eventual 2023 total" does use future information. It is **not** circular
with the outcome — nothing about emissions enters the threshold — so it does
not mechanically bias the DiD, and the two alternatives were checked and
rejected for good reasons (first-nonzero is censored for 13 countries; peak-flow
lands on 2023 for 9 countries through N+3 closeout).

The residual concern is mild: onset timing correlates with programme scale
(corr(onset_year, log final funding) = **+0.355**), so larger-funded countries
are classified as later-onset. If absorption capacity relates to economic
conditions, timing is not purely administrative. Worth one sentence labelling
it a look-ahead-by-construction; not a reason to change the definition.

---

## What's done well

- **Item 2's core numbers are exactly right, and the inference rigor is
  consistent with the rest of the project.** My independent re-derivation from
  the raw Eurostat files (4,999 reps × 5 seeds) reproduces all three:
  G2 −0.0736 (p_wild 0.021, 5-seed range 0.019–0.024), G5 +0.0728 (p_wild
  0.016, range 0.014–0.019), G6 −0.0008 (p 0.969). Both t(G−1) **and** wild
  bootstrap are reported for every headline number and they agree — the
  coordinator's check 2 passes cleanly.
- **The mechanism decomposition is the best analytical move in this phase, and
  it cuts against the Researcher's own initial framing.** Discovering that a
  significant energy-intensity result is entirely a value-added effect with
  *zero* energy effect (p=0.97), and then leading with "this is not an
  efficiency finding," is exactly the discipline this project has built. Many
  analysts would have shipped "digitalization improves energy efficiency."
- **The `nrg_d_indq_n` rejection was checked, not assumed** — verifying that its
  `nace_r2='TOTAL'` returns empty and refusing to hand-sum ~50 sub-sector codes
  avoids precisely the double-counting trap that was caught in Phase A's
  `20-99` rollup. Institutional memory is visibly working.
- **Item 1's `dimension_type` handling shows the same memory** — recognizing
  that Location / Intervention Field / Economic Activity slice the same money
  non-additively, and using only Thematic Objective, avoids a real trap.
- **The RRF absence and the NUTS2/NUTS3 rejection are both documented as
  checked negatives**, with reasons, rather than silently omitted.
- **The collinearity in the 3-way FE specification was diagnosed correctly**
  (it genuinely is singular) and solved rather than worked around by quietly
  dropping year effects.
- **The exogeneity discussion is honest and appropriately hedged** — it names
  left-censoring, N+3 closeout dynamics, and the marginal lead as three
  specific reasons the design is imperfect, and explicitly declines to claim
  clean identification or to strengthen the null into "funding does not work."
- **The report itself flags that item 2 is not the result the item was designed
  to find**, and connects it back to the project's recurring theme (growth
  story vs. emissions story). That connection is the right one.

---

## Recommended next step

**Item 2 (highest priority — this changes the project's headline):**
1. **Run the placebo.** Report lead +0.074 (p=0.027) vs. lag +0.064 (p=0.050)
   on the matched n=195 sample, and state plainly that the test cannot
   distinguish this from reverse causality or a common trend.
2. **Move the leave-one-out to G5** and report the stronger numbers (max
   p_z=0.038, max p_t=0.048, no sign flips, coef +0.060 to +0.101).
3. **Add the accession split** (EU-15 +0.050/p=0.055 vs. accession +0.118/p=0.022)
   and connect it to the Phase C convergence finding.
4. **Reframe the claim** from "digitalization is associated with faster
   industrial output growth" to something like: *"Digitalization and industrial
   value-added growth move together robustly — the association survives every
   fragility check, unlike every prior marginal result in this project. But a
   placebo test cannot establish direction, and the association is concentrated
   in catch-up economies, so the most parsimonious reading is a shared
   development trend rather than digitalization driving growth."*

**Item 1:**
5. Correct "13 of 18" to **12 of 18** (13 of 19 including the UK, which drops).
6. Remove the incorrect precision claim about `event_time = −5`; keep the
   multiple-comparisons argument, and note the group t-test is the weaker of
   the two pre-trend tests.
7. Follow the Phase C precedent: report the design as **unable to answer** the
   question rather than as having found no effect, given 12 of 18 countries
   have no observable pre-period and the clean-subset alternative has G=6.
8. Describe the year adjustment as an external year-mean subtraction, not FWL.

Once item 2 is reframed, Phase D's contribution is: one design that cannot
answer its question (honestly documented), and **one genuinely robust
correlation whose direction the data cannot establish** — which is a real
step up from four rounds of marginal results that dissolved entirely.

---

# Final pass — revisions verified

## Verdict: **GO.** Phase D is ready to fold in as final. The GB→UK fix checks out.

### Item 1 — the GB→UK bug is real, correctly diagnosed, and correctly fixed

I verified this from the raw sources rather than accepting the account, and it
holds up on every point:

1. **The mismatch is real.** `data/raw/eu_ets/eu-ets.csv` carries `GB` and only
   `GB` — no `UK` value exists. The Cohesion funding file's `ms` column carries
   `UK`. So before the fix, no UK row could ever join.
2. **The fix is correctly applied and correctly one-sided.**
   `phase_d_analysis.py:145` now reads
   `replace({"GR": "EL", "GB": "UK"})` on the ETS side, while line 159 maps only
   `{"GR": "EL"}` on the funding side — correct, since the funding data already
   uses `UK`. Remapping both would have been a second bug.
3. **The downstream effects are exactly what the bug predicts.** G went 18 → 19,
   n went 160 → 168, and the UK's pre-onset mean went from `NaN` / 0 pre-years
   to −0.0669 / 8 pre-years in `phase_d_item1_pretrend_check.csv`.
4. **13 of 19 is the correct count.** The onset file lists 19 countries; 13 are
   flagged left-censored (EE, EL, FR, HU, IT, LT, LV, PL, PT, SE, SI, SK, UK)
   and 6 are clean (CY, CZ, ES, HR, MT, RO). 13 + 6 = 19. ✓

**My "12 of 18" is correctly superseded and I want to be explicit about why.**
I caught the *symptom* — the onset file had 19 rows while the regression had
G=18, and the UK's pre-onset mean was `NaN` — but I attributed it to the UK
legitimately dropping out rather than diagnosing the missing `GB→UK` remap as
the root cause. The Researcher found the actual bug. That is a real catch, and
notably it is the same country-code trap this project has hit before (Phase A's
`GR→EL`), caught here by the Researcher unprompted while working on an
unrelated fix.

**Other item 1 corrections confirmed.** `event_time = −5`: SE **0.0237**, rank
**2 of 8** (only `+3` is tighter), full 19-country support at every event time,
p=0.030 — the corrected description matches the data exactly, and the incorrect
"fewest years of data contribute" claim is gone. F1 is now −0.005 (wild-boot
p=0.792), still null. The conclusion is reframed to "the design cannot answer
the question" per the Phase C precedent.

### Item 2 — all four numbers reproduce, and the reframing is honest

| Claim | Reported | My independent run |
|---|---|---|
| G5 value-added growth | +0.0728, p_wild 0.016 | **+0.0728, p_wild 0.016** (5-seed 0.014–0.019) |
| LOO **on G5**, max p | 0.038 (z) / 0.048 (t), drop IE | **0.038 / 0.048, drop IE** |
| LOO coef range / sign flips | +0.060 to +0.101, zero | **+0.060 to +0.101, zero** |
| Placebo: lead vs lag | lead +0.075 (p 0.031) > lag +0.057 (p 0.089) | same ordering, lead +0.074 > lag +0.064 |
| Accession vs EU-15 | +0.118 vs +0.050, 2.4× | **+0.118 vs +0.050** |

**The LOO is now genuinely on G5** — verified structurally, not just by the
label: all 28 coefficients are positive (+0.060 to +0.101), which could not be
true of the energy-intensity regression, whose coefficients are negative. A
`p_t_Gminus1` column was added, so both inference methods are reported as
everywhere else in this project.

Their placebo sample is n=221 to my n=195 (a slightly broader matched base);
the substantive result is identical and, under the wild bootstrap, sharper than
my own version: **the lead is the only timing variant that clears 5%**
(0.031), while both the lagged (0.089) and contemporaneous (0.085) specs do
not. That is the strongest available form of the finding.

**Reframing is honest — no residual causal implication.** I scanned the full
document for directional language. Every instance of "drives/causes" appears
either inside an explicit negation ("this is not a case where digitalization
measurably precedes growth"; "not that digitalization causes industrial
growth"; "not 'digitalization drives growth'") or as the hypothetical being
tested ("*If* digitalization drives industrial growth, lagged digitalization
should predict..."). The section heading itself — "this is where the causal
story breaks" — sets the right expectation, and the summary lands on "robust
correlation, wrong (or at least unestablished) causal direction." Nothing
smuggles the causal reading back in.

One point of care for anyone quoting this later: under the wild bootstrap,
*neither* subset is individually significant (EU-15 0.061, accession 0.053) —
sample-splitting costs power, so the split supports the **magnitude** claim
("2.4× larger in catch-up economies") but not a significance claim about either
subgroup. The report words it as concentration, not significance, which is
correct.

## Bottom line

Phase D closes the project cleanly. Its contribution:

- **Item 1:** a first causal-identification attempt, honestly reported as
  unable to answer its question — 13 of 19 countries have no observable
  pre-period, the clean subset has G=6, and a significant positive pre-trend
  sits at the sharpest-estimated lead.
- **Item 2:** the project's only robust correlation — digitalization and
  industrial value-added growth genuinely move together, surviving every
  fragility check that dissolved four earlier marginal findings — paired with
  an honest demonstration that the data cannot establish its direction, and a
  named, plausible common cause (convergence).

That is a materially better place to end than "everything was noise." The
project's standing conclusion on emissions specifically is unchanged: no
digitalization–emissions relationship survives correct inference at any level
of aggregation attempted — country, sector, region, funding-event timing, or
under raw, intensity, or energy outcomes.
