# AGENTS.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

Tower Upgrade Advisor is a Flask web application that recommends the best next permanent upgrade in "The Tower" (idle tower defense mobile game). It calculates marginal benefit per coin for each upgrade and ranks them using pluggable scoring engines.

## Build & Development Commands

```bash
# Install dependencies
pip install -e ".[dev]"          # Development (includes pytest, ruff, mypy)
pip install -e ".[extract]"      # Data extraction tools (playwright, httpx)

# Run the app
python app.py

# Testing
pytest                           # Run tests (fast, stops on first failure)
pytest -x -q -m ""               # Run all tests including slow/integration
pytest --cov=src --cov-report=term-missing  # With coverage
pytest tests/test_scoring.py::TestBalancedEngine::test_ranks_all_upgrades  # Single test

# Linting & Type Checking
ruff check src/ tests/           # Lint
ruff format --check src/ tests/  # Format check
ruff check --fix src/ tests/     # Auto-fix lint issues
ruff format src/ tests/          # Auto-format
mypy src/                        # Type check (strict mode)

# Data validation
python -m src.data_loader validate  # Validate upgrade data JSON

# All checks (lint + test + validate)
make check
```

## Architecture

### Core Data Flow
1. `data_loader.py` loads `data/upgrades.json` → `UpgradeDatabase` (Pydantic model)
2. `profile_manager.py` manages user profiles in `data/profiles/{id}.json`
3. Scoring engines (`scoring.py`) rank upgrades by `marginal_benefit / cost * weight`
4. Flask app (not yet implemented) serves recommendations

### Scoring Engines (Protocol-based)
All engines implement `ScoringEngine` protocol with `rank()` and `explain()` methods:
- **PerCategoryEngine**: Best upgrade per category (attack/defense/utility), no cross-category comparison
- **BalancedEngine**: Global ranking with user-adjustable category weights (0.0-2.0 sliders)
- **ReferenceEngine**: DPS-based efficiency scoring for attack upgrades, ported from jacoelt/tower-calculator. Uses `(DPS_after - DPS_before) / cost` for attack upgrades, falls back to `marginal_benefit / cost` for defense/utility.

### Key Scoring Formulas
```
# BalancedEngine
score = marginal_benefit / coin_cost * category_weight

# ReferenceEngine (attack upgrades)
DPS = damage * attack_speed_final * crit_mult * multishot_mult * bounce_mult
crit_mult = 1 - (crit_chance/100) + (crit_chance/100) * crit_factor
multishot_mult = 1 - (ms_chance/100) + (ms_chance/100) * ms_targets
bounce_mult = 1 - (bounce_chance/100) + (bounce_chance/100) * bounce_targets
efficiency = (new_DPS - current_DPS) / cost
```

### Data Models (`src/models.py`)
- `UpgradeDatabase`: Container for all upgrade definitions (versioned, includes game version)
- `UpgradeDefinition`: Single upgrade with levels array, category, effect_type (multiplicative/additive)
- `UpgradeLevel`: Per-level data (cost, cumulative_effect, effect_delta)
- `LabResearchDatabase` / `LabResearchDefinition`: Lab research boost data
- `Profile`: User state (current levels, lab levels, available coins, scoring weights)
- `RankedUpgrade`: Output of scoring engine with full transparency data

### Profile Storage
Profiles are stored as individual JSON files with atomic writes (write to `.tmp`, then rename). ProfileManager handles CRUD operations.

## Testing Patterns

- Test fixtures in `tests/fixtures/` (test_upgrades.json with 8 sample upgrades)
- Shared fixtures in `tests/conftest.py`: `test_upgrades`, `empty_profile`, `mid_profile`, `maxed_profile`
- Tests are organized by class per module (e.g., `TestPerCategoryEngine`, `TestBalancedEngine`)
- Markers: `@pytest.mark.slow`, `@pytest.mark.integration`

## Important Conventions

- All Pydantic models use v2 API (`model_validate`, `model_dump_json`, `model_copy`)
- Upgrade categories: `"attack"`, `"defense"`, `"utility"` (lowercase, match the in-game workshop tabs)
- Level 0 means "not purchased" — use `upgrade.base_value` for effect (1.0 for multiplicative, 0 for additive)
- `levels` array is 0-indexed but `level` field is 1-indexed (index `i` holds data for level `i+1`)
- Scores are rounded to 12 decimal places for deterministic comparison; tie-break: lower cost, then alphabetical name
