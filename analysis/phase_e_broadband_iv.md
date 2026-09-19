# Phase E: can broadband-infrastructure rollout instrument digitalization (DII)?

**Verdict: infeasible. The instrument is relevant in the naive specification but not excludable, so the design cannot identify anything. No headline second stage is reported.**

The case rests on exclusion, not on weak relevance:

1. **Relevance is adequate in the naive specification and would pass a conventional F >= 10 rule.** The best candidate (2013 NGA coverage x leave-one-out EU FTTP rollout) has F = 19.5 (G = 28, wild-cluster first-stage p = 0.009) in the Phase-D-comparable spec S1. A conventional "F >= 10 in the preferred spec" gate would be passed, and the naive IV for VA growth would be +0.127 with Anderson-Rubin set [0.02, 0.32]. I do not rest the verdict on a gate.
2. **The exclusion restriction is not credible.** The instrument is largely a development-level proxy; there is no first stage at all in the 2004+ accession economies (where Cohesion-funded rollout is the concern); household broadband can act on industry through non-firm-adoption channels; and the only significant reduced form (instrument -> industrial VA growth, wild p = 0.027) disappears once development is controlled.
3. **Supporting evidence: relevance itself is a development artefact.** F falls to 7.7 (GDPpc2013 x shock) and 4.9 (GDPpc2013 x year FE). The textbook shift-share first stage with country FE has F = 4.4 (wild p = 0.056) and unbounded AR sets. Under any development-robust specification the AR sets are uninformative, and AR is valid regardless of instrument strength.

Reproduce: `python scripts/download_eurostat_broadband.py` then `python analysis/phase_e_broadband_iv.py` (about 2 min; log in `analysis/output/phase_e_run_log.txt`; helpers `analysis/phase_e_lib.py`). Outputs: `analysis/output/phase_e_*.csv`.

## 1. Data (verified live, not assumed)

| Dataset | Content | Geography / years | Notes |
|---|---|---|---|
| `isoc_cbs` | % households covered by >2 (2013-20 only), >30, >100 Mbps (2013-25), >1 Gbps (2019-25) | 31 countries, **country level only**, total territory only | 403 cells per tier (2 Mbps: 248) |
| `isoc_cbt` | coverage by technology, total and rural (`terrtypo=DEG3`) | 31 countries, 2013-25 | DSL, BB_FX, NGA, SATL present throughout. FTTP 30-31 countries. In the 2013 baseline year DOCSIS 3.0 is missing for **EL, IS, IT** (over the whole panel only IT is absent entirely), VDSL for BG, LT, PT. 5G starts 2020, VHCN 2019, DOCSIS 3.1 and VDSL2 vectoring 2021. Rural (DEG3) is thinner (e.g. DOCSIS 20 countries in 2013) |
| `isoc_r_broad_h` | share of households with broadband **access** (`PC_HH`, `PC_HH_IACC`), 361 NUTS units, 2006-21 | regional | This is take-up (demand side), not infrastructure supply, so it cannot be an instrument. Fetched and documented, not used |

Regional infrastructure coverage does not exist in these Eurostat tables, so the Phase-C regional panel cannot be used. DII (`dii_high_share_manufacturing`) exists only for 2015-25 (levels with year FE, never differenced), so the 2013 baselines pre-date the endogenous variable.
Outcomes follow Phase D item 2 (G5): `d_log_va` (log industrial VA first difference; the file has no year gaps, so the contiguity guard in `phase_e_lib.contiguous_diff` is a no-op here) and `d_log_emissions` (verified EU-ETS, v2a panel).
"EU-15" means `accession_2004plus == 0` as in Phase D (it may include non-EU-15 non-accession countries such as NO, UK).
Estimation sample: rows with both outcomes, DII, controls and instrument non-missing (n = 284, G = 28), the same rows for OLS, first stage, reduced form and IV. Phase D's n = 257 additionally required energy data; the difference in OLS (+0.066 vs +0.073) is entirely that sample difference.

## 2. Instrument candidates (14 tried, all in `phase_e_first_stage_all_candidates.csv`)

