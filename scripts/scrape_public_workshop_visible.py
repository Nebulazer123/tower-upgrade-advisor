#!/usr/bin/env python3
"""Scrape visible workshop tables from the public Netlify calculator.

The public table pads each cell with hidden zero-font characters. This scraper
reads only leaf spans whose computed font size is visible, then normalizes the
rendered rows into the app's UpgradeDatabase schema.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, TypedDict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_loader import load_upgrades, save_upgrades, validate_upgrade_data  # noqa: E402
from src.models import UpgradeDatabase  # noqa: E402
from src.reference_coverage import compute_coverage, load_reference_manifest  # noqa: E402

SITE_URL = "https://tower-workshop-calculator.netlify.app/"
RAW_DIR = ROOT / "data" / "raw"
RAW_VISIBLE_PATH = RAW_DIR / "public_workshop_visible.json"
UPGRADES_PATH = ROOT / "data" / "upgrades.json"


class ParsedWorkshopRow(TypedDict):
    level: int
    value: float
    next_coin_cost: int | None


VISIBLE_ROWS_JS = """
() => {
  function visibleText(cell) {
    const pieces = [];
    for (const node of cell.querySelectorAll("span")) {
      if (node.querySelector("span")) continue;
      const style = getComputedStyle(node);
      if (
        parseFloat(style.fontSize) > 0 &&
        style.visibility !== "hidden" &&
        style.display !== "none"
      ) {
        pieces.push(node.textContent || "");
      }
    }
    return pieces.join("") || cell.innerText || cell.textContent || "";
  }

  const headers = Array.from(document.querySelectorAll("table thead th")).map((th) =>
    th.innerText.trim()
  );
  const rows = Array.from(document.querySelectorAll("table tbody tr")).map((tr) => {
    const values = Array.from(tr.cells).map(visibleText);
    return Object.fromEntries(
      values.map((value, index) => [headers[index] || `col_${index}`, value])
    );
  });
  const nextButton = Array.from(document.querySelectorAll("button")).find((button) => {
    const visible = Boolean(
      button.offsetWidth || button.offsetHeight || button.getClientRects().length
    );
    return visible && button.innerText.trim() === "Next";
  });
  return {
    headers,
    rows,
    nextEnabled: Boolean(nextButton && !nextButton.disabled),
  };
}
"""

CLICK_NEXT_JS = """
() => {
  const nextButton = Array.from(document.querySelectorAll("button")).find((button) => {
    const visible = Boolean(
      button.offsetWidth || button.offsetHeight || button.getClientRects().length
    );
    return visible && button.innerText.trim() === "Next";
  });
  if (!nextButton || nextButton.disabled) return false;
  nextButton.click();
  return true;
}
"""

ID_OVERRIDES = {
    "Damage / Meter": "damage_per_meter",
    "Multishot Chance": "multishot_chance",
    "Multishot Targets": "multishot_targets",
    "Bounce Shot Chance": "bounce_shot_chance",
    "Bounce Shot Targets": "bounce_shot_targets",
    "Bounce Shot Range": "bounce_shot_range",
    "Super Crit Chance": "super_crit_chance",
    "Super Crit Mult": "super_crit_mult",
    "Rend Armor Chance": "rend_armor_chance",
    "Rend Armor Mult": "rend_armor_mult",
    "Defense Percent": "defense_percent",
    "Defense Absolute": "defense_absolute",
    "Land Mine Chance": "land_mine_chance",
    "Land Mine Damage": "land_mine_damage",
    "Land Mine Radius": "land_mine_radius",
    "Cash / Wave": "cash_per_wave",
    "Coins / Kill Bonus": "coins_per_kill",
    "Coins / Wave": "coins_per_wave",
    "Interest / Wave": "interest_per_wave",
    "Enemy Attack Level Skip": "enemy_attack_level_skip",
    "Enemy Health Level Skip": "enemy_health_level_skip",
}

EFFECT_META = {
    "Range": ("m", "additive", "distance_m"),
    "Damage / Meter": ("%/m", "additive", "percent"),
    "Rapid Fire Duration": ("s", "additive", "seconds"),
    "Bounce Shot Range": ("m", "additive", "distance_m"),
    "Super Crit Chance": ("%", "additive", "percent"),
    "Super Crit Mult": ("x", "multiplicative", "multiplier"),
    "Rend Armor Chance": ("%", "additive", "percent"),
    "Rend Armor Mult": ("x", "multiplicative", "multiplier"),
    "Thorns": ("%", "additive", "percent"),
    "Lifesteal": ("%", "additive", "percent"),
    "Knockback Chance": ("%", "additive", "percent"),
    "Knockback Force": ("m", "additive", "distance_m"),
    "Orb Speed": ("s", "additive", "seconds"),
    "Orbs": ("count", "additive", "number"),
    "Shockwave Size": ("m", "additive", "distance_m"),
    "Shockwave Frequency": ("s", "additive", "seconds"),
    "Land Mine Chance": ("%", "additive", "percent"),
    "Land Mine Damage": ("x", "multiplicative", "multiplier"),
    "Land Mine Radius": ("m", "additive", "distance_m"),
    "Death Defy": ("%", "additive", "percent"),
    "Wall Health": ("HP", "additive", "suffix_number"),
    "Wall Rebuild": ("s", "additive", "seconds"),
    "Recovery Amount": ("%", "additive", "percent"),
    "Max Recovery": ("x", "multiplicative", "multiplier"),
    "Package Chance": ("%", "additive", "percent"),
    "Enemy Attack Level Skip": ("%", "additive", "percent"),
    "Enemy Health Level Skip": ("%", "additive", "percent"),
}


def slugify(name: str) -> str:
    return ID_OVERRIDES.get(name, re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_"))


def parse_suffix_number(value: str) -> float:
    text = value.strip().replace(",", "")
    if text in {"", "Maxed"}:
        raise ValueError(f"Cannot parse numeric value: {value!r}")
    suffixes = {
        "K": 1_000,
        "M": 1_000_000,
        "B": 1_000_000_000,
        "T": 1_000_000_000_000,
        "q": 1_000_000_000_000_000,
        "Q": 1_000_000_000_000_000_000,
        "s": 1_000_000_000_000_000_000_000,
        "S": 1_000_000_000_000_000_000_000_000,
    }
    suffix = text[-1]
    if suffix in suffixes:
        return float(text[:-1]) * suffixes[suffix]
    return float(text)


def parse_coin_cost(value: str) -> int | None:
    if value.strip() == "Maxed":
        return None
    return max(round(parse_suffix_number(value)), 1)


def parse_effect_value(value: str, value_kind: str) -> float:
    text = value.strip().replace(",", "")
    if value_kind == "percent" and text.endswith("%"):
        return float(text[:-1])
    if value_kind == "multiplier" and text.endswith("x"):
        return float(text[:-1])
    if value_kind == "seconds" and text.endswith("s"):
        return float(text[:-1])
    if value_kind == "distance_m" and text.endswith("M"):
        return float(text[:-1])
    if value_kind == "suffix_number":
        return parse_suffix_number(text)
    return float(text)


def expected_targets(missing_only: bool) -> list[dict[str, str]]:
    manifest = load_reference_manifest()
    current = load_upgrades()
    loaded_names = {upgrade.name.casefold() for upgrade in current.upgrades}
    targets: list[dict[str, str]] = []
    for category in manifest["categories"]:
        category_id = category["id"]
        category_label = category["name"]
        for order, upgrade in enumerate(category["upgrades"]):
            name = upgrade["name"]
            aliases = [alias.casefold() for alias in upgrade.get("aliases", [])]
            is_loaded = name.casefold() in loaded_names or any(
                alias in loaded_names for alias in aliases
            )
            if missing_only and is_loaded:
                continue
            targets.append(
                {
                    "category": category_id,
                    "category_label": category_label,
                    "name": name,
                    "display_order": str(order),
                }
            )
    return targets


def scrape_target(page: Any, target: dict[str, str], max_pages: int) -> dict[str, Any]:
    page.locator(f'button:has-text("{target["category_label"]}")').click()
    page.wait_for_timeout(350)
    page.locator("select").select_option(label=target["name"])
    page.wait_for_timeout(500)

    rows_by_level: dict[int, dict[str, str]] = {}
    headers: list[str] = []
    for _page_number in range(max_pages):
        payload = page.evaluate(VISIBLE_ROWS_JS)
        headers = payload["headers"]
        for row in payload["rows"]:
            level = int(parse_effect_value(row["Level"], "number"))
            rows_by_level[level] = row
        if not payload["nextEnabled"]:
            break
        clicked = page.evaluate(CLICK_NEXT_JS)
        if not clicked:
            break
        page.wait_for_timeout(250)
    else:
        raise RuntimeError(f"{target['name']}: hit max_pages={max_pages}")

    rows = [rows_by_level[level] for level in sorted(rows_by_level)]
    return {
        "category": target["category"],
        "name": target["name"],
        "headers": headers,
        "rows": rows,
    }


def normalize_upgrade(raw: dict[str, Any], display_order: int) -> dict[str, Any]:
    name = raw["name"]
    unit, effect_type, value_kind = EFFECT_META.get(name, ("pts", "additive", "suffix_number"))
    rows = raw["rows"]
    if len(rows) < 2:
        raise ValueError(f"{name}: need at least base row plus one level")

    parsed_rows: list[ParsedWorkshopRow] = [
        {
            "level": int(parse_effect_value(str(row["Level"]), "number")),
            "value": parse_effect_value(str(row["Value"]), value_kind),
            "next_coin_cost": parse_coin_cost(str(row["Next Coins"])),
        }
        for row in rows
    ]
    parsed_rows.sort(key=lambda row: int(row["level"]))

    base_value = float(parsed_rows[0]["value"])
    levels: list[dict[str, float | int]] = []
    for index in range(1, len(parsed_rows)):
        current = parsed_rows[index]
        previous = parsed_rows[index - 1]
        coin_cost = previous["next_coin_cost"]
        if coin_cost is None:
            break
        value = float(current["value"])
        previous_value = float(previous["value"])
        levels.append(
            {
                "level": index,
                "coin_cost": int(coin_cost),
                "cumulative_effect": round(value, 6),
                "effect_delta": round(value - previous_value, 6),
            }
        )

    if not levels:
        raise ValueError(f"{name}: no purchasable levels found")

    return {
        "id": slugify(name),
        "name": name,
        "category": raw["category"],
        "effect_unit": unit,
        "effect_type": effect_type,
        "base_value": round(base_value, 6),
        "max_level": len(levels),
        "display_order": display_order,
        "levels": levels,
    }


def merge_upgrades(new_upgrades: list[dict[str, Any]]) -> UpgradeDatabase:
    current = json.loads(UPGRADES_PATH.read_text(encoding="utf-8"))
    existing = {upgrade["name"].casefold(): upgrade for upgrade in current["upgrades"]}
    for upgrade in new_upgrades:
        existing[upgrade["name"].casefold()] = upgrade

    reference_order: dict[str, int] = {}
    order = 0
    for category in load_reference_manifest()["categories"]:
        for upgrade in category["upgrades"]:
            reference_order[upgrade["name"].casefold()] = order
            order += 1

    merged = sorted(
        existing.values(),
        key=lambda item: reference_order.get(item["name"].casefold(), 999),
    )
    for display_order, upgrade in enumerate(merged):
        upgrade["display_order"] = display_order

    candidate = {
        **current,
        "version": "public-visible-2026-06-15",
        "source": (
            "Merged from existing bundled data plus visible table scrape from "
            "https://tower-workshop-calculator.netlify.app/"
        ),
        "upgrades": merged,
    }
    return UpgradeDatabase.model_validate(candidate)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Scrape all public workshop upgrades.")
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Replace data/upgrades.json after validation.",
    )
    parser.add_argument(
        "--from-raw",
        action="store_true",
        help=f"Normalize the existing raw scrape at {RAW_VISIBLE_PATH}.",
    )
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    if args.from_raw:
        raw_upgrades = json.loads(RAW_VISIBLE_PATH.read_text(encoding="utf-8"))
        print(f"Loaded raw visible scrape from {RAW_VISIBLE_PATH}")
    else:
        targets = expected_targets(missing_only=not args.all)
        print(f"Scraping {len(targets)} upgrades from {SITE_URL}")

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print(
                "ERROR: install extraction deps first: "
                "pip install -e '.[extract]' && playwright install chromium"
            )
            return 1

        raw_upgrades = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not args.headful)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.set_default_timeout(20_000)
            page.goto(SITE_URL, wait_until="load", timeout=60_000)
            page.wait_for_load_state("networkidle", timeout=30_000)
            try:
                checkbox = page.locator('input[type="checkbox"]').first
                if checkbox.is_visible(timeout=5_000):
                    checkbox.check()
                    page.locator('button:has-text("Continue")').click()
            except Exception:
                pass
            page.locator('button:has-text("Data")').click()
            page.locator('button:has-text("Upgrades")').click()
            page.wait_for_selector("select", timeout=20_000)

            for index, target in enumerate(targets, start=1):
                raw = scrape_target(page, target, args.max_pages)
                raw_upgrades.append(raw)
                last_level = raw["rows"][-1]["Level"] if raw["rows"] else "?"
                print(
                    f"[{index:02}/{len(targets):02}] {target['name']}: "
                    f"{len(raw['rows'])} rows, last {last_level}"
                )
            browser.close()

        RAW_VISIBLE_PATH.write_text(json.dumps(raw_upgrades, indent=2), encoding="utf-8")
        print(f"Saved raw visible scrape to {RAW_VISIBLE_PATH}")

    normalized = [
        normalize_upgrade(raw, display_order=index)
        for index, raw in enumerate(raw_upgrades, start=1)
    ]
    merged_db = merge_upgrades(normalized)
    result = validate_upgrade_data(merged_db)
    if not result.ok:
        print(result.summary())
        return 1

    coverage = compute_coverage(merged_db)
    print(
        json.dumps(
            {
                "coverage": coverage,
                "elapsed_seconds": round(time.monotonic() - started, 2),
            },
            indent=2,
        )
    )
    if args.merge:
        save_upgrades(merged_db, UPGRADES_PATH)
        print(f"Merged {len(normalized)} upgrades into {UPGRADES_PATH}")
    else:
        out_path = RAW_DIR / "merged_visible_candidate.json"
        out_path.write_text(merged_db.model_dump_json(indent=2), encoding="utf-8")
        print(f"Saved validated candidate to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
