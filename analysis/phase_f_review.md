# Phase F review (independent)

Reviewer pass over `analysis/phase_f_patents.md` / `phase_f_patents.py` / `phase_f_build*.py`,
`scripts/download_eurostat_*`, `analysis/output/phase_f_*` and `data/raw/eurostat|geo/`.
Everything below was re-derived from the raw CSVs with reviewer-written code (own NUTS-vintage
chaining, own perpetual inventory, own within-FE OLS, own CR1 and own wild cluster bootstrap loop);
nothing was imported from `phase_f_*.py`. Four patent cells and four GVA cells were re-checked
against the live Eurostat API. No files were committed.

## Verdict

**Go, with four required corrections before this is written up.** The headline is reproducible to
machine precision, the predetermined design is implemented correctly, and there is no leakage.
The null is *real* — it is not manufactured by collinearity, by over-demanding controls, by zero
inflation in small regions, or by the lost regions — but it is a bound on **large** effects only,
and the inference behind that bound is weaker than the write-up says. One whole accession country
(Romania) is silently absent from every regression, and the diagnosis of the wild-bootstrap
disagreement is wrong (it is Italy, not Germany).

## Reproduction

Independent rebuild from raw → researcher's saved samples: identical unit sets at both levels, and
max |difference| ≤ 3.6e-15 on `x_dig`, `x_nondig`, `x_total`, `g_ind`, `ln_gvapc04`, `ind_share04`.

| Spec | level | n | G | coef | CI (t, G-1) | p t(G-1) | p wild (mine) | md |
|---|---|---|---|---|---|---|---|---|
| A3 CLAIM | NUTS2 | 177 | 18 | **-0.0422** | [-0.293, +0.209] | 0.727 | 0.736 | -0.042 / 0.73 / 0.74 ✓ |
| A3 CLAIM | NUTS3 | 956 | 24 | **-0.0223** | [-0.170, +0.126] | 0.758 | 0.871 | -0.022 / 0.76 / 0.87 ✓ |
| A2 dig-only | NUTS3 | 956 | 24 | +0.0705 | [+0.006, +0.135] | 0.034 | 0.132 | ✓ |
| A4 total patents | NUTS3 | 956 | 24 | +0.2400 | [-0.035, +0.515] | 0.084 | 0.017 | ✓ |
| B1 pooled, no FE | NUTS3 | 956 | 24 | +0.3470 | [+0.144, +0.550] | 0.002 | 0.049 | ✓ |

Units are correctly described: y = 100·[ln GVA(2019) − ln GVA(2005)]/14 is pp/yr, x is
asinh(stock per million inhabitants), so "pp/yr per unit of the transformed stock" is right.

## Confirmed issues

### 1. Romania is absent from every single regression, and this is not disclosed — MODERATE-HIGH

`nama_10r_3popgdp` has no NUTS3 population for RO between 2002 and 2011, so `pop04` is NaN for all
42 RO NUTS3 regions. That NaN propagates into `ln_gvapc04` **and** into every per-capita patent
stock (`x_dig`, `x_nondig`, `x_total`), so the `dropna(subset=need)` in `regional_block()` removes
Romania entirely. It is the only country affected (missing-control counts: 39 at NUTS3, 6 at NUTS2
— all RO).

The write-up never says so, and actively points the other way:
- §3 attributes the 1,050 → 956 drop to "CY and LU are single-unit"; the real arithmetic is
  997 EU27 units − 1 CY − 1 LU − **39 RO** = 956.
- §3 lists RO among the countries with "near 100%" patent retention, implying it is in the sample.
- §8 caveat 1 lists the lost countries (EE, HR, IE, LV, SI at NUTS2; EL, PT, HR at NUTS3) without RO.

I refitted with a nearest-available-year population fallback (2001/2012):

