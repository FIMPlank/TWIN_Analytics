# Review of `analysis/phase_e_broadband_iv.md`

Independent verification of Phase E. The instrument was rebuilt from the raw Eurostat
files upward rather than checked against the Researcher's outputs; the first-stage F was
cross-checked against a second implementation; two Eurostat series were re-pulled live
from the API; and three specifications the report does not run were run.

Reproduction: `python analysis/phase_e_broadband_iv.py` reproduces every number in the
write-up exactly (F = 19.535 / 7.656 / 4.851 full sample; 20.409 / 14.859 / 12.063
EU-15; partial R2 = 0.198; n = 284, G = 28; OLS +0.0660, IV +0.127, AR [0.02, 0.32];
gate 0 of 16). No number in the write-up is wrong.

---

## Verdict

| Question | Verdict |
|---|---|
| **Is "infeasible" the right call?** | **Yes — and it is under-argued, not over-argued.** Three independent checks I ran that the report does not run all push further in the same direction. |
| **Are the numbers right?** | **Yes, with one exception.** Every headline figure reproduces bit-for-bit and the first-stage F is the correct (cluster-robust) statistic. But the EU-15 / S3 and ACC / S3 cluster-robust statistics have more parameters than clusters and should not be quoted as they stand. |
| **Anything to fix before folding in?** | **Yes — four items, none of which change the verdict.** One framing fix (the report argues relevance where its real case is exclusion), one inference fix (k > G), one mis-constructed variable, and two factual corrections. |

**The core judgement is sound.** The design fails, the report says so, and it does not
claim identification anywhere. `§7 "What this does NOT show"` is the most disciplined
section in the project so far. Fold it in after the fixes below.

**The one thing the report gets structurally wrong** is *why* it fails. The verdict
paragraph leads with "F = 4.9 (<10)", i.e. with instrument **weakness**. That is not
the actual case, and it is the weaker case. The instrument is **strong and invalid**,
not weak — see issue 2.

---

## Confirmed issues

### 1. `k > G`: the EU-15 and accession S3 cluster-robust statistics are not trustworthy — SHOULD-FIX

The CR1 "meat" matrix is a sum of `G` outer products, so it has rank at most `G`. In the
S3 specifications the parameter count exceeds the cluster count:

| Spec | n | k (incl. Z) | G | k/G |
|---|---|---|---|---|
| all / S1 | 284 | 15 | 28 | 0.54 |
| all / S3 | 284 | 26 | 28 | **0.93** |
| EU-15 / S1 | 155 | 14 | 15 | 0.93 |
| **EU-15 / S3** | 155 | **25** | **15** | **1.67** |
| **ACC2004+ / S3** | 129 | **25** | **13** | **1.92** |

With `k > G` the cluster-robust variance matrix is singular. `V[j,j]` is still computable
(the code does not crash) but it is severely downward-biased, so **F is overstated and AR
sets are too narrow**. Concretely, the report's two most-quoted EU-15 numbers —
`F = 12.1` and the AR sets `[-0.17, 0.30]` (VA) / `[-0.61, 0.32]` (emissions) — are
optimistic by an unknown amount.

