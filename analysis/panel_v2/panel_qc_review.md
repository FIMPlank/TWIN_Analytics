# Review of `analysis/panel_v2/panel_qc.md` — Phase A data-engineering QC

Independent verification pass. Unlike the previous two rounds this checks
**data and merge quality only** — no model specification.

Method: re-ran `build_panel.py`, queried the live Eurostat `isoc_e_diin2` API
directly (3,122 rows across 7 NACE codes × 8 indicator versions), and
reconciled it against the cached extract and both output panels.

---

## Verdict

**Needs two fixes before Phase-B regressions — not a rework.**

The investigative work here is the best in the project so far: the version
mapping is *exactly* right, the coverage claims are *exactly* right, and the
two flagged quirks are *correctly* characterized. I could not fault the
empirical claims the report makes.

But two things would corrupt Phase B if left as-is:

1. **A silent `fillna(0)` bug** puts a systematically downward-biased
   digitalization value into 6.8% of v2a and 11.5% of v2b usable rows, and
   the bias is non-random across sectors.
2. **Panel v2b's emissions mass sits overwhelmingly on its weakest sector
   mapping** — 62% on the one rated "low". The per-row confidence ratings are
   honest, but unweighted, so the table reads far more reassuring than the
   panel actually is.

Neither is hard to fix. Both are invisible to anyone reading the QC report as
written.

---

## Confirmed issues

### 1. `dii_high_share` treats a suppressed HI *or* VHI as zero — BLOCKING

`build_panel.py:89-93`:

```python
piv["dii_high_share"] = (piv[hi_code].fillna(0) + piv[vhi_code].fillna(0)) / 100.0
both_missing = piv[hi_code].isna() & piv[vhi_code].isna()
piv.loc[both_missing, "dii_high_share"] = np.nan
```

The guard only catches cells where **both** components are missing. Where
exactly **one** is missing — a Eurostat suppression/non-publication, not a
zero — the missing side is silently counted as 0.

This is the same defect class I flagged in round one for `digital_any`
(`analysis.py:95`), where it happened to affect 0 rows. Here it bites:

| | affected | of | share |
|---|---|---|---|
| In-force DII cells | 161 | 1,405 | 11.5% |
| Panel v2a usable rows | 21 | 311 | 6.8% |
| Panel v2b usable rows | 102 | 884 | 11.5% |

81 cells are missing HI, 80 missing VHI — and HI is normally the *larger*
component, so the HI-missing cases are badly understated. Concrete rows from
the live API:

| country | NACE | year | HI | VHI | recorded share |
|---|---|---|---|---|---|
| DE | C19 | 2022 | 57.63 | *suppressed* | 0.576 |
| FR | C19 | 2022 | *suppressed* | 13.71 | 0.137 |
| BG | C19 | 2021-25 | *suppressed* | 0.00 | **0.000** |

Mean `dii_high_share` on affected rows is **0.120** vs **0.259** on unaffected
rows — affected cells are dragged toward zero, and some of the panel's
reported `min = 0.000` is manufactured by this, not observed.

**Why this is blocking rather than cosmetic:** the missingness is not random.
It concentrates in small-population sectors (C19 refining above all) and
smaller countries — precisely the cells the report elsewhere flags as noisy.
That makes it *non-classical* measurement error correlated with sector and
country size, which biases coefficients rather than merely attenuating them.

**Fix:** set `dii_high_share = NaN` whenever *either* component is missing
(`piv[[hi,vhi]].isna().any(axis=1)`), or use `.sum(min_count=2)`. Expect to
lose ~100 v2b rows — the right trade. Then re-run the coverage tables in the
QC report, since several will change.

### 2. Panel v2b's emissions mass rests on its weakest mapping — BLOCKING
(as framing, not arithmetic)

