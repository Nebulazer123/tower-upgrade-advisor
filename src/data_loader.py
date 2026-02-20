"""Data loading, validation, and persistence for upgrade data."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.models import UpgradeDatabase, UpgradeDefinition

__all__ = [
    "load_upgrades",
    "save_upgrades",
    "validate_upgrade_data",
    "ValidationResult",
    "DATA_DIR",
    "UPGRADES_PATH",
]

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
UPGRADES_PATH = DATA_DIR / "upgrades.json"


class ValidationResult:
    """Collected validation errors and warnings."""

    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def summary(self) -> str:
        lines = []
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)}):")
            for e in self.errors:
                lines.append(f"  - {e}")
        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  - {w}")
        if self.ok and not self.warnings:
            lines.append("All checks passed.")
        return "\n".join(lines)


def load_upgrades(path: Path | None = None) -> UpgradeDatabase:
    """Load and validate upgrade data from JSON file.

    Raises FileNotFoundError if file missing, ValidationError if data invalid.
    """
    p = path or UPGRADES_PATH
    if not p.exists():
        raise FileNotFoundError(f"Upgrade data not found: {p}")

    raw = json.loads(p.read_text(encoding="utf-8"))
    return UpgradeDatabase.model_validate(raw)


def save_upgrades(db: UpgradeDatabase, path: Path | None = None) -> None:
    """Save upgrade data to JSON file with atomic write."""
    p = path or UPGRADES_PATH
    p.parent.mkdir(parents=True, exist_ok=True)

    tmp = p.with_suffix(".tmp")
    tmp.write_text(
        db.model_dump_json(indent=2),
        encoding="utf-8",
    )
    tmp.rename(p)


def validate_upgrade_data(db: UpgradeDatabase) -> ValidationResult:
    """Run comprehensive validation checks on upgrade data.

    This goes beyond Pydantic's model validation to check cross-field
    business rules and data integrity.
    """
    result = ValidationResult()

    # --- Top-level checks ---
    if not db.upgrades:
        result.error("No upgrades in database")
        return result

    # --- Uniqueness checks ---
    ids_seen: set[str] = set()
    names_seen: set[str] = set()
    order_seen: dict[str, set[int]] = {}

    for upgrade in db.upgrades:
        # Duplicate ID
        if upgrade.id in ids_seen:
            result.error(f"Duplicate upgrade ID: {upgrade.id}")
        ids_seen.add(upgrade.id)

        # Duplicate name
        if upgrade.name in names_seen:
            result.warn(f"Duplicate upgrade name: {upgrade.name}")
        names_seen.add(upgrade.name)

        # Duplicate display_order within category
        cat_orders = order_seen.setdefault(upgrade.category, set())
        if upgrade.display_order in cat_orders:
            result.warn(f"Duplicate display_order {upgrade.display_order} in {upgrade.category}")
        cat_orders.add(upgrade.display_order)

        # --- Per-upgrade checks ---
        _validate_upgrade(upgrade, result)

    # --- Expected count check ---
    if len(db.upgrades) < 10:
        result.warn(f"Only {len(db.upgrades)} upgrades — expected at least 20-30")

    # --- Category coverage ---
    categories = {u.category for u in db.upgrades}
    for expected in ("attack", "defense", "utility"):
        if expected not in categories:
            result.warn(f"Missing expected category: {expected}")

    return result


def _validate_upgrade(upgrade: UpgradeDefinition, result: ValidationResult) -> None:
    """Validate a single upgrade's level data."""
    uid = upgrade.id

    # Level count
    if len(upgrade.levels) != upgrade.max_level:
        result.error(f"{uid}: level count {len(upgrade.levels)} != max_level {upgrade.max_level}")

    if not upgrade.levels:
        result.error(f"{uid}: no levels defined")
        return

    # Level continuity (1, 2, 3, ..., max_level)
    expected_levels = list(range(1, upgrade.max_level + 1))
    actual_levels = [lv.level for lv in upgrade.levels]
    if actual_levels != expected_levels:
        missing = set(expected_levels) - set(actual_levels)
        extra = set(actual_levels) - set(expected_levels)
        if missing:
            result.error(f"{uid}: missing levels: {sorted(missing)}")
        if extra:
            result.error(f"{uid}: unexpected levels: {sorted(extra)}")

    # Numeric integrity
    for lv in upgrade.levels:
        if not _is_finite(lv.coin_cost):
            result.error(f"{uid} level {lv.level}: coin_cost is not finite")
        if not _is_finite(lv.cumulative_effect):
            result.error(f"{uid} level {lv.level}: cumulative_effect is not finite")
        if not _is_finite(lv.effect_delta):
            result.error(f"{uid} level {lv.level}: effect_delta is not finite")

        if lv.coin_cost <= 0:
            result.error(f"{uid} level {lv.level}: coin_cost must be positive, got {lv.coin_cost}")

    # String leak check — this catches data like "1.2M" that was parsed as a string
    # (Pydantic would catch this at model validation, but we check raw data too)

    # Monotonicity: costs must be strictly increasing
    for i in range(1, len(upgrade.levels)):
        prev = upgrade.levels[i - 1]
        curr = upgrade.levels[i]
        if curr.coin_cost <= prev.coin_cost:
            result.error(
                f"{uid}: cost not increasing at level {curr.level} "
                f"({prev.coin_cost} -> {curr.coin_cost})"
            )

    # Monotonicity: cumulative_effect must be non-decreasing
    for i in range(1, len(upgrade.levels)):
        prev = upgrade.levels[i - 1]
        curr = upgrade.levels[i]
        if curr.cumulative_effect < prev.cumulative_effect:
            result.warn(
                f"{uid}: cumulative_effect decreased at level {curr.level} "
                f"({prev.cumulative_effect} -> {curr.cumulative_effect})"
            )

    # Effect delta consistency
    for i, lv in enumerate(upgrade.levels):
        if i == 0:
            expected_delta = lv.cumulative_effect - upgrade.base_value
        else:
            expected_delta = lv.cumulative_effect - upgrade.levels[i - 1].cumulative_effect
        if abs(lv.effect_delta - expected_delta) > 1e-6:
            result.warn(
                f"{uid} level {lv.level}: effect_delta {lv.effect_delta} != "
                f"expected {expected_delta:.6f}"
            )


