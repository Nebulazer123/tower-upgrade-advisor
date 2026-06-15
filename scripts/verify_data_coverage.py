#!/usr/bin/env python3
"""Report bundled workshop-data coverage against the public calculator surface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_upgrades  # noqa: E402
from src.reference_coverage import compute_coverage  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="Exit non-zero if coverage is partial."
    )
    args = parser.parse_args()

    report = compute_coverage(load_upgrades())
    print(json.dumps(report, indent=2))
    return 1 if args.strict and not report["complete"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
