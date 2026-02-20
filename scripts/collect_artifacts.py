#!/usr/bin/env python3
"""Visit the Tower Workshop Calculator, collect artifacts, and save for review.

Creates:
  - artifacts/screenshots/  - Page screenshots at each step
  - artifacts/sample_data.json - Sample upgrade data (one per category)
  - artifacts/site_structure.json - Dropdown options, categories, etc.
  - artifacts/summary.txt - Human-readable summary
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
SITE_URL = "https://tower-workshop-calculator.netlify.app/"


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: pip install -e '.[extract]' && playwright install chromium")
        sys.exit(1)

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    summary_lines: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--ignore-certificate-errors"],
        )
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        page.set_viewport_size({"width": 1280, "height": 800})
        page.set_default_timeout(15000)

        def screenshot(name: str) -> None:
            path = SCREENSHOTS_DIR / f"{name}.png"
            page.screenshot(path=path)
            summary_lines.append(f"  Screenshot: {path.name}")

        # 1. Landing
        print("Navigating to site...")
        page.goto(SITE_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_load_state("networkidle", timeout=30000)
        time.sleep(1)
        screenshot("01_landing")
        summary_lines.append("Step 1: Landing page captured")

        # 2. Accept agreement
        try:
            page.locator('input[type="checkbox"]').first.click()
            time.sleep(0.3)
            page.locator('button:has-text("Continue")').click()
            time.sleep(1)
            screenshot("02_after_agreement")
            summary_lines.append("Step 2: Agreement accepted")
        except Exception as e:
            summary_lines.append(f"Step 2: Agreement skipped ({e})")

        # 3. Click Data tab
        page.locator('button:has-text("Data")').click()
        time.sleep(1)
        screenshot("03_data_tab")
        summary_lines.append("Step 3: Data tab opened")

        # 4. Collect structure (categories, dropdown options)
        structure: dict = {"categories": ["Attack", "Defense", "Utility"]}
        sample_data: dict = {}

        for category in structure["categories"]:
            page.locator(f'button:has-text("{category}")').click()
            time.sleep(0.5)

            options = page.evaluate("""
                () => {
                    const sel = document.querySelector('select');
                    if (!sel) return [];
                    return Array.from(sel.options).map(o => ({value: o.value, text: o.text}));
                }
            """)

            structure[f"{category}_upgrades"] = [o["text"] for o in options]
            summary_lines.append(f"  {category}: {len(options)} upgrades")

            # Sample first upgrade in each category
            if options:
                first_opt = options[0]
                page.evaluate(f"""
                    () => {{
                        const sel = document.querySelector('select');
                        sel.value = '{first_opt["value"]}';
                        sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                """)
                time.sleep(0.5)

                # Paginate and collect all rows for sample
                all_rows: list = []
                seen: set = set()
                for _ in range(500):
                    rows = page.evaluate("""
                        () => {
                            const table = document.querySelector('table');
                            if (!table) return [];
                            const headers = [];
                            const hr = table.querySelector('thead tr');
                            if (hr) hr.querySelectorAll('th').forEach(th => headers.push(th.textContent.trim()));
                            const rows = [];
                            table.querySelectorAll('tbody tr').forEach(tr => {
                                const cells = tr.querySelectorAll('td');
                                if (cells.length === 0) return;
                                const row = {};
                                cells.forEach((td, i) => {
                                    const text = td.textContent.trim();
                                    const key = headers[i] || 'col_' + i;
                                    row[key] = text;
                                });
                                rows.push(row);
                            });
                            return rows;
                        }
                    """)
                    if not rows:
                        break
                    for r in rows:
                        lvl = r.get("Level", r.get("level", ""))
                        if lvl not in seen:
                            seen.add(lvl)
                            all_rows.append(r)
                    nxt = page.locator('button:has-text("Next")')
                    if nxt.is_visible(timeout=500) and nxt.is_enabled():
                        nxt.click()
                        time.sleep(0.08)
                    else:
                        break

                sample_data[f"{category}:{first_opt['text']}"] = {
                    "upgrade": first_opt["text"],
                    "category": category,
                    "row_count": len(all_rows),
                    "sample_rows": all_rows[:5],
                    "last_rows": all_rows[-3:] if len(all_rows) > 5 else [],
                }
                summary_lines.append(f"    Sample '{first_opt['text']}': {len(all_rows)} levels")

        screenshot("04_defense_health_sample")
        browser.close()

    # Save artifacts
    (ARTIFACTS_DIR / "site_structure.json").write_text(
        json.dumps(structure, indent=2), encoding="utf-8"
    )
    (ARTIFACTS_DIR / "sample_data.json").write_text(
        json.dumps(sample_data, indent=2, default=str), encoding="utf-8"
    )
    (ARTIFACTS_DIR / "summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    print("\n" + "\n".join(summary_lines))
    print(f"\nArtifacts saved to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
