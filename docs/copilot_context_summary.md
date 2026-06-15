# Copilot Context Summary — Tower Upgrade Advisor

> **Purpose:** Summarize everything that happened in the VS Code Copilot chat sessions so a new agent (or Cursor) can resume without losing context.

---

## Session 1: Planning (Phase 1)

### What happened:
- Received detailed system prompt defining the project scope, team structure, and constraints.
- Attempted to fetch reference site data via WebFetch — discovered it's a JS SPA (Create React App on Netlify). The 7.2MB minified bundle cannot be parsed without JavaScript execution.
- Found asset-manifest.json: `main.ef115c63.js` (main bundle) and `27.01d6ef0c.chunk.js` (web vitals only).
- Searched for GitHub repo — none found. Fandom wiki returned 403.
- Created 5 agent plans in parallel (Architect, Data, Algorithm, UI, Reliability).
- All agents hit turn limits, so team lead wrote all plan files directly.

### Artifacts produced (13 files):
- `docs/brief.md` — project brief
- `docs/plan_architect.md` — architecture plan
- `docs/plan_data.md` — data engineering plan
- `docs/plan_algorithm.md` — algorithm plan
- `docs/plan_ui.md` — UI plan
- `docs/plan_reliability.md` — reliability/testing plan
- `docs/decisions.md` — 6 cross-team decisions
- `docs/data_schema.md` — JSON schema spec
- `docs/scoring.md` — scoring engine specification
- `docs/execution_checklist.md` — phase-by-phase TODO
- `docs/assumptions.md` — 27 documented assumptions

### Key outcomes:
- Stack chosen: Python + Flask + htmx + Pydantic v2
- Storage: JSON files
- Scoring: marginal benefit / cost with category weights
- Extraction: Playwright-based 3-tier (network → bundle → DOM)

---

## Session 2: Phase 2 Approval + Implementation

### What happened:
- User approved Phase 1 with three modifications:
  1. **No hardcoded category weights.** Two modes: per-category best + balanced with adjustable sliders.
  2. **Extraction priority:** network interception → bundle analysis → DOM scraping.
  3. **Repo hygiene:** gitignore large scraped data.

### Built:
- `pyproject.toml` — project config (fixed build-backend from `setuptools.backends._legacy:_Backend` to `setuptools.build_meta`)
- `Makefile` — dev workflow commands
- `src/models.py` — 6 Pydantic v2 models with strict validation
- `src/scoring.py` — 3 scoring engines (PerCategoryEngine, BalancedEngine, ReferenceEngine stub)
- `src/data_loader.py` — load/save/validate with 15+ validation checks
- `src/profile_manager.py` — CRUD with atomic writes
- `scripts/extract_data.py` — 3-tier Playwright extraction script
- `tests/conftest.py` — 5 shared pytest fixtures
- `tests/fixtures/test_upgrades.json` — 6 test upgrades across 3 categories
- `tests/test_models.py` — 18 model tests
- `tests/test_scoring.py` — 21 scoring tests
- `tests/test_data_loader.py` — 13 data loader tests
- `tests/test_profile_manager.py` — 15 profile manager tests

### Bugs fixed during session:
1. `python` → `python3` (macOS PATH)
2. Wrong test assertion: expected "damage" as top upgrade but "health" had higher score (10/75=0.133 > 5/50=0.1)
3. 23 ruff lint errors auto-fixed + 4 manual fixes (UP017, SIM108, E501, B017, F401)

### Final state: 67/67 tests passing, lint clean.

---

## Session 3: Game Context Review

### What happened:
- User asked to read `docs/game_and_project_context.md` (384-line authoritative document).
- Identified 3 gaps between the code and the game context doc:

### Changes made:
1. **Added "utility" to category Literal** — was missing; game context doc §10 and reference site CSS both confirm it.
2. **Softened cumulative_effect monotonicity** — removed from Pydantic validator (was hard error), kept as warning in `data_loader.validate_upgrade_data()`. Per §10: "Do not enforce monotonic rules globally."
3. **Added `ScoringWeights.utility` field** — 4th slider (default 1.0, range 0-2).
4. **Changed `for_category()` fallback** — returns `1.0` instead of raising `ValueError` for unknown categories. Future game updates can't silently zero out upgrades.
5. **Added `Profile.tags` field** — free-form `list[str]` per §11 (farm build, push build, balanced build).

### Documented as: Decisions 7, 8, 9 in `docs/decisions.md`.

---

## Session 4: Git Commit + Push

- User confirmed categories are **attack, defense, utility**.
  - Current code uses `Literal["attack", "defense", "utility"]` and matching scoring weights.
- Staged 27 files, committed as `f2d1195` ("Phase 2: Foundation + Extraction Scaffolding + Validation Tests").
- Pushed to `origin/main`.

---

## What Was NOT Built

These items were deferred in the original foundation commit, but are now implemented in the working tree:
- **Real data extraction** — `scripts/scrape_public_workshop_visible.py` reads visible public table text.
- **Flask UI** — routes, templates, and static files exist.
- **`app.py`** — runs the local Flask app.
- **ReferenceEngine** — implements attack DPS reference checks with fallback scoring.
- **Data file** — `data/upgrades.json` covers 48/48 public workshop upgrades.

---

## Known Category Name Discrepancy

The user explicitly stated the categories are **attack, defense, utility**. The Pydantic model now defines:

```python
category: Literal["attack", "defense", "utility"]
```

This matches the public workshop selector and bundled dataset.
