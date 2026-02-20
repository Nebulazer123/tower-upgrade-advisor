# Tower Upgrade Advisor

Recommends the best next Workshop upgrade in "The Tower" (idle tower defense mobile game).

## What It Does

Tower Upgrade Advisor is a local-first desktop tool for players of "The Tower." Given your current upgrade levels and available coins, it ranks all permanent Workshop upgrades by value and recommends the single best next purchase. It shows transparent math: coin cost, marginal benefit, and score for each option.

- **Input:** Player profile (current levels per upgrade, coins available)
- **Output:** Ranked recommendations with explainable scoring
- **Reference:** [tower-workshop-calculator.netlify.app](https://tower-workshop-calculator.netlify.app/)

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run tests
make test

# Run the app (requires data/upgrades.json)
make run
```

On macOS, use `python3` (not `python`) for any manual Python commands.

## Architecture

| Module | Purpose |
|--------|---------|
| `src/models.py` | Pydantic v2 models: UpgradeDefinition, UpgradeDatabase, Profile, RankedUpgrade |
| `src/scoring.py` | ScoringEngine protocol + PerCategoryEngine, BalancedEngine, ReferenceEngine (stub) |
| `src/data_loader.py` | Load, validate, and save upgrade JSON |
| `src/profile_manager.py` | CRUD for profiles with atomic writes |
| `scripts/` | `extract_data.py` (Playwright extraction), `manual_import.py` (manual fallback) |
| `tests/` | 67 tests across models, scoring, data_loader, profile_manager |

## Scoring

All engines use the same core formula:

```
score = marginal_benefit / cost * category_weight
```

- **Per-category mode:** Best upgrade per category independently (no cross-category comparison)
- **Balanced mode:** Global ranking with user-adjustable sliders (Economy, Offense, Defense, Utility, 0–2 each)

## Current Status

| Phase | Status |
|-------|--------|
| Phase 1: Planning | Done — 13 docs, all approved |
| Phase 2: Foundation | Done — pyproject, Makefile, models, tests |
| Phase 3: Data | Partially done — extract_data.py scaffolding, data_loader exists, data/upgrades.json not yet extracted |
| Phase 4: Scoring | Done — scoring.py with 3 engines, 21 tests |
| Phase 5: Profile Management | Done — profile_manager.py with CRUD, 15 tests |
| Phase 6: UI | In progress — Flask + htmx being built |
| Phase 7: Integration | In progress — integration tests being added |

## Project Documentation

| Doc | Description |
|-----|-------------|
| `docs/brief.md` | Project goal, scope, non-goals |
| `docs/transfer_pack.md` | Quick handoff for any agent or teammate |
| `docs/todo_now.md` | Prioritized task list for Phase 4+ |
| `docs/decisions.md` | Technical decisions log |
| `docs/extraction_playbook.md` | Step-by-step extraction instructions |
| `docs/scoring.md` | Scoring engine specification |
| `docs/data_schema.md` | Upgrade JSON schema spec |

## Development

```bash
# Run tests
make test

# Lint
make lint

# Validate upgrade data (requires data/upgrades.json)
make validate

# Full check (lint + test + validate)
make check
```
