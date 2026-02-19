# Execution Checklist — Tower Upgrade Advisor

Phase 1 (Planning) is complete when all items below are checked.
Phase 2 (Implementation) follows after user approval.

---

## Phase 1: Planning (CURRENT)

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
- [ ] **User approval to proceed to Phase 2**

---

## Phase 2: Foundation (Owner: Architect + Reliability Engineer)

- [ ] Create `pyproject.toml` with dependencies (flask, pydantic, htmx, pytest, ruff, mypy)
- [ ] Create `Makefile` with standard targets (run, test, lint, check, validate)
- [ ] Create `src/__init__.py` and `src/models.py` (Pydantic models)
- [ ] Create `tests/conftest.py` with shared fixtures
- [ ] Create `tests/fixtures/test_upgrades.json` (small valid dataset)
- [ ] Create `data/schema.json` (JSON Schema for upgrades.json)
- [ ] Verify: `make lint` and `make typecheck` pass on empty project

---

## Phase 3: Data (Owner: Data Engineer)

- [ ] Create `scripts/extract_data.py` (Playwright extraction script)
- [ ] Attempt extraction from reference site
- [ ] If extraction fails: create `data/upgrades.json` manually with known game data
- [ ] Create `src/data_loader.py` (load + validate upgrades.json)
- [ ] Create `scripts/validate_data.py` (standalone validation)
- [ ] Create `tests/test_data_validation.py`
- [ ] Create `tests/test_data_loader.py`
- [ ] Verify: `data/upgrades.json` passes all validation rules
- [ ] Verify: `make validate` passes

---

## Phase 4: Scoring Engine (Owner: Algorithm Engineer)

- [ ] Create `src/scoring.py` (ScoringEngine protocol + V1 implementation)
- [ ] Create `tests/test_scoring.py` (unit tests + known-answer tests)
- [ ] Create `tests/test_regression.py` (golden file tests)
- [ ] Create `tests/fixtures/expected/ranking_basic.json`
- [ ] Verify: scoring is deterministic (same inputs → same outputs)
- [ ] Verify: `make test` passes

---

## Phase 5: Profile Management (Owner: UI Engineer)

- [ ] Create `src/profile_manager.py` (CRUD for profiles)
- [ ] Create `data/profiles/` directory with `default.json`
- [ ] Create `tests/test_profile_manager.py`
- [ ] Verify: create, read, update, delete profiles work
- [ ] Verify: atomic writes (write .tmp, rename) work

---

## Phase 6: UI (Owner: UI Engineer)

- [ ] Create `app.py` (Flask application)
- [ ] Create `templates/base.html` (base template with htmx)
- [ ] Create `templates/profile_select.html`
- [ ] Create `templates/dashboard.html`
- [ ] Create `templates/recommendation.html`
- [ ] Create `templates/upgrade_detail.html`
- [ ] Create `static/style.css`
- [ ] Vendor or CDN-link htmx.js
- [ ] Create `src/routes.py` (Flask routes)
- [ ] Verify: all views render correctly
- [ ] Verify: inline level editing works via htmx
- [ ] Verify: recommendation displays transparent math

---

## Phase 7: Integration + Polish (Owner: All)

- [ ] End-to-end test: new profile → enter levels → get recommendation
- [ ] Create `tests/test_integration.py`
- [ ] Verify: `make check` passes (lint + typecheck + test + validate)
- [ ] Update README.md with setup and usage instructions
- [ ] Verify: app starts with `make run` and works in browser

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
