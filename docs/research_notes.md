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

### 2026-06-15 — Public calculator verification pass

**Hypothesis:** The public Netlify calculators can be used as direct math/data verification sources for this app.

**Evidence:**
- Public lab calculator inspected: https://tower-lab-calculator.netlify.app/
- Public workshop calculator inspected: https://tower-workshop-calculator.netlify.app/
- Both apps gate usage behind a link-back agreement that says derivative resources should link back to the app and instruct users to view it for accurate information.
- After accepting the gate, the lab calculator exposes tabs for Intro, Input, Overview, Stats, Details, Cost Tables, and Gem Calc.
- After accepting the gate, the workshop calculator exposes tabs for Intro, Input, Overview, Analysis, and Data.
- The public workshop calculator's rendered upgrade names/values are partly DOM/font-obfuscated, matching the older scraper notes about garbled text extraction.
- The clearer DPS math source is the linked public code repository: https://github.com/jacoelt/tower-calculator
- `src/components/attack/AttackUpgrades.tsx` ranks attack upgrades by DPS increase divided by cost.
- The public source documents these assumptions: optimal valid targets, all bounces available, max multishot shots, rapid fire only from normal bullets, damage per meter ignored, and rapid fire duration fixed at 1 second.

**Result:** Confirmed with caveats. The public calculators are valid user-facing references and must be linked in README/UI. The public source repository is reliable for attack-DPS math. The workshop calculator's raw DOM text is not reliable, but the rendered visible table text is usable when the scraper ignores hidden zero-font spans.

**Next action:** Keep the reference-DPS engine visible in the UI, keep `scripts/verify_data_coverage.py --strict` as the coverage gate, and use `scripts/scrape_public_workshop_visible.py` for future refreshes.

### 2026-06-15 — Visible workshop table extraction

**Hypothesis:** The public workshop calculator's numeric table can be scraped by reading only the visible leaf text and ignoring hidden zero-font characters.

**Evidence:**
- A rendered screenshot of the Range table showed readable values while raw DOM extraction still produced junk from hidden text.
- `scripts/scrape_public_workshop_visible.py` collected only leaf spans whose computed font size was visible.
- The scraper loaded all 27 previously missing upgrades and merged them with the existing 21 bundled upgrades.
- `scripts/verify_data_coverage.py --strict` reports 48 of 48 public workshop upgrades loaded: 17 Attack, 18 Defense, 13 Utility.
- `python -m src.data_loader validate` accepts the merged dataset after allowing non-decreasing rounded public coin costs and documenting lower-is-better effect exceptions.

**Result:** Confirmed. The app now has a complete workshop-upgrade dataset against the public workshop selector.

**Next action:** Treat the visible public table values as the maintained bundled source. If exact hidden in-game costs are later available, add them as a higher-precision source and keep this scraper as an external regression check.

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

**Hypothesis:** The game uses attack, defense, and utility as categories.

**Evidence:**
- Reference site CSS uses `.attack`, `.defense`, `.utility`.
- User explicitly stated categories are **attack, defense, utility**.
- The current code uses `Literal["attack", "defense", "utility"]`.

**Result:** Confirmed. The public workshop selector and bundled dataset use exactly three categories: attack, defense, utility.

**Next action:** Keep models, scoring weights, UI, tests, and docs on Attack / Defense / Utility.

---

*Add new entries above this line.*