This is the coordinator's specific question, and the suspicion is correct —
though not because the "low" rating is wrong. The rating is apt. The problem
is that the crosswalk table is presented **unweighted**, so a reader counts
"1 high, 2 medium, 3 low, 1 unmapped" and concludes the panel is a mixed bag.
Weighted by the emissions each sector actually contributes (2024, usable v2b
rows):

| ETS activity | Confidence | 2024 Mt | Share of v2b mass |
|---|---|---|---|
| **20 Combustion of fuels** | **low** | 485.2 | **61.7%** |
| 24 Pig iron/steel | medium | 93.2 | 11.9% |
| 29 Cement clinker | low-medium | 79.9 | 10.2% |
| 21 Refining | **high** | 66.4 | 8.4% |
| 42 Bulk chemicals | medium-high | 28.8 | 3.7% |
| 30 Lime/dolomite | low-medium | 19.4 | 2.5% |
| 36 Paper/cardboard | medium | 13.6 | 1.7% |

**74.4% of the panel's emissions mass sits on "low" or "low-medium" mappings.
Only 12.1% sits on "medium-high" or "high".** The single mapping the
Researcher rated weakest carries nearly two-thirds of the panel.

On the substance of combustion→D35, the report's own diagnosis is correct and
I would put it more strongly. ETS activity 20 is a **process** category — any
large combustion installation, wherever it sits organizationally. NACE D35 is
an **enterprise principal-activity** classification. A combustion unit inside
a chemical works reports ETS activity 20, but its enterprise is NACE C20 and
its digitalization is counted in C20's DII, not D35's. So `dii_high_share` for
this row measures *utility-sector digitalization* while `d_log_emissions`
measures *combustion emissions economy-wide*. These are different populations
and their correlation is unknown — plausibly near zero. Confirming the scale
of the problem: activity 20 is **57.0%** of all EU ETS stationary emissions in
2024 (588.9 of 1,033.5 Mt), so this is not a niche cell.

**Fix (pick one, state it explicitly):**
- (a) Drop ETS 20 from v2b. Leaves ~38% of mass on better-matched sectors —
  a smaller but interpretable panel. My preference.
- (b) Keep it, but require Phase B to report every result with and without
  ETS 20, never pool without sector fixed effects, and add the
  emissions-weighted confidence table above to the QC report so the weakness
  is visible.

Either way the weighted table belongs in `panel_qc.md`. Right now the report
is accurate row-by-row and misleading in aggregate.

### 3. Panel v2a pairs manufacturing-only DII with economy-wide ETS emissions
— SHOULD-FIX (document at minimum)

`build_panel.py:249` takes DII at `nace_r2 == "C"` (manufacturing,
enterprises ≥10 employees) as `dii_high_share_manufacturing`, and merges it
onto `ets_total`, which is `main_activity_code == "20-99"` — **all** stationary
installations. But combustion (57% of that total) is largely outside NACE C,
and D35 utilities are entirely outside it.

So v2a regresses total-ETS emissions change on a digitalization measure that
does not cover the majority of the emissions being explained. That is a
defensible *proxy* choice for a country-level analysis — but it is a scope
mismatch, it is not stated anywhere in the QC report, and Phase B will read
`dii_high_share_manufacturing` as "how digitalized this country is" without
realizing the denominator problem. Add one paragraph; optionally offer a
`C`+`D35` composite as an alternative column.

### 4. Minor

- **`VERSION_BREAK_YEARS` (`build_panel.py:71`) is dead code** — defined,
  never referenced. Either use it to flag cross-version differences or delete
  it, so Phase B doesn't assume version breaks are being handled automatically.
  (`dii_version` *is* correctly carried into both panels, which is the thing
  that actually matters — good.)
- **ETS activity `50` is unmapped and unmentioned** — 90.4 Mt in 2024 (8.7% of
  stationary total), with a blank `main_activity_name` in the source. Aviation's
  exclusion is documented; this one isn't. One line would close it.
- **`dii_high_share` can exceed the "≥10 employees" population** — worth one
  sentence that DII covers only enterprises with ≥10 employees, so it is not a
  population-wide digitalization measure.