Shift-share form `Z_it = baseline_i(2013 coverage) x shock_t`, where the shock is the leave-one-out mean over the other countries in `isoc_cbt`/`isoc_cbs` (all 31, including CH, IS, NO, UK) of newer-technology coverage (FTTP, or >100 Mbps). With year FE the shock's main effect is absorbed, so this is baseline x common time pattern, close to baseline x trend: identification is largely cross-sectional in the baseline.

Baselines: NGA (VDSL + DOCSIS 3.0 + FTTP), VDSL, DOCSIS 3.0 (missing left as NaN; zero-fill for EL/IT as a sensitivity, `DOCSISz`), DSL, >100 Mbps. Also the rural-vs-total NGA gap and 2-year-lagged >100 Mbps coverage (both time-varying, not predetermined). A VHCN shock was dropped (sample shrinks to 2021+). A "non-fibre NGA" baseline (NGA minus FTTP) tried in an earlier draft was **removed**: NGA is a union, so subtraction is wrong where fibre and cable overlap (LT 2013: NGA = FTTP = 48.7 with 42.8% cable would give 0) and it needed an imputed value for CY. No inference is drawn about the source of NGA's strength from it.

Selection caveat: the "primary" `Z_NGAxFTTP` was picked for having the highest first-stage F among 14 candidates, which is optimistic. The a-priori classic legacy-cable instrument (DOCSIS 3.0, NaN) has F = 4.9 on n = 265, G = 26; the zero-filled version has F = 18.7 on n = 284, G = 28, so that contrast mixes the zero-fill with a sample change.

## 3. First stage

CR1 cluster-robust Wald F by country, reference F(1, G-1); with one instrument the Kleibergen-Paap rk-F equals it. **When the parameter count k exceeds the number of clusters G, the CR1 covariance is rank-deficient and F is optimistic; such cells are flagged `cr1_reliable = False` and should not be cited.** The wild-cluster bootstrap p for the same coefficient (1999 draws, Rademacher, restricted, fixed seed) is the more trustworthy statistic.

S1 = year FE + dGDPpc growth + accession dummy + energy-shock exposure (Phase D G5). S2 = S1 + GDPpc(2013) x EU-FTTP shock. S3 = S1 + GDPpc(2013) x year FE. S4 = country FE + year FE + dGDPpc + energy-shock (no accession dummy, absorbed). S5 = S4 + GDPpc(2013) x year FE.

`Z_NGAxFTTP` (`phase_e_first_stage_wild_bootstrap.csv`):

| Sample / spec | n, G, k | F (CR1) | p (CR1) | p (wild) | CR1 reliable? |
|---|---|---|---|---|---|
| all / S1 | 284, 28, 15 | 19.5 | 0.0001 | 0.009 | yes |
| all / S2 | 284, 28, 16 | 7.7 | 0.010 | 0.034 | yes |
| all / S3 | 284, 28, 26 | 4.9 | 0.036 | 0.064 | yes (k/G = 0.93) |
| all / S4 country FE | 284, 28, 41 | 4.4 | 0.046 | 0.056 | **no (k > G)** |
| all / S5 | 284, 28, 52 | 1.1 | 0.31 | 0.33 | **no** |
| EU-15 / S1 | 155, 15, 14 | 20.4 | 0.0005 | 0.018 | borderline (k/G = 0.93) |
| EU-15 / S2 | 155, 15, 15 | 14.9 | 0.002 | 0.018 | borderline (k = G) |
| EU-15 / S3 | 155, 15, 25 | 12.1 | 0.004 | 0.027 | **no (k > G)** |
| 2004+ / S1-S3 | 129, 13, 14-25 | 0.4 / 0.3 / 0.7 | | 0.80 / 0.60 / 0.40 | **no** (irrelevant regardless) |

Read F = 12.1 for EU-15/S3 as **not** evidence of EU-15 strength: the CR1 F is over-stated there (CR1 p 0.004 vs wild p 0.027) and the corresponding AR sets are optimistic. Even at face value F = 12 with G = 15 is below the Stock-Yogo 10% size-distortion cutoff (16.4) for a just-identified model. The full-sample F = 19.5 is also only modestly above 16.4, with 28 clusters.

