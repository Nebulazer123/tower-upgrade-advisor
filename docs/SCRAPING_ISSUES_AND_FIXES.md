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

### C. `data/upgrades.json` — Complete After Visible-Text Merge

- **Current**: 48 upgrades (17 Attack, 18 Defense, 13 Utility)
- **Site**: 48 upgrades (17 Attack, 18 Defense, 13 Utility)
- **Missing**: 0 upgrades
- **Caveat**: The merged costs/effects come from the public calculator's visible rendered table values. Large coin costs are display-rounded by the source, so adjacent displayed costs can be equal even when hidden exact costs differ.

---

## 3. Fixes Implemented

| Fix | File | Description |
|-----|------|-------------|
| Site verification script | `scripts/verify_site_structure.py` | Enumerates all categories and upgrades on the live site |
| Visible table scraper | `scripts/scrape_public_workshop_visible.py` | Reads only visible leaf text and merges the missing public workshop upgrades |
| innerText + table selector | `scripts/extract_data.py` | Prefer `innerText`, target table by "Level" header |
| Row validation | `scripts/extract_data.py` | `_is_valid_row()` skips obvious garbage |
| Partial save on error | `scripts/extract_data.py` | Saves `netlify_scraped_partial.json` if a run fails |
| `--quick` and `--no-headless` | `scripts/extract_data.py` | Quick test (2 upgrades × 3 pages) and visible browser for debugging |
| Better waits | `scripts/extract_data.py` | Longer waits after category/upgrade changes |

---

## 4. Recommended Scraping Method: Visible-Text Python Scraper

The maintained scraper is `scripts/scrape_public_workshop_visible.py`. It avoids the zero-font hidden characters by collecting only visible leaf spans from each cell, then normalizes the rendered public table rows into `data/upgrades.json`.

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[extract]"
playwright install chromium
python scripts/scrape_public_workshop_visible.py --merge
```

- Handles consent and navigation
- Paginates through each selected upgrade
- Writes raw visible rows to `data/raw/public_workshop_visible.json`
- Validates the merged result before writing `data/upgrades.json`
- Preserves the existing app schema and category order

The older Node/Playwright scrapers remain in the repo as experiments, but they are no longer the recommended source of truth for this app.

---

## 5. Quick Checks

```bash
# Verify public site structure and expected upgrade count
python scripts/verify_site_structure.py

# Verify bundled dataset coverage against the public workshop selector
python scripts/verify_data_coverage.py --strict

# Rebuild the merged dataset from a previously saved visible scrape
python scripts/scrape_public_workshop_visible.py --from-raw --merge
```

---

## 6. If You Still See Missing Categories Or Upgrades

1. **Check public structure first**  
   Run `python scripts/verify_site_structure.py` and inspect `data/raw/site_structure_verified.json`. That confirms what the site exposes.

2. **Check app coverage**  
   Run `python scripts/verify_data_coverage.py --strict`. The app should report 48/48 loaded with no missing upgrades.

3. **Check the source data**  
   Categories in the dashboard come from `data/upgrades.json`. If coverage regresses, rerun the visible scraper and inspect `data/raw/public_workshop_visible.json`.

4. **Avoid raw DOM text scraping**  
   Naive `textContent` / `innerText` extraction can still return hidden junk. Use the visible leaf-span scraper instead.
