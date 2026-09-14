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
| JRC-EU-ETS-FIRMS (firm matching) | ⏳ manual download needed | `data/raw/jrc_firms/` |
| E-PRTR / Industrial Emissions | ⏳ manual download needed | `data/raw/eprtr/` |
| EIBIS aggregate (country/sector) | ⏳ manual download needed | `data/raw/eibis/` |
| EIBIS firm-level microdata | 🔒 requires proposal to EIB | not in repo |
| Eurostat CIS microdata | 🔒 requires Eurostat accreditation | not in repo |
| German AFiD-Panel | 🔒 requires FDZ application | not in repo |
| France EACEI | 🔒 requires CASD application | not in repo |
| CSRD/ESAP disclosures | ⏳ not live until 2027 | not in repo |
| CBAM registry | ⏳ too thin to use yet | not in repo |

Three sources (JRC-FIRMS, E-PRTR, EIBIS aggregate) sit behind JS-driven data
portals with no stable bulk-download URL, so they can't be scripted as plain
HTTP downloads. Running their scripts prints the exact manual-export steps;
once you save the exported file to the path it names, re-running the script
confirms it's in place.

### EU ETS data — what's actually in `data/raw/eu_ets/`

Pulled from the [`datasets/eu-emissions-trading-system`](https://github.com/datasets/eu-emissions-trading-system)
GitHub mirror (public domain, ODC-PDDL-1.0):
- `eu-ets.csv` — verified emissions/allowances by **country × main activity ×
  year** (83,906 rows, 2005–present). This is a country/sector aggregate, not
  facility-level.
- `eu-ets-sector-emissions.csv` — the same data aggregated further, by sector
  and year only (for quick trend charts).

For **facility-level** verified emissions (matching the one-pager's
description of "the closest thing to ground-truth physical emissions data"),
use the EEA's own ETS Data Viewer/full dataset download linked in
`docs/data_sources.md` — that bulk file is much larger and sits behind the
same kind of JS portal as the other manual sources above.

## Setup

```bash
pip install -r requirements.txt
python scripts/download_all.py
```

## Next steps

1. Manually export E-PRTR, JRC-FIRMS, and EIBIS aggregate data per the
   instructions each script prints, to build out `data/raw/`.
2. Submit the EIBIS firm-level microdata proposal (see
   `docs/data_sources.md`) — this is the highest-value source and has the
   longest lead time, so start it early.
3. Build the merge/panel-construction pipeline in `data/processed/`, joining
   EU ETS verified emissions to firm identifiers via JRC-EU-ETS-FIRMS.