| | n | G | A3 dig | p wild | ACC-only A3 | ACC n, G |
|---|---|---|---|---|---|---|
| NUTS3 as-is | 956 | 24 | -0.022 | 0.87 | -0.034 | 144, 11 |
| NUTS3 + RO | 995 | 25 | -0.026 | 0.82 | **-0.111** | **183, 12** |
| NUTS2 as-is | 177 | 18 | -0.042 | 0.74 | -0.239 | 35, 6 |
| NUTS2 + RO | 183 | 19 | -0.052 | 0.66 | -0.304 | 41, 7 |

**Conclusions survive** (still null, still no positive accession effect — if anything more
negative), but the accession NUTS3 subsample was 21% smaller than it needed to be, and the
disclosure as written is inaccurate. Fix the population input and re-run; do not just add a caveat.

### 2. The wild-vs-t disagreement is misdiagnosed: the dominant cluster is Italy, not Germany — MODERATE

§8 caveat 2 blames "unbalanced clusters (DE 40%, IT/FR 10% each)". Germany is 40% of *units* but
that is not what drives the variance. Computing the per-cluster influence on β̂ and the
Carter–Schnepel–Steigerwald effective number of clusters G* on the NUTS3 sample:

| regression | nominal G | **G\*** | top variance shares |
|---|---|---|---|
| A3 (claim, x_dig) | 24 | **1.9** | IT 0.71, FR 0.16, DE 0.04 |
| A4 (x_total) | 24 | **3.0** | IT 0.43, DE 0.37, NL 0.09 |

I also confirmed the mechanism behind wild p = 0.017 vs t p = 0.084 directly: for A4 the bootstrap
|t| distribution is *narrower* than t(23) — 90/95/99th percentiles 1.52 / 1.65 / 1.86 against
t-critical 1.71 / 2.07 / 2.81. So the restricted Rademacher bootstrap is **anti-conservative** here
(the known small-G\* failure), rather than the t-test being conservative. The researcher's call to
treat A4 as suggestive only is correct; the stated reason is not, and the fix offered (equal country
weights, Webb weights) does not address a G* of 3. Two further checks I ran point the same way:
dropping Germany gives A4 = +0.363 with p_t = p_wild = 0.025, while re-clustering Germany at
Bundesland level (G = 37) gives +0.249, p_t 0.080 / p_wild 0.099 — i.e. the "significance" moves
around with the cluster definition.

Consequence for the headline that the write-up does not draw: the claim CI [-0.17, +0.13] and the
power statement built on it rest on a CR1 variance that is effectively a two-country calculation.
For A3 the bootstrap 97.5th percentile (2.04) is close to t-critical (2.07), so the CI is roughly
defensible — but that has to be shown, not assumed from "18–24 clusters".

### 3. Region loss is strongly correlated with the outcome, which §8 does not say — MINOR-MODERATE

Comparing EU27 NUTS3 regions that survive the harmonisation with those that do not, on the same
outcome (nominal B-E GVA growth 2005-19, pp/yr):

| | n | mean growth |
|---|---|---|
| kept | 956 | 2.37 |
| lost | 213 | **3.60** |
| EU15 kept / lost | 812 / 115 | 1.89 / 1.38 |
| accession kept / lost | 144 / 98 | 5.11 / **6.20** |

So 40% of accession NUTS3 regions are lost and the lost ones grew ~1.1 pp/yr faster. §8 discloses
*which* countries are lost but not that the loss is non-random in the outcome. I checked that it
does not change the answer — restricting to the 14 countries with ≥97% patent retention gives
A3 = -0.043 (p_wild 0.83); A4 = +0.232 (p_t 0.107, p_wild 0.008, same disagreement) — but the
disclosure should state the selection, not just the country list.

### 4. `scripts/download_eurostat_patents.py` docstring contradicts the analysis — MINOR

