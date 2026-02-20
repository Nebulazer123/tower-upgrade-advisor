# Research Notes — Tower Upgrade Advisor

> **Purpose:** Structured log of investigations. Use the template below for every research task.

---

## Template

```markdown
### [Date] — [Topic]

**Hypothesis:** What you expected to find.

**Evidence:** What you actually found. Include URLs, file paths, screenshots, or code snippets.

**Result:** Confirmed / Refuted / Partially confirmed / Inconclusive

**Next action:** What to do based on this finding.
```

---

## Research Log

### 2025-02-19 — Reference site technology

**Hypothesis:** The reference site might serve JSON data via an API or embed it in a fetchable endpoint.

**Evidence:**
- WebFetch of the root URL returned minimal HTML — a React SPA shell with no inline data.
- `asset-manifest.json` found at `/asset-manifest.json`:
  - Main bundle: `static/js/main.ef115c63.js`
  - Chunk: `static/js/27.01d6ef0c.chunk.js` (web vitals only)
- Main bundle is ~7.2MB minified — too large for WebFetch to parse.
- No REST API endpoints discovered.
- Fandom wiki returned 403.
- No public GitHub repository found.

**Result:** Refuted. No API endpoints exist. Data is embedded in the JS bundle or generated client-side.

**Next action:** Use Playwright to intercept network responses (Tier 1) or parse the downloaded bundle (Tier 2).

---

### 2025-02-19 — CSS selectors on reference site

**Hypothesis:** The reference site's stylesheet reveals DOM structure useful for scraping.

**Evidence:**
- CSS file analysis revealed these class names:
  - `.category`, `.category-name` — category containers
  - `.attack`, `.defense`, `.utility` — category type classes
  - `.upgrade`, `.upgrade-value` — upgrade rows
  - `.cost`, `.level` — cost/level display
  - `.current`, `.target` — level input fields
  - `#overview`, `#analysis` — page sections
  - `.name-button`, `.upgrade-name` — upgrade name display

**Result:** Confirmed. CSS class names suggest a structured DOM that can be scraped.

**Next action:** Use these selectors in the Tier 3 DOM scraping fallback. Validate against actual rendered DOM.

---

### 2025-02-19 — Category naming

**Hypothesis:** The game uses "offense", "defense", "economy" as categories.

**Evidence:**
- Reference site CSS uses `.attack`, `.defense`, `.utility` (not `.offense` or `.economy`).
- User explicitly stated categories are **attack, defense, utility**.
- The code currently uses `Literal["offense", "defense", "economy", "utility"]`.

**Result:** Partially confirmed. The site uses "attack" (not "offense") and "utility" (not "economy"). There may or may not be an "economy" category — this will be resolved by extraction.

**Next action:** After running extraction, update the Literal to match the actual data.

---

### 2026-02-19 — Wiki data extraction (successful)

**Hypothesis:** The game-vault.net wiki has structured per-level data tables that can be parsed reliably.

**Evidence:**
- Fetched `https://the-tower-idle-tower-defense.game-vault.net/wiki/Workshop` (413K chars HTML)
- Wiki page contains MediaWiki HTML tables with columns: Level, Value, Cost, Total Cost
- 27 upgrades have complete per-level data (every level listed)
- 5 additional upgrades have sampled data at 10-level intervals (Cash Bonus, Coins/Kill, Coins/Wave, Cash/Wave, Critical Factor)
- Upgrade data uses HTML `<table class="mw-collapsible mw-collapsed wikitable">` with `<th>/<td>` cells
- Section markers use `<span class="mw-headline" id="...">` for navigation
- Some span IDs are duplicated (e.g., "Orbs" appears twice — h3 and h5 level)
- Bounce Shot Range section is confusingly titled "Cost" in the heading
- Costs use suffixes: K (thousands), M (millions), B (billions), T (trillions), q (quadrillions)
- Values use unit suffixes: % (percent), x (multiplier), s (seconds), M (meters)

**Result:** Confirmed. Successfully extracted 32 upgrades across 4 categories.

**Next action:** Data is validated and saved to `data/upgrades.json`.

---

### 2026-02-19 — Reference site (tower-workshop-calculator.netlify.app) assessment

**Hypothesis:** The Netlify calculator site could provide structured data via network interception or bundle parsing.

**Evidence:**
- WebFetch of the main page timed out
- Site is a React SPA with ~7.2MB minified JS bundle
- No API endpoints discovered
- No public GitHub repository found
- Bundle hash `main.ef115c63.js` may be outdated
- wiki data source proved more reliable and comprehensive

**Result:** Inconclusive (site timed out). Wiki approach was more successful.

**Next action:** Wiki extraction is the primary approach. Calculator site could be revisited if more granular data is needed for 6000-level upgrades.

---

### 2026-02-19 — Extraction results summary

**32 upgrades extracted:**

| Category | Count | Upgrades |
|----------|-------|----------|
| offense | 12 | Attack Speed (99), Critical Chance (79), Critical Factor (16*), Range (79), Multishot Chance (99), Multishot Targets (7), Rapid Fire Chance (85), Rapid Fire Duration (99), Bounce Shot Chance (85), Bounce Shot Targets (7), Bounce Shot Range (60), Super Crit Chance (100) |
| defense | 12 | Defense Percent (99), Thorn Damage (99), Lifesteal (80), Knockback Chance (80), Knockback Force (40), Orb Speed (38), Orbs (4), Shockwave Size (35), Shockwave Frequency (40), Land Mine Chance (50), Land Mine Radius (50), Death Defy (75) |
| economy | 4 | Cash Bonus (16*), Coins Per Kill (16*), Coins Per Wave (16*), Cash Per Wave (16*) |
| utility | 4 | Free Attack Upgrades (99), Free Defense Upgrades (99), Free Utility Upgrades (99), Package Chance (60) |

*Asterisk = sampled data, renumbered from milestones.

**Not extracted (sampled data with non-monotonic or missing costs):**
- Damage (6000 levels, sampled every 100 — costs drop anomalously after level 100)
- Health (6000 levels, sampled every 100)
- Health Regen (6000 levels, sampled every 100)
- Defense Absolute (5000 levels, sampled every 100)
- Super Crit Multi (120 levels, sampled every 10)
- Rend Armor Chance/Mult (299 levels each, sampled every 10)
- Land Mine Damage (200 levels, sampled every 10)
- Wall Health (1800 levels, sampled every 100)
- Wall Rebuild (300 levels, sampled every 10)
- Recovery Amount (300 levels, sampled every 10)
- Max Recovery (500 levels, sampled every 10)
- Enemy Attack/Health Level Skip (699 levels each, sampled every 10)
- Damage/Meter (200 levels, sampled every 10)

**Validation:** Passes `python3 -m src.data_loader validate` with 0 errors, 40 warnings.
- 39 warnings: `shockwave_frequency` cumulative_effect decreasing (expected — lower frequency = better)
- 1 warning: `knockback_force` level 30 effect decreased (wiki data anomaly)

---

*Add new entries above this line.*