Confirmation via wild-cluster bootstrap on the *same* first-stage coefficient (1999
Rademacher draws, restricted, the report's own `wild_p_restricted`):

| Spec | CR1 F | CR1 p(F) | wild-cluster p |
|---|---|---|---|
| all / S1 | 19.53 | 0.0001 | **0.0095** |
| all / S2 | 7.66 | 0.0101 | **0.0330** |
| all / S3 | 4.85 | 0.0363 | **0.0685** |
| EU-15 / S1 | 20.41 | 0.0005 | **0.0175** |
| EU-15 / S2 | 14.86 | 0.0018 | **0.0165** |
| EU-15 / S3 | 12.06 | 0.0037 | **0.0335** |

The bootstrap p is 3-90x larger than the CR1 p in every cell. The ordering is unchanged,
so **nothing in the verdict flips** — the bias runs toward *more* pessimism. But §6's
"cluster-robust F and AR sets are approximate" understates this: it is not approximation,
it is a rank-deficient estimator in two of the three samples. Say so, and either drop the
EU-15/S3 AR sets or replace the `F(1,G-1)` reference with a wild-bootstrap AR.

Note this is exactly the family of error `phase_d_review.md` caught before (naive
cluster-z p-values). The Researcher avoided it for OLS and the reduced form — the wild
bootstrap is used there — but not for the first stage or AR.

### 2. The verdict argues relevance; the real case is exclusion — SHOULD-FIX (framing)

The gate is `F >= 10 in S3 for both full sample and EU-15`. The report itself flags that
the gate was written after seeing the S1 table. Because of that, the honest question the
coordinator asked is the right one: **does infeasibility survive an ex-ante-defensible
gate?** Under the conventional pre-registered gate — `F >= 10` in the *preferred*
specification, which for Phase-D comparability is S1 — `Z_NGAxFTTP` passes comfortably
(19.5 full / 20.4 EU-15), and the "headline" would have been IV = +0.127, AR
[0.02, 0.32], excluding zero.

So **"infeasible" does not follow from the gate.** It follows from two other things the
report actually establishes but subordinates:

1. The first-stage strength is demonstrably a development proxy. I verified this is not a
   mechanical over-control artefact (see §"Not too pessimistic" below): the first-stage
   *coefficient* halves (0.399 -> 0.200) and partial R2 falls 0.198 -> 0.049, while only
   an extra 15pp of the instrument's variance is absorbed. That is a coefficient change,
   not a precision loss.
2. Once the development channel is controlled, the AR sets are uninformative — and AR is
   valid **regardless of instrument strength**, so this conclusion does not depend on the
   F gate at all.

Recommend restating the verdict as: *the instrument is strong but not excludable; the
weak-instrument-robust confidence sets in the only conditionally defensible specification
are too wide to be informative.* That case is immune to the forking-paths objection the
report raises against itself. The current framing invites a reader to reply "your gate was
too strict" — and they would have a point.

Related: with F = 19.5 and G = 28 the IV Wald t-test is not reliable (Stock-Yogo 10%
size-distortion cutoff for a just-identified model is 16.38, and the tF adjustment of
Lee et al. would push the 5% critical value well above 1.96). The report correctly reports
AR sets alongside, but it should mark `IV_p_t` as not to be read rather than printing it
next to the AR set. The report's claim that KP rk-F = effective F = this F in the
just-identified case is **correct**.

### 3. `b_NGAnf` is mis-constructed, and the inference drawn from it is unsafe — MEDIUM

`analysis/phase_e_broadband_iv.py`:

```python
d["b_NGAnf"] = d.country_code.map(base13["NGA_TOTAL"] - base13["FTTP_TOTAL"].fillna(0)).clip(lower=0)
```

Two problems:

- **The disjointness assumption fails where it matters most.** Eurostat 2013, LT:
  `NGA = 48.7`, `FTTP = 48.7`, `DOCSIS3_0 = 42.8`. NGA is a union, so subtracting FTTP
  yields `b_NGAnf(LT) = 0` for a country with 42.8% cable coverage. The same
  fibre-and-cable overlap affects the other fibre-rich baselines. `b_NGAnf` is therefore
  attenuated by construction, most severely in exactly the countries the report's
  interpretation turns on.
- **`.fillna(0)` fabricates a value.** CY has no 2013 FTTP observation, so
  `b_NGAnf(CY) = b_NGA(CY) = 77.0` — the largest value in the 28-country cross-section —
  is imputed, not measured.

The report uses `NGAnf`'s F = 3.0 to conclude that NGA's strength "comes substantially
from baseline FTTP (fibre-rich Baltic/Romanian starts)". That conclusion is plausible and
may well be right, but **this variable cannot support it**: a weak F on a badly attenuated
regressor is what attenuation predicts. Either soften the claim to a conjecture, or redo
it properly — Eurostat `isoc_cbt` carries `FTTP_DOCSIS3_0` (the overlap) and `CBL_MM`,
which permit an exact rather than an assumed decomposition. Impact on the verdict: none
(`NGAnf` is a rejected candidate either way), but the interpretive sentence in §3 should
not stand as written.

### 4. The "contiguity guard" claim is false — LOW (factual)

§1 and §6 both say `d_log_va` uses a contiguity-guarded difference "so it differs slightly
from Phase D's un-guarded diff", and §6 lists this among the reasons OLS is +0.066 rather
than +0.073. I checked: in `industry_value_added_absolute.csv` there are **zero** rows
where the guarded and un-guarded differences disagree — the VA series has no year gaps,
so `contiguous_diff` is a no-op on this file.

The entire +0.066 vs +0.073 gap is the sample. That part reconciles perfectly and is
**fully explained and harmless** (see "What's done well"). Just delete the guard as an
explanation.

### 5. Two data-description inaccuracies — LOW

- §1 says DOCSIS 3.0 is missing for "**EL, IT**". In the 2013 baseline year — the only one
  that enters the instrument — it is missing for **EL, IS and IT**. (Over the full panel,
  only IT is absent entirely.) `b_DOCSISz` zero-fills EL and IT but not IS; harmless, since
  IS drops from the estimation sample for want of DII, but the sentence is wrong.
- The DOCSIS comparison in §3 (`4.9` NaN vs `18.7` zero-filled) is presented as the effect
  of the zero-fill. It is partly a **sample change**: `Z_DOCSISxFTTP` runs on n = 265,
  G = 26; `Z_DOCSISzxFTTP` on n = 284, G = 28. State both.
- Minor: the "leave-one-out EU-mean" shock is a mean over all 31 countries in `isoc_cbt`,
  including CH, IS, NO and UK. Harmless — it is a near-common shifter and year FE absorb
  its level — but call it what it is.

### 6. Gap, not an error: the textbook shift-share specification is never run — SHOULD-ADD

The report tests S1/S2/S3, all of which are pooled cross-sections with year FE and **no
country fixed effects**. The canonical shift-share first stage — country FE + year FE, so
that identification comes from *differential trends* in DII across baseline levels rather
than from cross-country levels — is absent. This is the most direct possible answer to the
coordinator's masked-signal worry, and it is cheap. I ran it on the report's own sample and
estimator:

| Spec | Outcome | F | partial R2 | RF (t) | IV | AR 95% |
|---|---|---|---|---|---|---|
| Country FE + year FE + Phase-D controls | `d_log_va` | **4.34** | 0.058 | +0.114 (1.73) | +0.341 | **[-0.06, 3.0] unbounded** |
| Country FE + year FE + Phase-D controls | `d_log_emissions` | **4.34** | 0.058 | +0.227 (0.87) | +0.681 | **[-3.0, 3.0] unbounded** |
| + GDPpc2013 x year FE | `d_log_va` | 1.02 | 0.017 | +0.111 (1.36) | +0.610 | unbounded |
| + GDPpc2013 x year FE | `d_log_emissions` | 1.02 | 0.017 | +0.233 (0.69) | +1.277 | unbounded |

Country FE absorb 95.6% of the instrument's variance (vs 50.1% under S1 and 64.9% under
S3), the first stage collapses to F = 4.34, and both AR sets are unbounded. **Adding this
removes the last escape route for the design** and does so without relying on the
`GDPpc2013 x year FE` control that a critic could call over-fitting. Add it to §3 and §5.3.

