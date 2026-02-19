# Extraction Playbook — Tower Upgrade Advisor

> **Purpose:** Step-by-step instructions for extracting real upgrade data from the reference site. This is the critical path for the project.

---

## Reference Site

- **URL:** https://tower-workshop-calculator.netlify.app/
- **Tech:** Create React App (JS SPA) hosted on Netlify
- **Bundle:** `static/js/main.ef115c63.js` (~7.2MB minified)
- **No public GitHub repo found**
- **No REST API or JSON endpoints discovered via WebFetch**

---

## Prerequisites

```bash
# Install extraction dependencies
pip install -e ".[extract]"

# Install Chromium for Playwright
playwright install chromium
```

---

## Extraction Script

**File:** `scripts/extract_data.py`

**Run:**
```bash
python scripts/extract_data.py
```

**Output locations:**
- `data/raw/` — raw artifacts from each tier (gitignored)
- `data/upgrades.json` — normalized output (committable)

---

## Three-Tier Extraction Strategy

### Tier 1: Network Interception (Preferred)

**What it does:** Launches Chromium via Playwright, navigates to the reference site, and intercepts all network responses looking for JSON payloads that contain upgrade data.

**How to tell if it worked:**
- Console output: `[Tier 1] Found upgrade data in network response!`
- File created: `data/raw/network_responses.json`

**Common failure modes:**
- The site may not make any XHR/fetch calls — all data may be embedded in the JS bundle.
- The site may load data from `localStorage` or hardcoded in the bundle, not from a network request.

**Debug steps:**
1. Open the reference site in a real browser (Chrome).
2. Open DevTools → Network tab → Filter by `Fetch/XHR`.
3. Reload the page.
4. Look for any JSON responses containing upgrade names (e.g., "Attack Speed", "Damage").
5. If you find one, note the URL — it can be added to the script as a direct fetch.

### Tier 2: JS Bundle Analysis

**What it does:** Downloads the main JS bundle (`main.ef115c63.js`) and searches for embedded data structures using regex patterns.

**How to tell if it worked:**
- Console output: `[Tier 2] Found N upgrade names in bundle`
- Console output: `[Tier 2] Parsed N items from array!`
- File created: `data/raw/bundle.js`

**Common failure modes:**
- The bundle is minified — variable names are mangled.
- Data may be split across multiple objects, not in a single parseable array.
- JSON regex patterns may not match the minified format.

**Debug steps:**
1. Open `data/raw/bundle.js` in VS Code.
2. Search for known upgrade names: `"Attack Speed"`, `"Damage"`, `"Critical Chance"`.
3. Look at the surrounding context — is there an array of objects? A lookup table?
4. Try to extract the data structure manually and understand its format.
5. If found, write a targeted parser for that specific format.

**Key known upgrade names to search for:**
```
Attack Speed, Damage, Critical Chance, Critical Factor,
Health, Health Regen, Defense, Thorns,
Coins per Kill, Coins per Wave, Interest,
Land Mines, Death Defy, Orb Speed
```

### Tier 3: DOM Scraping (Fallback)

**What it does:** Navigates to the rendered page, waits for React to hydrate, then traverses the DOM using CSS selectors to extract upgrade data.

**How to tell if it worked:**
- Console output: `[Tier 3] Found N categories with upgrades`
- Files created: `data/raw/page.html`, `data/raw/dom_extracted.json`

**Common failure modes:**
- CSS selectors may be wrong — the site's class names may have changed.
- React may not have finished rendering when the scraper runs.
- The DOM may not contain all per-level data (costs, effects) — only the currently displayed level.

**Debug steps:**
1. Open the reference site in a real browser.
2. Open DevTools → Elements tab.
3. Inspect the DOM structure manually:
   - What class names are used for categories? (Expected: `.category`, `.attack`, `.defense`, `.utility`)
   - What class names are used for upgrades? (Expected: `.upgrade`, `.name-button`)
   - Where are costs displayed? (Expected: `.cost`)
   - Where are level inputs? (Expected: `.current input`, `.target input`)
4. Update the CSS selectors in `extract_via_dom()` to match reality.
5. If per-level data requires iterating through UI controls (clicking to change levels), add Playwright interactions.

**Known CSS selectors from reference site CSS:** (discovered during Phase 1 research)
```css
.category, .category-name
.attack, .defense, .utility
.upgrade, .upgrade-value
.cost, .level
.current, .target
#overview, #analysis
.name-button, .upgrade-name
```

---

## Post-Extraction: Validation

After extraction produces `data/upgrades.json`, validate it:

```bash
python -m src.data_loader validate
```

### Expected validation checks:
- No duplicate upgrade IDs
- Levels are continuous (1, 2, 3, ..., max_level)
- All numeric fields are actual numbers (not strings like "1.2M")
- Costs are monotonically increasing
- Cumulative effects are generally non-decreasing (warnings OK)
- Effect deltas are consistent with cumulative effects
- At least 20-30 upgrades expected

### If validation fails:
1. Check `data/raw/` artifacts for the raw extracted data.
2. Compare raw data against what the reference site actually shows.
3. Fix the normalization logic in `normalize_to_schema()` in `extract_data.py`.
4. Re-run and re-validate.

---

## Post-Extraction: Category Name Update

After extraction, check what category names the data actually uses.

**Current code:**
```python
category: Literal["offense", "defense", "economy", "utility"]
```

**User says categories are:** attack, defense, utility

**Action:** Update the Literal in `src/models.py` to match extracted data. Also update:
- `ScoringWeights` field names (if changing from offense→attack, economy→utility)
- `docs/decisions.md` Decision 7
- `tests/fixtures/test_upgrades.json` fixture data
- All test assertions that reference category names

---

## Manual Fallback

If all three tiers fail:

1. Open the reference site in a browser.
2. Manually record each upgrade's:
   - Name
   - Category
   - Max level
   - Per-level costs (click through levels)
   - Per-level effects
3. Enter data into `data/upgrades.json` following the schema in `docs/data_schema.md`.
4. Validate with `python -m src.data_loader validate`.

A template `scripts/manual_import.py` should be created to help with this (not yet built).

---

## Extraction Artifact Inventory

After a successful extraction run, you should have:

| File | Source | Committed? |
|------|--------|------------|
| `data/raw/network_responses.json` | Tier 1 | No (gitignored) |
| `data/raw/bundle.js` | Tier 2 | No (gitignored) |
| `data/raw/page.html` | Tier 3 | No (gitignored) |
| `data/raw/dom_extracted.json` | Tier 3 | No (gitignored) |
| `data/raw/extracted.json` | Whichever tier succeeded | No (gitignored) |
| `data/upgrades.json` | Normalized output | Yes |

---

## Troubleshooting

### "Playwright not installed"
```bash
pip install -e ".[extract]"
playwright install chromium
```

### "httpx not installed"
```bash
pip install -e ".[extract]"
```

### "No tier succeeded"
- Check if the reference site is accessible in a browser.
- Try with `headless=False` in `extract_data.py` (line in `extract_all()` function) to see what the browser sees.
- Check if the site has been redesigned (new bundle hash, different DOM structure).

### "Bundle URL returns 404"
- The bundle hash `ef115c63` was discovered during Phase 1 research and may change.
- Navigate to the site in a browser, view source, find the current `<script>` tag for `main.*.js`.
- Update `BUNDLE_URL` in `extract_data.py`.

### "Category names don't match"
- This is expected. The Literal will be updated after extraction.
- Temporarily widen the Literal or change category values in the extracted data to match.
