#!/usr/bin/env python3
"""Merge data from GitHub-parsed and Netlify-scraped sources into upgrades.json.

Priority: GitHub data is authoritative for the 13 core upgrades it contains.
Netlify data fills in additional upgrades not in the GitHub repo.
Overlapping upgrades are cross-validated and discrepancies logged.

Usage:
    python scripts/merge_data.py                  # merge both sources
    python scripts/merge_data.py --github-only     # only use GitHub data

Output:
    data/upgrades.json      - final merged upgrade database
    data/lab_research.json  - lab research data (from GitHub only)
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
UPGRADES_PATH = DATA_DIR / "upgrades.json"
LAB_PATH = DATA_DIR / "lab_research.json"

GITHUB_PATH = RAW_DIR / "github_parsed.json"
NETLIFY_PATH = RAW_DIR / "netlify_scraped.json"


def load_github_data() -> dict | None:
    if not GITHUB_PATH.exists():
        print(f"GitHub data not found at {GITHUB_PATH}")
        return None
    return json.loads(GITHUB_PATH.read_text(encoding="utf-8"))


def load_netlify_data() -> dict | None:
    if not NETLIFY_PATH.exists():
        print(f"Netlify data not found at {NETLIFY_PATH}")
        return None
    return json.loads(NETLIFY_PATH.read_text(encoding="utf-8"))


def normalize_netlify_upgrade(name: str, data: dict) -> dict | None:
    """Convert a single Netlify-scraped upgrade into our schema format."""
    rows = data.get("rows", [])
    if not rows:
        return None

    category = data.get("category", "utility")
    upgrade_id = name.lower().replace(" ", "_").replace("/", "_")

    first_value = rows[0].get("Value", rows[0].get("value", 0))
    if isinstance(first_value, str):
        try:
            first_value = float(first_value)
        except ValueError:
            first_value = 0

    is_mult = first_value >= 1.0 and len(rows) > 1
    if is_mult:
        second_value = rows[1].get("Value", rows[1].get("value", 0)) if len(rows) > 1 else 0
        if isinstance(second_value, str):
            try:
                second_value = float(second_value)
            except ValueError:
                second_value = 0
        if second_value < 1.0:
            is_mult = False

    base_value = first_value if is_mult else 0.0
    effect_type = "multiplicative" if is_mult else "additive"

    levels = []
    for i, row in enumerate(rows):
        value = row.get("Value", row.get("value", 0))
        cost = row.get("Next Coins", row.get("next_coins",
               row.get("Cost", row.get("cost", 0))))

        if isinstance(value, str):
            try:
                value = float(value.replace(",", ""))
            except ValueError:
                continue
        if isinstance(cost, str):
            try:
                cost = float(cost.replace(",", ""))
            except ValueError:
                cost = 0

        level_num = int(row.get("Level", row.get("level", i))) + 1

        if cost <= 0 and i > 0:
            continue

        if i == 0:
            delta = value - base_value
        else:
            prev_val = rows[i - 1].get("Value", rows[i - 1].get("value", 0))
            if isinstance(prev_val, str):
                try:
                    prev_val = float(prev_val.replace(",", ""))
                except ValueError:
                    prev_val = 0
            delta = value - float(prev_val)

        levels.append({
            "level": level_num,
            "coin_cost": max(round(cost), 1),
            "cumulative_effect": round(float(value), 6),
            "effect_delta": round(float(delta), 6),
        })

    if not levels:
        return None

    return {
        "id": upgrade_id,
        "name": name,
        "category": category,
        "effect_unit": "pts",
        "effect_type": effect_type,
        "base_value": base_value,
        "max_level": len(levels),
        "display_order": 0,
        "levels": levels,
    }


def cross_validate(github_upgrade: dict, netlify_upgrade: dict) -> list[str]:
    """Compare overlapping upgrades between the two sources."""
    issues = []
    name = github_upgrade["name"]

    g_levels = github_upgrade.get("levels", [])
    n_levels = netlify_upgrade.get("levels", [])

    if len(g_levels) != len(n_levels):
        issues.append(
            f"{name}: level count mismatch "
            f"(GitHub={len(g_levels)}, Netlify={len(n_levels)})"
        )

    check_count = min(len(g_levels), len(n_levels), 10)
    for i in range(check_count):
        g = g_levels[i]
        n = n_levels[i]
        if abs(g["cumulative_effect"] - n["cumulative_effect"]) > 0.1:
            issues.append(
                f"{name} level {g['level']}: value mismatch "
                f"(GitHub={g['cumulative_effect']}, Netlify={n['cumulative_effect']})"
            )
        if abs(g["coin_cost"] - n["coin_cost"]) > 1:
            issues.append(
                f"{name} level {g['level']}: cost mismatch "
                f"(GitHub={g['coin_cost']}, Netlify={n['coin_cost']})"
            )

    return issues


def merge(github_only: bool = False) -> dict:
    """Merge both data sources into a single UpgradeDatabase."""
    github_data = load_github_data()
    netlify_data = load_netlify_data() if not github_only else None

    if github_data is None and netlify_data is None:
        print("ERROR: No data sources available")
        sys.exit(1)

    github_upgrades: dict[str, dict] = {}
    if github_data:
        for u in github_data.get("upgrades", []):
            github_upgrades[u["id"]] = u
        print(f"GitHub: {len(github_upgrades)} upgrades loaded")

    netlify_upgrades: dict[str, dict] = {}
    if netlify_data:
        display_order = len(github_upgrades)
        for key, data in netlify_data.items():
            name = data.get("name", key.split(":")[-1])
            normalized = normalize_netlify_upgrade(name, data)
            if normalized:
                display_order += 1
                normalized["display_order"] = display_order
                netlify_upgrades[normalized["id"]] = normalized
        print(f"Netlify: {len(netlify_upgrades)} upgrades loaded")

    # Cross-validate overlapping upgrades
    github_ids = set(github_upgrades.keys())
    all_issues: list[str] = []

    # Map GitHub IDs to likely Netlify equivalents
    name_to_github = {u["name"].lower(): u for u in github_upgrades.values()}

    for nid, nu in netlify_upgrades.items():
        nname = nu["name"].lower()
        if nname in name_to_github:
            gu = name_to_github[nname]
            issues = cross_validate(gu, nu)
            if issues:
                all_issues.extend(issues)
            else:
                print(f"  Cross-validated OK: {nu['name']}")

    if all_issues:
        print(f"\nCross-validation issues ({len(all_issues)}):")
        for issue in all_issues:
            print(f"  - {issue}")

    # Build final list: GitHub upgrades first (authoritative), then new Netlify ones
    final_upgrades: list[dict] = list(github_upgrades.values())

    added_names = {u["name"].lower() for u in final_upgrades}
    for nid, nu in netlify_upgrades.items():
        if nu["name"].lower() not in added_names:
            final_upgrades.append(nu)
            added_names.add(nu["name"].lower())

    # Reassign display_order
    for i, u in enumerate(final_upgrades):
        u["display_order"] = i + 1

    db = {
        "version": "merged-v1",
        "game_version": "2025-09",
        "source": "github.com/jacoelt/tower-calculator + tower-workshop-calculator.netlify.app",
        "upgrades": final_upgrades,
    }

    return db


def main() -> None:
    github_only = "--github-only" in sys.argv

    print("Merging upgrade data...", flush=True)
    db = merge(github_only=github_only)

    # Save upgrades.json
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPGRADES_PATH.write_text(json.dumps(db, indent=2), encoding="utf-8")
    print(f"\nSaved {len(db['upgrades'])} upgrades to {UPGRADES_PATH}")

    # Copy lab research if available
    lab_src = RAW_DIR / "lab_research.json"
    if lab_src.exists():
        shutil.copy2(lab_src, LAB_PATH)
        lab_data = json.loads(lab_src.read_text(encoding="utf-8"))
        print(f"Copied {len(lab_data)} lab researches to {LAB_PATH}")

    # Validate with our schema
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.models import UpgradeDatabase
        validated = UpgradeDatabase.model_validate(db)
        print(f"\nSchema validation PASSED: {len(validated.upgrades)} upgrades")
    except Exception as e:
        print(f"\nSchema validation FAILED: {e}")
        print("The data was saved anyway - manual fixes may be needed.")


if __name__ == "__main__":
    main()
