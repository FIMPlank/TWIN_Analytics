# Review of `analysis/phase_c_analysis.md`

Independent verification of the three Phase-C refinements. Items 1 and 3 got
the full adversarial treatment; item 2 was spot-checked as instructed.

Method: re-ran all three items; independently re-geocoded a 300-facility
random sample against the NUTS2021 polygons; re-derived the pollutant coverage
from the 370k-row raw facility file; ran leave-one-out and wild cluster
bootstrap on item 3; and tested the one comparison neither item 1 nor item 3
makes.

---

## Verdict

| Item | Verdict |
|---|---|
| **1 — NUTS2 regional panel** | **Needs rework before any result is shown.** Engineering is excellent; the two headline numbers are not trustworthy and one is an artifact of clustering at the wrong level. |
| **2 — Emissions intensity** | **GO as-is.** Clean. |
| **3 — Large-firm EIBIS split** | **The framing is wrong and must be inverted.** The effect is not about firm size at all. |

Item 3 is the important one. **The report has found something real and
flagged the wrong thing as the finding.** The large-firm story does not
survive a like-for-like comparison — but the 15-country subset story, which
the report treats only as a caveat, is where the actual signal is. Details
below.

---

## Confirmed issues

### 1. Item 3: the "large-firm effect" is entirely a sample-restriction
effect — BLOCKING

