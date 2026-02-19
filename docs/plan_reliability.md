# Reliability Engineer Plan — Tower Upgrade Advisor

## 1. Test Strategy

### Test Pyramid

```
         ┌──────────┐
         │   E2E    │  ← Playwright browser tests (later, not V1)
        ┌┴──────────┴┐
        │ Integration │  ← Flask test client, data→scoring→output
       ┌┴────────────┴┐
       │  Data Valid.  │  ← Automated checks on upgrades.json
      ┌┴──────────────┴┐
      │   Unit Tests    │  ← Scoring engine, data loader, profile manager
      └────────────────┘
```

### Unit Tests (`tests/test_*.py`)
| Module | Test Focus | Priority |
|--------|-----------|----------|
| `scoring.py` | Known-answer scoring, edge cases, determinism | P0 |
| `data_loader.py` | Load valid data, reject invalid data, schema validation | P0 |
| `profile_manager.py` | CRUD, atomic writes, corrupt file handling | P1 |
| `models.py` | Pydantic model validation, serialization | P1 |

### Data Validation Tests (`tests/test_data_validation.py`)
Run against `data/upgrades.json` on every test execution:
- Schema conformance
- Completeness checks
- Numeric integrity
- Monotonicity

### Integration Tests (`tests/test_integration.py`)
- Load data → create profile → run scoring → verify output format
- Flask route tests: GET/POST all routes, verify status codes and response content
- Profile save → reload → verify identity

### Regression Tests (`tests/test_regression.py`)
- "Golden file" tests: known profile + known data → expected exact ranking
- Store expected outputs in `tests/fixtures/expected_ranking_*.json`
- Any scoring change must update golden files explicitly

## 2. Test Infrastructure

### Framework: pytest
**pytest is the right choice.** No disagreement here. Reasons:
- Standard for modern Python
- Rich plugin ecosystem (pytest-cov, pytest-xdist, pytest-sugar)
- Better assertion introspection than unittest
- Fixture system is excellent for test data

### Coverage Targets
| Module | Target | Rationale |
|--------|--------|-----------|
| `scoring.py` | 95%+ | Core logic; correctness is critical |
| `data_loader.py` | 90%+ | Data integrity is critical |
| `profile_manager.py` | 85%+ | CRUD with error handling |
| `models.py` | 80%+ | Mostly Pydantic, which handles its own validation |
| `routes.py` | 75%+ | Integration-level, some paths tested via Flask client |
| **Overall** | **85%+** | Reasonable without being wasteful |

**DISAGREEMENT on 100% coverage:** Pursuing 100% is counterproductive. It incentivizes testing trivial getters/setters and writing tests that assert implementation details rather than behavior. 85% with meaningful coverage of critical paths is better than 100% with cargo-cult tests.

### Fixtures
```
tests/
├── conftest.py              # Shared fixtures
├── fixtures/
│   ├── test_upgrades.json   # Small valid dataset (5 upgrades, 10 levels each)
│   ├── test_profile.json    # Standard test profile
│   ├── invalid_data/
│   │   ├── missing_fields.json
│   │   ├── bad_types.json
│   │   ├── string_costs.json    # "1.2M" instead of 1200000
│   │   ├── non_monotonic.json
│   │   └── duplicate_ids.json
│   └── expected/
│       └── ranking_basic.json   # Expected output for golden test
├── test_scoring.py
├── test_data_loader.py
├── test_data_validation.py
├── test_profile_manager.py
├── test_integration.py
└── test_regression.py
```

### Test Marks
```python
# In conftest.py or individual files
import pytest

# Fast tests (< 1s each): run always
# Slow tests (data validation, integration): marked
pytestmark_slow = pytest.mark.slow
pytestmark_integration = pytest.mark.integration

# pytest.ini / pyproject.toml:
# [tool.pytest.ini_options]
# markers = ["slow: marks tests as slow", "integration: integration tests"]
# addopts = "-m 'not slow'" # default: skip slow tests
```

## 3. Data Integrity Guardrails

### Validation Suite (runs as pytest AND standalone script)

```python
# scripts/validate_data.py AND tests/test_data_validation.py

class DataValidator:
    def validate_schema(self, data: dict) -> list[str]:
        """JSON Schema validation against data/schema.json"""

    def validate_completeness(self, data: dict) -> list[str]:
        """No missing levels, no gaps, expected upgrade count"""

    def validate_numeric_integrity(self, data: dict) -> list[str]:
        """All costs positive, all effects numeric, no NaN/Inf"""

    def validate_monotonicity(self, data: dict) -> list[str]:
        """Costs increasing, effects non-decreasing"""

    def validate_uniqueness(self, data: dict) -> list[str]:
        """No duplicate IDs, no duplicate names per category"""

    def validate_parsing(self, data: dict) -> list[str]:
        """No string leaks, no formatted numbers"""

    def validate_all(self, data: dict) -> list[str]:
        """Run all validators, return list of error messages"""
```

### Specific Checks

| Check | Rule | Severity |
|-------|------|----------|
| Schema conformance | All required fields present and typed correctly | ERROR |
| No missing levels | Levels 1..max_level all present, no gaps | ERROR |
| No duplicate upgrade IDs | Unique across entire dataset | ERROR |
| Costs positive | Every `coin_cost > 0` | ERROR |
| Effects numeric | `isinstance(v, (int, float))` and not `math.isnan/isinf` | ERROR |
| Costs monotonic | `cost[n+1] > cost[n]` for all n | ERROR |
| Effects non-decreasing | `effect[n+1] >= effect[n]` | WARNING (some upgrades may have special behavior) |
| No string numbers | No values matching `r'^\d[\d,.]+[KMB]?$'` in numeric fields | ERROR |
| Level bounds | `0 <= level <= max_level` for all profile entries | ERROR |
| Expected count | Total upgrades matches documented count | WARNING |
| Display order unique | No duplicate display_order within a category | WARNING |

