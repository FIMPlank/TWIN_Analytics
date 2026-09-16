# Review of `analysis/extension_analysis.md`

Second-round review, covering the four extension items. The first-round review
(`analysis/review.md`) is unchanged and still applies to
`first_pass_analysis.md`.

Everything was re-run (`python analysis/extension_analysis.py`, Python 3.12.10
/ statsmodels 0.15.0 / pandas 3.0.5). **All reported numbers reproduce
exactly** — the covariate table (0.247/0.403/0.202/0.394 with p =
0.075/0.0006/0.168/0.0008), both permutation p-values (0.096, 0.163), both new
EIBIS correlations, and the wave-coverage counts.

The headline question — *is the Eurostat-controls result another Bulgaria-style
artifact?* — got a dedicated stress test: leave-one-country-out, control-by-
control decomposition, small-cluster-corrected inference, a wild cluster
bootstrap, and lagged/differenced re-specifications.

---

## Verdict

**Not a Bulgaria-style artifact — but not presentable as a finding either,
because it rests on an undefended specification choice.**

This needs one more targeted pass, materially smaller than round one.

The short version: the result is **robust to everything the coordinator
suspected** (Malta, the Baltics, Slovenia, Ireland, any single country, any
single control) and **fragile to something nobody checked** — whether the
controls enter in levels or in changes. It also carries a p-value that is
roughly 15× too small for the number of clusters.

The Researcher's decision *not* to promote this to the headline was the right
call. But the caveats offered in support of that call point at the wrong
risks, so the document currently reads as "we're being cautious about a result
we can't fault," when the accurate reading is "we're being cautious about a
result that has an identifiable, testable weak point."

---

## Confirmed issues

### 1. The result depends entirely on controls entering as *levels* against a
*differenced* outcome — BLOCKING for presentation

This is the finding that matters. The outcome is `d_log_emissions` (a
year-over-year **change**); all three controls enter as **levels**
(`log_gdp_per_capita`, `industry_va_share`, `electricity_price` —
`extension_analysis.py:174`, `191`). That mismatch is never mentioned or
defended in `extension_analysis.md`.

Re-specifying the controls to match the outcome, **on the identical n=48
estimation sample** so that power is held constant:

| Controls on the same n=48 sample | coef | p |
|---|---|---|
| Bare (no controls) | +0.194 | 0.151 |
| **Levels** (as reported) | +0.358 | **0.0011** |
| **Changes** (Δ controls, matching Δ outcome) | +0.200 | **0.212** |

Same observations, same clustering, same regressor. The entire result is the
levels-vs-changes choice. It is *not* a sample-size effect — that is why the
comparison is run on n=48 for all three rows.

A lagged-levels version (controls at t−1, i.e. pre-determined) sits in
between: coef +0.326, **p = 0.010**, n=49.

What is most likely happening: slow-moving level controls on a differenced
outcome act as *partial country fixed effects*. They absorb cross-country
variation in trend levels and thereby change what identifies `digital_multi` —
which is precisely why the coefficient grows rather than shrinks. That is a
mechanical consequence of the specification, not evidence of a real effect
surviving confounders.

**Until the report states which specification it believes and why, the
p≈0.001 number should not be shown to anyone.**

### 2. The reported p-value is overstated by roughly an order of magnitude —
BLOCKING (correctness of a reported number)

`statsmodels`' `cov_type="cluster"` reports **z-based** p-values — it does not
apply a t(G−1) reference distribution or any small-cluster correction. With
G=26 clusters and 5 parameters this is meaningfully anticonservative.

| Inference method (Model 1c) | p |
|---|---|
| As reported (statsmodels z-based CRV1) | 0.0006 |
| Correct t(G−1 = 25) reference | 0.0020 |
| **Wild cluster bootstrap** (Rademacher, restricted null, 9,999 reps) | **0.0090** |

Model 3c: 0.0008 → 0.0026 (t) → **0.0123** (wild bootstrap).