---

## What's done well

This section is longer than usual because the verification work genuinely
holds up under adversarial checking.

- **The DII version mapping is exactly correct.** I pulled the live API and
  counted non-null cells by year × version independently. The result matches
  `VERSION_IN_FORCE` cell for cell: v1 → 2015-2019, v2 → 2018 + 2020, v3 →
  2021/2023/2025, v4 → 2022/2024, with 2018 the sole dual-version year. The
  v3/v4 annual alternation from 2021 is real and is genuinely non-obvious —
  I would not have predicted it. Resolving this with an explicit mapping
  rather than averaging across versions was the right call, and keeping
  version selection in the build step rather than the fetch script (so the
  raw pull stays complete) is good design.
- **The coverage-gap finding is exactly correct.** Live API confirms C19,
  C20, C22_C23 and D35 have **zero** countries before 2021, while C, C16-C18
  and C24_C25 go back to 2015. The cached extract matches the live pull at
  2,809 rows exactly. The headline — "partially, and unevenly" — is the honest
  framing, and leading the report with the disappointing half of the answer
  rather than the "11 years!" half is exactly the discipline this project has
  shown throughout.
- **Both flagged quirks are correctly characterized, and I checked both
  against the alternative hypothesis that they were bugs.**
  - *Norway −682%*: real. It is a stable multi-year series (−562 to −682 from
    2017-2024), not a one-off spike — consistent with a large net exporter, not
    a parsing error.
  - *100% cells*: real, and notably **not** a symptom of issue 1. All 13 rows
    at exactly 1.000 have *both* HI and VHI present and summing to 100 (e.g.
    BE C19 2024: HI=0.00, VHI=100.00; IE C19 2024: HI=100.00, VHI=0.00). The
    "tiny survey population" reading is right.
- **The source-file substitution is justified and correctly executed.**
  `eu-ets-sector-emissions.csv` is confirmed to be 161 rows × 3 columns
  (`sector`, `year`, `emissions_mt`) with no country dimension — it genuinely
  cannot support the requested panel. The substitution to `eu-ets.csv` avoids
  every trap from round one: `citl_information == "2. Verified emissions"`
  filter present, fund/aggregate rows excluded, and **no `20-99`/`21-99`
  rollup leakage into v2b** (verified: only the 7 specific activity codes
  appear). Deviating from the brief *and documenting why* in both the code and
  the report is the right handling.
- **Every headline number reproduces exactly**: v2a 636 rows / 311 usable / 29
  countries / 2015-2025; v2b 3,421 rows / 884 usable; the entire sector × year
  coverage table cell-for-cell; all five missingness percentages.
- **Country-code handling is consistent with prior rounds and extended
  correctly.** `GR→EL` and the new `GB→UK` are both right (Eurostat DII does
  carry `UK`); no stray `GR`/`GB` survives; IS/LI/XI correctly have no DII and
  are identified as survey non-coverage rather than treated as a bug.
- **The report refuses to run regressions** and says so explicitly, including
  declining to pre-empt the Phase-B question. Given how much pressure there
  usually is to peek, that deserves saying.

---

## Recommended next step

In order, roughly two hours total:

1. **Fix the `fillna(0)` bug** (`build_panel.py:89-93`): NaN the share when
   *either* HI or VHI is missing. Re-run both panels and regenerate every
   coverage/descriptive table in `panel_qc.md` — several counts will move.
2. **Add the emissions-weighted crosswalk table** to `panel_qc.md` §2, and
   decide explicitly whether ETS 20 stays. If it stays, write the Phase-B
   instruction into the QC report: *report all pooled results with and without
   ETS 20; never pool without sector fixed effects.*
3. **Add a paragraph to §3** on the v2a manufacturing-vs-total scope mismatch.
4. Delete or wire up `VERSION_BREAK_YEARS`; add one line on ETS activity 50
   and one on the ≥10-employee population base.