The docstring states "a patent carrying several IPC classes is counted in each class, so class rows
do not sum to the total". That is false, and the whole `nondig = total − digital` construction
depends on it being false. I verified fractional counting **at class level** against the live API:
DE212, 2004, sum of all G01–G21 classes = 158.05 vs section G = 158.06 (ratio 1.000); and locally
A–H vs IPC totals give ratios 0.9999 / 0.9998 / 0.9998 in 1990 / 2000 / 2004. The analysis is right;
the docstring would mislead anyone reproducing this. Fix the docstring.

### 5. Smaller points

- §1's "+0.2–0.3 per within-country SD" uses the raw within-country SD of `x_dig` (1.11 / 1.39).
  The SD of the *identifying* variation (after partialling out non-digital, controls, FE) is
  0.81 / 1.10, so the correct per-SD bound is ~0.14–0.17 pp/yr. This errs conservative, but say
  which SD is meant.
- §3's `corr(asinh digital, asinh non-digital) = 0.83–0.90` is the raw cross-sectional correlation.
  The correlation the FE regression actually faces is the **within-country** one: 0.66 (NUTS2) and
  0.59 (NUTS3). Quoting only the raw figure overstates the collinearity problem.
- The A3 accession split at NUTS2 (n = 35, G = 6, CI [-0.93, +0.45]) is not informative enough to
  support "no evidence of a 2.4x larger effect"; the NUTS3 version (G = 11–12) carries that claim,
  not the NUTS2 one. Phrase accordingly.
- CR1's small-sample factor uses k = number of regressors only, excluding the absorbed country FE.
  This makes the SE marginally too small. Negligible here (n ≫ G), but worth a line.

## Masked-signal check: is the null informative?

**Mostly yes, for large effects; the collinearity story is weaker than the write-up implies.**

After country FE, controls and the non-digital stock, the digital stock still retains
**61.9%** of its within-country variance at NUTS3 (SD 1.10 of 1.39) and **52.7%** at NUTS2
(0.81 of 1.11). Partial R² of `x_dig` on the rest of the model is 0.38 / 0.47 — real, but far from
the "close to collinear" reading suggested by the raw 0.83–0.90 correlation.

Everything I threw at it is null in the same place (NUTS2 / NUTS3 coefficient, p_wild):

| variant | NUTS2 | NUTS3 |
|---|---|---|
| digital only, no controls | -0.042 (0.58) | +0.019 (0.64) |
| digital + controls (A2) | -0.004 (0.96) | +0.071 (0.13) |
| A3 claim | -0.042 (0.74) | -0.022 (0.87) |
| explicitly orthogonalised digital (FWL) | -0.042 (0.74) | -0.022 (0.87) |
| digital **share** of stock (+ x_total) | -0.78 (0.50) | -0.80 (0.81) |
| log(dig/nondig) ratio (+ x_total) | +0.009 (0.95) | -0.004 (0.97) |
| drop zero-digital-stock units | -0.006 (0.97) | -0.006 (0.98) |
| drop smallest population quartile | +0.028 (0.85) | -0.041 (0.91) |
| drop smallest-stock quartile | -0.027 (0.87) | +0.040 (0.65) |
| high-patent-coverage countries only | — | -0.043 (0.83) |
| Romania restored | -0.052 (0.66) | -0.026 (0.82) |

So the null is not an artefact of collinearity, of the non-digital control, of measurement error in
tiny/zero-patent regions, or of the lost regions. The one variant that is genuinely uninformative is
the digital-share spec (CI roughly ±3 pp/yr) — worth reporting as such rather than as another null.

**Minimum detectable effect** (80% power, 5%, from the CR1 SE): 0.35 pp/yr (NUTS2) and 0.21 pp/yr
(NUTS3) per asinh unit, i.e. **0.23–0.29 pp/yr per SD of the identifying variation**, against a
within-country outcome SD of 1.69 pp/yr. The design can therefore exclude effects above roughly
0.14 outcome-SD per regressor-SD and nothing smaller — and per issue 2, that bound is itself built
on a G* ≈ 2 variance estimate, so treat it as an order of magnitude rather than a number.

