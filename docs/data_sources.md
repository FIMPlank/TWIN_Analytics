# Datasets: Digitalization → Real vs. Reported Emissions Reduction

Reference catalogue of data sources for testing whether digitalization intensity
predicts *verified* emissions reduction, or only *disclosed* sustainability
performance. Adapted from the original research one-pager; kept in sync with
`scripts/` — each open-access source below has a corresponding fetch script.

---

## ✅ Available now — open access, no application needed

### EU ETS verified emissions (EUTL / EEA Data Viewer)
Facility-level, independently verified emissions — the closest thing to
ground-truth physical emissions data in Europe. Free, no registration.
- EEA ETS Data Viewer: https://www.eea.europa.eu/data-and-maps/dashboards/emissions-trading-viewer-1
- Full dataset download: https://www.eea.europa.eu/data-and-maps/data/european-union-emissions-trading-scheme-17
- Machine-readable mirror (GitHub datapackage): https://github.com/datasets/eu-emissions-trading-system
- **Fetch script:** [`scripts/download_eu_ets.py`](../scripts/download_eu_ets.py) — pulls the GitHub
  datapackage mirror (full installation-level panel + sector-level aggregate).

### JRC-EU-ETS-FIRMS (firm-level matching)
Maps EU ETS account holders to ORBIS/Bureau van Dijk firm identifiers — this is
what lets you connect ETS emissions to firm-level financials or survey data.
- Dataset page: https://data.jrc.ec.europa.eu/dataset/bdd1b71f-1bc8-4e65-8123-bbdd8981f116
- Note: linking onward to actual ORBIS company records requires institutional
  access to Bureau van Dijk/Moody's ORBIS (usually via university library).
- **Fetch script:** [`scripts/download_jrc_firms.py`](../scripts/download_jrc_firms.py) — the JRC Data
  Catalogue serves this behind a JS portal with no stable direct-download URL,
  so the script checks for a manually-placed file and otherwise prints the
  manual-download steps.

### E-PRTR / Industrial Emissions Portal
Facility-level pollutant releases (~33,000 sites, 91 pollutants, 33 countries),
broader than ETS. Free, no registration.
- Portal & downloads: https://industry.eea.europa.eu/industrial-emissions/dataset
- Legacy dataset page: https://www.eea.europa.eu/data-and-maps/data/member-states-reporting-art-7-under-the-european-pollutant-release-and-transfer-register-e-prtr-regulation-23
- **Fetch script:** [`scripts/download_eprtr.py`](../scripts/download_eprtr.py) — the EEA portal is a
  JS-driven catalogue without a stable bulk-CSV URL, so the script documents
  the manual export steps and checks for a manually-placed file.

### EIBIS — aggregate/country data
Country- and sector-level results (not firm microdata) on digitalization and
climate investment are open on the data portal — useful for
descriptive/contextual figures while you pursue firm-level access below.
- Data portal: https://data.eib.org/eibis/
- Download tool: https://data.eib.org/eibis/download
- **Fetch script:** [`scripts/download_eibis_aggregate.py`](../scripts/download_eibis_aggregate.py) —
  the download tool is an interactive picker with no stable direct-file URL,
  so the script documents the manual export steps and checks for a
  manually-placed file.

---

## 🔒 Reachable, but requires an application/registration first

### EIBIS firm-level microdata
~13,000 EU+US firms/year, panel since 2016, includes both a digitalization
module and a climate/environmental investment module in the same firms —
likely the best single source.
- How to get it: email a short research proposal (objectives, hypotheses,
  variables/methodology, CVs) to **EIBIS_data_access@eib.org**; a committee
  chaired by the EIB Economics Department director reviews it. Access is
  granted for collaborative projects aiming at a publication.
- Background: https://www.eib.org/en/publications-research/economics/surveys-data/eibis/about/index

### Eurostat Community Innovation Survey (CIS) microdata
Includes digital technology adoption questions, large representative EU firm
samples.
- How to get it: your institution must first be accredited by Eurostat as a
  "research entity." Two access tiers exist — anonymised **Scientific Use
  Files** (remote/on request) or confidential **Secure Use Files** (Eurostat
  SAFE Centre, Luxembourg, on-site or accredited remote access point).
- Start here: https://ec.europa.eu/eurostat/web/microdata/community-innovation-survey
- Access conditions overview: https://cros.ec.europa.eu/topic/community-innovation-survey

### German AFiD-Panel (energy use / energy establishments)
Official firm/establishment-level energy consumption data (electricity, fuel
use) from Destatis/Länder statistical offices — good physical-energy
alternative to carbon-accounting figures.
- How to get it: apply via the Forschungsdatenzentrum (FDZ) der Statistischen
  Ämter der Länder. Access via on-site guest workstation (GWAP) or controlled
  remote data processing (KDFV); Bavarian data specifically requires KDFV.
- AFiD-Modul Energieverwendung: https://www.forschungsdatenzentrum.de/de/energie/afid-modul-energieverwendung
- AFiD-Panel Energiebetriebe: https://www.forschungsdatenzentrum.de/de/energie/afid-panel-energiebetriebe
- FDZ-Länder overview/contact: https://www.konsortswd.de/datenzentren/alle-datenzentren/fdz-laender/

### France — EACEI (enquête annuelle sur les consommations d'énergie dans l'industrie)
French equivalent of the AFiD energy module.
- Access via INSEE's Réseau Quetelet / Centre d'accès sécurisé aux données
  (CASD) — application-based, similar process to the German FDZ.

---

## ⏳ Not usable yet — flagged for later, don't plan around these now

### CSRD sustainability disclosures via ESAP (European Single Access Point)
This is the "disclosed" counterpart you'd want to compare against verified
ETS figures — but it isn't operational yet.
- ESAP go-live is staggered from **10 July 2027**, with full submission
  obligations phasing in through **January 2030**.
- The ESRS XBRL taxonomy itself is still being finalized (EFRAG's updated
  taxonomy is targeted for **December 2026**).
- Until ESAP is live, CSRD data exists only as scattered PDF/iXBRL filings on
  individual company websites and national officially appointed mechanisms
  (OAMs) — usable in principle via manual/scraped collection for a small
  sample, but not as a ready-made panel.
- Tracking page: https://www.xbrl.org/news/eu-issues-esap-legislation/

### CBAM registry (carbon border adjustment mechanism)
Import-based embedded-emissions data; too thin and too narrowly scoped
(imports only, not general firm output) to serve as a panel yet. Revisit in
1–2 years once volumes accumulate.

---

## Practical note on sequencing
Given the access lead times above (EIBIS: weeks to months for proposal
review; Eurostat/FDZ: months for accreditation), the realistic fastest path
to a first analysis is: **EU ETS/EUTL (open) + JRC-EU-ETS-FIRMS matching
(open) + your own ORBIS access (if your institution has it)** — this alone
lets you build a verified-emissions panel with firm characteristics without
waiting on any external application. EIBIS or CIS microdata would then layer
in the digitalization-intensity variable once access comes through.