The result still clears 5% under the gold-standard small-cluster method, which
is genuinely notable. But "p≈0.001" is wrong and should be reported as
**p≈0.01**. Note this also means round one's guidance was followed only
halfway: clustering was applied, but the small-cluster caveat the first-pass
report itself raised was not actually acted on numerically.

### 3. The block-permutation machinery was built, then not applied to the one
result that needed it — SHOULD-FIX

Item 3 applies the permutation test to Models 1 and 3 — the *bare* specs whose
null status was never in doubt. It is not applied to Models 1c/3c, the only
new result with a small p-value and the one where asymptotic cluster inference
is least trustworthy. The tooling to do this already exists in the file. (My
wild cluster bootstrap in issue 2 fills the gap, but it should be in the
Researcher's own script.)

### 4. Contemporaneous controls are plausibly *bad controls* — SHOULD-FIX
(design, not arithmetic)

`industry_va_share` and `electricity_price` are measured in the same year as
the emissions change they are meant to control for. Both respond to the same
shocks that move emissions: when industry contracts, industrial value-added
share falls and emissions fall together; when power prices spike, industrial
output is curtailed and emissions fall. Conditioning on a contemporaneous
consequence of the shock is a textbook bad-control problem, and it is not
discussed anywhere in the write-up.

This is the substantive reason to prefer the lagged or differenced
specification in issue 1, and it is why the divergence there should be treated
as a red flag rather than as spec-hunting noise.

### 5. The implied magnitude is too large to be credible — SHOULD-FIX

Nowhere is the coefficient translated into something a reader can judge.
SD(`digital_multi`) = 0.126, so the reported +0.403 implies:

> a one-standard-deviation increase in national digitalization is associated
> with **+5.1 percentage points** of annual emissions growth

against a sample mean annual change of **−10.0%**. In other words, one SD of
digitalization would erase *half* of the average country's entire annual
emissions decline. For a country-level survey share over three years, that is
not a plausible structural magnitude. Implausible effect size on a
short panel is itself evidence of residual confounding — it belongs in the
report as a caution, and it is a strong independent argument against
presenting this as a finding.

### 6. Ireland's national-accounts distortion is present in the data (but is
*not* driving the result) — NICE-TO-HAVE

The classic gotcha is confirmed in the merged data. Ireland 2024:
`gdp_per_capita` = €89,300 (second only to Luxembourg) and `industry_va_share`
= **32.0%** — the highest in the entire sample, above Czechia (26.9) and
Germany (23.4). Both are inflated by multinational IP onshoring and contract
manufacturing booked in Ireland with little corresponding physical activity
and essentially no ETS footprint (Irish ETS emissions are ~11 Mt, mid-table).
So Ireland enters with substantial measurement error on **two of the three**
controls simultaneously.

To the Researcher's credit, this does not drive anything:

| Sample | coef | p |
|---|---|---|
| Full (n=74) | +0.403 | 0.0006 |
| Drop IE | +0.445 | 0.0000 |
| Drop IE, LU | +0.371 | 0.0005 |
| Drop IE, LU, CY, MT | +0.377 | 0.0004 |

Dropping Ireland *strengthens* the result. Worth one sentence in the report
as a known limitation of `industry_va_share` as a proxy for physical
industrial structure, not more.

### 7. The report's own caveats aim at the wrong risks — SHOULD-FIX (framing)

`extension_analysis.md` lines 81–86 lead with the sample-restriction worry:
*"Some of the further move to p=0.001 could reflect this sample, not the
controls per se."* Decomposition shows this is largely unfounded:

- Sample restriction (n=81→74) alone: p 0.114 → 0.075
- Adding the controls on that fixed sample: p 0.075 → 0.0006

The controls do nearly all the work; the sample restriction does very little.
And the coordinator's Bulgaria hypothesis is cleanly refuted — **leave-one-
country-out across all 26 countries gives a maximum p of 0.0041** and a
minimum coefficient of +0.306. Nothing here resembles the round-one situation
where one Bulgarian observation carried the whole result.