## What's done well

- **No leakage.** I corrupted every post-2004 patent cell to a large constant and re-ran the
  baseline stock: byte-identical. Perpetual inventory matches the closed form
  Σ P_t (1−d)^(2004−t) to 2e-13. The placebo stock genuinely uses 2005–2012 only.
- **NaN-vs-0 handled correctly** — the trap that bit Phase B/C. Every one of the 1,426 patent NUTS3
  codes has data in some year (median 33 of 36), so treating absent cube cells as zero is right, not
  a NaN→0 bug. And the NUTS2 aggregation really is NaN-safe: I tested every NUTS2 unit in the
  analysis sample for a child that is absent from (not merely NaN in) the B-E pivot — **zero cases**,
  so no silent partial sums.
- **Vintage chaining is sound where it can be checked.** No two 2010 codes collide on the same new
  code unflagged (a merge would have double-counted); flagged splits/merges are dropped rather than
  guessed; spot checks behave as expected (FR421→FRF11 clean recode; DE801/DE808/EL251 flagged).
- **Live data check passes.** pat_ep_ripc DE212/2004/G06 = 57.03, ITC4C/2000/IPC = 528.35,
  FR101/2004/H04 = 128.34, PL127/1998/IPC = 5.3; nama_10r_3gva B-E CP_MNAC DE212 2005/2019 =
  12,618.58 / 22,408.97, ITC4C 2005 = 21,212.3, PL911 2019 = 25,225 — all exact against local files.
- **LOO is on the right regression.** `loo()` is called with `("x_dig","x_nondig")` + CTRL, target
  `x_dig` — the actual claim regression — at all three levels, plus separate A2 and A4 runs. Not the
  Phase C error.
- **Identical samples.** n = 177 / 956 across A1–A5, Aw, B, C and every D robustness row (one
  exception, n = 954, from the 3-year-average outcome).
- **Framing is honest.** §7 explicitly refuses the "rules out" reading, states correctly that a
  predetermined stock removes reverse causality but not shared long-run drivers, and flags that
  inventor residence ≠ where industrial value added is produced. §5 correctly calls the placebo
  weakly informative because the "future" stock correlates 0.83–0.96 with the baseline, correctly
  reports that P0 (the earlier-window analogue) is *negative* rather than replicating a positive
  sign, and flags the one significant negative (P4, NUTS2) as a multiplicity/noise artefact with the
  wrong sign. §8 caveat 3 pre-emptively discounts the two p-values just under 0.05. The PYP claim
  checks out (8 countries span 2006–2019; 9 have any PYP data). The unverified
  inventor-residence/ESMS caveat is fair — the ESMS page is genuinely 404 — and the load-bearing
  half of it (fractional, additive class counting) I have now verified live.

## Recommended next step

1. Fix the Romania population gap (nearest-year fallback, or `demo_r_pjanaggr3`) and re-run the
   whole file. Correct §3's sample arithmetic and §8's list of lost countries.
2. Replace the "Germany is 40% of units" diagnosis with the effective-cluster computation
   (G* = 1.9 for A3, 3.0 for A4, Italy dominant) and report G* next to every claim-carrying row.
   State plainly that with G* ≈ 2–3 neither p-value is reliable and that the claim CI is a
   two-country object — this weakens the power statement in §1 and should be said there.
3. Add the kept-vs-lost outcome comparison (2.37 vs 3.60 pp/yr; 5.11 vs 6.20 within accession) to
   §8 caveat 1, plus the high-coverage-only robustness row showing it does not change the answer.
4. Fix the `download_eurostat_patents.py` docstring; quote the within-country correlation (0.59–0.66)
   alongside the raw one; say which SD the "per within-country SD" statement uses.
5. Optional but cheap: report the digital-share spec as uninformative rather than as a null, and add
   the drop-zero-stock / drop-small-region rows — they are the strongest available evidence that the
   null is not a measurement-error artefact.
