# Cursor Composer Kickoff — Tower Upgrade Advisor

> **Instructions:** Copy everything below this line and paste it as your first message in Cursor Composer.

---

You are picking up an in-progress Python project called **Tower Upgrade Advisor**. This prompt contains everything you need to understand the project, what has been built, what hasn't, and what to do next.

## What this project is

A local-first desktop tool that recommends the single best next permanent upgrade (coin-based "Workshop" upgrades) to buy in the mobile game "The Tower" (idle tower defense). It must be transparent, deterministic, and trustworthy — no hidden weights, no invented data.

**Reference tool (inspiration, not spec):** https://tower-workshop-calculator.netlify.app/
That site is a React SPA on Netlify. No public GitHub repo. No API. Data is baked into a ~7.2MB minified JS bundle.

## The game in 30 seconds

1. Player does repeated runs, earning coins.
2. Between runs, player spends coins on permanent Workshop upgrades (damage, health, attack speed, etc.).
3. Each upgrade has levels. Each level has a cost and an effect delta.
4. The question this tool answers: **"Given my current levels and coins, what should I buy next?"**
5. Answer = `score = marginal_benefit / coin_cost` (optionally weighted by category).

**Categories are: attack, defense, utility** (the user confirmed this). The code currently uses `Literal["offense", "defense", "economy", "utility"]` — this MUST be updated after real data extraction reveals actual category names.

## Tech stack

- **Python 3.11+**
- **Flask + htmx** (UI, not yet built)
- **Pydantic v2** (data models, runtime validation)
- **pytest** (67 tests, all passing)
- **ruff** (linting, clean)
- **JSON files** for data storage (not SQLite)
- **Playwright** (data extraction, not yet run)

## What has been built (Phases 1-3, DONE)

### Source code (`src/`)

**`src/models.py`** — 6 frozen/validated Pydantic v2 models:
- `UpgradeLevel`: level, coin_cost, cumulative_effect, effect_delta (NaN/Inf rejected)
- `UpgradeDefinition`: id, name, category (Literal), effect_type (multiplicative|additive), base_value, max_level, levels[] — validates level continuity and cost monotonicity
- `UpgradeDatabase`: version, game_version, source, upgrades[] — has `get_upgrade()`, `get_by_category()`, `upgrade_ids()`
- `ScoringWeights`: economy/offense/defense/utility floats (0-2, default 1.0) — `for_category()` returns 1.0 for unknowns (safe fallback)
- `Profile`: id, name, timestamps, available_coins, levels dict, weights, tags[] — `get_level()` defaults to 0
- `RankedUpgrade`: full scoring output with transparency fields

**`src/scoring.py`** — Protocol-based scoring with 3 engines:
- `ScoringEngine` Protocol: `name`, `version`, `rank()`, `explain()`
- `PerCategoryEngine` ("per_category_best", v1.0): returns best upgrade per category, no cross-category comparison. `score = marginal_benefit / cost`
- `BalancedEngine` ("balanced", v1.0): ranks ALL upgrades globally. `score = marginal_benefit / cost * category_weight`. Takes `ScoringWeights`.
- `ReferenceEngine` ("reference", v0.0): stub, raises `NotImplementedError`
- `compute_marginal_score()`: pure function, handles maxed upgrades, zero cost, level 0
- Deterministic tie-breaking: score desc → cost asc → name asc. Scores rounded to 12 decimal places.

**`src/data_loader.py`** — Load/save/validate upgrade JSON:
- `load_upgrades(path)` → `UpgradeDatabase` (Pydantic validation)
- `save_upgrades(db, path)` — atomic write (.tmp + rename)
- `validate_upgrade_data(db)` → `ValidationResult` with errors and warnings
- 15+ validation checks: duplicate IDs, level continuity, cost monotonicity (hard error), effect monotonicity (warning only per game context doc §10), effect delta consistency, NaN/Inf, string leak detection
- CLI: `python -m src.data_loader validate`

**`src/profile_manager.py`** — CRUD with atomic writes:
- `ProfileManager(data_dir)` — all ops on `data/profiles/`
- Methods: list, get, create, save, delete, duplicate, update_level, update_coins, update_weights, backup
- Atomic: writes to .tmp then renames

### Extraction scaffolding (`scripts/`)

**`scripts/extract_data.py`** — 3-tier Playwright extraction (NEVER BEEN RUN):
- Tier 1: `extract_via_network()` — intercept XHR/fetch responses for JSON payloads
- Tier 2: `extract_via_bundle()` — download main.js bundle, regex search for embedded data
- Tier 3: `extract_via_dom()` — Playwright DOM traversal with CSS selectors
- `normalize_to_schema()` and `validate_extracted()` for post-processing
- **This script is scaffolding. The user will do their own research on the best scraping approach. Do not run it blindly — wait for user direction.**

### Tests (`tests/`)

67 tests, all passing. Run with `pytest -x -q`.

