# AGENTS.md

This file provides guidance to AI agents (Cursor, WARP, etc.) when working with code in this repository.

## Project Overview

Tower Upgrade Advisor is a Flask web application that recommends the best next permanent upgrade in "The Tower" (idle tower defense mobile game). It calculates marginal benefit per coin for each upgrade and ranks them using pluggable scoring engines.

## Build & Development Commands

Use `python3` on macOS (not `python`).

```bash
# Install dependencies
pip install -e ".[dev]"          # Development (includes pytest, ruff, mypy)
pip install -e ".[extract]"      # Data extraction tools (playwright, httpx)

# Run the app (requires app.py and data/upgrades.json; app.py in progress)
python3 app.py

# Testing (67 tests)
pytest -x -q                    # Run tests (fast, stops on first failure)
pytest -x -q -m ""              # Run all tests including slow/integration
pytest --cov=src --cov-report=term-missing  # With coverage
pytest tests/test_scoring.py::TestBalancedEngine::test_ranks_all_upgrades  # Single test

# Linting & Type Checking
ruff check src/ tests/ scripts/ # Lint
ruff format --check src/ tests/ scripts/ # Format check
ruff check --fix src/ tests/ scripts/ # Auto-fix lint issues
ruff format src/ tests/ scripts/ # Auto-format
mypy src/                      # Type check (strict mode)

# Data validation
python3 -m src.data_loader validate  # Validate upgrade data JSON

# All checks (lint + test + validate)
make check
```

## Architecture

### Core Data Flow
1. `data_loader.py` loads `data/upgrades.json` → `UpgradeDatabase` (Pydantic model)
2. `profile_manager.py` manages user profiles in `data/profiles/{id}.json`
3. Scoring engines (`scoring.py`) rank upgrades by `marginal_benefit / cost * weight`
4. Flask app (`app.py`, templates/, static/) — UI being built (templates/base.html, index.html, static/style.css, htmx.min.js exist; app.py in progress)

### Scoring Engines (Protocol-based)
All engines implement `ScoringEngine` protocol with `rank()` and `explain()` methods:
- **PerCategoryEngine**: Best upgrade per category (offense/defense/economy/utility), no cross-category comparison
- **BalancedEngine**: Global ranking with user-adjustable category weights (0.0-2.0 sliders)
- **ReferenceEngine**: Stub for reverse-engineered reference tool logic (raises NotImplementedError)

### Key Scoring Formula
```
score = marginal_benefit / coin_cost * category_weight
marginal_benefit = next_level_effect - current_level_effect
```

### Data Models (`src/models.py`)
- `UpgradeDatabase`: Container for all upgrade definitions (versioned, includes game version)
- `UpgradeDefinition`: Single upgrade with levels array, category, effect_type (multiplicative/additive)
- `UpgradeLevel`: Per-level data (cost, cumulative_effect, effect_delta)
- `Profile`: User state (current levels, available coins, scoring weights)
- `RankedUpgrade`: Output of scoring engine with full transparency data

### Profile Storage
Profiles are stored as individual JSON files with atomic writes (write to `.tmp`, then rename). ProfileManager handles CRUD operations.

## Testing Patterns

- 67 passing tests across test_models (18), test_scoring (21), test_data_loader (13), test_profile_manager (15)
- Test fixtures in `tests/fixtures/` (test_upgrades.json with 6 sample upgrades)
- Shared fixtures in `tests/conftest.py`: `test_upgrades`, `empty_profile`, `mid_profile`, `maxed_profile`
- Tests are organized by class per module (e.g., `TestPerCategoryEngine`, `TestBalancedEngine`)
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`

## Important Conventions

- All Pydantic models use v2 API (`model_validate`, `model_dump_json`, `model_copy`)
- Upgrade categories: `"offense"`, `"defense"`, `"economy"`, `"utility"` in code (lowercase). User says game uses attack/defense/utility — Literal will be updated after extraction.
- Level 0 means "not purchased" — use `upgrade.base_value` for effect (1.0 for multiplicative, 0 for additive)
- `levels` array is 0-indexed but `level` field is 1-indexed (index `i` holds data for level `i+1`)
- Scores are rounded to 12 decimal places for deterministic comparison; tie-break: lower cost, then alphabetical name