So the report is *over*-cautious about sample composition and *silent* on the
two things that actually undermine the number (issues 1 and 2). The caution is
directionally right but pointed at the wrong target — which is its own kind of
problem, because a reader who checks the stated caveat will find it doesn't
bite and may conclude the result is sturdier than it is.

### 8. Sanity checks on items 2–4 — all clean

- **Permutation block logic (item 3) verified correct.** Reconstructed the
  shuffle at `extension_analysis.py:274-288`: every country receives an intact
  real 3-year block, each country's own within-block year-to-year structure is
  preserved, outcomes stay correctly aligned to their own country, and
  self-pairing occurs at the expected rate (1/27 on the seeded draw). The
  column-relabel-then-reorder idiom is subtle but does the right thing. Both
  p-values reproduce (0.096, 0.163).
- **Item 2 verified.** Both correlations reproduce (−0.009/p=0.937;
  +0.142/p=0.205); the "adds nothing" conclusion is correct and the framing as
  a second independent null is fair.
- **Item 4 verified locally.** The wave-coverage table reproduces exactly
  (0 non-null for 2018–2022, 27 for each of 2023–2025). The *live API* counts
  quoted in the write-up (1,585 / 989 / 596 rows) could not be re-verified
  offline — the committed script only re-checks the cached ALL/ALL cells. The
  local evidence is fully consistent with the claim. Consider persisting the
  API response so the claim is reproducible rather than resting on prose.
- **Eurostat pull verified.** Unit filters are exactly as documented
  (`CLV20_EUR_HAB`; `PC_TOT`/`B-E`/`B1G`; ex-tax EUR/kWh). Both semesters are
  present for every year 2023–2025, so the semi-annual→annual averaging at
  `extension_analysis.py:120-121` is not silently averaging a half-year against
  full years — a real risk that was checked and is clean. Values spot-check as
  plausible (LU €101k, FI/SE electricity ~€0.08/kWh, MT industry share 7.6%).
  The 7 dropped rows are genuinely missing electricity prices for small
  markets, correctly reported.
- **Round-one fix landed:** EIBIS `EU`/`US` aggregate rows are now explicitly
  filtered (`extension_analysis.py:70`).

---

## What's done well

