#!/usr/bin/env python3
"""Parse upgrade data from jacoelt/tower-calculator's dataStrings.ts.

Fetches the TypeScript source from GitHub and extracts all workshop upgrade
tables and lab research tables into structured JSON.

Usage:
    python scripts/parse_github_data.py           # fetch from GitHub & parse
    python scripts/parse_github_data.py FILE.ts    # parse a local file

Output:
    data/raw/github_parsed.json     – raw parsed data
    data/raw/lab_research.json      – lab research tables
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

DATASTRINGS_URL = (
    "https://raw.githubusercontent.com/jacoelt/tower-calculator/"
    "main/src/data/dataStrings.ts"
)

WORKSHOP_UPGRADES: dict[str, dict[str, str]] = {
    "damageStr": {
        "id": "damage",
        "name": "Damage",
        "category": "attack",
        "effect_unit": "pts",
        "effect_type": "additive",
    },
    "attackSpeedStr": {
        "id": "attack_speed",
        "name": "Attack Speed",
        "category": "attack",
        "effect_unit": "x",
        "effect_type": "multiplicative",
    },
    "criticalChanceStr": {
        "id": "crit_chance",
        "name": "Critical Chance",
        "category": "attack",
        "effect_unit": "%",
        "effect_type": "additive",
    },
    "criticalFactorStr": {
        "id": "crit_factor",
        "name": "Critical Factor",
        "category": "attack",
        "effect_unit": "x",
        "effect_type": "multiplicative",
    },
    "multishotChanceStr": {
        "id": "multishot_chance",
        "name": "Multishot Chance",
        "category": "attack",
        "effect_unit": "%",
        "effect_type": "additive",
    },
    "multishotTargetsStr": {
        "id": "multishot_targets",
        "name": "Multishot Targets",
        "category": "attack",
        "effect_unit": "count",
        "effect_type": "additive",
    },
    "rapidFireChanceStr": {
        "id": "rapid_fire_chance",
        "name": "Rapid Fire Chance",
        "category": "attack",
        "effect_unit": "%",
        "effect_type": "additive",
    },
    "bounceChanceStr": {
        "id": "bounce_chance",
        "name": "Bounce Shot Chance",
        "category": "attack",
        "effect_unit": "%",
        "effect_type": "additive",
    },
    "bounceTargetsStr": {
        "id": "bounce_targets",
        "name": "Bounce Shot Targets",
        "category": "attack",
        "effect_unit": "count",
        "effect_type": "additive",
    },
    "healthStr": {
        "id": "health",
        "name": "Health",
        "category": "defense",
        "effect_unit": "HP",
        "effect_type": "additive",
    },
    "healthRegenStr": {
        "id": "health_regen",
        "name": "Health Regen",
        "category": "defense",
        "effect_unit": "HP/s",
        "effect_type": "additive",
    },
    "defensePercentStr": {
        "id": "defense_percent",
        "name": "Defense Percent",
        "category": "defense",
        "effect_unit": "%",
        "effect_type": "additive",
    },
    "defenseFlatStr": {
        "id": "defense_absolute",
        "name": "Defence Absolute",
        "category": "defense",
        "effect_unit": "pts",
        "effect_type": "additive",
    },
}

LAB_RESEARCH: dict[str, dict[str, str]] = {
    "labDamageStr": {
        "id": "lab_damage",
        "name": "Lab Damage",
        "boost_type": "multiplicative",
    },
    "labCritFactorStr": {
        "id": "lab_crit_factor",
        "name": "Lab Crit Factor",
        "boost_type": "multiplicative",
    },
    "labAttackSpeedStr": {
        "id": "lab_attack_speed",
        "name": "Lab Attack Speed",
        "boost_type": "multiplicative",
    },
    "labDefenseFlatStr": {
        "id": "lab_defense_flat",
        "name": "Lab Defense Flat",
        "boost_type": "multiplicative",
    },
    "labDefensePercentStr": {
        "id": "lab_defense_percent",
        "name": "Lab Defense Percent",
        "boost_type": "additive",
    },
}


def k_to_number(s: str) -> float:
    """Convert strings like '1.02K' to 1020.0, matching the reference kToNumber()."""
    s = s.strip()
    if s.endswith("K"):
        return float(s[:-1]) * 1000
    if s.endswith("M"):
        return float(s[:-1]) * 1_000_000
    if s.endswith("B"):
        return float(s[:-1]) * 1_000_000_000
    return float(s)


def extract_template_strings(ts_content: str) -> dict[str, str]:
    """Extract all 'export const xxxStr = `...`' blocks from TypeScript."""
    pattern = re.compile(r"export\s+const\s+(\w+)\s*=\s*`([^`]*)`", re.DOTALL)
    return {m.group(1): m.group(2).strip() for m in pattern.finditer(ts_content)}


def parse_workshop_block(block: str) -> list[dict[str, float]]:
    """Parse a tab-separated workshop data block: level, value, cost."""
    rows: list[dict[str, float]] = []
    for line in block.strip().splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        rows.append({
            "level": k_to_number(parts[0]),
            "value": k_to_number(parts[1]),
            "cost": k_to_number(parts[2]),
        })
    return rows


def parse_lab_block(block: str) -> list[dict[str, float]]:
    """Parse a tab-separated lab research block: level, value."""
    rows: list[dict[str, float]] = []
    for line in block.strip().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        rows.append({
            "level": k_to_number(parts[0]),
            "value": k_to_number(parts[1]),
        })
    return rows


def to_upgrade_schema(
    meta: dict[str, str], raw_rows: list[dict[str, float]], display_order: int,
) -> dict:
    """Convert raw parsed rows to the UpgradeDatabase upgrade schema.

    In the source data:
      - Row at index 0 (level=0) is the base/unpurchased state.
      - Each row's cost is what you pay to buy THAT level from the previous.
      - The cost at level 0 is the cost to go from nothing to level 1.
      - A trailing row with cost=0 is a sentinel meaning "no more upgrades".
    """
    if not raw_rows:
        return {**meta, "base_value": 0.0, "max_level": 0, "display_order": display_order,
                "levels": []}

    # Data format in dataStrings.ts:
    #   Row at game-level N: {level: N, value: V_N, cost: C_N}
    # Where:
    #   V_N = stat value when you have N levels purchased
    #   C_N = cost to go from level N to level N+1
    # Base/unpurchased state = game-level 0 (row 0)
    #
    # Our schema: level K has:
    #   cumulative_effect = stat value at level K = V_K (from row K)
    #   coin_cost = cost to reach level K from level K-1 = C_{K-1} (from row K-1)
    #   effect_delta = V_K - V_{K-1}
    base_value = raw_rows[0]["value"]

    levels = []
    for game_level in range(1, len(raw_rows)):
        row = raw_rows[game_level]
        prev_row = raw_rows[game_level - 1]

        cost = round(prev_row["cost"])
        if cost <= 0:
            break

        value = row["value"]
        prev_value = prev_row["value"]
        delta = value - prev_value

        levels.append({
            "level": game_level,
            "coin_cost": max(cost, 1),
            "cumulative_effect": round(value, 6),
            "effect_delta": round(delta, 6),
        })

    return {
        "id": meta["id"],
        "name": meta["name"],
        "category": meta["category"],
        "effect_unit": meta["effect_unit"],
        "effect_type": meta["effect_type"],
        "base_value": base_value,
        "max_level": len(levels),
        "display_order": display_order,
        "levels": levels,
    }


def fetch_datastrings(local_path: str | None = None) -> str:
    """Fetch dataStrings.ts content from GitHub or a local file."""
    if local_path:
        return Path(local_path).read_text(encoding="utf-8")

    import urllib.request
    print(f"Fetching {DATASTRINGS_URL} ...")
    with urllib.request.urlopen(DATASTRINGS_URL) as resp:
        return resp.read().decode("utf-8")


def main(local_path: str | None = None) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    ts_content = fetch_datastrings(local_path)
    blocks = extract_template_strings(ts_content)
    print(f"Found {len(blocks)} data blocks: {list(blocks.keys())}")

    upgrades = []
    display_order = 0

    for var_name, meta in WORKSHOP_UPGRADES.items():
        if var_name not in blocks:
            print(f"  WARNING: {var_name} not found in source")
            continue

        rows = parse_workshop_block(blocks[var_name])
        display_order += 1
        upgrade = to_upgrade_schema(meta, rows, display_order)
        upgrades.append(upgrade)
        print(f"  {meta['name']}: {len(rows)} levels (cost range: "
              f"{rows[0]['cost']:.0f} - {rows[-1]['cost']:.0f})")

    lab_researches = []
    for var_name, meta in LAB_RESEARCH.items():
        if var_name not in blocks:
            print(f"  WARNING: {var_name} not found in source")
            continue

        rows = parse_lab_block(blocks[var_name])
        lab_researches.append({
            **meta,
            "max_level": len(rows),
            "levels": [
                {"level": int(r["level"]), "value": round(r["value"], 4)}
                for r in rows
            ],
        })
        print(f"  {meta['name']}: {len(rows)} levels")

    db = {
        "version": "github-parsed",
        "game_version": "2025-09",
        "source": "github.com/jacoelt/tower-calculator/dataStrings.ts",
        "upgrades": upgrades,
    }

    out_path = RAW_DIR / "github_parsed.json"
    out_path.write_text(json.dumps(db, indent=2), encoding="utf-8")
    print(f"\nSaved {len(upgrades)} workshop upgrades to {out_path}")

    lab_path = RAW_DIR / "lab_research.json"
    lab_path.write_text(json.dumps(lab_researches, indent=2), encoding="utf-8")
    print(f"Saved {len(lab_researches)} lab researches to {lab_path}")

    return db


if __name__ == "__main__":
    path_arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(path_arg)
