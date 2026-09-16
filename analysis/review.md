# Review of `analysis/first_pass_analysis.md`

Reviewer pass over the Researcher's first-pass econometrics. Code was re-run
end-to-end (`python analysis/analysis.py`, Python 3.12.10 / statsmodels 0.15.0
/ pandas 3.0.5) and all reported numbers reproduce **exactly** — correlations,
all five model coefficients, SEs, p-values, R², VIFs, Shapiro-Wilk W=0.911,
3/81 Cook's D flags. Reproducibility is not an issue here.

Additional checks were run independently (block permutation test, alternative
clustering, leave-one-out, lag specification, variance decomposition). Those
are what this review is mostly about.

---

## Verdict

**Needs a focused rework of the framing and the inference — not of the data
pipeline.**

The data build is clean and the *bottom-line conclusion is correct* (no robust
association is detectable). But the document cannot be shown to a
non-technical stakeholder as-is, for two reasons:

1. The stated hypothesis contradicts itself on direction, so a lay reader will
   read the one "significant" result as the opposite of what it actually says.
2. The single p<0.05 result in the whole report is not significant once the
   report's *own* preferred standard errors are applied. The prose attributes
   its disappearance to the wrong cause.

Neither is fatal to the project. Both are ~half a day of edits. The underlying
merge, the coverage discovery, and the honesty about the null are genuinely
good work that should be kept.

---

## Confirmed issues

### 1. The hypothesis statement is internally contradictory — BLOCKING

`first_pass_analysis.md` lines 8–13:

> "...is **positively associated** with the year-over-year change in its EU ETS
> verified emissions — i.e., more-digitalized country-years show **smaller
> emissions increases / larger emissions decreases**..."

These two halves say opposite things. The outcome is `d_log_emissions`
(Δ log emissions). A **positive** coefficient means more-digitalized
country-years have **higher** emissions growth — i.e. they cut emissions
*less*. The "i.e." gloss describes a **negative** coefficient.

This is not a typographical nitpick, because it inverts the reading of every
number in the results table:

- Model 1 (+0.211, p=0.047) — the report's only nominally significant result —
  is evidence pointing **against** the twin-transformation story, not for it.
  The report never states this in plain language anywhere.
- Model 4 (−0.348) is the only coefficient with the **theory-consistent** sign.
  The report (lines 166–170) dismisses it as "idiosyncratic within-country
  noise" without noting that the sign it flipped *to* is the hypothesized one.

A business/policy reader skimming "positive and significant" will conclude the
opposite of what the data says. Fix the H1 wording, and add one explicit
sentence in Results: *"Read literally, the pooled result says more-digitalized
countries reduced emissions slightly less, not more — but see below, it does
not survive correct standard errors."*

### 2. Model 1's p=0.047 is an artifact of treating 81 observations as
independent — BLOCKING

`analysis.py:194` fits Model 1 with `cov_type="HC1"`. But the panel is 27
countries × 3 years; the three observations per country are plainly not
independent, and the report itself argues this by clustering Model 3 on
`country_code` (`analysis.py:211-212`). Applying the same clustering to Model 1:

| Model 1 SE treatment | coef | p |
|---|---|---|
| HC1 (as reported) | +0.211 | **0.047** |
| Clustered by country (report's own standard) | +0.211 | **0.114** |

So the headline significance is gone **before any fixed effects are added.**

This makes the Results narrative (lines 127–135) factually wrong about
mechanism: *"it loses significance as soon as year fixed effects are added
(Model 3, p=0.216)"*. It loses significance as soon as the standard errors
acknowledge the panel structure. Year FE are a second-order contributor. The
same SE inconsistency applies to Model 2 (HC1 on n=27 — defensible there, it
is a single cross-section) and, less defensibly, to Model 4 (below).

Corroborating independent checks, all consistent:

- **Block permutation test** (5,000 reps, whole country series permuted across
  countries so within-country dependence is preserved): **p = 0.095**.
- **Cross-sectional collapse** (27 countries, mean digital vs. cumulative
  2022→2025 Δlog emissions): r = +0.340, **p = 0.083**.
- **Lagged spec** (digital at t−1, clustered, n=54): +0.246, **p = 0.082**.

Every honest route lands at p ≈ 0.08–0.21. Nothing in this dataset clears 5%.
That is a cleaner and more defensible story than the current one — but the
report has to tell it.

### 3. The significance is driven by essentially one country — SHOULD-FIX

Lines 148–154 flag Bulgaria 2025 (Cook's D = 0.28) as an order of magnitude
more influential than any other point, then decline to test it: *"Results are
not reported with/without this point removed here."* This is a three-line
check and it should not have been left undone. Result:

| Model 1 sample | coef | p |
|---|---|---|
| Full (n=81) | +0.211 | 0.047 |
| Drop BG-2025 (n=80) | +0.170 | 0.086 |
| Drop Bulgaria entirely (n=78) | +0.110 | 0.210 |

Removing **one observation out of 81** halves the coefficient and kills the
p-value. Combined with issue 2, the Model 1 result is not a finding.

### 4. Model 4 uses HC1 where Model 3 uses clustered SEs — SHOULD-FIX

`analysis.py:223` fits the two-way FE model with `cov_type="HC1"` while
`analysis.py:211` clusters Model 3. Inconsistent, and HC1 understates
uncertainty in a fixed-effects panel. Corrected:

- Model 4 as reported (HC1): −0.348, p = 0.131
- Model 4 clustered by country: −0.348, **p = 0.214**

The reported p=0.131 in the results table (line 124) is too small. It does not
change the conclusion, but it is an error in the table.

### 5. Two-way FE discards ~81% of the usable variance — SHOULD-FIX (design)

The report calls Model 4 "likely underpowered" but does not quantify why.
Decomposition of `digital_multi`:

- Between-country SD: **0.119**
- Mean within-country SD: **0.051**

Country FE absorb the between-country variation, leaving a regressor whose
residual variance is roughly **(0.051/0.119)² ≈ 19%** of the original — and
that residual is mostly EIBIS sampling noise (these are survey shares with a
few hundred firms per country-year; year-to-year wobble of ±2–5pp is within
sampling error). Model 4 is not a demanding test of the hypothesis; it is
mostly a regression of emissions changes on survey noise. **Including it in the
headline results table invites a lay reader to treat the sign flip as a
substantive finding.** It belongs in an appendix or a footnote, not row 4 of
the main table.

To be explicit on the question posed: no, two-way FE is **not** a sensible
specification with T=3, one of which (2023, i.e. the 2022→2023 change) carries
the energy-shock collapse. It should not be presented as "the most demanding
spec" — it is the least informative one here.

### 6. Four correlations tested, one clears 5% — SHOULD-FIX

The correlation table (lines 108–113) reports four tests; `digital_multi` at
p=0.047 is the only one under 0.05. With even a naive Bonferroni correction
(α = 0.0125), nothing survives. Not mentioned anywhere. Given that issue 2
already kills this result, a single sentence suffices — but it should be there.

### 7. Model 5 (E-PRTR) is uninformative and should not be in the main table
— SHOULD-FIX

n=17, **10** clusters, coefficient +1.983 with SE 1.480. The report correctly
calls it "completely uninformative" (line 135), but it still appears as a row
in the headline results table with a coefficient a lay reader will read as a
198% effect. Cluster-robust inference on 10 clusters is not meaningful.
Move it to a footnote or drop it.

### 8. Zero figures produced — SHOULD-FIX (presentability)

`analysis/output/` contains eight CSVs and one TXT and **no figures at all**.
For a business/policy audience, the single most persuasive and most honest
artifact this dataset supports is a 27-point scatter (mean digitalization vs.
cumulative emissions change) with a fitted line and a confidence band that
visibly contains zero, with Bulgaria labelled. That one chart communicates the
entire finding better than the five-model table does.

### 9. Minor / nice-to-have

- **`digital_any` construction** (`analysis.py:95`) uses
  `.fillna(0) + .fillna(0)`, which would silently fabricate a value if exactly
  one component were missing. Verified harmless in practice — 0 of 145 rows
  have exactly one component missing — but it is a latent bug; use
  `.sum(min_count=2)` or an explicit mask.
- **EIBIS contains `EU` and `US` aggregate rows** (verified: 29 "countries" =
  27 EU + EU aggregate + US). These are never filtered in `analysis.py`; they
  drop out only because no matching `country_code` exists in the ETS panel.
  Correct outcome by luck, not by design. Add an explicit filter.
- **Country-code reconciliation is correct.** Verified: ETS ships 32 codes
  including `GR`, `GB`, `XI`, `NO`, `IS`, `LI`; `GR→EL` is mapped at
  `analysis.py:54`; the non-EIBIS codes drop out on the inner merge as
  documented. `NAME_TO_CODE` for E-PRTR handles Greece→EL and both Czechia
  spellings. No merge bug found. The report's claim here holds up.
- **EIBIS coverage claim verified.** `Multiple technologies` at
  `sector=ALL, size=ALL` is 0/29 non-null for waves 2018–2022 and 29/29 for
  2023–2025, exactly as the report states. This was a genuine and useful
  discovery.
- **Shapiro-Wilk** is correctly computed but is near-irrelevant at n=81 with
  robust SEs; it reads as diagnostic box-ticking. The skew it detects is
  better communicated as "a few countries had very large one-year swings."
- **VIF** is correctly computed on the Model 2 estimation sample (n=27) and
  correctly interpreted. No issue.
- **Cook's D alignment** (`analysis.py:252-256`) relies on `panel_m3` being
  row-identical to the model's estimation sample. It is here (both n=81, no
  NaNs), so the numbers are right — but the re-`dropna` + `reset_index` pattern
  is fragile and would silently misalign if a covariate were ever added. Prefer
  aligning on the model's own index.

---

## What's done well

This deserves to be said plainly, because the instinct behind this report is
right even where the execution slips:

- **The null result is reported as a null result.** There is no p-hacking, no
  quiet dropping of the inconvenient specification, no "marginally significant
  (p=0.047) suggests a promising relationship." The headline sentence is
  literally "the association ... is not robust." That is the correct call and
  many analysts would not have made it.
- **The FE sensitivity ladder was the right instinct.** Running 1 → year FE →
  two-way FE and *reporting the sign flip rather than hiding it* is exactly the
  behaviour you want. The issue is which specification got promoted to
  headline, not that the ladder was built.
- **The data-coverage discovery is the most valuable output in the folder.**
  Establishing that EIBIS's digitalization breakdown is empty at the ALL/ALL
  aggregation before 2023 — and that this collapses a notional 8-year panel to
  3 years — is a genuine finding that saves the next analyst weeks. It is
  correctly documented as "not visible from the README."
- **The merge is actually correct.** GR→EL, non-country fund rows, the
  `20-99` double-count trap, aviation exclusion, E-PRTR biomass filter: all
  verified, all right, all documented with reasons. The `20-99` reasoning in
  particular (comments at `analysis.py:32-36`) is the kind of thing that is
  usually silently wrong.
- **"What this does NOT show"** (lines 223–247) is unusually disciplined. The
  explicit refusal to spin the absent `climate_target_share` result into a
  greenwashing narrative — when that narrative is the repo's stated research
  motivation — is good scientific conduct.
- **The limitations section correctly identifies aggregation bias, the
  energy-shock window, and the firm-level data gap** without using them as an
  excuse. The JRC crosswalk was inspected and honestly declared unusable rather
  than forced into the analysis.

---

## Recommended next step

The smallest change set that makes this presentable — roughly half a day:

1. **Fix the H1 direction sentence** (lines 8–13) so "positive" and its gloss
   agree, and add one plain-language sentence to Results spelling out what the
   positive pooled sign would mean if it were real.
2. **Re-run Models 1 and 4 with country-clustered SEs** and update the results
   table (M1: p 0.047 → 0.114; M4: p 0.131 → 0.214). Then rewrite the Results
   narrative: the result dies from *non-independence and one Bulgarian
   observation*, not from year fixed effects.
3. **Add the leave-one-out row** (drop BG-2025 → p=0.086; drop BG → p=0.210).
   Three lines of code; it is the most convincing fragility evidence available.
4. **Demote Models 4 and 5 out of the headline table** into an appendix, with
   the variance-decomposition number (within SD 0.051 vs between SD 0.119) as
   the stated reason two-way FE cannot work here.
5. **Lead with one scatter plot instead of five regressions**: 27 countries,
   mean `digital_multi` on x, cumulative 2022→2025 Δlog emissions on y, fitted
   line, 95% band that visibly straddles zero, Bulgaria labelled. Caption:
   *"There is a faint positive tilt (r=+0.34, p=0.083), meaning more-digitalized
   countries cut emissions slightly less — but the band covers zero, and
   removing Bulgaria removes the tilt. On this data, digitalization intensity
   and verified emissions change are not measurably related."*
6. **Optionally add the block permutation test** (p=0.095). With n=81 and a
   3-year panel, a randomization check is more credible to a skeptical reader
   than another asymptotic p-value, and it costs ten lines.

For a non-technical audience, the deliverable should be: one chart, one
paragraph saying no relationship is detectable at country level, one paragraph
saying why (3 years of usable data, country averages, energy-crisis window),
and one paragraph on what firm-level EIBIS microdata would unlock. The
five-model table becomes an appendix.

**Do not present this to a stakeholder before fixes 1–3.** Fix 1 risks the
reader drawing the exact opposite conclusion; fix 2 risks presenting a
significance claim that the report's own methodology contradicts.
