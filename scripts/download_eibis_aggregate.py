"""Download EIBIS aggregate (country/sector/size-level) survey results.

Source: https://data.eib.org/eibis/
Country- and sector-level results (not firm microdata) on digitalization and
climate/energy-efficiency investment. Free, no registration. Useful for
descriptive/contextual figures while pursuing firm-level microdata access
separately (see docs/data_sources.md, "EIBIS firm-level microdata").

The download page (https://data.eib.org/eibis/download) is an interactive
indicator picker, but its "Download > File" button calls a stable JSON API
(`/eibis/download/table?i=<indicator name>`, repeatable `i=` param for
multiple indicators) that can be queried directly.

INDICATORS below covers the digitalization module and the climate/energy
module the one-pager flags as most relevant. To add more: open
https://data.eib.org/eibis/download, use the indicator search box, and copy
the exact label text into this list.

Usage:
    python scripts/download_eibis_aggregate.py
"""

import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

BASE_URL = "https://data.eib.org/eibis/download/table"

INDICATORS = [
    "Implementation of digital technologies",
    "Share of firms using generative AI tools",
    "Climate change targets for own GHG emissions",
    "Impact of climate change - Physical risk",
    "Impact of climate change - Risks associated with the transition to a net zero economy over the next five years",
    "Investment plans to tackle climate change impact",
]

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "eibis"
OUT_FILE = OUT_DIR / "eibis_aggregate.csv"


def fetch_indicator(indicator: str) -> pd.DataFrame:
    url = f"{BASE_URL}?&i={quote(indicator)}"
    print(f"Fetching '{indicator}' ...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    payload = response.json()

    columns = payload["header"]["classicHeaders"]
    value_columns = payload["header"]["graphHeaders"][0]["columns"]

    rows = []
    for row in payload["data"]:
        record = {
            "country": row.get("country"),
            "survey_wave": row.get("year"),
            "sector": row.get("sector"),
            "size": row.get("size"),
            "indicator": indicator,
        }
        for col_name, value in zip(value_columns, row.get("values", [])):
            record[col_name] = value
        rows.append(record)

    return pd.DataFrame(rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    frames = [fetch_indicator(indicator) for indicator in INDICATORS]
    combined = pd.concat(frames, ignore_index=True, sort=False)
    combined.to_csv(OUT_FILE, index=False)
    print(f"Saved {len(combined)} rows to {OUT_FILE}")
    print(
        "This is aggregate country/sector/size data, not firm microdata. "
        "See docs/data_sources.md for how to request EIBIS firm-level "
        "microdata from the EIB."
    )


if __name__ == "__main__":
    main()