- **The Researcher did not oversell this.** Faced with a p=0.001 after a
  reported null, the temptation to upgrade the headline is enormous. The report
  explicitly refuses ("does **not** mean the tightened result should be treated
  as a confirmed finding", lines 257–263) and keeps it as a flagged pattern.
  That judgment call is correct, and it is the single most important thing in
  the document.
- **Round-one feedback was genuinely absorbed, not performed.** Clustered SEs
  are now the default throughout; the literal "against H1" direction is stated
  plainly and repeatedly rather than buried; the `EU`/`US` filter was added; the
  permutation test was actually built.
- **The same-sample comparison design (n=74 bare vs. n=74 controlled) is
  exactly right** and is what let me isolate issue 1 so cleanly. Many analysts
  would have compared n=81 bare against n=74 controlled and confounded the two.
  The Researcher anticipated this and pre-empted it (lines 52–56).
- **The condition-number diagnosis is correct and well-handled.** Identifying
  cond. no. 683 as a regressor-scaling artifact and verifying via z-scored
  re-fit (lines 90–97) is the right call — I confirmed VIFs are all below 1.8.
  That is a diagnostic many would have either ignored or panicked about.
- **Item 4 is real diligence.** Going back to the live API to confirm a
  negative-coverage claim across *all* sector/size cells — rather than
  re-asserting it from the same cached CSV — is exactly the right instinct for
  a claim that shapes the whole project's scope.
- **The `custom.js` indicator-discovery work (item 2) is genuinely resourceful**,
  and the aside about `Implementation of digital technologies` being filed
  under `INNOVATION ACTIVITIES` is the kind of undocumented detail worth
  recording.
- **Item 2's negative result is framed correctly** as strengthening the null
  rather than as a failed attempt.

---

## Recommended next step

Smallest change set that makes the extension presentable — roughly half a day:

1. **Add the levels-vs-changes robustness row** (issue 1), on the fixed n=48
   sample: bare +0.194/p=0.151, levels +0.358/p=0.0011, changes
   +0.200/p=0.212, lagged levels +0.326/p=0.010. Then state plainly which
   specification the report stands behind. Given the bad-control argument
   (issue 4), **lagged controls are the defensible default** — and on that
   spec the result is p≈0.01, not p≈0.001.
2. **Correct the p-values** (issue 2). Report the wild cluster bootstrap
   (p=0.009 / 0.012) as the headline inference for 1c/3c, with the z-based
   figure dropped entirely. One paragraph noting statsmodels' z-default is a
   useful methodological note for the repo.
3. **Run the existing block-permutation test on 1c/3c** (issue 3) — the code
   is already in the file, it needs a covariate-aware formula and a loop.
4. **Add the leave-one-country-out table** (max p = 0.0041, min coef = +0.306).
   This is *positive* evidence and deserves to be shown: it is the cleanest
   available demonstration that this is not a repeat of round one, and it
   should replace the currently-unfounded sample-composition caveat.
5. **Add one magnitude sentence** (issue 5): "1 SD of digitalization ≈ +5.1pp
   annual emissions growth, against a −10.0% sample mean — implausibly large
   for a three-year country panel, and itself a reason for caution."
6. **One sentence on Ireland** (issue 6), with the drop-IE row as evidence it
   isn't driving anything.

For a stakeholder, the honest one-paragraph version after these fixes is:

> Adding standard economic controls does not make the digitalization–emissions
> association go away — it strengthens it, in the direction *opposite* to the
> project's hypothesis, and it holds up when any single country is removed.
> But it holds only when the controls are specified in levels; specified as
> changes, it disappears. On the most defensible specification the p-value is
> about 0.01, not 0.001, and the implied effect is too large to be structural.
> This is a pattern worth chasing with firm-level data, not a result.

**Presentable after fixes 1, 2 and 4.** Fix 2 corrects a wrong number; fix 1
prevents a reader from treating a specification artifact as a finding; fix 4
is the strongest evidence the Researcher has and is currently missing.

---

# Round 3 — final verification pass

Re-ran everything and independently re-implemented the wild cluster bootstrap
from scratch rather than trusting the Researcher's implementation.

## Verdict: **GO** — presentable, with one reproducibility fix

Both blocking issues from round 2 are properly fixed, not papered over. The
write-up now leads with the corrected numbers, designates the defensible
specification explicitly, and hedges appropriately. Nothing left in the
document would lead a reader to a wrong conclusion.

## Item-by-item verification

**1. Levels vs. changes vs. lagged — CONFIRMED, reproduces exactly.**
Independent refit on the fixed n=48 / 25-country / 2024-25 sample: bare
+0.194 (p=0.151), levels +0.358 (p=0.0011), changes +0.201 (p=0.212), lagged
+0.341 (p=0.0072). Matches
`extension_levels_vs_changes_vs_lagged.csv` to four decimals. Holding the
sample fixed at n=48 across all four specs (`extension_analysis.py:271-273`)
is the right construction, and dropping 2023 uniformly — rather than letting
some countries carry a thin 2022 baseline — is a defensible, well-documented
choice.

**2. Small-cluster correction — CONFIRMED, implementation is sound.**
Audited `wild_cluster_bootstrap_p` (`extension_analysis.py:365-382`) line by
line and re-implemented it independently. It is textbook Cameron–Gelbach–Miller:
restricted (null-imposed) residuals, Rademacher weights drawn **per cluster**
(`size=G`) and broadcast within cluster, bootstrap-*t* with the cluster-robust
SE recomputed each rep, CRV1 finite-sample correction
`(G/(G-1))·((n-1)/(n-k))`, 4,999 reps (odd, correct practice), two-sided on
|t|. **Resampling unit is the whole country block — correct. No leakage.**
G=25, so t(G−1)=t(24) is right. My independent values: t(24) p=0.0129
(pooled) / 0.0117 (+year FE), matching their 0.01285 / 0.01166.

**3. Block-permutation on controlled specs — CONFIRMED, now actually run.**
Section 1e covers all four controlled specs (levels/lagged × pooled/year-FE),
5,000 reps, reproducing 0.0086 / 0.0076 / 0.0104 / 0.0124. Note they replaced
the pivot-and-flatten with a keyed merge (`extension_analysis.py:443-461`)
specifically because the n=48 sample is *not* a balanced 25×2 grid — that is
a real hazard correctly anticipated and avoided.

**4. Effect size — CONFIRMED exact.** SD(`digital_multi`)=0.1326, sample mean
Δlog=−0.0726 (−7.3%), 0.3405×0.1326=0.0452 → **+4.5pp**, and 4.52/7.26 =
**62%**. All correct. Tone is right: it is presented as *a reason for
skepticism* ("classic symptom of residual confounding... not a reason for more
confidence"), which is the correct reading.

**5. Honesty — PASSES.** The write-up leads with p≈0.03–0.04 as "the real
p-value", explicitly labels the old 0.0006 as depending on an undefended
choice, names the bad-control problem, carries the "against H1" direction
throughout, and keeps "pattern worth chasing, not a confirmed finding." No
overclaiming re-introduced.

## Remaining issues

### A. Bootstrap seed is not reproducible — SHOULD-FIX (only real defect)

`extension_analysis.py:403`:

```python
rng_boot = np.random.default_rng(20250916 + hash((spec_label, fe_label)) % 1000)
```

Python randomizes `hash()` on strings per process (PYTHONHASHSEED). Verified:
three runs gave three different seeds. So the bootstrap p-values **change on
every run**, and the document already disagrees with its own output file:

| Spec | `extension_analysis.md` | `extension_small_cluster_inference.csv` |
|---|---|---|
| Levels, pooled | 0.0196 | 0.0182 |
| Lagged, pooled | 0.0404 | 0.0384 |

Substantively harmless — I ran 10 independent seeds: lagged pooled ranges
0.0352–0.0444 (mean 0.0374), lagged +year FE 0.0304–0.0384 (mean 0.0331). The
claim "≈0.03–0.04" is stable and every draw stays under 0.05. But the exact
digits are not reproducible, which is a real defect in a repo whose whole
selling point is reproducibility. Fix: replace `hash(...)` with a fixed
per-spec offset (e.g. `enumerate` index), and re-sync the table to the output.

### B. Section 1e overstates the agreement between the two methods —
NICE-TO-HAVE

"The permutation p-values land close to the wild-bootstrap p-values" — they
are 2–4× apart (0.0086 vs 0.0196; 0.0104 vs 0.0404), consistently *smaller*.
This is expected: the test permutes `digital_multi` while holding covariates
fixed, which is anticonservative when the regressor correlates with the
covariates — and here it does (r = +0.41 with lagged log GDP/capita, −0.31
with lagged electricity price). Freedman–Lane (permuting reduced-model
residuals) is the covariate-aware variant. Not blocking: the report already
designates the bootstrap as the real p-value and quotes the union range
0.01–0.04. Suggest softening to "both small-cluster-appropriate methods keep
the result under 5%, with the permutation variant the more optimistic of the
two."

### C. Leave-one-out was run on the demoted levels spec — NICE-TO-HAVE

Section 1f's LOO (max p=0.0041, min coef=+0.306) is computed on the n=74
*levels* spec, not the lagged spec now carried forward. The report discloses
this plainly, and it answers the coordinator's original question, so it is not
misleading — but the robustness evidence technically belongs to a
specification the document has just demoted. Re-running LOO on the lagged n=48
spec would close the loop.

## Bottom line

Fix A (ten minutes) and this is ready. B and C are polish and do not change
what a reader would conclude.
