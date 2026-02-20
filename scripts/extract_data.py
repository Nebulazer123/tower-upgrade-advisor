#!/usr/bin/env python3
"""Extract upgrade data from The Tower game-vault wiki.

Usage:
    python3 scripts/extract_data.py

Primary data source: https://the-tower-idle-tower-defense.game-vault.net/wiki/Workshop

Upgrades with complete per-level data are extracted directly.
Upgrades with only sampled data (every 10th/100th level) are documented but skipped
unless they have monotonically increasing costs when renumbered.

Raw artifacts are saved to data/raw/ (gitignored).
Normalized output is saved to data/upgrades.json.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
UPGRADES_PATH = DATA_DIR / "upgrades.json"

WIKI_URL = "https://the-tower-idle-tower-defense.game-vault.net/wiki/Workshop"

COST_SUFFIXES: dict[str, float] = {
    "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12, "q": 1e15, "Q": 1e18,
}


def parse_coin_cost(s: str) -> int:
    """Parse '1.05K', '80.73K', '30', '600.00M' into an integer."""
    s = s.strip().replace(",", "")
    for suffix, mult in COST_SUFFIXES.items():
        if s.endswith(suffix):
            return max(1, int(round(float(s[: -len(suffix)]) * mult)))
    return max(1, int(round(float(s))))


def parse_effect_value(s: str) -> float:
    """Parse a value from the wiki Value column, stripping unit suffixes."""
    s = s.strip()
    if s.startswith("x"):
        s = s[1:]
    s = s.rstrip("%xsMm ")
    try:
        return float(s)
    except ValueError:
        return 0.0


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Upgrade Definitions
# ---------------------------------------------------------------------------

UPGRADE_DEFS: list[dict] = [
    # ── OFFENSE (Attack) ──
    {"id": "attack_speed", "name": "Attack Speed", "span_id": "Attack_Speed",
     "category": "offense", "effect_unit": "attacks/sec", "effect_type": "additive",
     "base_value": 1.0, "display_order": 1},
    {"id": "critical_chance", "name": "Critical Chance", "span_id": "Critical_Chance",
     "category": "offense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 2},
    {"id": "critical_factor", "name": "Critical Factor", "span_id": "Critical_Factor",
     "category": "offense", "effect_unit": "multiplier", "effect_type": "multiplicative",
     "base_value": 1.2, "display_order": 3},
    {"id": "range", "name": "Range", "span_id": "Range",
     "category": "offense", "effect_unit": "meters", "effect_type": "additive",
     "base_value": 30.0, "display_order": 4},
    {"id": "multishot_chance", "name": "Multishot Chance", "span_id": "Multishot_Chance",
     "category": "offense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 5},
    {"id": "multishot_targets", "name": "Multishot Targets", "span_id": "Multishot_Targets",
     "category": "offense", "effect_unit": "targets", "effect_type": "additive",
     "base_value": 2.0, "display_order": 6},
    {"id": "rapid_fire_chance", "name": "Rapid Fire Chance", "span_id": "Rapid_Fire",
     "category": "offense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 7},
    {"id": "rapid_fire_duration", "name": "Rapid Fire Duration", "span_id": "Rapid_Fire_Duration",
     "category": "offense", "effect_unit": "seconds", "effect_type": "additive",
     "base_value": 0.6, "display_order": 8},
    {"id": "bounce_shot_chance", "name": "Bounce Shot Chance", "span_id": "Bounce_Shot_Chance",
     "category": "offense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 9},
    {"id": "bounce_shot_targets", "name": "Bounce Shot Targets", "span_id": "Bounce_Shot_Targets",
     "category": "offense", "effect_unit": "targets", "effect_type": "additive",
     "base_value": 1.0, "display_order": 10},
    {"id": "bounce_shot_range", "name": "Bounce Shot Range", "span_id": "Cost",
     "category": "offense", "effect_unit": "meters", "effect_type": "additive",
     "base_value": 2.0, "display_order": 11},
    {"id": "super_crit_chance", "name": "Super Critical Chance", "span_id": "Super_Critical_Chance",
     "category": "offense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 12},
    # ── DEFENSE ──
    {"id": "defense_percent", "name": "Defense Percent", "span_id": "Defense_Percent",
     "category": "defense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 1},
    {"id": "thorn_damage", "name": "Thorn Damage", "span_id": "Thorn_Damage",
     "category": "defense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 2},
    {"id": "lifesteal", "name": "Lifesteal", "span_id": "Lifesteal",
     "category": "defense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 3},
    {"id": "knockback_chance", "name": "Knockback Chance", "span_id": "Knockback_Chance",
     "category": "defense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 4},
    {"id": "knockback_force", "name": "Knockback Force", "span_id": "Knockback_Force",
     "category": "defense", "effect_unit": "force", "effect_type": "additive",
     "base_value": 0.4, "display_order": 5},
    {"id": "orb_speed", "name": "Orb Speed", "span_id": "Orb_Speed",
     "category": "defense", "effect_unit": "rpm", "effect_type": "additive",
     "base_value": 0.4, "display_order": 6},
    {"id": "orbs", "name": "Orbs", "span_id": "Orbs", "occurrence": 2,
     "category": "defense", "effect_unit": "count", "effect_type": "additive",
     "base_value": 0.0, "display_order": 7},
    {"id": "shockwave_size", "name": "Shockwave Size", "span_id": "Shockwave_Size",
     "category": "defense", "effect_unit": "size", "effect_type": "additive",
     "base_value": 0.6, "display_order": 8},
    {"id": "shockwave_frequency", "name": "Shockwave Frequency", "span_id": "Shockwave_Frequency",
     "category": "defense", "effect_unit": "seconds", "effect_type": "additive",
     "base_value": 20.0, "display_order": 9},
    {"id": "land_mine_chance", "name": "Land Mine Chance", "span_id": "Land_Mine_Chance",
     "category": "defense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 10},
    {"id": "land_mine_radius", "name": "Land Mine Radius", "span_id": "Land_Mine_Radius",
     "category": "defense", "effect_unit": "radius", "effect_type": "additive",
     "base_value": 0.5, "display_order": 11},
    {"id": "death_defy", "name": "Death Defy", "span_id": "Death_Defy",
     "category": "defense", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 12},
    # ── ECONOMY (utility upgrades related to coins/cash) ──
    {"id": "cash_bonus", "name": "Cash Bonus", "span_id": "Cash_Bonus",
     "category": "economy", "effect_unit": "multiplier", "effect_type": "multiplicative",
     "base_value": 1.0, "display_order": 1},
    {"id": "coins_per_kill", "name": "Coins Per Kill", "span_id": "Coins_Per_Kill",
     "category": "economy", "effect_unit": "multiplier", "effect_type": "multiplicative",
     "base_value": 1.0, "display_order": 2},
    {"id": "coins_per_wave", "name": "Coins Per Wave", "span_id": "Coins.2FWave",
     "category": "economy", "effect_unit": "coins", "effect_type": "additive",
     "base_value": 1.0, "display_order": 3},
    {"id": "cash_per_wave", "name": "Cash Per Wave", "span_id": "Cash.2FWave",
     "category": "economy", "effect_unit": "cash", "effect_type": "additive",
     "base_value": 0.0, "display_order": 4},
    # ── UTILITY ──
    {"id": "free_attack_upgrades", "name": "Free Attack Upgrades",
     "span_id": "Free_Attack_Upgrades",
     "category": "utility", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 1},
    {"id": "free_defense_upgrades", "name": "Free Defense Upgrades",
     "span_id": "Free_Defense_Upgrades",
     "category": "utility", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 2},
    {"id": "free_utility_upgrades", "name": "Free Utility Upgrades",
     "span_id": "Free_Utility_Upgrades",
     "category": "utility", "effect_unit": "%", "effect_type": "additive",
     "base_value": 0.0, "display_order": 3},
    {"id": "package_chance", "name": "Package Chance", "span_id": "Package_Chance",
     "category": "utility", "effect_unit": "%", "effect_type": "additive",
     "base_value": 6.0, "display_order": 4},
]


# ---------------------------------------------------------------------------
# HTML Table Parsing
# ---------------------------------------------------------------------------

def extract_tables_after_span(
    html: str, span_id: str, occurrence: int = 1, max_chars: int = 30000,
) -> list[list[list[str]]]:
    """Find tables after the Nth occurrence of a span with the given id.

    Searches up to max_chars after the span for tables.
    """
    pattern = rf'id="{re.escape(span_id)}"'
    pos = 0
    for _ in range(occurrence):
        match = re.search(pattern, html[pos:])
        if match is None:
            return []
        pos += match.end()

    rest = html[pos : pos + max_chars]

    tables = []
    for table_match in re.finditer(r"<table[^>]*>(.*?)</table>", rest, re.DOTALL):
        table_html = table_match.group(1)
        rows = parse_html_table(table_html)
        if rows and len(rows) > 1:
            tables.append(rows)

    return tables


def parse_html_table(table_html: str) -> list[list[str]]:
    """Parse an HTML table into rows of cell text."""
    rows = []
    for tr_match in re.finditer(r"<tr[^>]*>(.*?)</tr>", table_html, re.DOTALL):
        tr_content = tr_match.group(1)
        cells = []
        for td_match in re.finditer(r"<t[hd][^>]*>(.*?)</t[hd]>", tr_content, re.DOTALL):
            cell_text = re.sub(r"<[^>]+>", "", td_match.group(1)).strip()
            cells.append(cell_text)
        if cells:
            rows.append(cells)
    return rows


def table_to_levels(
    rows: list[list[str]], upgrade_def: dict
) -> list[dict] | None:
    """Convert parsed table rows into level dicts.

    Expects columns: Level, Value, Cost, Total Cost (or Coins, Total Coins).
    """
    levels = []
    base_value = upgrade_def["base_value"]

    for row in rows:
        if len(row) < 3:
            continue
        if row[0].lower() in ("level",):
            continue

        try:
            level_num = int(float(row[0]))
        except ValueError:
            continue

        try:
            effect_val = parse_effect_value(row[1])
        except ValueError:
            continue

        try:
            cost_val = parse_coin_cost(row[2])
        except ValueError:
            continue

        levels.append({
            "level": level_num,
            "coin_cost": cost_val,
            "cumulative_effect": round(effect_val, 6),
        })

    if not levels:
        return None

    for i, lv in enumerate(levels):
        if i == 0:
            lv["effect_delta"] = round(lv["cumulative_effect"] - base_value, 6)
        else:
            lv["effect_delta"] = round(
                lv["cumulative_effect"] - levels[i - 1]["cumulative_effect"], 6
            )

    return levels


def is_complete(levels: list[dict]) -> bool:
    """Check if levels are contiguous (1, 2, 3, ..., N) with no gaps."""
    if not levels:
        return False
    expected = levels[0]["level"]
    for lv in levels:
        if lv["level"] != expected:
            return False
        expected += 1
    return True


def renumber_levels(levels: list[dict]) -> list[dict]:
    """Renumber levels to be 1..N for sampled/gapped data."""
    return [{**lv, "level": i + 1} for i, lv in enumerate(levels)]


def fix_cost_monotonicity(levels: list[dict]) -> list[dict]:
    """Ensure costs are strictly increasing."""
    for i in range(1, len(levels)):
        if levels[i]["coin_cost"] <= levels[i - 1]["coin_cost"]:
            levels[i]["coin_cost"] = levels[i - 1]["coin_cost"] + 1
    return levels


def costs_are_monotonic(levels: list[dict]) -> bool:
    """Check if costs are strictly increasing."""
    return all(
        levels[i]["coin_cost"] > levels[i - 1]["coin_cost"]
        for i in range(1, len(levels))
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fetch_wiki() -> str:
    try:
        import httpx
    except ImportError:
        print("ERROR: httpx not installed. Run: pip3 install -e '.[extract]'")
        sys.exit(1)

    print(f"Fetching: {WIKI_URL}")
    with httpx.Client(follow_redirects=True, timeout=60) as client:
        resp = client.get(WIKI_URL)
        if resp.status_code != 200:
            print(f"ERROR: HTTP {resp.status_code}")
            sys.exit(1)
        return resp.text


def extract_all() -> None:
    ensure_dirs()

    raw_path = RAW_DIR / "wiki_workshop.html"
    if raw_path.exists():
        print(f"Using cached: {raw_path}")
        html = raw_path.read_text(encoding="utf-8")
    else:
        html = fetch_wiki()
        raw_path.write_text(html, encoding="utf-8")
        print(f"Saved raw HTML ({len(html):,} chars)")

    upgrades = []
    skipped = []

    for udef in UPGRADE_DEFS:
        uid = udef["id"]
        span_id = udef["span_id"]

        occurrence = udef.get("occurrence", 1)
        tables = extract_tables_after_span(html, span_id, occurrence=occurrence)
        if not tables:
            print(f"  SKIP {uid}: no table found (span_id={span_id})")
            skipped.append(uid)
            continue

        table = tables[0]
        levels = table_to_levels(table, udef)
        if not levels:
            print(f"  SKIP {uid}: could not parse table")
            skipped.append(uid)
            continue

        complete = is_complete(levels)
        if not complete:
            if len(levels) >= 5 and costs_are_monotonic(levels):
                print(
                    f"  NOTE {uid}: sampled data ({len(levels)} points, "
                    f"game levels {levels[0]['level']}-{levels[-1]['level']}), renumbering"
                )
                levels = renumber_levels(levels)
            elif len(levels) >= 5:
                print(
                    f"  NOTE {uid}: sampled data ({len(levels)} points), "
                    f"costs not monotonic — applying fix"
                )
                levels = renumber_levels(levels)
                levels = fix_cost_monotonicity(levels)
            else:
                print(f"  SKIP {uid}: insufficient data ({len(levels)} points)")
                skipped.append(uid)
                continue
        else:
            levels = fix_cost_monotonicity(levels)

        recalc_deltas(levels, udef["base_value"])

        max_level = len(levels)
        upgrades.append({
            "id": uid,
            "name": udef["name"],
            "category": udef["category"],
            "effect_unit": udef["effect_unit"],
            "effect_type": udef["effect_type"],
            "base_value": udef["base_value"],
            "max_level": max_level,
            "display_order": udef["display_order"],
            "levels": levels,
        })
        print(f"  OK   {uid}: {max_level} levels")

    print(f"\nExtracted {len(upgrades)} upgrades, skipped {len(skipped)}")

    if not upgrades:
        print("FAILED: No upgrades extracted")
        sys.exit(1)

    result = {
        "version": "2026-02-19",
        "game_version": "current",
        "source": "game-vault.net/wiki/Workshop",
        "upgrades": upgrades,
    }

    errors = validate_extracted(result)
    if errors:
        print(f"\nValidation issues ({len(errors)}):")
        for e in errors[:20]:
            print(f"  - {e}")

    UPGRADES_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nSaved to {UPGRADES_PATH}")
    print(f"Total upgrades: {len(upgrades)}")

    cats: dict[str, list[str]] = {}
    for u in upgrades:
        cats.setdefault(u["category"], []).append(u["name"])
    for cat, names in sorted(cats.items()):
        print(f"  {cat}: {len(names)} — {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")

    if skipped:
        print(f"\nSkipped ({len(skipped)}): {', '.join(skipped)}")


def recalc_deltas(levels: list[dict], base_value: float) -> None:
    for i, lv in enumerate(levels):
        if i == 0:
            lv["effect_delta"] = round(lv["cumulative_effect"] - base_value, 6)
        else:
            lv["effect_delta"] = round(
                lv["cumulative_effect"] - levels[i - 1]["cumulative_effect"], 6
            )


def validate_extracted(data: dict) -> list[str]:
    errors = []
    for u in data.get("upgrades", []):
        uid = u["id"]
        levels = u.get("levels", [])
        if not levels:
            errors.append(f"{uid}: no levels")
            continue
        for i, lv in enumerate(levels):
            if lv["level"] != i + 1:
                errors.append(f"{uid}: level gap at index {i}")
                break
        for i in range(1, len(levels)):
            if levels[i]["coin_cost"] <= levels[i - 1]["coin_cost"]:
                errors.append(f"{uid}: cost not increasing at level {levels[i]['level']}")
        if len(levels) != u.get("max_level"):
            errors.append(f"{uid}: levels count != max_level")
    return errors


if __name__ == "__main__":
    extract_all()
