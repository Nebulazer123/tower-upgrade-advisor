#!/usr/bin/env python3
"""Manual data entry CLI — fallback when automated extraction fails.

Usage:
    python3 scripts/manual_import.py --template output.json
    python3 scripts/manual_import.py --import input.json
    python3 scripts/manual_import.py --import input.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# Ensure the project root is importable when running as a script.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from pydantic import ValidationError  # noqa: E402

from src.data_loader import UPGRADES_PATH, save_upgrades, validate_upgrade_data  # noqa: E402
from src.models import UpgradeDatabase  # noqa: E402

# ---------------------------------------------------------------------------
# Template generation
# ---------------------------------------------------------------------------

_TEMPLATE: dict = {
    "_comment": (
        "Fill in this template with your upgrade data. "
        "Remove all '_comment' fields before importing."
    ),
    "version": "YYYY-MM-DD",
    "game_version": "0.0.0",
    "source": "manual",
    "upgrades": [
        {
            "_comment": "Copy this block for each upgrade.",
            "id": "example_upgrade",
            "name": "Example Upgrade",
            "category": "offense",
            "effect_unit": "%",
            "effect_type": "multiplicative",
            "base_value": 1.0,
            "max_level": 3,
            "display_order": 1,
            "levels": [
                {
                    "_comment": "Fill in levels 1 through max_level with increasing coin_cost",
                    "level": 1,
                    "coin_cost": 100,
                    "cumulative_effect": 1.1,
                    "effect_delta": 0.1,
                },
                {
                    "level": 2,
                    "coin_cost": 250,
                    "cumulative_effect": 1.2,
                    "effect_delta": 0.1,
                },
                {
                    "level": 3,
                    "coin_cost": 500,
                    "cumulative_effect": 1.3,
                    "effect_delta": 0.1,
                },
            ],
        },
    ],
}


def generate_template(output_path: Path) -> None:
    """Write a blank template JSON file to *output_path*."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(_TEMPLATE, indent=2) + "\n", encoding="utf-8")
    print(f"Template written to {output_path}")


# ---------------------------------------------------------------------------
# JSON import
# ---------------------------------------------------------------------------


def _strip_comments(obj: object) -> object:
    """Recursively remove keys starting with '_comment'."""
    if isinstance(obj, dict):
        return {k: _strip_comments(v) for k, v in obj.items() if not k.startswith("_comment")}
    if isinstance(obj, list):
        return [_strip_comments(item) for item in obj]
    return obj


def import_json(input_path: Path) -> UpgradeDatabase:
    """Parse and validate a user-filled JSON file, returning an UpgradeDatabase."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    cleaned = _strip_comments(raw)
    try:
        db = UpgradeDatabase.model_validate(cleaned)
    except ValidationError as exc:
        print("Pydantic validation failed:", file=sys.stderr)
        for err in exc.errors():
            loc = " -> ".join(str(p) for p in err["loc"])
            print(f"  {loc}: {err['msg']}", file=sys.stderr)
        sys.exit(1)
    return db


# ---------------------------------------------------------------------------
# CSV import
# ---------------------------------------------------------------------------

_CSV_COLUMNS = [
    "upgrade_id",
    "name",
    "category",
    "effect_unit",
    "effect_type",
    "base_value",
    "max_level",
    "display_order",
    "level",
    "coin_cost",
    "cumulative_effect",
    "effect_delta",
]


def import_csv(input_path: Path) -> UpgradeDatabase:
    """Parse a CSV file and construct an UpgradeDatabase.

    Each row represents one level of one upgrade. Rows are grouped by
    ``upgrade_id``; upgrade-level metadata (name, category, …) is taken
    from the first row in each group.
    """
    with input_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            print("Error: CSV file is empty or has no header row.", file=sys.stderr)
            sys.exit(1)

        missing = set(_CSV_COLUMNS) - set(reader.fieldnames)
        if missing:
            print(f"Error: CSV is missing required columns: {sorted(missing)}", file=sys.stderr)
            sys.exit(1)

        rows = list(reader)

    if not rows:
        print("Error: CSV contains no data rows.", file=sys.stderr)
        sys.exit(1)

    # Group rows by upgrade_id, preserving encounter order.
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        uid = row["upgrade_id"].strip()
        groups.setdefault(uid, []).append(row)

    upgrades = []
    for uid, group in groups.items():
        first = group[0]
        levels = []
        for r in group:
            levels.append(
                {
                    "level": int(r["level"]),
                    "coin_cost": int(r["coin_cost"]),
                    "cumulative_effect": float(r["cumulative_effect"]),
                    "effect_delta": float(r["effect_delta"]),
                }
            )
        levels.sort(key=lambda lv: lv["level"])

        upgrades.append(
            {
                "id": uid,
                "name": first["name"].strip(),
                "category": first["category"].strip(),
                "effect_unit": first["effect_unit"].strip(),
                "effect_type": first["effect_type"].strip(),
                "base_value": float(first["base_value"]),
                "max_level": int(first["max_level"]),
                "display_order": int(first["display_order"]),
                "levels": levels,
            }
        )

    raw_db = {
        "version": "manual-csv-import",
        "game_version": "unknown",
        "source": "csv-import",
        "upgrades": upgrades,
    }

    try:
        db = UpgradeDatabase.model_validate(raw_db)
    except ValidationError as exc:
        print("Pydantic validation failed after CSV conversion:", file=sys.stderr)
        for err in exc.errors():
            loc = " -> ".join(str(p) for p in err["loc"])
            print(f"  {loc}: {err['msg']}", file=sys.stderr)
        sys.exit(1)
    return db


# ---------------------------------------------------------------------------
# Shared validation + save
# ---------------------------------------------------------------------------


def validate_and_save(db: UpgradeDatabase, dest: Path) -> None:
    """Run business-rule validation and persist to *dest* if clean."""
    result = validate_upgrade_data(db)

    if result.warnings:
        for w in result.warnings:
            print(f"WARNING: {w}", file=sys.stderr)

    if not result.ok:
        print("Validation errors — data NOT saved:", file=sys.stderr)
        for e in result.errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    dest.parent.mkdir(parents=True, exist_ok=True)
    save_upgrades(db, dest)
    print(f"Validated and saved {len(db.upgrades)} upgrades to {dest}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manual data entry tool for Tower Upgrade Advisor.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--template",
        metavar="OUTPUT",
        type=Path,
        help="Generate a blank template JSON file at OUTPUT.",
    )
    group.add_argument(
        "--import",
        dest="import_file",
        metavar="INPUT",
        type=Path,
        help="Import a filled JSON or CSV file and save to data/upgrades.json.",
    )
    parser.add_argument(
        "--output",
        metavar="DEST",
        type=Path,
        default=None,
        help=f"Override destination path (default: {UPGRADES_PATH}).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.template is not None:
        generate_template(args.template)
        return

    input_path: Path = args.import_file
    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        db = import_csv(input_path)
    elif suffix == ".json":
        db = import_json(input_path)
    else:
        print(
            f"Error: unsupported file extension '{suffix}'. Use .json or .csv.",
            file=sys.stderr,
        )
        sys.exit(1)

    dest = args.output or UPGRADES_PATH
    validate_and_save(db, dest)


if __name__ == "__main__":
    main()
