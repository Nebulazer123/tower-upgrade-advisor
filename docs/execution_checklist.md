# Execution Checklist — Tower Upgrade Advisor

Phase 1 (Planning) is complete when all items below are checked.
Phase 2 (Implementation) follows after user approval.

---

## Phase 1: Planning (DONE)

- [x] Create docs/brief.md
- [x] Create docs/plan_architect.md
- [x] Create docs/plan_data.md
- [x] Create docs/plan_algorithm.md
- [x] Create docs/plan_ui.md
- [x] Create docs/plan_reliability.md
- [x] Create docs/decisions.md
- [x] Create docs/data_schema.md
- [x] Create docs/scoring.md
- [x] Create docs/execution_checklist.md
- [x] Create docs/assumptions.md
- [x] **User approval to proceed to Phase 2**

---

## Phase 2: Foundation (DONE)

- [x] Create `pyproject.toml` with dependencies (flask, pydantic, htmx, pytest, ruff, mypy)
- [x] Create `Makefile` with standard targets (run, test, lint, check, validate)
- [x] Create `src/__init__.py` and `src/models.py` (Pydantic models)
- [x] Create `tests/conftest.py` with shared fixtures
- [x] Create `tests/fixtures/test_upgrades.json` (small valid dataset)
- [ ] Create `data/schema.json` (JSON Schema for upgrades.json) — optional; validation in data_loader
- [x] Verify: `make lint` and `make typecheck` pass on empty project

---

## Phase 3: Data (PARTIALLY DONE)

- [x] Create `scripts/extract_data.py` (Playwright extraction script — scaffolding)
- [ ] Attempt extraction from reference site
- [ ] If extraction fails: create `data/upgrades.json` manually with known game data
- [x] Create `src/data_loader.py` (load + validate upgrades.json)
- [x] Create `scripts/validate_data.py` (standalone validation) — validation via `python3 -m src.data_loader validate`
- [x] Create `tests/test_data_validation.py` — validation covered in test_data_loader.py
- [x] Create `tests/test_data_loader.py`
- [ ] Verify: `data/upgrades.json` passes all validation rules — file does not exist yet
- [ ] Verify: `make validate` passes — requires data/upgrades.json

---

## Phase 4: Scoring Engine (DONE)

- [x] Create `src/scoring.py` (ScoringEngine protocol + 3 engines: PerCategory, Balanced, Reference stub)
- [x] Create `tests/test_scoring.py` (21 tests: unit + known-answer)
- [ ] Create `tests/test_regression.py` (golden file tests) — optional
- [ ] Create `tests/fixtures/expected/ranking_basic.json` — optional
- [x] Verify: scoring is deterministic (same inputs → same outputs)
- [x] Verify: `make test` passes (67/67)

---

## Phase 5: Profile Management (DONE)

- [x] Create `src/profile_manager.py` (CRUD for profiles with atomic writes)
- [x] Create `data/profiles/` directory — created at runtime when profiles are saved
- [x] Create `tests/test_profile_manager.py` (15 tests)
- [x] Verify: create, read, update, delete profiles work
- [x] Verify: atomic writes (write .tmp, rename) work

---

## Phase 6: UI (IN PROGRESS)

- [ ] Create `app.py` (Flask application)
- [x] Create `templates/base.html` (base template with htmx)
- [x] Create `templates/index.html`
- [ ] Create `templates/profile_select.html`
- [ ] Create `templates/dashboard.html`
- [ ] Create `templates/recommendation.html`
- [ ] Create `templates/upgrade_detail.html`
- [x] Create `static/style.css`
- [x] Vendor or CDN-link htmx.js (static/htmx.min.js)
- [ ] Create `src/routes.py` (Flask routes) — or inline in app.py
- [ ] Verify: all views render correctly
- [ ] Verify: inline level editing works via htmx
- [ ] Verify: recommendation displays transparent math

---

## Phase 7: Integration + Polish (IN PROGRESS)

- [ ] End-to-end test: new profile → enter levels → get recommendation
- [ ] Create `tests/test_integration.py`
- [ ] Verify: `make check` passes (lint + test + validate)
- [x] Update README.md with setup and usage instructions
- [ ] Verify: app starts with `make run` and works in browser (blocked until app.py exists)

---

## Dependencies

```
Phase 1 (Planning) → [User Approval]
    ↓
Phase 2 (Foundation) → no deps
    ↓
Phase 3 (Data) → depends on Phase 2 (models, schema)
Phase 4 (Scoring) → depends on Phase 2 (models) + Phase 3 (data loader)
Phase 5 (Profiles) → depends on Phase 2 (models)
    ↓
Phase 6 (UI) → depends on Phase 3, 4, 5
    ↓
Phase 7 (Integration) → depends on all above
```
