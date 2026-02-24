# Scraping Issues & Fixes — Summary

## Yes, We Talked About This

From **UTILITY_UPGRADES_ADDED.md**:
> "Netlify calculator: Has all three categories but **scraping produced corrupted data**"  
> "Fix Netlify scraper: Debug why the scraper produces garbled text"

---

## 1. Site Verification ✅ DONE

**The site has all 3 categories and 48 upgrades.**

Run: `python scripts/verify_site_structure.py`

| Category | Count | Upgrades |
|----------|-------|----------|
| **Attack** | 17 | Damage, Attack Speed, Critical Chance, Critical Factor, Range, Damage / Meter, Multishot Chance, Multishot Targets, Rapid Fire Chance, Rapid Fire Duration, Bounce Shot Chance, Bounce Shot Targets, Bounce Shot Range, Super Crit Chance, Super Crit Mult, Rend Armor Chance, Rend Armor Mult |
| **Defense** | 18 | Health, Health Regen, Defense Percent, Defense Absolute, Thorns, Lifesteal, Knockback Chance, Knockback Force, Orb Speed, Orbs, Shockwave Size, Shockwave Frequency, Land Mine Chance, Land Mine Damage, Land Mine Radius, Death Defy, Wall Health, Wall Rebuild |
| **Utility** | 13 | Cash Bonus, Cash / Wave, Coins / Kill Bonus, Coins / Wave, Free Attack Upgrade, Free Defense Upgrade, Free Utility Upgrade, Interest / Wave, Recovery Amount, Max Recovery, Package Chance, Enemy Attack Level Skip, Enemy Health Level Skip |
| **TOTAL** | **48** | |

Output saved to: `data/raw/site_structure_verified.json`

---

## 2. Problems Found

### A. `netlify_scraped.json` — Only Attack:Damage

- **Before**: File contained only `"Attack:Damage"` with corrupted data
- **Why**: Python `extract_data.py` either crashed early or produced garbled output
- **Current**: With fixes, the script now processes all 3 categories and saves 6+ upgrades in quick mode

### B. Corrupted Data (Garbled Values)

Values like `"O5I227)|7ZwHJ7.`U0nF0v~NZ~7DuKCB50gCB50g"` instead of numbers.

**Likely cause**: The site uses a custom font or obfuscation so that `textContent` / `innerText` return encoded characters instead of the visible numbers. Playwright’s `page.evaluate()` sees the raw DOM text, not the rendered numbers.

### C. `data/upgrades.json` — Incomplete

- **Current**: 21 upgrades (9 Attack, 4 Defense, 8 Utility)
- **Site**: 48 upgrades (17 Attack, 18 Defense, 13 Utility)
- **Missing**: 27 upgrades

---

## 3. Fixes Implemented

| Fix | File | Description |
|-----|------|-------------|
| Site verification script | `scripts/verify_site_structure.py` | Enumerates all categories and upgrades on the live site |
| innerText + table selector | `scripts/extract_data.py` | Prefer `innerText`, target table by "Level" header |
| Row validation | `scripts/extract_data.py` | `_is_valid_row()` skips obvious garbage |
| Partial save on error | `scripts/extract_data.py` | Saves `netlify_scraped_partial.json` if a run fails |
| `--quick` and `--no-headless` | `scripts/extract_data.py` | Quick test (2 upgrades × 3 pages) and visible browser for debugging |
| Better waits | `scripts/extract_data.py` | Longer waits after category/upgrade changes |

---

## 4. Recommended Scraping Method: Node Script

The **Node/Playwright scraper** (`scripts/scrape_tower_calculator_v2.js`) has been shown to capture correct data (e.g. 100 rows per page with valid numbers).

```bash
npm install
npx playwright install chromium
npm run scrape:v2
```

- Uses Playwright locators, which work better with the site’s rendering
- Handles consent and navigation
- Paginates through all levels
- Output: `scraped_tower_data.json`
- Note: Full scrape can take several hours (48 upgrades × 5000+ levels each)

---

## 5. Quick Checks

```bash
# Verify site structure (fast)
python scripts/verify_site_structure.py

# Quick Python scrape (2 upgrades per category, 3 pages each)
python scripts/extract_data.py --quick

# Full Python scrape (all 48, may have corrupted values)
python scripts/extract_data.py --no-headless
```

---

## 6. If You Still See Missing Categories

1. **In scraped output**  
   Run `python scripts/verify_site_structure.py` and inspect `data/raw/site_structure_verified.json`. That confirms what the site exposes.

2. **In the app dashboard**  
   Categories come from `data/upgrades.json`. The app has all 3 categories (attack, defense, utility), but some upgrades are missing because that file has 21 of 48.

3. **In `netlify_scraped.json`**  
   If a run fails partway, partial results go to `netlify_scraped_partial.json`. Check both files.
