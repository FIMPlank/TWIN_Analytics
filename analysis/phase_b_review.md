# Review of `analysis/phase_b_analysis.md`

Independent verification of the Phase-B regression work on the panels
validated in `analysis/panel_v2/panel_qc_review.md`.

Approach: re-ran every headline specification from the working files rather
than trusting the summary, and — per the brief — actively hunted for the
*opposite* failure mode: a real effect being masked by a construction error.
I could not find one. The null is real. But three of the report's supporting
claims do not survive checking, and one of them is load-bearing for how a
reader interprets the placebo test.

---

## Verdict

**Sound null — present after four small fixes, none of which change the
conclusion.**

The headline claim is verified and sturdy. Every v2a and v2b coefficient
reproduces exactly; the minimum naive-z p-value across all 18 reported models
is **0.224** (the report's "never below 0.22" is correct); no wild-bootstrap
p-value anywhere is below 0.05. I stress-tested for a masked effect four
different ways — dropping Norway, winsorizing the energy control, dropping the
energy control entirely, and re-running the placebo on a common sample — and
the DII coefficient never moved outside +0.066 to +0.085 with p in the
0.24–0.32 range. There is no hidden signal here.

What needs fixing is **interpretation of three checks**, not the null itself:
the placebo comparison is run on two different samples, the v2b sign flip is
attributed to noise when it has a single identifiable cause, and the EIBIS
"agreement" is presented as independent corroboration when the two measures
correlate at r=0.71.

---

## Confirmed issues

### 1. The placebo comparison is not apples-to-apples, and the "well-behaved
placebo" claim depends on that — SHOULD-FIX (blocking for this claim only)

The lead/lag *construction* is correct — I verified this first, since an
off-by-one would make the whole check meaningless. `add_lag_lead`
(`phase_b_analysis.py:171-179`) uses explicit year-offset merges rather than
positional `.shift()`, which is the right, gap-safe choice. Spot-checking
Austria: at 2016, `dii_lag` = 0.2463 = the 2015 value; `dii_lead` = 0.2674 =
the 2017 value. Lead genuinely is t+1 predicting the emissions change at t.
No off-by-one.

The problem is the **samples**. A3 (`dii_lag`) and A4 (`dii_lead`) both report
n=251 — which reads as aligned, and is a coincidence. The lag spec drops each
country's first year; the lead spec drops each country's last year. Only
**221 of 251 rows overlap**; 30 rows are unique to each side.

Re-running both on the common 221-row sample:

| Spec | As reported (n=251, different rows) | Common sample (n=221) |
|---|---|---|
| A3 REAL (lagged DII) | +0.072 | +0.066 |
| A4 PLACEBO (lead DII) | **−0.013** | **+0.049** |

On a like-for-like sample the placebo coefficient is **74% the size of the
"real" one and the same sign** — not "close to zero". So the report's claim
(lines 143-147) that "future DII genuinely does not 'predict' the past better
than lagged DII predicts the future" is an artifact of comparing two different
samples. On a common sample, lead and lag are close to interchangeable, which
is what you would expect if the (non-significant) association reflects a
slow-moving country characteristic rather than anything with a time direction.

This does not change the conclusion — neither is remotely significant — but it
removes the report's basis for calling the placebo "well-behaved". Fix:
restrict both specs to rows where lag *and* lead exist, and rewrite the claim
as "on a common sample, lead and lagged DII are nearly interchangeable,
consistent with a slow-moving country characteristic rather than a timed
effect."

### 2. The v2b sign flip is not noise — it is entirely one control —
SHOULD-FIX

The report frames the v2a/v2b divergence as instability "easily explained by
noise" (line 207) and "aggregation-related noise" (line 229). Decomposing it
by adding each control singly to the same B2 estimation sample:

| Added to bare + year FE + sector FE | full cut | excl-combustion |
|---|---|---|
| (bare) | +0.085 | +0.084 |
| + GDP growth | +0.096 | +0.089 |
| + energy-shock exposure | +0.079 | +0.079 |
| **+ accession_2004plus** | **−0.080** | **−0.111** |

**`accession_2004plus` alone flips the sign; neither other control does.**
Two further facts the report misses:

- The flip is nearly identical across both cuts (−0.080 vs −0.111), so it does
  **not** trace back to the combustion/D35 mapping problem flagged in Phase A.
  That hypothesis is cleanly refuted.
- The same control does **not** flip v2a (+0.069 → +0.076 on the A2 sample).

So the divergence has a single, identifiable, substantively interesting cause:
conditioning on the accession split moves the sector-panel slope negative but
leaves the country-panel slope positive. That is the convergence/catch-up story
the A5/B5 interaction was built to test, surfacing in the *main effect* instead
of the interaction term. Calling it noise is underselling a real pattern.

Still not significant, so it changes no conclusion — but the report should say
what actually causes it rather than attributing it to noise.

### 3. The EIBIS cross-check overstates independence — SHOULD-FIX

A6 reproduces (DII +0.175 p=0.288; EIBIS +0.182 p=0.224). But on the same
79-row overlap, **corr(DII, EIBIS) = 0.709**.

The report calls these "two independently constructed digitalization measures"
that "agree on both sign and rough magnitude", offering "useful triangulation"
showing the earlier finding "was not an idiosyncrasy of that specific survey"
(lines 167-176). With r=0.71 the two measures are largely tracking the same
cross-country variation, so obtaining similar coefficients is close to
mechanical. Independent *construction* is not independent *information*.

The honest version is narrower: *"DII and EIBIS correlate at r=0.71 on the
overlap, so they are not independent measurements; that they yield similar
non-significant coefficients is a consistency check on measurement, not
corroborating evidence."* As written, a non-technical reader will take
"triangulation" to mean two independent sources confirming each other.

### 4. The interaction's power caveat is present but under-emphasized —
SHOULD-FIX

The caveat appears once (lines 156-158) and is accurate. But it does not
reappear in Part B, in "What changed relative to the country-level analysis",
or in "What this analysis does NOT show" — where the reader actually looks for
what can and cannot be concluded. Meanwhile lines 246-250 say the convergence
interaction "rules out 'just proxying for catch-up growth' as an explanation",
which is materially stronger than the evidence supports.

Group balance is reasonable (13 accession-wave vs 15 EU-15 countries), but
with G=28 clusters, a cross-level interaction, and a wild-bootstrap p of 0.792,
this test could not have detected a moderate real difference. Per the brief's
framing, which I agree with: **a non-significant interaction at G≈28 is weak
evidence against the convergence hypothesis, not evidence for ruling it out.**
Line 155's "not supported" is right; line 248's "rules out" is not. Make the
caveat a sentence in the conclusions, and change "rules out" to "fails to
detect, with limited power to do so."

This matters more given issue 2: the accession variable *does* move the v2b
point estimate substantially as a main effect. Concluding that catch-up
dynamics are ruled out, while the catch-up control is the one thing that flips
the sector panel's sign, is internally inconsistent.

### 5. Minor

- **The Phase-A Norway warning was not acted on.** `energy_shock_exposure`
  (`phase_b_analysis.py:196-202`) uses raw 2021 energy-import dependency, where
  Norway is **−622.2** and the next most extreme country is **+1.4**. Phase A
  explicitly flagged this variable as needing winsorization. Verified harmless
  in practice — dropping Norway gives +0.077 (p=0.284), winsorizing at 1/99
  gives +0.085 (p=0.238), dropping the control gives +0.083 (p=0.250), vs
  +0.081 (p=0.263) as run — but it should be winsorized on principle, and the
  robustness row is worth one line in the report.
- **Norway is silently coded as EU-15.** `eu_accession_cohort` is NaN for NO,
  IS, LI, XI; `.isin([...])` maps NaN to False, so `accession_2004plus` = 0 —
  the EU-15 baseline. Affects 11 rows in the controlled v2a sample. Given
  issue 2 makes this variable consequential, the non-EU countries should be
  explicitly excluded or given their own indicator rather than absorbed into
  the reference category.
- **`N_BOOT` dropped from 4,999 (extension) to 1,999.** Defensible when every
  p-value exceeds 0.25, but worth a one-line justification for consistency with
  the earlier work.

---

## What's done well

- **Rigour was designed in, not retrofitted.** Three p-values per model with
  the wild bootstrap declared authoritative *before* seeing results, the
  placebo run as a first-class model, controls specified as pre-determined
  rather than contemporaneous. Every methodological lesson from rounds 1-3 was
  internalized rather than re-learned. The "not found by a Reviewer this time"
  section header is earned.
- **All three Phase-A constraints genuinely respected**, verified in code: no
  `.diff()` on any DII variable anywhere; `C(ets_activity_code)` present in
  every v2b formula; both cuts reported side by side in every table with
  neither presented alone; the v2a scope mismatch restated at the head of
  Part A.
- **The lag/lead builder uses year-offset merges rather than positional
  `.shift()`** (`phase_b_analysis.py:171-179`), with a comment explaining
  exactly why. That is the correct choice for an unbalanced panel and is the
  kind of thing that silently corrupts this sort of analysis.
- **The energy-shock control is correctly constructed** as a pre-crisis (2021)
  baseline × crisis-window dummy — a direct, correct application of the
  bad-control lesson from the extension round.
- **The null is not oversold as proof of zero.** Limitation 5 and the entire
  "What this analysis does NOT show" section are careful and correct,
  especially the distinction between "does not replicate as significant" and
  "was wrong" (line 300-303). That is a genuinely subtle point stated well.
- **The v2a/v2b divergence was surfaced rather than buried**, even though
  reporting it complicates a clean story. The diagnosis needs fixing (issue 2),
  but the instinct to flag it was right.
- **Every number reproduces exactly.** A1 +0.069/0.314, A2 +0.081/0.263,
  A5 +0.074/0.280 and +0.043/0.756, A6a +0.175/0.288, A6b +0.182/0.224,
  B1-B5 on both cuts. Minimum naive-z p = 0.224 across all models, confirming
  the "never below 0.22" claim.

---

## Recommended next step

Four edits, none requiring new analysis beyond what is in this review:

1. **Re-run A3/A4 (and B3/B4) on a common lag-and-lead sample** and restate
   the placebo finding: on like-for-like rows the placebo coefficient is +0.049
   vs +0.066 for the real spec — nearly interchangeable, not "close to zero."
2. **Replace the "noise" framing of the v2b sign flip** with the decomposition
   in issue 2: the flip is entirely `accession_2004plus`, identical across both
   cuts (so not a combustion/D35 artifact), and absent in v2a.
3. **Soften the EIBIS cross-check** to a measurement-consistency claim, and
   report r=0.709.
4. **Change "rules out" to "fails to detect, with limited power"** for the
   convergence interaction, and carry the G=28 power caveat into the
   conclusions section.

After these, this is presentable as the final word on Phase B. The substantive
finding — no detectable, stable relationship between digitalization intensity
and verified emissions change, on an 11-year panel, two aggregation levels, two
crosswalk cuts, and three inference methods — is well-established and survived
everything I threw at it.

---

# Final pass — all four fixes verified

## Verdict: **GO.** Present this as the final Phase-B result.

All four fixes are correctly implemented, and the two self-caught
transcription errors check out. I re-ran every affected specification
independently.

**Fix 1 — matched-sample placebo: correct, and the v2b result is reported
honestly.** Reproduces exactly on all three panels:

| Panel | REAL (lagged) | PLACEBO (lead) | n |
|---|---|---|---|
| v2a | +0.066 | +0.049 | 221 |
| v2b full | −0.027 | **−0.102** | 474 |
| v2b excl-combustion | −0.009 | **−0.125** | 433 |

The v2b framing is accurate and **not** glossed over. The report states
plainly that v2b's lag and lead are "**not** close to interchangeable", gives
both pairs of numbers explicitly, and — the part that matters — says it is
"reported here precisely rather than folded into a single 'lag and lead are
interchangeable' claim that v2a's numbers support but v2b's do not." That is
the right call: the v2b placebo coefficient is 4× (full) and 14×
(excl-combustion) the magnitude of the real one, which is a *failed* placebo,
and the report neither buries it nor overreads it. Given nothing is
significant, declining to draw a conclusion from it is correct.

**Fix 2 — decomposition method is sound.** Verified in code
(`phase_b_analysis.py:254-259`, `387-391`): each control is added singly to
the bare + FE specification, all fit on `a2_df` / `b2_df` — the *same* fixed
estimation sample as the full controlled model. No sample drift between rows,
which is exactly the construction needed for the comparison to isolate the
control rather than confound it with attrition. Every coefficient in the
decomposition table matches my independent run. The two conclusions drawn from
it (identical magnitude across cuts ⇒ not a combustion/D35 artifact; no flip in
v2a) are both correct.

**Fix 3 — EIBIS reframing is adequate, and better than what I asked for.**
r=0.709 on n=79 reproduces. The report now states the two measures are "**not
independent measurements**", that their coefficients landing together is
"close to a mechanical consequence of the high correlation", and labels it a
measurement-consistency check rather than corroboration. It also preserves the
one narrow claim the data *does* support — that the original EIBIS result was
not an artifact of that survey's particular construction — and scopes it
explicitly rather than letting it drift back into "triangulation."

**Fix 4 — no residual overclaiming.** I scanned the full document for
`rules out / ruled out / confirms / proves / establishes / corroborat* /
triangulat*`. Every surviving instance is either a negation ("not ruled out",
"does not rule out", "**not** 'rules out the convergence story'") or one of two
correctly-scoped narrow claims: the combustion/D35 explanation for the v2b
divergence (genuinely ruled out by the identical cross-cut magnitudes) and the
EIBIS survey-idiosyncrasy point above. The convergence caveat now appears in
Part A, in the decomposition discussion, in the limitations, and in "What this
analysis does NOT show" — and is correctly linked to Fix 2, noting that the
same variable that fails as an interaction is what moves v2b's main effect, so
the hypothesis is "live, not ruled out." That internal inconsistency I flagged
is resolved.

**Transcription errors.** Both confirmed applied: `0.792 → 0.791` (old value
gone from the document). The `0.314 → 0.308` fix is also applied — `0.314`
still appears once, but as A1's `p_naive_z`, a different column, so there is no
conflict. I ran a full markdown-vs-CSV reconciliation across all 30 models: every
reported coefficient and wild-bootstrap p-value matches its source row once the
document's Unicode minus sign (U+2212) is normalised. The only six values in
the CSVs with no markdown counterpart are the decomposition rows'
p-values, which the report deliberately omits because that table is a
directional argument about sign, not significance — all six are in the
0.248–0.652 range, so nothing significant is being hidden. Worth one clause
noting they are all non-significant, but that is polish, not a fix.

## Remaining (optional, non-blocking)

- Add a half-sentence to the decomposition table noting all its p-values are
  non-significant (0.25–0.65), so no reader mistakes the sign discussion for a
  significance claim.
- The v2b failed placebo could carry one forward-looking sentence: any future
  significant v2b lagged result should be treated with extra suspicion given
  that lead DII currently "predicts" better than lag. Useful for whoever picks
  this up next.

Neither affects what the analysis concludes.

## Bottom line

The substantive finding is well-established and survived four rounds of
adversarial review: **no detectable, stable relationship between digitalization
intensity and verified emissions change** — across an 11-year country panel and
a sector-country-year panel, two crosswalk cuts, five specification families,
and three inference methods, with the wild cluster bootstrap authoritative
throughout. Minimum naive-z p-value across all 30 models is 0.224; nothing
approaches significance under any method. The report is honest about what that
does and does not mean, and the three checks that could have been oversold
(placebo, sign flip, EIBIS agreement) are now each stated at exactly the
strength the numbers support.
