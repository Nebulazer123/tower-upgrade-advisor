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

*Add new entries above this line.*
