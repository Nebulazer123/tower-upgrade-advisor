#!/usr/bin/env python3
"""Add basic utility upgrades to upgrades.json.

This script adds placeholder utility upgrades based on wiki data.
The data is incomplete and should be refined with actual game data.

Usage:
    python scripts/add_utility_upgrades.py
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPGRADES_PATH = DATA_DIR / "upgrades.json"

# Utility upgrades based on wiki research
# Data from: https://the-tower-idle-tower-defense.game-vault.net/wiki/
UTILITY_UPGRADES = [
    {
        "id": "cash_bonus",
        "name": "Cash Bonus",
        "category": "utility",
        "effect_unit": "x",
        "effect_type": "multiplicative",
        "base_value": 1.0,
        "max_level": 149,
        "display_order": 14,
        "levels": [
            {"level": i+1, "coin_cost": int(30 * (1.08 ** i)), 
             "cumulative_effect": round(1.0 + (i+1) * 0.01, 2),
             "effect_delta": 0.01}
            for i in range(149)
        ],
    },
    {
        "id": "cash_per_wave",
        "name": "Cash / Wave",
        "category": "utility",
        "effect_unit": "$",
        "effect_type": "additive",
        "base_value": 0.0,
        "max_level": 149,
        "display_order": 15,
        "levels": [
            {"level": i+1, "coin_cost": int(30 * (1.08 ** i)),
             "cumulative_effect": (i+1) * 4.0,
             "effect_delta": 4.0}
            for i in range(149)
        ],
    },
    {
        "id": "coins_per_kill_bonus",
        "name": "Coins / Kill Bonus",
        "category": "utility",
        "effect_unit": "%",
        "effect_type": "additive",
        "base_value": 0.0,
        "max_level": 100,
        "display_order": 16,
        "levels": [
            {"level": i+1, "coin_cost": int(50 * (1.09 ** i)),
             "cumulative_effect": round((i+1) * 0.5, 1),
             "effect_delta": 0.5}
            for i in range(100)
        ],
    },
    {
        "id": "coins_per_wave",
        "name": "Coins / Wave",
        "category": "utility",
        "effect_unit": "coins",
        "effect_type": "additive",
        "base_value": 0.0,
        "max_level": 100,
        "display_order": 17,
        "levels": [
            {"level": i+1, "coin_cost": int(40 * (1.09 ** i)),
             "cumulative_effect": (i+1) * 2.0,
             "effect_delta": 2.0}
            for i in range(100)
        ],
    },
    {
        "id": "interest_per_wave",
        "name": "Interest / Wave",
        "category": "utility",
        "effect_unit": "%",
        "effect_type": "additive",
        "base_value": 0.0,
        "max_level": 99,
        "display_order": 18,
        # Real data from wiki: https://the-tower-idle-tower-defense.game-vault.net/wiki/Interest
        "levels": [
            {"level": i+1, "coin_cost": int(125 * (1.12 ** i)),
             "cumulative_effect": round((i+1) * 0.06, 2),
             "effect_delta": 0.06}
            for i in range(99)
        ],
    },
    {
        "id": "free_attack_upgrade",
        "name": "Free Attack Upgrade",
        "category": "utility",
        "effect_unit": "count",
        "effect_type": "additive",
        "base_value": 0.0,
        "max_level": 20,
        "display_order": 19,
        "levels": [
            {"level": i+1, "coin_cost": int(5000 * (1.5 ** i)),
             "cumulative_effect": float(i+1),
             "effect_delta": 1.0}
            for i in range(20)
        ],
    },
    {
        "id": "free_defense_upgrade",
        "name": "Free Defense Upgrade",
        "category": "utility",
        "effect_unit": "count",
        "effect_type": "additive",
        "base_value": 0.0,
        "max_level": 20,
        "display_order": 20,
        "levels": [
            {"level": i+1, "coin_cost": int(5000 * (1.5 ** i)),
             "cumulative_effect": float(i+1),
             "effect_delta": 1.0}
            for i in range(20)
        ],
    },
    {
        "id": "free_utility_upgrade",
        "name": "Free Utility Upgrade",
        "category": "utility",
        "effect_unit": "count",
        "effect_type": "additive",
        "base_value": 0.0,
        "max_level": 20,
        "display_order": 21,
        "levels": [
            {"level": i+1, "coin_cost": int(5000 * (1.5 ** i)),
             "cumulative_effect": float(i+1),
             "effect_delta": 1.0}
            for i in range(20)
        ],
    },
]


def main() -> None:
    if not UPGRADES_PATH.exists():
        print(f"ERROR: {UPGRADES_PATH} not found. Run merge_data.py first.")
        return

    # Load existing data
    data = json.loads(UPGRADES_PATH.read_text(encoding="utf-8"))
    
    # Check if utility upgrades already exist
    existing_ids = {u["id"] for u in data["upgrades"]}
    utility_ids = {u["id"] for u in UTILITY_UPGRADES}
    
    if utility_ids & existing_ids:
        print("Utility upgrades already exist. Skipping.")
        return
    
    # Add utility upgrades
    data["upgrades"].extend(UTILITY_UPGRADES)
    data["source"] += " + utility upgrades from wiki (placeholder data)"
    
    # Save
    UPGRADES_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Added {len(UTILITY_UPGRADES)} utility upgrades to {UPGRADES_PATH}")
    print(f"Total upgrades: {len(data['upgrades'])}")
    
    # Validate
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.models import UpgradeDatabase
        validated = UpgradeDatabase.model_validate(data)
        print(f"\nSchema validation PASSED: {len(validated.upgrades)} upgrades")
        
        # Count by category
        by_cat = {}
        for u in validated.upgrades:
            by_cat[u.category] = by_cat.get(u.category, 0) + 1
        print(f"\nUpgrades by category:")
        for cat, count in sorted(by_cat.items()):
            print(f"  {cat}: {count}")
    except Exception as e:
        print(f"\nSchema validation FAILED: {e}")


if __name__ == "__main__":
    main()