### 7. Cohesion funding is speculated about, not checked, with the data in the repo — LOW

§4.2 says high baseline fibre in LT/LV/RO/BG "plausibly reflects cheap greenfield/municipal
builds (possibly publicly co-financed; **not verified here**)". The hedge is honest, but
`data/raw/cohesion/digital_investment_2014_2020.csv` is already in this repository and was
used in Phase D item 1. A quick unnormalised cut (n = 19 countries with declared ICT
expenditure) gives corr(baseline FTTP, log declared ICT spend) = +0.32 and
corr(log GDPpc 2013, log ICT spend) = -0.59 — directionally consistent with the story, but
far too crude to cite (totals rather than per-capita, and a selected sample). Either do it
properly (per-capita, EU-15 vs accession split) or say explicitly that the repo has the
data and it was left for later. Do not leave it as an unexamined conjecture when the file
is one directory away.

---

## Not too pessimistic: the masked-signal failure mode does not apply

The coordinator's specific worry — that a valid instrument is being killed by an overly
demanding `GDPpc2013 x year FE` control with only 28 clusters — does not hold up. Three
independent reasons:

1. **S3 removes little additional variance.** R2 of Z on the control set is 0.501 (S1),
   0.612 (S2), 0.649 (S3). Going S1 -> S3 costs ~15pp of Z's variance. If only precision
   were lost, F would fall from 19.5 to roughly 14, not to 4.9.