Other candidates, full sample S1 / S3 F: NGA x >100 Mbps 17.8 / 4.4; DOCSIS(zero-filled) x FTTP 18.7 / 5.5; >100 Mbps baseline x FTTP 10.2 / 1.2; VDSL x FTTP 3.4 / 0.0; DOCSIS(NaN) x FTTP 4.9 / 1.4; DSL 0.6 / 0.6; rural gap 0.4 / 6.2; lagged coverage 2.8 / 0.2. Only baseline-NGA-type instruments (and DOCSIS with zero-fill) clear 10 in S1.

Ex-post gate used in code: F >= 10 in S3 for both the full sample and EU-15 (0 of 14 pass; `phase_e_gate.csv`). This was written after seeing the S1 table and, given the k > G problem, EU-15/S3 could not be relied on anyway. It is descriptive only; the verdict does not depend on it (see top).

## 4. Exclusion-restriction scrutiny (the crux)

The restriction (rollout affects outcomes only via firm digital adoption) is untestable. Evidence and plausibility:

1. **Cohesion funding / convergence (accession split).** The instrument has no first stage among 2004+ accession economies (F 0.3-0.7; wild p 0.4-0.8, all specs). Where high 2013 fibre coverage exists in poorer new member states (LT, LV, RO, BG), it plausibly reflects greenfield or publicly co-financed builds tied to the accession/convergence process, the same confound that undermined the Phase-D growth result. I did not test this: `data/raw/cohesion/digital_investment_2014_2020.csv` exists in the repo (used in Phase D item 1) but a proper per-capita check was left for later. A crude unnormalised cut by the Reviewer was directionally consistent but too crude to cite.
2. **Baseline coverage tracks development.** 2013 NGA coverage correlates 0.39 with log GDPpc(2013) (R2 0.15; 0.31 with an EU-15 dummy); VDSL 0.45. First-stage strength falls from 19.5 (S1) to 7.7 (S2) to 4.9 (S3), and to 4.4 with country FE. The first-stage coefficient halves (0.40 -> 0.20) from S1 to S3, so this is a change in the estimate, not merely lost precision.
3. **Reduced form vs development.** VA growth on the instrument (all, S1) = +0.051, wild p = 0.027. With GDPpc2013 x shock: +0.011 (p = 0.63); x year FE: -0.006 (p = 0.78). The only significant reduced form vanishes with the development control, consistent with Phase D's convergence reading. Emissions reduced form: -0.02 / -0.07 / -0.06, never significant (wild p 0.24-0.57).
4. **Non-firm-adoption channels.** Household broadband coverage can raise industrial VA through demand, remote work, services and telecom/network construction, and through sectoral composition (cable-rich, service-heavy economies) that also drives emissions. Coverage is % of households, not industrial sites, so it is also a noisy proxy for what firms can buy.
5. **Pre-period falsification** (weak, mildly reassuring): baseline coverage does not predict 2006-13 mean industrial VA growth (28 countries, HC3 p > 0.3, with or without EU-15 and GDPpc controls). It says nothing about the post-2015 channel and has little power.
6. **Identification is cross-sectional.** The shock is close to a common trend, so the design inherits every cross-country level confound (institutions, GDP, industrial structure) and has none of the within-country variation that makes shift-share attractive.

**Plausibility assessment:** not credible for the full sample; at best conditionally plausible in EU-15 after development controls, where inference is unreliable (k > G) and CIs are uninformative. No identification is claimed.

## 5. Results

### 5.1 No headline second stage

### 5.2 Diagnostic-only (NOT results; `phase_e_diagnostic_2sls.csv`) for `Z_NGAxFTTP`

OLS p = wild-cluster bootstrap (restricted, 1999 draws). RF = reduced form. IV = just-identified 2SLS. AR = Anderson-Rubin 95% set on a grid [-3, 3], step 0.01, F(1, G-1) reference (not bootstrapped). The IV Wald t-test is stored in the CSV but not reported here: at these F/G it is not reliable. Cells with k > G (marked *) have rank-deficient CR1 covariance, so their AR sets are optimistically narrow.