After (1) and (2), this panel is trustworthy to run Phase B on. Items 3-4 are
documentation hygiene and can ride along.

**One forward-looking note for Phase B** (not a Phase-A defect): with v3/v4
alternating every year from 2021, *every* year-over-year difference in the
2021-2025 window crosses a methodology boundary. A first-differenced
digitalization regressor is not clean anywhere in that window. The report
correctly flags this and correctly declines to resolve it — but whoever runs
Phase B should treat it as a first-order design constraint, not a footnote.

---

# Final verification — fixes applied

Re-checked against the live Eurostat API. **All four items pass.**

**1. NaN fix — correctly implemented, not just correctly counted.**
`build_panel.py:112` now uses `piv[[hi_code, vhi_code]].sum(axis=1, min_count=2)`,
which is the right idiom. Verified against the live API that the fix removes
the actual bugged cells rather than relabeling them: of the **161 one-sided
cells** the API returns, **0 remain** in `panel_v2_dii_long.csv` and **0**
remain in usable v2b. Counts land exactly where predicted (v2a 311→290, v2b
884→782). Two `dii_high_share == 0` rows survive in usable v2b — I checked
these: both have HI *and* VHI genuinely published as 0.00, so they are real
zeros, correctly retained.

**2. Emissions-weighted crosswalk table — reconciles.** Their figures are
computed on the post-fix panel (782 usable rows); mine were on the pre-fix
panel (884), which fully explains the sub-point differences:

| Bucket | My pre-fix figure | Their post-fix figure |
|---|---|---|
| low (ETS 20) | 61.7% | 61.5% |
| low + low-medium | 74.4% | 74.0% |
| high + medium-high | 12.1% | 12.3% |

Same picture, correctly recomputed on the corrected data. The table is now in
`panel_qc.md` §2 and persisted to
`analysis/output/panel_v2b_crosswalk_emissions_weighted.csv`.

**3. Both Phase-B cuts correctly built.** `panel_sector_country_year_v2.csv`
(3,421 rows / 782 usable) and `..._excl_combustion.csv` (2,785 rows / 697
usable). Verified the difference is *exactly* the 636 activity-20 rows
(3,421 − 2,785 = 636, and activity 20 has precisely 636 rows in the full
file); remaining activity codes are 21/24/29/30/36/42 with no 20; column
lists are identical. Nothing else changed.

**4. `dii_version_break_vs_prior_year` — logic correct.** I recomputed the
flag independently from the verified version-by-year mapping; it matches
row-for-row in both panels. Per-year: 2015 True (no prior DII year — a
conservative and correctly-documented choice), 2016-2019 False (continuous
v1), 2020 True (v1→v2), 2021-2025 all True (v2→v3 then v3/v4 alternating).
That is exactly right.

*Minor note:* the flag is True for **80%** of rows in *both* panels, not the
65%/79% quoted in the hand-off. The flag itself is correct; only the quoted
summary figure is off. Worth correcting wherever that number is repeated.

## Final verdict: **GO for Phase B**

Both blocking issues are properly resolved, and the two supporting artifacts
(the weighted crosswalk table and the excl-combustion cut) give Phase B what
it needs to handle the D35 weakness honestly rather than silently.

Carry these three constraints into Phase B — all documented, none blocking:

1. **Report every pooled v2b result on both cuts** (full and
   excl-combustion), and never pool across sectors without sector fixed
   effects. 61.5% of the full panel's emissions mass rests on the weakest
   mapping.
2. **A first-differenced DII regressor is unsafe across 80% of rows.** Every
   year-to-year transition from 2020 onward crosses a methodology boundary.
   Prefer levels, or restrict to same-version year pairs — there are very few.
3. **Panel v2a's `dii_high_share_manufacturing` does not cover the majority of
   the emissions it is paired with** (combustion alone is 57% of ETS
   stationary totals and sits outside NACE C). Treat it as a country-level
   proxy, and say so in any write-up.