- `tests/conftest.py` — 5 fixtures: test_upgrades (6 upgrades), empty_profile, mid_profile, maxed_profile, offense_weighted_profile, tmp_profiles_dir
- `tests/fixtures/test_upgrades.json` — 6 test upgrades across 3 categories (offense, defense, economy), 5 levels each
- `tests/test_models.py` — 18 tests (UpgradeLevel, UpgradeDefinition validators, ScoringWeights fallback, Profile)
- `tests/test_scoring.py` — 21 tests (compute_marginal_score, PerCategoryEngine, BalancedEngine, ReferenceEngine, tie-breaking)
- `tests/test_data_loader.py` — 13 tests (loading, validation, raw JSON checks)
- `tests/test_profile_manager.py` — 15 tests (CRUD, atomic writes, backups)

### Documentation (`docs/`)

22 docs total. The critical ones:
- `docs/game_and_project_context.md` — 384-line authoritative reference for game mechanics, project scope, model behavior rules, V1 definition of done. **Read this if you need to understand any "why" question.**
- `docs/decisions.md` — 9 numbered decisions with rationale
- `docs/assumptions.md` — 36 documented assumptions
- `docs/data_schema.md` — JSON schema for upgrades.json and profiles
- `docs/scoring.md` — scoring engine specification
- `docs/todo_now.md` — prioritized task list
- `docs/extraction_playbook.md` — extraction debugging guide
- `docs/transfer_pack.md` — project overview for onboarding

## What has NOT been built

- **`data/upgrades.json`** — does not exist. No real data has been extracted yet.
- **`app.py`** — does not exist. No Flask routes, templates, or UI.
- **ReferenceEngine** — stub only.
- **`scripts/manual_import.py`** — not created.
- **Integration/E2E tests** — only unit tests exist.

## Key architectural rules

1. **Never invent data.** If a cost, effect, or level is unknown, it stays unknown. Don't guess.
2. **Never add hidden weights.** All scoring weights must be visible and user-adjustable.
3. **Scoring must be deterministic and explainable.** Same inputs = same outputs. Show the math.
4. **Cost monotonicity = hard error. Effect monotonicity = warning only.** Per game context doc §10.
5. **`for_category()` returns 1.0 for unknowns.** New categories can't silently get zeroed out.
6. **Atomic writes everywhere.** Write to .tmp, rename. No partial file corruption.
7. **New decisions → `docs/decisions.md`.** New assumptions → `docs/assumptions.md`.
8. **Tests must pass after every change.** `pytest -x -q` (67 passed). `ruff check src/ tests/ scripts/` (clean).

## Golden commands

```bash
pip install -e ".[dev]"                    # Install dev deps
pytest -x -q                               # Run tests (expect 67 passed)
ruff check src/ tests/ scripts/            # Lint (expect clean)
pip install -e ".[extract]"                # Install extraction deps
playwright install chromium                # Browser for extraction
python -m src.data_loader validate         # Validate upgrades.json
make check                                 # lint + test + validate
```

## Known issues and discrepancies

1. **Category names:** Code has `Literal["offense", "defense", "economy", "utility"]`. User says game uses **attack, defense, utility**. Must update after extraction.
2. **ScoringWeights fields:** Named `economy`, `offense`, `defense`, `utility`. May need renaming to match actual categories after extraction.
3. **Reference site bundle hash:** `main.ef115c63.js` was discovered during Phase 1. May have changed. Check page source if extraction script 404s.
4. **`data_schema.md` vs `models.py`:** The doc schema has a `categories` wrapper and `cumulative_cost` field. The Pydantic model is flatter (upgrades[] directly on UpgradeDatabase, no cumulative_cost). After extraction, reconcile these.

## What to do next

The extraction approach is NOT finalized. The user will do their own research on the reference site. When they're ready:

1. **Data extraction (Phase 4)** — Extract real upgrade data. The user drives the research on scraping strategy.
2. **Flask UI (Phase 5)** — `app.py`, templates, htmx partials, scoring wired to routes.
3. **Polish** — Integration tests, coverage to 85%, manual import fallback.

**Wait for the user to tell you what to work on.** Don't start extraction autonomously. Read the relevant docs when asked about a specific area.

## File tree for reference

```
src/models.py            # Pydantic models (UpgradeLevel, UpgradeDefinition, UpgradeDatabase, ScoringWeights, Profile, RankedUpgrade)
src/scoring.py           # Scoring engines (PerCategoryEngine, BalancedEngine, ReferenceEngine stub)
src/data_loader.py       # Load/save/validate upgrade data
src/profile_manager.py   # Profile CRUD with atomic writes
scripts/extract_data.py  # 3-tier extraction scaffolding (untested)
tests/conftest.py        # Shared pytest fixtures
tests/fixtures/test_upgrades.json
tests/test_models.py     # 18 tests
tests/test_scoring.py    # 21 tests
tests/test_data_loader.py    # 13 tests
tests/test_profile_manager.py # 15 tests
docs/game_and_project_context.md  # Authoritative game/project reference
docs/decisions.md        # 9 decisions with rationale
docs/assumptions.md      # 36 assumptions
docs/data_schema.md      # JSON schema spec
docs/scoring.md          # Scoring spec
docs/todo_now.md         # Prioritized task list
docs/extraction_playbook.md  # Extraction debug guide
docs/transfer_pack.md    # Project overview
pyproject.toml           # Python 3.11+, deps, tool config
Makefile                 # Dev workflow shortcuts
```
