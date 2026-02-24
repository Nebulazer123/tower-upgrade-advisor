#!/usr/bin/env python3
"""QA manual test: navigate Tower Upgrade Advisor, capture screenshots, report issues.

Run with: python scripts/qa_manual_test.py
Requires: pip install -e ".[extract]" && playwright install chromium
Flask app must be running at http://127.0.0.1:5000/
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
QA_DIR = PROJECT_ROOT / "qa_artifacts"
SCREENSHOTS_DIR = QA_DIR / "screenshots"
BASE_URL = "http://127.0.0.1:5000"


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: pip install -e '.[extract]' && playwright install chromium")
        sys.exit(1)

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    issues: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()
        page.set_default_timeout(10000)

        def screenshot(name: str) -> Path:
            path = SCREENSHOTS_DIR / f"{name}.png"
            page.screenshot(path=path)
            return path

        def check_visible(selector: str, msg: str) -> bool:
            try:
                el = page.locator(selector).first
                if not el.is_visible(timeout=2000):
                    issues.append({"type": "visibility", "msg": msg, "selector": selector})
                    return False
            except Exception as e:
                issues.append({"type": "visibility", "msg": msg, "error": str(e)})
                return False
            return True

        # --- 1. Profiles page ---
        print("1. Navigating to profiles...")
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=5000)
        time.sleep(0.5)
        screenshot("01_profiles")
        check_visible('input[name="name"]', "Profile name input should be visible")
        check_visible('button:has-text("Create")', "Create button should be visible")

        # --- 2. Create profile "QA Test" ---
        print("2. Creating profile 'QA Test'...")
        page.fill('input[name="name"]', "QA Test")
        page.click('button:has-text("Create")')
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)

        if "/profile/" not in page.url:
            issues.append({"type": "functional", "msg": "Create profile did not redirect to dashboard"})

        screenshot("02_dashboard")

        # --- 3. Dashboard: check elements ---
        print("3. Checking dashboard...")
        check_visible('h1:has-text("QA Test")', "Dashboard should show profile name")
        check_visible('#coins-input', "Coins input should be visible on dashboard")
        check_visible('.upgrade-table', "Upgrade table should be visible")
        check_visible('.level-input', "Level inputs should exist")

        # Test coins update (HTMX) - wait for the POST request to complete
        with page.expect_response(lambda r: "/coins" in r.url and r.request.method == "POST", timeout=5000) as resp_info:
            coins_input = page.locator('#coins-input').first
            coins_input.fill("1000000")
            coins_input.blur()
        resp = resp_info.value
        time.sleep(0.4)  # Allow HTMX swap to complete
        coins_display = page.locator('#coins-display-dashboard').first
        display_text = coins_display.text_content() or ""
        if resp.status != 200:
            issues.append({"type": "htmx", "msg": f"Coins HTMX returned {resp.status}"})
        elif "1,000,000" not in display_text:
            issues.append({"type": "htmx", "msg": f"Coins display not updated (got: {display_text!r})"})

        screenshot("03_dashboard_coins_updated")

        # Test level change in first upgrade row
        first_level_input = page.locator('.level-input').first
        if first_level_input.is_visible():
            first_level_input.fill("1")
            first_level_input.press("Enter")
            time.sleep(0.6)
            # Check row updated (cost/effect changed)
            screenshot("04_dashboard_level_changed")

        # --- 4. Recommendations page ---
        print("4. Navigating to recommendations...")
        page.click('a:has-text("Get Recommendation")')
        page.wait_for_load_state("networkidle")
        time.sleep(0.5)
        screenshot("05_recommendations")

        check_visible('.weight-controls', "Weight controls should be visible")
        check_visible('.slider', "Sliders should be visible")

        # Test weight sliders
        sliders = page.locator('input[type="range"]')
        if sliders.count() >= 3:
            attack_slider = sliders.nth(0)
            attack_slider.fill("1.5")
            time.sleep(0.5)
            # HTMX triggers on change
            time.sleep(0.8)
            screenshot("06_recommendations_slider_moved")

        # Test level +/- buttons (only click enabled ones)
        plus_btn = page.locator('button[aria-label="Increase level"]').first
        if plus_btn.is_visible() and plus_btn.is_enabled():
            plus_btn.click()
            time.sleep(0.8)
            screenshot("07_recommendations_level_plus")
        minus_btn = page.locator('button[aria-label="Decrease level"]').first
        if minus_btn.is_visible() and minus_btn.is_enabled():
            minus_btn.click()
            time.sleep(0.8)
            screenshot("08_recommendations_level_minus")

        # --- 5. Layout checks ---
        print("5. Checking layout...")
        # Coins editor on recommend page: dashboard uses #coins-input, recommend uses #coins-input-recommend
        rec_coins = page.locator('#coins-input-recommend')
        if rec_coins.count() == 0:
            issues.append({"type": "ux", "msg": "Recommend page coins input has id coins-input-recommend but may conflict with display"})

        # Check for duplicate IDs (each page should have one coins display)
        coins_displays = page.locator('[id^="coins-display-"]')
        if coins_displays.count() > 1:
            issues.append({"type": "ux", "msg": "Multiple coins-display elements on page - possible ID conflict"})

        # --- 6. Responsive check (narrow viewport) ---
        print("6. Testing responsive layout...")
        page.set_viewport_size({"width": 400, "height": 800})
        time.sleep(0.3)
        screenshot("09_responsive_400px")
        page.set_viewport_size({"width": 1280, "height": 900})

        browser.close()

    # --- Report ---
    report_path = QA_DIR / "qa_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# QA Test Report - Tower Upgrade Advisor\n\n")
        f.write("## Screenshots\n\n")
        for p in sorted(SCREENSHOTS_DIR.glob("*.png")):
            f.write(f"- `{p.name}`\n")
        f.write("\n## Issues Found\n\n")
        if not issues:
            f.write("No issues automatically detected.\n")
        else:
            for i, iss in enumerate(issues, 1):
                f.write(f"### {i}. [{iss.get('type', 'unknown')}]\n")
                f.write(f"{iss['msg']}\n")
                for k, v in iss.items():
                    if k not in ("type", "msg"):
                        f.write(f"- {k}: {v}\n")
                f.write("\n")

    print(f"\nScreenshots: {SCREENSHOTS_DIR}")
    print(f"Report: {report_path}")
    if issues:
        print(f"\n{len(issues)} potential issue(s) logged.")


if __name__ == "__main__":
    main()
