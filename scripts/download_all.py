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
    "download_eurostat_dii_regional.py",
    "download_eurostat_industry_va_absolute.py",
    "download_nuts2_boundaries.py",
]
# NOTE: the large E-PRTR facility-level file needed for the NUTS2 regional
# panel (analysis/phase_c_analysis.py, panel v3) is NOT fetched by this
# script -- it requires `python scripts/download_eprtr.py --all` (or the
# single-file fetch documented in analysis/phase_c_analysis.md), same as
# the other large facility-level E-PRTR tables.

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def main() -> None:
    for name in SCRIPTS:
        print(f"\n=== {name} ===")
        runpy.run_path(str(SCRIPT_DIR / name), run_name="__main__")


if __name__ == "__main__":
    main()