def _is_finite(value: int | float) -> bool:
    """Check that a numeric value is finite (not NaN or Inf)."""
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def validate_raw_json(data: Any) -> ValidationResult:
    """Validate raw JSON data before Pydantic parsing.

    Catches issues like string numbers ("1.2M") that Pydantic might coerce.
    """
    result = ValidationResult()

    if not isinstance(data, dict):
        result.error("Top-level data must be a dict")
        return result

    upgrades = data.get("upgrades")
    if not isinstance(upgrades, list):
        result.error("'upgrades' must be a list")
        return result

    for i, item in enumerate(upgrades):
        if not isinstance(item, dict):
            result.error(f"upgrades[{i}] must be a dict")
            continue

        name = item.get("name", f"upgrades[{i}]")
        levels = item.get("levels")
        if not isinstance(levels, list):
            result.error(f"{name}: 'levels' must be a list")
            continue

        for j, lv in enumerate(levels):
            if not isinstance(lv, dict):
                result.error(f"{name} levels[{j}]: must be a dict")
                continue

            # Check for string numbers (the critical "1.2M" leak check)
            for field in ("coin_cost", "cumulative_effect", "effect_delta"):
                val = lv.get(field)
                if isinstance(val, str):
                    result.error(
                        f"{name} levels[{j}].{field}: string value '{val}' — expected numeric"
                    )

    return result


# --- CLI entry point for `python -m src.data_loader validate` ---

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "validate":
        try:
            db = load_upgrades()
        except FileNotFoundError as e:
            print(f"FAIL: {e}")
            sys.exit(1)
        except ValidationError as e:
            print(f"FAIL: Pydantic validation error:\n{e}")
            sys.exit(1)

        vr = validate_upgrade_data(db)
        print(vr.summary())
        sys.exit(0 if vr.ok else 1)
    else:
        print("Usage: python -m src.data_loader validate")
        sys.exit(1)