The report's claim is that the large-firm EIBIS series, being closer to the
ETS-regulated population, "shows a noticeably larger, closer-to-significant
coefficient (+0.273) than the all-firms aggregate (+0.178)". That comparison
is **27 countries vs. 15 countries**. The missing cell is the all-firms
measure on the same 15 countries. Running it (wild cluster bootstrap, 4,999
reps, the project's own standard):

| Spec | n | G | coef | wild-boot p |
|---|---|---|---|---|
| ALL firms, 27 countries | 81 | 27 | +0.178 | 0.253 |
| **ALL firms, same 15 countries** | 45 | 15 | **+0.352** | **0.047** |
| Large firms, 15 countries | 45 | 15 | +0.273 | 0.060 |

**On a fixed sample, switching from all-firms to large-firms makes the result
weaker, not stronger** — the coefficient falls from +0.352 to +0.273 and the
p-value rises from 0.047 to 0.060. The "1.5× larger" claim (line 252) holds
only against the 27-country baseline; against the like-for-like baseline the
large-firm coefficient is **0.78×**, i.e. smaller.

The mechanism is plain once checked: **corr(Large, ALL `digital_multi`) =
0.952** on those 15 countries. The two series are near-identical, so there is
essentially no independent large-firm signal available to find.

This is structurally the same error I flagged in the Phase-B extension round,
where an n=74 controlled model was compared against an n=81 bare model and the
sample restriction was mistaken for a treatment effect. The same confound has
recurred in a new guise. The fix is the same: add the like-for-like row.

**What is actually going on** — and this deserves the "worth chasing" flag the
report currently attaches to the firm-size story:

The 15 countries that report a large-firm breakdown are **systematically
different**, and in exactly the direction that matters:

| | IN (15) | OUT (12) |
|---|---|---|
| Median GDP/capita 2024 | €25,600 | €31,745 |
| Median 2024 ETS emissions | 23.9 Mt | 6.6 Mt |
| Share of total 2024 ETS mass | **84%** | 16% |

The subset is the poorer, heavy-industry, big-emitter half of the EU — the
countries carrying 84% of the ETS mass. Restricting to them produces a
nominally significant positive coefficient **regardless of which firm-size cut
is used**. That is a far more interesting (and more worrying) pattern than a
firm-size effect, and it is a sample-selection story, not a measurement story.

It is also fragile in a familiar way. Leave-one-out across all 15 clusters on
the large-firm spec: max p = 0.139 (dropping France), min coef = +0.151 —
**dropping Bulgaria alone cuts the coefficient by 45%** (0.273 → 0.151). The
same country that drove the original EIBIS false positive is again the single
most influential observation. So this is more robust than the Bulgaria false
alarm (which died at p=0.21) but not clean.

**Recommendation:** delete the firm-size framing. Replace it with: *"Restricting
to the 15 big-emitter countries that report a large-firm breakdown produces a
nominally significant positive coefficient (ALL-firms +0.352, p=0.047; large-firms
+0.273, p=0.060) — but this is a property of the country subset, not of firm
size: the all-firms measure performs slightly better on the same countries, and
the two series correlate at 0.95. Whether the big-emitter subset genuinely
behaves differently is worth a dedicated test; it is not established here, and
dropping Bulgaria alone halves it."*

### 2. Item 1: C1's marginal p-value is an artifact of clustering at the wrong
level — BLOCKING

`phase_c_analysis.py` clusters item 1 on `NUTS_ID` — **58 region clusters** —
but the panel contains only **8 countries**, and the C2 specification's fixed
effects operate at country level. Regions within a country share national
energy prices, carbon policy, weather and industrial cycles; treating 58
regions as independent understates the standard errors.

| Spec | Clustered by region (as coded) | Clustered by country |
|---|---|---|
| C1 bare | +0.099, **p=0.058** | +0.099, **p=0.152** |
| C2 + country FE | −0.007, p=0.921 | −0.007, p=0.934 |

The report presents C1 as "the closest any model in this entire project has
come to conventional significance from below" (line 168). That distinction
disappears at the correct clustering level. Given this project's consistent
discipline about cluster-robust inference, clustering below the level at which
shocks actually operate is a notable slip.

### 3. Item 1: C1 is not merely marginal, it is wildly unstable — BLOCKING

Leave-one-country-out on C1 (region-clustered, i.e. the report's own spec):

| Dropped | coef | p |
|---|---|---|
| **ES** | **+0.195** | **0.003** |
| HU | +0.061 | 0.228 |
| BG | +0.066 | 0.194 |
| DK | +0.091 | 0.109 |
| AT | +0.101 | 0.094 |

Spain alone is **35 of 97 rows (36%)** of the panel; dropping it *doubles* the
coefficient and drops p to 0.003. Dropping Hungary or Bulgaria pushes p to
~0.2. The estimate swings across an order of magnitude of p-values depending
on which of eight countries is present.

On the coordinator's direct question: **"8 country clusters is simply too few
to trust either number" is the correct read.** The report's "collapses to
compositional, not regional" (lines 173-179) is a reasonable hypothesis but is
not something a 97-row, 8-country, 2-year panel can establish. C2's null is as
untrustworthy as C1's marginal result — it is not evidence that the regional
relationship is absent, only that this panel cannot address it.

### 4. Item 1: the biomass substitution is a directional confound correlated
with the regressor — BLOCKING (understated, not undisclosed)

The coverage-collapse claim is **confirmed exactly** — I re-derived it from the
raw 370k-row file: precisely 15 countries and 823 facilities report
`Carbon dioxide (CO2) excluding biomass`. Not a filter bug.

But the substitution is worse than "not directly comparable" (line 149-152).
Two things the report misses:

**(a) The two labels are separate fields, not nested.** `Carbon dioxide (CO2)`
(37,653 rows) and `...excluding biomass` (6,805 rows) coexist for 6,781
facility-years. Among the 8 countries in the usable panel, **only 4 (BG, DK,
RO, SI) report both** — for AT, ES, HR and HU the biogenic share is simply
**unknown**.

**(b) Where both are reported, the inflation is large and highly
country-asymmetric.** Median ratio of generic to excl-biomass CO2:

| Sweden | Finland | Denmark | Germany | BG / SI | CY, CZ, EE, MT, NL, NO |
|---|---|---|---|---|---|
| **5.61×** | **2.05×** | 1.34× | 1.27× | ~1.13× | 1.00× |

(p90 across facilities = 31.6×.) So the switch does not add biogenic CO2
uniformly — it inflates biomass-heavy economies by 100-460% and leaves others
untouched. Those are disproportionately the Nordic, high-digitalization
countries, which means **the measurement error correlates with the
regressor**. Worse, the *changes* now partly track biomass combustion swings
driven by heating demand, forestry cycles and renewable-energy policy — none of
which has anything to do with industrial digitalization.

The deviation was correctly documented rather than hidden, which is to the
Researcher's credit. But it needs the quantification above, and the conclusion
that the resulting outcome variable is not a usable proxy for fossil emissions
in a cross-country comparison.

### 5. Item 1: one coordinate corruption is misfiled as an offshore-geocoding
limitation — SHOULD-FIX

The geocoding itself is excellent (see "What's done well"). But of the 18
wrong-country facilities, the report says they are "almost entirely offshore
oil/gas platforms" (line 118). Seventeen are. The eighteenth is:

> **FJERNVARME FYN FYNSVÆRKET A/S** (Denmark) — Longitude 9.8097, Latitude
> **5.334676**, assigned `ITG1` (Sicily).

Odense sits at ~55.3°N. This is a **truncated latitude in the source data**
(55.334676 → 5.334676, leading digit lost), not an offshore point-in-polygon
limitation — a different defect class entirely. Harmless to the current panel
(the record appears only in 2015, outside the 2023-24 window), and I checked
for others: the remaining 35 far-from-centroid facilities are all legitimate
French overseas departments, correctly geocoded. So this is one bad source
record, not a pattern. But calling it offshore hides a category of error that
*would* bite if the panel window were extended, and a coordinate-plausibility
check should be added.

### 6. Item 1: composite heterogeneity is acknowledged but not acted on —
SHOULD-FIX

Of the 97 usable rows: **49 are built from only 2 components**, 3 from just 1,
43 from 4. Half the panel's regressor is a fundamentally different measurement
from the other half. The report says this plainly (lines 88-91), which is good,
but then regresses on it as if it were one variable. At minimum, report C1/C2
restricted to the 4-component rows as a robustness check, or include
`n_components` as a control.

### 7. Item 2 — no issues found

Verified and clean:
- Units are correct: `CLV20_MEUR` (chain-linked volumes, million EUR),
  `nace_r2='B-E'`, `na_item='B1G'` — the absolute level, correctly distinct
  from the percentage share already in the panel.
- The decomposition `d_log(intensity) = d_log(emissions) − d_log(VA)` is
  **exact** (verified numerically to 1e-9), not an approximation as claimed.
- Merge is correct; `d_log_va` is computed within country before differencing.
- Results replicate exactly: v2a bare +0.0686 → +0.0304; controlled +0.0809 →
  +0.0149, on the identical n=284 sample.
- Mean industrial output growth of +1.9%/yr is plausible.

The report's read — that intensity neither rescues nor undermines the Phase-B
null — is accurate and appropriately modest.

---

## What's done well

- **The geocoding is genuinely excellent, and I tried hard to break it.** I
  re-geocoded a 300-facility random sample independently against the NUTS2021
  polygons: **289/300 exact `NUTS_ID` match, and zero cases of a facility
  falling inside one polygon but being assigned another.** All 11
  non-matches were genuine `within`-failures handled by the documented
  nearest-polygon fallback, every one an offshore platform (Foinaven FPSO,
  Forties Alpha, Snorre, Schiehallion, Stella FPF) or a French overseas
  department. The overseas departments are a nice detail — Réunion → `FRY4`,
  Mayotte → `FRY5`, French Guiana → `FRY3`, Martinique → `FRY2`, all correct,
  which many geocoding pipelines get wrong.
- **The offshore-platform diagnosis is right and the handling is right.** The
  18 wrong-country cases reproduce exactly, and 17 are unambiguously North Sea
  platforms (TOTAL E&P Danmark, INEOS E&P, Sleipner Vest, Statfjord, Armada,
  Lomond, Pierce FPSO). Dropping them rather than retaining a known-bad country
  assignment is the correct call, and the reasoning given is sound.
- **The coverage-collapse claim was checked, not assumed, and is exactly
  right** — 15 countries, 823 facilities. The Researcher could easily have
  blamed a filter bug or quietly widened the definition; instead they verified
  the source limitation and documented the deviation prominently.
- **Item 1 is labeled PROVISIONAL, unprompted, in the second paragraph of the
  document**, with an explicit statement that the panel has not had the
  Reviewer sign-off every other panel in this project received. That is
  exactly the right instinct and it made this review easier.
- **Item 3 was flagged prominently rather than buried** (line 56: "Flagged
  prominently below, not buried"), and all three of the report's own caveats
  (G=15, non-random subset, still not significant) are accurate as far as they
  go. The instinct to surface it was right — the diagnosis just needs
  inverting.
- **Item 2 is exactly as clean as advertised**, including the observation that
  the log decomposition is exact rather than approximate.
- **DII's lack of a firm-size dimension was verified against the live API**
  (`size_emp = GE10` only) rather than assumed, and the resulting inability to
  cross-check item 3 against an independent measure is stated as a limitation
  rather than glossed.
- **Composite construction is transparently documented**, including the
  component-count distribution and the explicit disclaimer that it is "a
  simple, transparent composite, not a validated index."

---

## Recommended next step

**Item 3 (do this first — it changes what the project reports):**
1. Add the ALL-firms-on-15-countries row (+0.352, p=0.047) and rewrite the item
   as a sample-composition finding, not a firm-size one.
2. Report corr(Large, ALL) = 0.952 as the reason no firm-size contrast is
   detectable.
3. Add the leave-one-out table (max p=0.139; Bulgaria halves the coefficient)
   and the subset-composition table (84% of ETS mass, lower GDP, larger
   emitters).
4. Flag the big-emitter subset as the thing worth chasing, with the honest
   caveat that G=15 and Bulgaria-sensitivity make it a lead, not a result.

**Item 1:**
5. Re-cluster on country and report C1 at p=0.152; drop the "closest to
   significance in the project" claim entirely.
6. Add the leave-one-country-out table (Spain drops p to 0.003; Hungary/Bulgaria
   push it to ~0.2) and replace "collapses to compositional" with "8 country
   clusters cannot support either estimate."
7. Add the biomass ratio-by-country table and state that 4 of 8 panel countries
   have an unknown biogenic share, so the outcome is not a usable fossil-CO2
   proxy for cross-country comparison.
8. Reclassify the Fynsværket record as a source coordinate corruption and add a
   coordinate-plausibility check.
9. Add a 4-component-only robustness row.

**Item 2:** ship as-is.

Once item 3 is reframed, the project's bottom line is unchanged — no robust,
significant relationship survives correct inference anywhere — but it will
carry one genuinely interesting open lead (the big-emitter subset) instead of
one mislabeled one (firm size).

---

# Final pass — fixes applied

Both fixes verified with independent multi-seed bootstraps (4,999 reps × 5
seeds each, to separate real differences from Monte-Carlo noise).

## Verdict: **GO.** Fold Phase C in as "further confirms the null, no new signal."

### Item 1 — infeasibility framing is honest, neither under- nor overstated

Every new number reproduces:

| Check | Reported | My independent run |
|---|---|---|
| C1, country-clustered wild boot | 0.250 | **0.252** (5-seed range 0.245–0.259) |
| 4-component-only robustness | −0.021, G=6 | **−0.021, G=6** (exact) |

The framing is calibrated correctly in both directions:

- **Not understated.** All three compounding problems are stated as problems,
  not caveats: the clustering correction is shown as a before/after table
  (0.066 → 0.250), Spain's leave-one-out is reported with its *opposite*-direction
  instability (+0.195, p=0.003) rather than only the p-inflating drops, and the
  biomass issue is labeled a confound with the country-asymmetry table (Sweden
  5.61×, Finland 2.05×) plus the disclosure that 4 of 8 panel countries have an
  entirely unknown biogenic share.
- **Not overstated.** It concludes the *panel* is infeasible, not that no
  regional relationship exists — the correct and narrower claim. The closing
  argument is the right one: restricting to countries with a known biogenic
  share collapses back to the already-unusable n=15, and any other E-PRTR
  pollutant field hits the same 15-country ceiling. That demonstrates there is
  no way out with current data, rather than asserting it.
- The 4-component robustness row is included even though it helps nothing
  (G drops to 6), explicitly labeled "not decisive... included for
  completeness." Reporting a check that makes your panel look worse is the
  right instinct.

The old "closest to significance anywhere in this project" claim is fully
retired; the remaining `0.066` mentions are a retrospective reference to the
first draft, the before/after table, and a coincidental leave-one-out
coefficient.

### Item 2 — unchanged, verified clean in the previous pass

### Item 3 — reframing reproduces and is appropriately hedged

| Spec | Reported coef / p | My run (5-seed mean, range) |
|---|---|---|
| E1a ALL, 27 countries | +0.178 / 0.262 | +0.178 / 0.265 (0.252–0.275) |
| **E1b ALL, same 15** | **+0.352 / 0.057** | **+0.352 / 0.049 (0.047–0.053)** |
| E1c Large, 15 | +0.273 / 0.062 | +0.273 / 0.063 (0.060–0.064) |
| corr(ALL, Large) | 0.952 | **0.9523** |
| Drop Bulgaria | +0.151 (−45%) | confirmed |

The load-bearing ordering — **all-firms outperforms large-firms on the
identical sample** — reproduces robustly, and the firm-size framing is
correctly dropped with r=0.952 given as the mechanical reason. The
big-emitter-subset pattern is now the stated lead, with the composition table
(83.6% of ETS mass, lower median GDP, larger median emitter) and the
Bulgaria-sensitivity both in the open. "Fragile lead, not a finding" is the
right label, and explicitly connecting Bulgaria's recurrence to the project's
original false positive is a nice touch.

**One small note for whoever quotes this later:** E1b sits exactly on the 0.05
boundary. Their 0.057 and my 0.049 straddle it, which is Monte-Carlo variation
plus rep-count difference, not a discrepancy. It does not affect the "fragile
lead" framing — but the number should never be quoted as confidently
non-significant. Worth adding "p ≈ 0.05, on the threshold" rather than a bare
0.057. Cosmetic.

## Nothing left to fix

Phase C is ready to fold in. Its contribution to the project is: one refinement
confirmed infeasible with honest documentation of why, one refinement
confirming the null under an alternative outcome, and one apparent finding
correctly dissolved into a named, specific, still-open lead. The standing
conclusion — no digitalization–emissions relationship in this data survives
correct small-cluster inference at country, sector, or regional aggregation,
under raw or intensity outcomes — is unchanged and better supported.

The recurring pattern the report notes in its combined read is worth carrying
forward as the project's most transferable methodological finding: **in this
data, every marginal result across four review rounds has traced back to either
a sample-composition artifact or a single influential country — twice
Bulgaria.**
