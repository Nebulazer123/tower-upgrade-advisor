"""Reference workshop coverage helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

from src.models import UpgradeDatabase

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_MANIFEST_PATH = PROJECT_ROOT / "data" / "reference_workshop_upgrades.json"


class CategoryCoverage(TypedDict):
    category: str
    label: str
    expected: int
    loaded: int
    missing: int
    missing_names: list[str]
    present_names: list[str]
    complete: bool
    percent: int


class CoverageReport(TypedDict):
    expected: int
    loaded: int
    missing: int
    complete: bool
    percent: int
    verified_at: str
    source: dict[str, str]
    categories: dict[str, CategoryCoverage]


def normalize_upgrade_name(value: str) -> str:
    """Normalize display names for source-to-local matching."""
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def load_reference_manifest(path: Path | None = None) -> dict[str, Any]:
    """Load the public workshop reference manifest."""
    manifest_path = path or REFERENCE_MANIFEST_PATH
    raw: object = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Reference manifest must be a JSON object: {manifest_path}")
    return raw


def compute_coverage(
    upgrades: UpgradeDatabase,
    manifest: dict[str, Any] | None = None,
) -> CoverageReport:
    """Compare local bundled upgrades with the public workshop reference surface."""
    reference = manifest or load_reference_manifest()
    loaded_by_category: dict[str, set[str]] = {}
    for upgrade in upgrades.upgrades:
        loaded_by_category.setdefault(upgrade.category, set()).add(
            normalize_upgrade_name(upgrade.name)
        )

    categories: dict[str, CategoryCoverage] = {}
    total_expected = 0
    total_loaded = 0

    for category in reference.get("categories", []):
        category_id = str(category["id"])
        label = str(category.get("name", category_id.capitalize()))
        expected_upgrades = category.get("upgrades", [])
        loaded_names = loaded_by_category.get(category_id, set())
        present_names: list[str] = []
        missing_names: list[str] = []

        for expected in expected_upgrades:
            name = str(expected["name"])
            aliases = [str(alias) for alias in expected.get("aliases", [])]
            candidates = {normalize_upgrade_name(name)}
            candidates.update(normalize_upgrade_name(alias) for alias in aliases)
            if loaded_names & candidates:
                present_names.append(name)
            else:
                missing_names.append(name)

        expected_count = len(expected_upgrades)
        loaded_count = len(present_names)
        total_expected += expected_count
        total_loaded += loaded_count
        categories[category_id] = {
            "category": category_id,
            "label": label,
            "expected": expected_count,
            "loaded": loaded_count,
            "missing": len(missing_names),
            "missing_names": missing_names,
            "present_names": present_names,
            "complete": loaded_count == expected_count,
            "percent": round((loaded_count / expected_count) * 100) if expected_count else 100,
        }

    return {
        "expected": total_expected,
        "loaded": total_loaded,
        "missing": total_expected - total_loaded,
        "complete": total_loaded == total_expected,
        "percent": round((total_loaded / total_expected) * 100) if total_expected else 100,
        "verified_at": str(reference.get("verified_at", "unknown")),
        "source": {str(key): str(value) for key, value in reference.get("source", {}).items()},
        "categories": categories,
    }