| Outcome | Sample / spec | FS F | OLS (p_wild) | RF (p_wild) | IV | AR 95% |
|---|---|---|---|---|---|---|
| VA growth | all / S1 | 19.5 | +0.066 (0.008) | +0.051 (0.027) | +0.127 | [0.02, 0.32] |
| VA growth | all / S2 | 7.7 | +0.023 (0.31) | +0.011 (0.63) | +0.043 | [-0.19, 0.34] |
| VA growth | all / S3 | 4.9 | +0.011 (0.60) | -0.006 (0.78) | -0.028 | [-0.84, 0.42] |
| VA growth | all / S4 country FE * | 4.4 | +0.028 (0.47) | +0.114 (0.12) | +0.341 | unbounded, [-0.06, 3.0+] |
| VA growth | all / S5 * | 1.1 | +0.030 (0.55) | +0.111 (0.28) | +0.610 | unbounded |
| VA growth | EU-15 / S3 * | 12.1 | -0.002 (0.92) | +0.012 (0.69) | +0.033 | [-0.17, 0.30] (optimistic) |
| Emissions | all / S1 | 19.5 | +0.081 (0.32) | -0.022 (0.57) | -0.055 | [-0.34, 0.13] |
| Emissions | all / S3 | 4.9 | +0.076 (0.46) | -0.059 (0.37) | -0.293 | unbounded/disjoint |
| Emissions | all / S4 * | 4.4 | +0.290 (0.006) | +0.227 (0.54) | +0.681 | unbounded |
| Emissions | EU-15 / S3 * | 12.1 | +0.063 (0.51) | -0.004 (0.95) | -0.011 | [-0.61, 0.32] (optimistic) |
| both | 2004+ (any spec) * | 0.3-0.7 | | | | unbounded |

Reading: the only "significant" IV (VA growth, all/S1: +0.127, AR [0.02, 0.32]) is the one that disappears under any development control, i.e. it is a development-level artefact, not evidence that digitalization raises VA growth. The country-FE first stage (F = 4.4, the textbook shift-share form, which removes cross-country levels entirely and so does not rely on the GDPpc x year-FE control) leaves the AR sets unbounded, so the "over-demanding control masks a real signal" worry does not rescue the design. Even at face value (and optimistic) the EU-15/S3 AR sets include zero, include the OLS estimates, and cannot distinguish positive, zero and mildly negative effects. The IV design says nothing about causal direction. (Country-FE OLS for emissions is +0.29, wild p = 0.006, a within-country association that is not the subject here and is not instrumented credibly.) No spec shows an emissions effect from the instrument.

### 5.3 Robustness (first stage; CR1 F, so read with the k > G caveat)
- Leave-one-country-out (full sample, S1): F 12.2-24.0 (lowest dropping IT, NL, MT); RF t 2.0-2.8. In S3: F 2.1-7.3 in every draw, RF t -0.75 to 0.18. No single country creates or destroys the pattern; the problem is structural.
- Within EU-15, S3 (k > G, optimistic): F 6.6-12.5; below 10 when dropping NL (6.6), BE (7.3), IT (8.1) or ES (9.3); IV for VA ranges -0.006 to 0.086.
- The accession split was tested by separate sub-sample first stages, not only an interaction.

## 6. Limitations

- G = 28 (15 / 13 in the splits). CR1 F and AR sets are rank-deficient in cells with k > G (flagged). Wild bootstrap is used for OLS, reduced-form and first-stage p-values; AR sets are not bootstrapped.
- Instrument picked on first-stage F from 14 candidates (forking paths); the ex-post gate was set after seeing the S1 table. The verdict does not rely on either.
- Coverage is household-based and country-level only; DII and outcomes are country-level, so no sector or regional variation can be used.
- Controls (dlog GDPpc, energy-shock exposure) come from Phase D and may be bad controls; kept for comparability.
- OLS here (+0.066 VA, +0.081 emissions) is on n = 284, not Phase D's n = 257.
- Cohesion-fund correlation with baseline fibre was not properly tested.

## 7. What this does NOT show

- It does **not** show digitalization has no causal effect on VA growth or emissions; the design is uninformative (wide or unbounded AR sets).
- It does **not** show digitalization causes industrial VA growth; the positive naive IV shares the development confound.
- It does **not** resolve the reverse-causality / convergence question from Phase D; direction remains unidentified.
- It does not show rural or legacy broadband is irrelevant to firm digitalization, only that country-level Eurostat coverage with this shift-share form cannot support an instrument.
- A more promising design needs sub-national or firm-level infrastructure variation (regional fibre rollout timing, distance to legacy exchanges/cable head-ends, tender/voucher rule discontinuities) plus enterprise-level adoption data, none of which are in this repository.