2. **The coefficient moves, not just the standard error.** First-stage coefficient
   0.399 -> 0.251 -> 0.200; partial R2 0.198 -> 0.079 -> 0.049. The relationship itself is
   the thing that is concentrated in the income-aligned component of baseline coverage.
3. **A completely different, less demanding control also kills it.** Country FE (issue 6)
   give F = 4.34 without touching GDP at all.

Conversely, the diagnostics are **not** over-read. I verified that the AR test at
`beta = 0` is numerically identical to the reduced-form cluster Wald test (F = 5.57,
p = 0.0258, equal to RF t2 = 5.57 to machine precision), so the S1 AR set genuinely does
exclude zero and is *valid* weak-instrument-robust inference. The report does not pretend
otherwise: it attributes that rejection to the development confound rather than to
strength, which is the correct read, and labels the whole block DIAGNOSTIC-ONLY.

---

## What's done well

- **First stage first, with a gate, before any second stage, and the gate's own weakness
  disclosed.** The report states in plain text that the gate was written after seeing the
  S1 table and that selecting on F flatters the instrument. That is unusual discipline and
  it is what let me evaluate issue 2 rather than have to discover it.
- **The right F statistic.** `first_stage()` computes a genuine cluster-robust CR1 Wald
  statistic, not the homoskedastic F. Cross-check against statsmodels `cov_type="cluster"`:
  19.53 / 7.66 / 4.85 — exact agreement. The homoskedastic F for the same regression is
  **66.5**, so using it would have inflated the headline more than threefold. The
  just-identified KP rk-F = effective F equivalence is stated correctly.
- **The n = 284 vs Phase D's n = 257 difference is fully explained and harmless.** I
  verified independently: the 257 rows are a **strict subset** of the 284 (0 rows outside,
  27 extra), the difference is exactly Phase D's additional requirement of non-missing
  industrial energy data, and re-running Phase D's G5 formula on the 257 rows reproduces
  **+0.0728** to four decimals. The sample relaxation is a deliberate, documented, correct
  choice.
- **The leave-one-out instrument is constructed correctly.** Verified by hand: for FTTP in
  2015, DE's LOO mean is 30.5552 against a manual mean over the other 29 countries of
  30.5552; LT 2015 = 29.0724 vs 29.0724; DE 2020 = 51.060; LT 2020 = 49.2867. Own-country
  exclusion is per-year and the denominator correctly adjusts for own-country missingness.
- **Country codes are clean.** `EL` and `UK` are used consistently on both sides of every
  merge; no `GR` or `GB` appears anywhere in the Phase E code or the broadband files. The
  four dropped countries (IS, LI, UK, XI) drop for a substantive reason — no DII — not
  through a silent code mismatch. This is the bug class that bit Phase D and it is absent.
