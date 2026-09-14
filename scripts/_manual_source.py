"""Shared helper for sources that sit behind a JS-driven portal with no
stable direct-download URL. These scripts can't be fully automated, so they
check whether the file has already been placed manually and otherwise print
step-by-step instructions.
"""

from pathlib import Path


def check_or_instruct(expected_files: list[Path], instructions: str) -> None:
    missing = [f for f in expected_files if not f.exists()]
    if not missing:
        print("All expected files already present:")
        for f in expected_files:
            print(f"  {f}")
        return

    print("Manual download required — this source has no stable bulk-download URL.")
    print()
    print(instructions)
    print()
    print("Expected file(s) not yet found:")
    for f in missing:
        print(f"  {f}")
