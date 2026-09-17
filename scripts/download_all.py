"""Run all dataset fetch scripts in sequence.

Usage:
    python scripts/download_all.py
"""

import runpy
import sys
from pathlib import Path

SCRIPTS = [
    "download_eu_ets.py",
    "download_jrc_firms.py",
    "download_eprtr.py",
    "download_eibis_aggregate.py",
    "download_eurostat.py",
    "download_eurostat_dii.py",
    "download_eurostat_energy_dependency.py",
]

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def main() -> None:
    for name in SCRIPTS:
        print(f"\n=== {name} ===")
        runpy.run_path(str(SCRIPT_DIR / name), run_name="__main__")


if __name__ == "__main__":
    main()
