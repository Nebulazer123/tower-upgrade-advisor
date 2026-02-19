# Transfer Pack — Tower Upgrade Advisor

> **Purpose:** Give any agent or teammate everything needed to resume work on this project in under 5 minutes.

---

## What Is This Project?

A **local-first macOS/Windows desktop tool** that recommends the single best next permanent upgrade to buy in the mobile game "The Tower" (idle tower defense).

- **Input:** A player profile (current upgrade levels + coins available).
- **Output:** A ranked recommendation with transparent scoring math.
- **Reference tool (inspiration):** https://tower-workshop-calculator.netlify.app/

---

## Current Phase

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Planning | **Done** | 13 docs in `docs/`, all reviewed and approved |
| Phase 2: Foundation | **Done** | Models, scoring, data loader, profile manager, tests (67/67), lint clean |
| Phase 3: Transfer Pack | **In Progress** | You are reading it |
| Phase 4: Data Extraction | **Not Started** | Extract real data from reference site using Playwright |
| Phase 5: UI (Flask + htmx) | **Not Started** | Local web UI for daily use |

---

## Repo Layout

```
tower-upgrade-advisor/
├── src/
│   ├── __init__.py
│   ├── models.py           # 6 Pydantic v2 models (UpgradeLevel, UpgradeDefinition, UpgradeDatabase, ScoringWeights, Profile, RankedUpgrade)
│   ├── scoring.py          # 3 engines: PerCategoryEngine, BalancedEngine, ReferenceEngine (stub)
│   ├── data_loader.py      # Load/save/validate upgrade JSON
│   └── profile_manager.py  # CRUD with atomic writes
├── scripts/
│   └── extract_data.py     # 3-tier Playwright extraction (not yet run)
├── tests/
│   ├── conftest.py          # 5 shared fixtures
│   ├── fixtures/
│   │   └── test_upgrades.json  # 6 test upgrades, 3 categories, 5 levels each
│   ├── test_models.py       # 18 tests
│   ├── test_scoring.py      # 21 tests
│   ├── test_data_loader.py  # 13 tests
│   └── test_profile_manager.py # 15 tests
├── data/                    # Created at runtime (gitignored: raw/, profiles/)
├── docs/                    # 13+ planning/context docs
├── prompts/                 # Cursor kickoff prompt
├── pyproject.toml           # Python 3.11+, Flask, Pydantic, pytest, ruff
├── Makefile                 # install, test, lint, validate, run
└── .gitignore
```

---

## Golden Commands

```bash
# Install for development
pip install -e ".[dev]"

# Run all 67 tests
pytest -x -q

# Lint
ruff check src/ tests/ scripts/

# Install extraction dependencies
pip install -e ".[extract]" && playwright install chromium

# Run extraction (Phase 4 — not yet validated)
python scripts/extract_data.py

# Validate extracted data
python -m src.data_loader validate

# Full check (lint + test + validate)
make check
```

---

## Key Technical Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Python + Flask + htmx + Pydantic | Stable, battle-tested, full HTML control |
| 2 | JSON files (not SQLite) | Human-readable, git-diffable, sufficient for V1 |
| 3 | Two scoring modes (per-category + balanced sliders) | No hidden weights; user controls the sliders |
| 4 | 3-tier extraction (network → bundle → DOM) | Highest fidelity first, DOM as fallback |
| 5 | pytest at 85% coverage | Meaningful without being wasteful |
| 6 | One JSON file per profile | Simple atomic writes, CRUD via Flask |
| 7 | Categories: offense, defense, economy, utility | Four values; `for_category()` falls back to 1.0 |
| 8 | Effect monotonicity = warning, cost monotonicity = hard error | Per game context doc §10 |
| 9 | Profile tags are free-form strings | User's own vocabulary, no schema update needed |

---

## Phase 3 "Done" Definition

Phase 3 is done when:
- [ ] All transfer pack docs exist and are internally consistent
- [ ] `docs/todo_now.md` has a prioritized task list for Phase 4+
- [ ] `docs/extraction_playbook.md` has step-by-step extraction instructions
- [ ] `prompts/cursor_kickoff.md` can be pasted into Cursor to resume work
- [ ] All existing tests still pass (67/67)
- [ ] Lint is clean
- [ ] Changes are committed and pushed

---

## Where to Start

1. Read `docs/todo_now.md` — the prioritized "what to do next" list.
2. Read `docs/extraction_playbook.md` — how to extract real data.
3. Run `make check` to verify repo health.
4. If resuming in Cursor, paste `prompts/cursor_kickoff.md` as your first message.
