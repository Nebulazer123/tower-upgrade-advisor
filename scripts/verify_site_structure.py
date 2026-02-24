#!/usr/bin/env python3 -u
"""Verify Tower Workshop Calculator site structure - categories and upgrade counts.

Quick diagnostic: navigate to site, accept consent, go to Data->Upgrades,
and enumerate dropdown options for each category. No full scrape.

Usage:
    python scripts/verify_site_structure.py
    python scripts/verify_site_structure.py --no-headless  # see browser
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

SITE_URL = "https://tower-workshop-calculator.netlify.app/"
CATEGORIES = ["Attack", "Defense", "Utility"]


def verify() -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright not installed. pip install playwright && playwright install chromium")
        sys.exit(1)

    result = {"categories": {}, "summary": {}}

    with sync_playwright() as p:
        show_browser = "--no-headless" in sys.argv
        browser = p.chromium.launch(headless=not show_browser)
        page = browser.new_page()
        page.set_default_timeout(20000)

        print("Navigating...")
        page.goto(SITE_URL, wait_until="load", timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        import time
        time.sleep(3)

        # Consent
        try:
            cb = page.locator('input[type="checkbox"]').first
            if cb.is_visible(timeout=5000):
                cb.check()
                time.sleep(0.5)
                page.locator('button:has-text("Continue")').click()
                time.sleep(1.5)
                print("Accepted consent")
        except Exception as e:
            print(f"Consent: {e}")

        # Data -> Upgrades
        page.locator('button:has-text("Data")').click()
        time.sleep(1)
        page.locator('button:has-text("Upgrades")').click()
        time.sleep(1)

        for cat in CATEGORIES:
            print(f"\n--- {cat} ---")
            page.locator(f'button:has-text("{cat}")').click()
            time.sleep(1)

            opts = page.evaluate("""
                () => {
                    const sel = document.querySelector('select');
                    if (!sel) return [];
                    return Array.from(sel.options).map(o => o.text);
                }
            """)
            result["categories"][cat] = opts
            result["summary"][cat] = len(opts)
            print(f"  {len(opts)} upgrades: {opts}")

        browser.close()

    total = sum(result["summary"].values())
    result["summary"]["total"] = total
    print(f"\n=== TOTAL: {total} upgrades across {len(CATEGORIES)} categories ===")
    return result


if __name__ == "__main__":
    out = verify()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / "site_structure_verified.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"\nSaved to {path}")
