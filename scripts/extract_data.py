#!/usr/bin/env python3
"""Extract upgrade data from the Tower Workshop Calculator reference site.

Usage:
    python scripts/extract_data.py

Extraction priority (3-tier):
    1. Network interception — intercept JSON/XHR responses for embedded data
    2. JS bundle analysis — download and parse the main JS bundle for data arrays
    3. DOM scraping — traverse the rendered DOM as last resort

Requires: pip install -e ".[extract]" && playwright install chromium

Raw artifacts are saved to data/raw/ (gitignored).
Normalized output is saved to data/upgrades.json.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
UPGRADES_PATH = DATA_DIR / "upgrades.json"

REFERENCE_URL = "https://tower-workshop-calculator.netlify.app/"
BUNDLE_URL = REFERENCE_URL + "static/js/main.ef115c63.js"


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Tier 1: Network Interception
# ---------------------------------------------------------------------------

async def extract_via_network(page) -> dict | None:  # type: ignore[no-untyped-def]
    """Listen for XHR/fetch responses that contain upgrade data."""
    print("[Tier 1] Attempting network interception...")

    captured: list[dict] = []

    async def handle_response(response) -> None:  # type: ignore[no-untyped-def]
        url = response.url
        content_type = response.headers.get("content-type", "")
        if "json" in content_type or url.endswith(".json"):
            try:
                body = await response.json()
                captured.append({"url": url, "data": body})
                print(f"  [Tier 1] Captured JSON from: {url}")
            except Exception:
                pass

    page.on("response", handle_response)

    await page.goto(REFERENCE_URL, wait_until="networkidle")
    await asyncio.sleep(3)  # Wait for any lazy-loaded data

    if captured:
        raw_path = RAW_DIR / "network_responses.json"
        raw_path.write_text(json.dumps(captured, indent=2), encoding="utf-8")
        print(f"  [Tier 1] Saved {len(captured)} responses to {raw_path}")

        # Check if any captured response looks like upgrade data
        for item in captured:
            data = item["data"]
            if _looks_like_upgrade_data(data):
                print("  [Tier 1] Found upgrade data in network response!")
                return data

    print("  [Tier 1] No upgrade data found in network responses.")
    return None


# ---------------------------------------------------------------------------
# Tier 2: JS Bundle Analysis
# ---------------------------------------------------------------------------

async def extract_via_bundle(page) -> dict | None:  # type: ignore[no-untyped-def]
    """Download the main JS bundle and search for embedded data structures."""
    print("[Tier 2] Attempting JS bundle analysis...")

    try:
        import httpx

        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(BUNDLE_URL)
            if resp.status_code != 200:
                print(f"  [Tier 2] Failed to download bundle: HTTP {resp.status_code}")
                return None

            bundle = resp.text
            raw_path = RAW_DIR / "bundle.js"
            raw_path.write_text(bundle, encoding="utf-8")
            print(f"  [Tier 2] Downloaded bundle ({len(bundle):,} chars) to {raw_path}")

            return _parse_bundle_for_data(bundle)

    except ImportError:
        print("  [Tier 2] httpx not installed. Run: pip install -e '.[extract]'")
        return None
    except Exception as e:
        print(f"  [Tier 2] Error: {e}")
        return None


def _parse_bundle_for_data(bundle: str) -> dict | None:
    """Search the minified JS bundle for embedded upgrade data.

    Looks for patterns like:
    - Arrays of objects with upgrade-like fields
    - String arrays with known upgrade names
    - JSON-serialized data constants
    """
    # Known upgrade name patterns to search for
    known_names = [
        "Attack Speed", "Damage", "Critical Chance", "Critical Factor",
        "Health", "Health Regen", "Defense", "Thorns",
        "Coins per Kill", "Coins per Wave", "Interest",
        "Land Mines", "Death Defy", "Orb Speed",
    ]

    found_names: list[str] = []
    for name in known_names:
        if name in bundle:
            found_names.append(name)

    if found_names:
        print(f"  [Tier 2] Found {len(found_names)} upgrade names in bundle: {found_names[:5]}...")
    else:
        print("  [Tier 2] No known upgrade names found in bundle.")
        return None

    # Try to find JSON-like data structures near upgrade names
    # Look for patterns like: [{name:"Attack Speed",... or {"Attack Speed":...
    # This is heuristic and may need refinement

    # Pattern 1: Array of objects with "name" field
    pattern1 = re.compile(
        r'\[\s*\{[^}]*?"name"\s*:\s*"[^"]*Attack[^"]*"[^]]*\]',
        re.DOTALL,
    )
    matches = pattern1.findall(bundle)
    if matches:
        for m in matches[:3]:
            print(f"  [Tier 2] Found potential data array ({len(m)} chars)")
            try:
                data = json.loads(m)
                if isinstance(data, list) and len(data) > 5:
                    print(f"  [Tier 2] Parsed {len(data)} items from array!")
                    return {"raw_upgrades": data, "source": "bundle_array"}
            except json.JSONDecodeError:
                pass

    # Pattern 2: Look for large object literals with numeric arrays (costs)
    # This finds patterns like: costs:[100,250,500,...] or cost:[100,250,500,...]
    cost_pattern = re.compile(r'cost[s]?\s*:\s*\[(\d[\d,\s]+)\]')
    cost_matches = cost_pattern.findall(bundle)
    if cost_matches:
        print(f"  [Tier 2] Found {len(cost_matches)} cost-like arrays")

    print("  [Tier 2] Could not parse structured data from bundle (needs manual review).")
    print(f"  [Tier 2] Raw bundle saved to {RAW_DIR / 'bundle.js'} for inspection.")
    return None


# ---------------------------------------------------------------------------
# Tier 3: DOM Scraping
# ---------------------------------------------------------------------------

async def extract_via_dom(page) -> dict | None:  # type: ignore[no-untyped-def]
    """Scrape the rendered DOM for upgrade data."""
    print("[Tier 3] Attempting DOM scraping...")

    await page.goto(REFERENCE_URL, wait_until="networkidle")
    await asyncio.sleep(5)  # Wait for React to render

    # Save raw HTML
    html = await page.content()
    raw_path = RAW_DIR / "page.html"
    raw_path.write_text(html, encoding="utf-8")
    print(f"  [Tier 3] Saved rendered HTML ({len(html):,} chars) to {raw_path}")

    # Extract categories and upgrades from DOM
    data = await page.evaluate("""
    () => {
        const result = { categories: [] };

        // Find category sections
        const categories = document.querySelectorAll('.category');
        if (categories.length === 0) {
            // Try alternative selectors
            const sections = document.querySelectorAll('.upgrade-section, [class*="category"]');
            if (sections.length === 0) {
                return { error: "No category elements found", html_length: document.body.innerHTML.length };
            }
        }

        categories.forEach(cat => {
            const catData = {
                name: '',
                upgrades: []
            };

            // Get category name
            const nameEl = cat.querySelector('.category-name');
            if (nameEl) catData.name = nameEl.textContent.trim();

            // Determine category type from class
            if (cat.classList.contains('attack')) catData.type = 'offense';
            else if (cat.classList.contains('defense')) catData.type = 'defense';
            else if (cat.classList.contains('utility')) catData.type = 'economy';
            else catData.type = 'unknown';

            // Get upgrades within category
            const upgrades = cat.querySelectorAll('.upgrade');
            upgrades.forEach(u => {
                const upgrade = {
                    name: '',
                    values: {}
                };

                // Get upgrade name
                const nameBtn = u.querySelector('.name-button, .upgrade-name');
                if (nameBtn) upgrade.name = nameBtn.textContent.trim();

                // Get current/target values
                const currentEl = u.querySelector('.current input, .current');
                const targetEl = u.querySelector('.target input, .target');
                if (currentEl) upgrade.values.current = currentEl.value || currentEl.textContent.trim();
                if (targetEl) upgrade.values.target = targetEl.value || targetEl.textContent.trim();

                // Get cost
                const costEl = u.querySelector('.cost');
                if (costEl) upgrade.values.cost = costEl.textContent.trim();

                if (upgrade.name) catData.upgrades.push(upgrade);
            });

            if (catData.upgrades.length > 0) result.categories.push(catData);
        });

        return result;
    }
    """)

    if data and "categories" in data and data["categories"]:
        print(f"  [Tier 3] Found {len(data['categories'])} categories with upgrades")
        raw_path = RAW_DIR / "dom_extracted.json"
        raw_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data
    else:
        print(f"  [Tier 3] DOM extraction returned: {data}")
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _looks_like_upgrade_data(data: object) -> bool:
    """Heuristic: does this data look like upgrade definitions?"""
    if isinstance(data, list):
        if len(data) > 5 and isinstance(data[0], dict):
            keys = set(data[0].keys())
            upgrade_keys = {"name", "cost", "level", "effect", "category", "type"}
            if keys & upgrade_keys:
                return True
    if isinstance(data, dict):
        if any(k in data for k in ("upgrades", "workshops", "permanent")):
            return True
    return False


def normalize_to_schema(raw_data: dict) -> dict:
    """Convert raw extracted data to the UpgradeDatabase JSON schema.

    This is a template — the exact normalization depends on what tier
    successfully extracted data and what format it returned.
    """
    normalized: dict = {
        "version": "extracted",
        "game_version": "unknown",
        "source": "tower-workshop-calculator.netlify.app",
        "upgrades": [],
    }

    # Handle Tier 3 DOM data
    if "categories" in raw_data:
        category_map = {"attack": "offense", "defense": "defense", "utility": "economy"}
        display_order = 0

        for cat in raw_data["categories"]:
            cat_type = cat.get("type", "unknown")
            for u in cat.get("upgrades", []):
                display_order += 1
                name = u.get("name", "")
                upgrade_id = name.lower().replace(" ", "_").replace("/", "_")

                normalized["upgrades"].append({
                    "id": upgrade_id,
                    "name": name,
                    "category": cat_type,
                    "effect_unit": "unknown",
                    "effect_type": "additive",
                    "base_value": 0,
                    "max_level": 1,
                    "display_order": display_order,
                    "levels": [],  # Needs per-level data — may require iterating the UI
                })

    return normalized


def validate_extracted(data: dict) -> list[str]:
    """Basic validation of extracted data before saving."""
    errors = []

    upgrades = data.get("upgrades", [])
    if not upgrades:
        errors.append("No upgrades extracted")
        return errors

    ids_seen: set[str] = set()
    for i, u in enumerate(upgrades):
        uid = u.get("id", f"upgrade_{i}")

        if uid in ids_seen:
            errors.append(f"Duplicate ID: {uid}")
        ids_seen.add(uid)

        levels = u.get("levels", [])
        if not levels:
            errors.append(f"{uid}: no levels data")

        for lv in levels:
            cost = lv.get("coin_cost")
            if not isinstance(cost, (int, float)) or cost <= 0:
                errors.append(f"{uid} level {lv.get('level')}: invalid cost {cost}")

            effect = lv.get("cumulative_effect")
            if isinstance(effect, str):
                errors.append(f"{uid} level {lv.get('level')}: string effect '{effect}'")

    return errors


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

async def extract_all() -> None:
    """Run all extraction tiers in order until one succeeds."""
    ensure_dirs()

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("ERROR: Playwright not installed.")
        print("Run: pip install -e '.[extract]' && playwright install chromium")
        sys.exit(1)

    print(f"Starting extraction from {REFERENCE_URL}")
    print(f"Raw artifacts will be saved to {RAW_DIR}")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        raw_data = None

        # Tier 1: Network Interception
        try:
            raw_data = await extract_via_network(page)
        except Exception as e:
            print(f"  [Tier 1] Error: {e}")

        # Tier 2: JS Bundle Analysis
        if raw_data is None:
            try:
                raw_data = await extract_via_bundle(page)
            except Exception as e:
                print(f"  [Tier 2] Error: {e}")

        # Tier 3: DOM Scraping
        if raw_data is None:
            try:
                raw_data = await extract_via_dom(page)
            except Exception as e:
                print(f"  [Tier 3] Error: {e}")

        await browser.close()

    if raw_data is None:
        print()
        print("FAILED: No tier succeeded in extracting data.")
        print("Options:")
        print("  1. Check if the reference site is accessible")
        print("  2. Run with headed browser: modify headless=False")
        print("  3. Try manual data entry with scripts/manual_import.py")
        sys.exit(1)

    # Save raw extraction
    raw_path = RAW_DIR / "extracted.json"
    raw_path.write_text(json.dumps(raw_data, indent=2), encoding="utf-8")
    print(f"\nRaw data saved to {raw_path}")

    # Normalize
    normalized = normalize_to_schema(raw_data)

    # Validate
    errors = validate_extracted(normalized)
    if errors:
        print(f"\nValidation found {len(errors)} issues:")
        for e in errors:
            print(f"  - {e}")
        print("\nSaving anyway — manual review needed.")

    # Save normalized output
    UPGRADES_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    print(f"\nNormalized data saved to {UPGRADES_PATH}")
    print(f"Upgrades extracted: {len(normalized.get('upgrades', []))}")


if __name__ == "__main__":
    asyncio.run(extract_all())