- **The data fetch is correct — verified against the live Eurostat API.** `isoc_cbt`
  DE/NGA/TOTAL 2013 = 74.8 (file: 74.8); LT/FTTP/TOTAL 2020 = 67.0 (file: 67.0); `isoc_cbs`
  NL/MBPS_GT100 series matches cell for cell. Unit is `PC_HH` ("Percentage of households")
  in both; `isoc_cbs` has only `terrtypo = TOTAL` (so the speed pivot, which omits
  `terrtypo`, cannot silently average total with rural); zero duplicate
  (geo, time, series, terrtypo) cells in either file; EU aggregates are correctly excluded
  at download.
- **Sample discipline across estimators.** `rows_for()` requires both outcomes, DII, all
  controls, `gdp13` **and** the instrument to be non-missing before anything runs, so OLS,
  first stage, reduced form, IV and AR are all on identical rows, and S1/S2/S3 are
  comparable to each other. Phase B/C reviews caught non-matched-sample comparisons; this
  is the fix, applied pre-emptively.
- **`isoc_r_broad_h` was fetched, examined and then correctly refused.** Recognising that
  household broadband *take-up* is a demand-side outcome that co-moves with DII by
  construction — and documenting the rejection rather than quietly using the only regional
  series available — is the single best judgement call in the phase.
- **§4 exclusion discussion is honest and §7 is explicit.** Nothing anywhere claims causal
  identification. The household-vs-enterprise coverage mismatch, the sectoral-composition
  channel, the network-construction channel and the "shift-share here is really a level
  comparison" problem are all raised by the author against the author's own design. The
  pre-period falsification is reported *and* correctly discounted for power (n = 28).

---

## Recommended next step

**Fold Phase E in as a documented negative result, after the following edits.** Do not
re-run the design; there is nothing left to extract from country-level Eurostat coverage.

1. **Rewrite the verdict paragraph and §5.2 around exclusion, not relevance** (issue 2).
   Lead with: the instrument is strong (F = 19.5) but is substantially a development proxy,
   and the weak-instrument-robust AR sets in the only conditionally defensible
   specification are uninformative. Note explicitly that under a conventional ex-ante gate
   (F >= 10 in the preferred spec) this instrument would have *passed*, and that the
   verdict does not rest on the post-hoc gate. This makes the conclusion stronger, not
   weaker.
2. **Add the country-FE first stage** (issue 6) to §3 and §5.3: F = 4.34, both AR sets
   unbounded. One extra formula string in `SPECS`; it closes the masked-signal objection.
3. **Fix the inference caveat for `k > G`** (issue 1). Add the wild-cluster-bootstrap
   first-stage p-values, mark EU-15/S3 and ACC/S3 as rank-deficient, and either drop the
   EU-15/S3 AR sets or bootstrap them. Stop printing `IV_p_t` next to AR sets without a
   health warning.
4. **Soften or redo the `b_NGAnf` claim** (issue 3), and note the `.fillna(0)` imputation
   for CY.
5. **Delete the contiguity-guard explanation** (issue 4) and fix the DOCSIS/sample
   descriptions (issue 5). One-line edits.
6. Decide on the Cohesion check (issue 7): do it per-capita or say plainly it was not done.

**For the project as a whole**, Phase E settles the question it was asked. The +0.073
DII / industrial-VA correlation now has three independent strikes against a causal reading
— the placebo (Phase D), the accession-cohort concentration (Phase D), and now a failed
instrument whose own first-stage strength turns out to be the same development confound in
a new costume. The convergence interpretation is no longer one hypothesis among several;
it is the one the evidence keeps pointing at. The write-up should say that, and the project
should stop looking for a causal effect in country-level EU panel data. §7's closing
paragraph already names what a real design would need (sub-national rollout timing,
firm-level adoption) — promote that from a footnote to the project's conclusion.
