# EIBIS Firm-Level Microdata — Research Proposal (Draft)

**Status: DRAFT — needs your review, personal/institutional details, and a CV before sending.**
Send to: **EIBIS_data_access@eib.org** (reviewed by a committee chaired by the EIB Economics
Department director; see `docs/data_sources.md` and
https://www.eib.org/en/publications-research/economics/surveys-data/eibis/about/index).

Fields marked `[FILL IN]` need your input. Everything else is drafted from the analysis
already completed in this repo and can be used close to as-is, or trimmed/edited freely —
this is a starting point, not a final draft.

---

## 1. Applicant(s)

- **Name(s):** [FILL IN]
- **Institutional affiliation:** [FILL IN]
- **Position/role:** [FILL IN]
- **Contact email:** [FILL IN]
- **CV(s):** attach separately, per EIBIS's stated requirement.
- **Collaborators (if any):** [FILL IN — EIBIS microdata access is granted "for collaborative
  projects aiming at a publication," so note co-authors or institutional partners here if
  applicable]

## 2. Project title

**Twin Transformation: Does Digitalization Predict Verified Emissions Reduction, or Only
Disclosed Climate Ambition? A Firm-Level Test**

## 3. Background and motivation

The EU's "twin transformation" agenda treats the digital and green transitions as mutually
reinforcing. This is a plausible but largely untested empirical claim at firm level: does a
firm's digital-technology adoption predict a reduction in its *actual, independently verified*
emissions, or only in its *disclosed* climate targets and investment intentions — measures
that are self-reported and not independently audited?

We have already completed an extensive country- and sector-level test of this question using
open data (EU ETS verified emissions, EIBIS *aggregate* survey results, Eurostat's Digital
Intensity Index), summarized in the attached technical report [FILL IN: attach
`analysis/report/TWIN_Analytics_First_Findings.pdf`, or reference the GitHub repository at
https://github.com/FIMPlank/TWIN_Analytics]. That analysis — built and independently reviewed
across five rounds of researcher/reviewer scrutiny, with small-cluster-robust inference,
placebo/timing checks, and a convergence-economics robustness test — found **no significant
relationship** between digitalization intensity and verified-emissions change at the country
or industrial-sector level, across an 11-year panel and two independent digitalization
measures.

This null result is informative but structurally limited: **every variable in that analysis is
a country- or sector-wide average.** A country-level correlation (or its absence) cannot
distinguish between two very different underlying realities — (a) digitalizing firms and
emissions-cutting firms are genuinely unrelated populations, or (b) they are the *same* firms,
but the relationship is invisible at the aggregate level because it is diluted by averaging
across firms that never digitalized and firms that were never significant emitters in the
first place. Only firm-level microdata that observes *the same firms* on both a digitalization
measure and a climate/environmental-investment measure can distinguish these.

EIBIS is, to our knowledge, the best-positioned dataset to close this gap: a panel since 2016,
~13,000 EU+US firms/year, with **both a digitalization module and a climate/environmental
investment module administered to the same respondents in the same survey wave** — precisely
the co-observation that no open dataset we have found provides.

## 4. Research objectives and hypotheses

**RQ1 (primary):** At the firm level, does digital-technology adoption intensity predict a
firm's *disclosed climate investment or GHG-target-setting behavior* (EIBIS's own climate
module — the "disclosure" side)?

**RQ2 (primary, the gap this proposal is designed to close):** Where EIBIS firm identifiers
can be linked to EU ETS installation-level *verified* emissions data (via the JRC-EU-ETS-FIRMS
crosswalk to ORBIS firm IDs — already inspected in our open-data work, but not linkable to
EIBIS without this access), does digitalization intensity predict *actual verified emissions
change*, not just disclosed intent?

**H1:** Firm-level digitalization intensity is positively associated with disclosed climate
investment/target-setting (a relatively low bar, testing survey-response consistency).

**H2 (the substantive test):** Firm-level digitalization intensity is associated with
*verified* emissions reduction, net of firm size, sector, and country fixed effects.

**H3 (the disclosure-reality gap, the project's central question):** The disclosure-side
association (H1) is stronger/more robust than the verified-outcome association (H2) — i.e.,
digitalization predicts what firms *say* about their climate ambitions more reliably than what
independently audited data shows they *do*.

Our country-level prior (a robust null on the verified-outcome side, not yet tested against a
disclosure-side benchmark at the same level of aggregation) is directly consistent with H3 but
cannot distinguish it from simple non-existence of any relationship. Firm-level data is
required to test H3 as stated.

## 5. Data and methodology

**Primary data requested:** EIBIS firm-level microdata (digitalization module + climate/
environmental investment module), panel years [FILL IN: specify range, e.g. 2018-2025 if
available, or match to survey waves overlapping EU ETS phase 4], EU+US coverage.

**Linked data (already open-access, already integrated into our pipeline):**
- EU ETS verified emissions (installation-level, EUTL) — already downloaded and validated in
  our repository.
- JRC-EU-ETS-FIRMS (EU ETS account holder ↔ ORBIS/Bureau van Dijk firm-ID crosswalk) — already
  downloaded; this is the linking key that would let EIBIS firm IDs be matched to verified
  ETS emissions, if EIBIS provides (or can be matched to) ORBIS/BvD firm identifiers.
- [If applicable] ORBIS financial/firmographic data, if the applicant's institution has
  separate ORBIS access: [FILL IN — do you/your institution have ORBIS access? This
  materially strengthens the proposal, since it is the remaining link needed for a complete
  firm-level chain.]

**Methodology:** Firm-level panel regression (fixed effects: firm, sector, country, year),
with the same standard of statistical rigor already demonstrated in our open-data work:
cluster-robust standard errors appropriate to the panel's cluster structure (with small-sample
corrections, e.g. wild cluster bootstrap, if the number of clusters is limited), a
placebo/timing check (does future digitalization "predict" past emissions? — a check for
reverse causality), and controls for firm size, sector composition, and macroeconomic
conditions (GDP growth, energy prices) drawn from the same free public sources already
integrated into our pipeline (Eurostat).

**Reproducibility and transparency:** All non-restricted code, data, and documentation for
this project are maintained in a public repository
(https://github.com/FIMPlank/TWIN_Analytics). We would maintain the same standard for any
firm-level extension, publishing all derived/aggregated results and code subject to EIBIS's
microdata confidentiality and disclosure-control requirements, and would follow EIBIS's stated
access modality (on-site/remote secure environment, as required) for any non-aggregable
output.

## 6. Expected outputs / publication plan

[FILL IN — EIBIS microdata access is stated to be granted "for collaborative projects aiming
at a publication." Specify your intended venue/format: a working paper, a submission to a
specific journal or conference, a policy report, etc. If this is an academic project, name the
target outlet or research program it sits within.]

## 7. Timeline

[FILL IN — e.g. data access requested by [DATE], analysis over [N months], draft results by
[DATE].]

---

## Notes for whoever sends this

- The EIB's own page (linked above) says access is reviewed by a committee chaired by the EIB
  Economics Department director and granted for collaborative projects aiming at publication —
  make sure Section 6 is concrete, since that appears to be a real gating criterion, not
  boilerplate.
- Attaching the existing technical report/repo as evidence of research capacity and rigor is a
  genuine strength of this application — the aggregate-level work is real, reviewed, and
  directly motivates exactly the access being requested. Don't undersell it.
- If your institution does *not* have separate ORBIS access, RQ2/H2 will need EIBIS's own
  guidance on whether their microdata already carries a usable firm identifier that maps to EU
  ETS installations, or whether a different linking strategy is needed — worth asking directly
  in the application or a follow-up email rather than assuming.