## 4. CI Recommendations

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff          # Linting
      - id: ruff-format   # Formatting
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        additional_dependencies: [pydantic, flask]
  - repo: local
    hooks:
      - id: fast-tests
        name: Fast tests
        entry: pytest -x -q -m "not slow and not integration"
        language: system
        pass_filenames: false
```

**DISAGREEMENT on pre-commit hooks for a solo developer:** Pre-commit hooks add friction for small changes. For a solo project used daily, I'd recommend:
- **Keep:** ruff (fast, catches real bugs)
- **Keep:** ruff-format (auto-fixes, zero effort)
- **Optional:** mypy (useful but can be slow; run manually)
- **Skip in pre-commit:** pytest (run manually before commits; too slow for pre-commit)

Alternative: Use a simple `make check` target that runs everything.

### Makefile
```makefile
.PHONY: test lint typecheck check validate run

test:
    pytest -x -q

test-all:
    pytest -x --slow --integration

lint:
    ruff check src/ tests/
    ruff format --check src/ tests/

typecheck:
    mypy src/

validate:
    python scripts/validate_data.py

check: lint typecheck test validate

run:
    python app.py
```

### GitHub Actions (if/when repo goes to GitHub)
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -e ".[dev]"
      - run: make check
```

## 5. Failure Modes Analysis

| # | Failure Mode | Impact | Mitigation |
|---|-------------|--------|------------|
| 1 | `data/upgrades.json` missing or corrupt | App won't start | Validate on startup; clear error message; ship a known-good default | |
| 2 | Numeric overflow in cost calculation | Wrong recommendation | Use Python's arbitrary-precision ints; validate max values |
| 3 | Division by zero in scoring | Crash | Validate all costs > 0; assert before division |
| 4 | Profile JSON corrupt | Lost user data | Atomic writes (write to .tmp, rename); backup on save |
| 5 | Upgrade at max level attempted | Score for non-existent level | Filter out max-level upgrades before scoring |
| 6 | New game version adds upgrades | Missing data | Profile loads gracefully with missing upgrades (default to 0); validation warns |
| 7 | New game version removes upgrades | Orphaned profile data | Profile load ignores unknown upgrade IDs; validation warns |
| 8 | Floating-point comparison issues | Unstable rankings | Use `decimal.Decimal` for costs, or sort with epsilon tolerance |
| 9 | File permission error on write | Can't save profile | Catch `PermissionError`, show user-friendly message |
| 10 | Concurrent access to same profile | Data race | Unlikely for local tool; add file locking if needed later |
| 11 | Very large profile directory | Slow listing | Unlikely for V1; glob-based listing is fine |
| 12 | User enters negative level | Invalid state | Validate level >= 0 at input and model level |
| 13 | Browser cache serves stale data | Confusing UI | Set no-cache headers for htmx endpoints |
| 14 | Port already in use | Flask won't start | Try port 5000, fallback to 5001, clear message |

## 6. Determinism and Reproducibility

### Scoring Determinism
- No `random` calls anywhere in scoring code
- No floating-point operations that depend on platform (use `round(x, 10)` for comparisons)
- Tie-breaking rule is deterministic: lower cost wins, then alphabetical
- Sort is stable (Python's sort is stable)

### Recommendation Logging
```python
@dataclass
class RecommendationLog:
    timestamp: str
    profile_snapshot: dict
    engine_name: str
    engine_version: str
    ranking: list[RankedUpgrade]
    data_version: str
```

Store in `data/logs/` as append-only JSON lines. Optional for V1 but the interface should exist.

### Snapshot Testing
- Store expected outputs for known inputs in `tests/fixtures/expected/`
- `pytest` compares actual vs expected; any change requires explicit update
- Update command: `pytest --update-snapshots`

## 7. Risks and Unknowns

1. **Test data accuracy**: Test fixtures may not represent real game data patterns
2. **Validation rules may be too strict**: Edge cases in real data may fail validation
3. **No real game data available yet**: Can't write meaningful golden tests until data is extracted
4. **CI may be overkill for solo project**: Balance automation vs. friction
5. **Type checking coverage**: mypy may struggle with Flask/Jinja2 dynamic typing
6. **Test maintenance burden**: Too many tests = burden when refactoring; focus on behavior tests

## 8. Messages to Other Teammates

### To Architect
- Need `pyproject.toml` with `[project.optional-dependencies]` for dev deps (pytest, mypy, ruff)
- Need a `Makefile` for standard commands
- Recommend Python 3.11+ for improved error messages and typing

### To Data Engineer
- I will write validation tests for every rule you define
- Please provide at least 3 "bad data" examples for negative testing (string costs, missing levels, etc.)
- Validation should return structured errors, not just pass/fail

### To Algorithm Engineer
- I need 3-5 "known answer" test cases: specific profile + specific data → expected ranking
- Please document the exact tie-breaking rules
- Scoring function must be a pure function for testability

### To UI Engineer
- Every Flask route must return proper HTTP status codes
- htmx endpoints must work with Flask test client (they're just HTTP)
- Add `data-testid` attributes to key elements for future E2E tests

## 9. Acceptance Tests

1. `pytest` runs green with 85%+ coverage across all modules
2. `data/upgrades.json` passes all validation rules
3. At least 3 known-answer regression tests pass
4. `make check` runs lint + typecheck + tests + validation in a single command
5. No `assert` statements in production code (use proper error handling); all assertions in tests
