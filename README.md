# TWIN Analytics

Data foundation for analyzing the **Twin Transformation** (digital ↔ green):
whether digitalization intensity predicts *verified* emissions reduction, or
only *disclosed* sustainability performance.

See [`docs/data_sources.md`](docs/data_sources.md) for the full catalogue of
data sources, what's open-access vs. application-gated, and why.

## Repo structure

```
data/
  raw/            source data, one subfolder per dataset (see below)
  processed/      cleaned/merged panels produced from raw/ (not yet populated)
docs/
  data_sources.md full source catalogue with access instructions
scripts/
  download_*.py   one fetch script per open-access source
  download_all.py runs all fetch scripts in sequence
```

## Datasets currently loaded

| Source | Status | Location |
|---|---|---|
| EU ETS verified emissions (EUTL mirror) | ✅ downloaded | `data/raw/eu_ets/` |
| JRC-EU-ETS-FIRMS (firm matching) | ✅ downloaded | `data/raw/jrc_firms/` |
| E-PRTR / Industrial Emissions | ✅ downloaded (aggregates; facility tables optional) | `data/raw/eprtr/` |
| EIBIS aggregate (country/sector/size) | ✅ downloaded | `data/raw/eibis/` |
| EIBIS firm-level microdata | 🔒 requires proposal to EIB | not in repo |
| Eurostat CIS microdata | 🔒 requires Eurostat accreditation | not in repo |
| German AFiD-Panel | 🔒 requires FDZ application | not in repo |
| France EACEI | 🔒 requires CASD application | not in repo |
| CSRD/ESAP disclosures | ⏳ not live until 2027 | not in repo |
| CBAM registry | ⏳ too thin to use yet | not in repo |

All four open-access sources are fetched by real HTTP scripts — none require
manual clicking. Each catalogue/portal page itself is a JS-driven UI with no
obvious bulk-download link, but every one of them serves the actual file(s)
from a stable underlying URL once you find it (see comments at the top of
each script for how it was found).

### What's actually in `data/raw/`

- **`eu_ets/`** — country × main-activity × year verified emissions/allowances
  panel (83,906 rows, 2005–present), from the
  [GitHub EUTL mirror](https://github.com/datasets/eu-emissions-trading-system).
  This is a country/sector aggregate, not facility-level.
- **`jrc_firms/jrc_eu_ets_firms.xlsx`** — EU ETS account holder ↔ ORBIS/BvD
  firm-ID matching table (5.6MB). Connecting the BvD IDs to actual ORBIS
  company records requires separate institutional ORBIS access.
- **`eprtr/`** — E-PRTR national/sector/activity-level aggregates for air
  releases, water releases, transfers, waste transfers, and LCP energy
  (ver. 15.0, Dec. 2025). The five large **facility-level** tables
  (`F1_4`, `F2_4`, `F4_2`, `F5_2`, `F6_1` — 48–305MB each) are *not*
  downloaded by default; run `python scripts/download_eprtr.py --all` to
  pull those too (they're gitignored — see below).
- **`eibis/eibis_aggregate.csv`** — EIBIS country × sector × firm-size ×
  survey-wave results (9,510 rows) for the digitalization module
  (technology adoption, generative AI use) and climate module (GHG targets,
  transition/physical risk perception, climate investment plans). Edit
  `INDICATORS` in `scripts/download_eibis_aggregate.py` to pull more
  questions.

## Setup

```bash
pip install -r requirements.txt
python scripts/download_all.py
```

Large E-PRTR facility-level tables are not part of `download_all.py`; run
`python scripts/download_eprtr.py --all` separately if you need them (they're
gitignored, not committed).

## Explore the data

Two ways to look at the data, both free:

- **[`viz/dashboard.html`](viz/dashboard.html)** — a static, no-install
  dashboard (open the file directly in a browser, or view it published as an
  [Artifact](https://claude.ai/code/artifact/f43126fa-d0c9-45f6-ae79-b00064ee1509)):
  EU ETS emissions by sector, EIBIS digitalization vs. climate targets, and
  E-PRTR CO2 by country.
- **`app.py`** — an interactive [Streamlit](https://streamlit.io) app with
  live filters/dropdowns (country, pollutant, indicator, survey wave, year)
  and a build-your-own scatter comparing any two EIBIS indicators:
  ```bash
  streamlit run app.py
  ```
  Opens at `http://localhost:8501`. Runs entirely locally against
  `data/raw/`; no account or internet access needed once the data is
  downloaded.

## Next steps

1. Submit the EIBIS firm-level microdata proposal (see
   `docs/data_sources.md`) — this is the highest-value source and has the
   longest lead time, so start it early.
2. Build the merge/panel-construction pipeline in `data/processed/`, joining
   EU ETS verified emissions to firm identifiers via JRC-EU-ETS-FIRMS, and
   (once available) EIBIS digitalization/climate measures at the firm level.
3. If facility-level granularity is needed beyond the EU ETS country/sector
   aggregate, pull the EEA's own facility-level ETS bulk file (linked in
   `docs/data_sources.md`) or the E-PRTR facility tables (`--all` above).
