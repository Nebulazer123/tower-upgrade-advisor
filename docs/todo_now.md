# TODO Now — Tower Upgrade Advisor

> **Purpose:** The single prioritized task list for what to do next. This is the most important document for resuming work.

---

## Priority 1: Data Extraction Research + Execution (Phase 4)

This is the critical path. Without real data, nothing else works.

**Important:** The extraction approach is NOT finalized. The existing `scripts/extract_data.py` is scaffolding based on best guesses from Phase 1 research. The user needs to do their own research on the reference site to figure out the best scraping strategy before committing to an approach. The 3-tier script may need significant rework.

### P1.0 — Research the reference site hands-on (USER-DRIVEN)
- Open https://tower-workshop-calculator.netlify.app/ in a real browser.
- Use DevTools (Network tab, Elements tab, Sources tab) to understand:
  - Where does the data come from? (XHR? Embedded in JS? localStorage?)
  - What does the DOM structure actually look like?
  - Are the CSS selectors in `extract_data.py` still correct?
  - Has the bundle hash changed from `main.ef115c63.js`?
- Log findings in `docs/research_notes.md` using the template.
- **This step determines whether the extraction script needs a rewrite or just tweaks.**

### P1.1 — Decide on extraction approach based on research
- Update `scripts/extract_data.py` if the research reveals a different data source or DOM structure.
- The current 3-tier approach (network → bundle → DOM) may be right, wrong, or partially right.
- The extraction playbook (`docs/extraction_playbook.md`) has debugging steps for each tier.

### P1.2 — Run extraction and iterate
- The reference site is a React SPA. The extraction script's Tier 1 (network interception) and Tier 2 (bundle parsing) are best guesses. Tier 3 (DOM scraping) CSS selectors are based on the site's stylesheet but untested.
- Read `docs/extraction_playbook.md` for the full debugging methodology.
- Save raw artifacts to `data/raw/` for inspection even if parsing fails.

### P1.3 — Validate extracted data
- **Command:** `python -m src.data_loader validate`
- Fix any validation errors. Common issues:
  - String costs like "1.2M" not parsed to integers
  - Missing levels
  - Category names don't match the Literal in `models.py`

### P1.4 — Update category Literal after extraction
- The code currently has `Literal["offense", "defense", "economy", "utility"]`.
- The user says categories are **attack, defense, utility**.
- After extraction, update the Literal to match whatever the real data uses.
- Update `ScoringWeights` field names to match if needed.

### P1.5 — Commit validated data
- `data/upgrades.json` should be committed if it's reasonably small (<1MB).
- `data/raw/` stays gitignored.

---

## Priority 2: Flask UI (Phase 5)

### P2.1 — Create `app.py` with Flask routes
- Profile selector (dropdown or tabs)
- Upgrade level input grid (one row per upgrade, grouped by category)
- "Recommend" button that calls the scoring engine
- Results display showing top N recommendations with math

### P2.2 — Create HTML templates with htmx
- `templates/base.html` — layout
- `templates/profile.html` — level input + recommendations
- Use htmx for partial-page updates (no full JS framework)

### P2.3 — Static CSS
- Clean, minimal styling
- Match the upgrade ordering from the reference tool

### P2.4 — Wire scoring engines to the UI
- Per-category mode: show best-per-category in separate sections
- Balanced mode: show global ranking with slider controls
- Display the `explain()` output for each recommendation

---

## Priority 3: Polish and Hardening

### P3.1 — Add integration tests for extraction
- Test that extracted data passes all validators
- Golden-file test: known input → known output

### P3.2 — Add E2E tests for Flask UI
- Test profile CRUD via routes
- Test recommendation endpoint returns valid JSON

### P3.3 — Manual import fallback
- Create `scripts/manual_import.py` for manual data entry
- Template CSV/JSON that users can fill in if extraction breaks

### P3.4 — Coverage to 85%
- Run `pytest --cov=src --cov-report=term-missing`
- Add tests for uncovered branches

---

## Priority 4: Future (Not V1)

These are documented for awareness but should NOT be started until P1-P3 are done:
- Multi-step path planning (best next N purchases)
- In-run cash upgrade recommendations
- Run simulation mode
- Patch-versioned datasets
- Mobile UI
- Hosted deployment

---

## Quick Status Check

```bash
# Are tests passing?
pytest -x -q

# Is lint clean?
ruff check src/ tests/ scripts/

# Does data exist?
ls data/upgrades.json

# Can data be validated?
python -m src.data_loader validate
```
