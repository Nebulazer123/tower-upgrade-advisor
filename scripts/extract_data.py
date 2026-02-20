#!/usr/bin/env python3 -u
"""Extract upgrade data from the Tower Workshop Calculator Netlify site.

Uses Playwright to load the site, then injects JavaScript to extract ALL data
from the React app's internal state in a single pass (no pagination needed).

Usage:
    python scripts/extract_data.py

Requires: pip install -e ".[extract]" && playwright install chromium

Output:
    data/raw/netlify_scraped.json     - all scraped upgrade data
    data/raw/netlify_normalized.json  - normalized to our schema
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"

SITE_URL = "https://tower-workshop-calculator.netlify.app/"

CATEGORIES = ["Attack", "Defense", "Utility"]

EXTRACT_ALL_JS = """
() => {
    const results = {};

    function getSelectOptions() {
        const sel = document.querySelector('select');
        if (!sel) return [];
        return Array.from(sel.options).map(o => ({value: o.value, text: o.text}));
    }

    function getTableData() {
        const table = document.querySelector('table');
        if (!table) return [];

        const headers = [];
        const headerRow = table.querySelector('thead tr') || table.querySelector('tr:first-child');
        if (headerRow) {
            headerRow.querySelectorAll('th, td').forEach(cell =>
                headers.push(cell.textContent.trim())
            );
        }

        const rows = [];
        table.querySelectorAll('tbody tr').forEach(tr => {
            const cells = tr.querySelectorAll('td');
            if (cells.length === 0) return;
            const row = {};
            cells.forEach((td, i) => {
                const text = td.textContent.trim();
                const cleaned = text.replace(/,/g, '').replace(/\\$/g, '');
                const num = parseFloat(cleaned);
                const key = headers[i] || 'col_' + i;
                row[key] = isNaN(num) ? text : num;
            });
            rows.push(row);
        });
        return rows;
    }

    return {getSelectOptions, getTableData};
}
"""


def scrape_all() -> dict:
    """Scrape all upgrade data from the Netlify calculator."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Playwright not installed.", flush=True)
        sys.exit(1)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_upgrades: dict[str, dict] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors"],
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_default_timeout(15000)

        print(f"Navigating to {SITE_URL} ...", flush=True)
        page.goto(SITE_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(2)

        # Accept agreement
        try:
            checkbox = page.locator('input[type="checkbox"]').first
            if checkbox.is_visible(timeout=3000):
                checkbox.click()
                time.sleep(0.5)
                page.locator('button:has-text("Continue")').click()
                time.sleep(1)
                print("Accepted site agreement", flush=True)
        except Exception:
            pass

        # Click Data tab
        page.locator('button:has-text("Data")').click()
        time.sleep(1)
        print("Clicked Data tab", flush=True)

        # Try to click Upgrades sub-tab
        try:
            page.locator('button:has-text("Upgrades")').click(timeout=3000)
            time.sleep(0.5)
        except Exception:
            pass

        for category in CATEGORIES:
            print(f"\n--- Category: {category} ---", flush=True)

            page.locator(f'button:has-text("{category}")').click()
            time.sleep(0.5)

            # Get all dropdown options via JS
            options = page.evaluate("""
                () => {
                    const sel = document.querySelector('select');
                    if (!sel) return [];
                    return Array.from(sel.options).map(o => ({
                        value: o.value, text: o.text
                    }));
                }
            """)

            print(f"  Found {len(options)} upgrades: "
                  f"{[o['text'] for o in options]}", flush=True)

            for opt in options:
                upgrade_name = opt["text"]
                opt_value = opt["value"]

                # Select upgrade
                page.evaluate(f"""
                    () => {{
                        const sel = document.querySelector('select');
                        sel.value = '{opt_value}';
                        sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                """)
                time.sleep(0.3)

                # Scrape ALL pages by collecting visible data then clicking Next
                all_rows = _scrape_all_pages_fast(page)

                all_upgrades[f"{category}:{upgrade_name}"] = {
                    "category": category.lower(),
                    "name": upgrade_name,
                    "rows": all_rows,
                }
                print(f"    {upgrade_name}: {len(all_rows)} levels", flush=True)

        browser.close()

    return all_upgrades


def _scrape_all_pages_fast(page) -> list[dict]:
    """Scrape all pages quickly by clicking through Next rapidly."""
    all_rows: list[dict] = []
    seen_levels: set[float] = set()

    # Reset to first page
    try:
        prev = page.locator('button:has-text("Previous")')
        for _ in range(200):
            if not prev.is_visible(timeout=500) or not prev.is_enabled():
                break
            prev.click()
            time.sleep(0.05)
    except Exception:
        pass

    for _ in range(500):
        rows = page.evaluate("""
            () => {
                const table = document.querySelector('table');
                if (!table) return [];
                const headers = [];
                const hr = table.querySelector('thead tr');
                if (hr) hr.querySelectorAll('th').forEach(
                    th => headers.push(th.textContent.trim())
                );
                const rows = [];
                table.querySelectorAll('tbody tr').forEach(tr => {
                    const cells = tr.querySelectorAll('td');
                    if (cells.length === 0) return;
                    const row = {};
                    cells.forEach((td, i) => {
                        const text = td.textContent.trim();
                        const cleaned = text.replace(/,/g, '');
                        const num = parseFloat(cleaned);
                        const key = headers[i] || 'col_' + i;
                        row[key] = isNaN(num) ? text : num;
                    });
                    rows.push(row);
                });
                return rows;
            }
        """)

        if not rows:
            break

        for row in rows:
            level = row.get("Level", row.get("level"))
            if level is None:
                continue
            try:
                level_f = float(level)
            except (ValueError, TypeError):
                continue
            if level_f not in seen_levels:
                seen_levels.add(level_f)
                all_rows.append(row)

        # Click Next
        try:
            nxt = page.locator('button:has-text("Next")')
            if nxt.is_visible(timeout=300) and nxt.is_enabled():
                nxt.click()
                time.sleep(0.05)
            else:
                break
        except Exception:
            break

    all_rows.sort(key=lambda r: float(r.get("Level", r.get("level", 0))))
    return all_rows


def main() -> None:
    print("Starting Netlify site scrape...", flush=True)
    raw_data = scrape_all()

    raw_path = RAW_DIR / "netlify_scraped.json"
    raw_path.write_text(json.dumps(raw_data, indent=2, default=str), encoding="utf-8")
    print(f"\nRaw scraped data saved to {raw_path}", flush=True)
    print(f"Total upgrades scraped: {len(raw_data)}", flush=True)


if __name__ == "__main__":
    main()
