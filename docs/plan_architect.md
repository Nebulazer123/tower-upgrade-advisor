# Architect Plan — Tower Upgrade Advisor

## 1. Stack Decision

### Options Evaluated

| Option | Pros | Cons | V1 Fit |
|--------|------|------|--------|
| **Python + Textual TUI** | Zero browser deps, fast startup, matches Python scaffold, terminal-native | Limited visual richness, no tables with sorting easily, learning curve for Textual | Medium |
| **Python + Flask/FastAPI + htmx** | Full HTML/CSS control, local server, rich tables/forms, htmx keeps it simple | Requires running a server, two-language concern (Python+HTML), more moving parts | High |
| **TypeScript/Electron** | Rich desktop UI, powerful | Heavy, doesn't match Python scaffold, overkill for V1, slow startup | Low |
| **Python + Streamlit** | Fastest to prototype, built-in widgets, auto-reload | Janky feel on re-render, limited control, profile management awkward, hard to customize deeply | Medium-High |
| **Python + NiceGUI** | Python-native web UI, simple API, auto-refresh, good table support | Newer library, smaller community, less battle-tested | Medium-High |

### Recommendation: Python + Flask + htmx

**Rationale:**
1. Matches the existing Python scaffolding
2. Full control over layout — critical for showing transparent math tables
3. htmx keeps interactivity simple without a JS build step
4. Local-first by default (runs on localhost)
5. Profile management via standard routes/forms
6. Easy to test backend independently of UI
7. Can later add hosting if desired

**Disagreement note:** The empty `app.py` hints at a pure Python approach. Streamlit would be faster to prototype, but its re-render model makes stateful profile editing painful. Flask + htmx is the right tradeoff for a tool used daily — it's stable, predictable, and fully customizable.

## 2. Repo Layout

```
tower-upgrade-advisor/
├── app.py                    # Flask application entry point
├── pyproject.toml            # Project config, dependencies
├── requirements.txt          # Pinned deps (or use pyproject.toml)
├── data/
│   ├── upgrades.json         # Normalized upgrade data (source of truth)
│   ├── schema.json           # JSON Schema for upgrades.json validation
│   └── profiles/             # User profiles (one .json per profile)
│       └── default.json
├── src/
│   ├── __init__.py
│   ├── models.py             # Pydantic models: Upgrade, Profile, UpgradeScore
│   ├── data_loader.py        # Load + validate upgrades.json
│   ├── scoring.py            # Scoring engine (Protocol + implementations)
│   ├── profile_manager.py    # CRUD for profiles
│   └── routes.py             # Flask routes (if separated from app.py)
├── templates/                # Jinja2 HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── recommendation.html
│   ├── profile_select.html
│   └── upgrade_detail.html
├── static/                   # CSS, minimal JS
│   └── style.css
├── scripts/
│   ├── extract_data.py       # Playwright extraction script
│   └── validate_data.py      # Standalone data validation
├── tests/
│   ├── test_scoring.py
│   ├── test_data_loader.py
│   ├── test_profile_manager.py
│   ├── test_validation.py
│   └── fixtures/
│       └── test_upgrades.json
├── docs/                     # Project documentation (this directory)
├── prompts/                  # Agent prompts for reproducibility
├── .gitignore
└── README.md
```

## 3. Integration Plan

### Data Layer
- `data/upgrades.json` is the single source of truth for upgrade data
- Loaded at app startup via `data_loader.py`
- Validated against `data/schema.json` on every load
- Pydantic models (`models.py`) enforce types at runtime

### Logic Layer
- `scoring.py` implements the `ScoringEngine` protocol
- Takes a profile + upgrade data → returns ranked list
- Pure functions, no side effects, fully testable
- Scoring engine is injected (swappable)

### UI Layer
- Flask serves Jinja2 templates
- htmx handles interactive elements (level inputs, profile switch) without full page reloads
- Dashboard shows all upgrades grouped by category with current levels
- Recommendation view highlights #1 pick with transparent math

### Profile Management
- Profiles stored as individual JSON files in `data/profiles/`
- Each profile: `{name, created, modified, levels: {upgrade_id: current_level}}`
- ProfileManager handles CRUD, validation, listing
- URL-routed: `/profile/<name>/dashboard`, `/profile/<name>/recommend`

## 4. Risks and Unknowns

1. **Data accuracy**: If extraction from reference site fails, we have no verified data source
2. **Game updates**: New game versions may add/remove upgrades, breaking our data
3. **Flask development server**: Not production-grade, but fine for local use
4. **htmx learning curve**: Team needs familiarity; fallback to plain forms if needed
5. **Profile corruption**: No database, pure JSON files — need atomic writes
6. **Scaling**: JSON file per profile is fine for < 100 profiles; would need SQLite if more
7. **Dependency management**: Need to pin versions; uv or pip-tools recommended

## 5. Messages to Other Teammates

### To Data Engineer
- Upgrade data must live in `data/upgrades.json`
- Format: JSON array of upgrade objects with nested level arrays
- Must include a `data/schema.json` for validation
- Profiles go in `data/profiles/*.json`
- I expect Pydantic models in `src/models.py` to match your schema exactly

### To Algorithm Engineer
- Scoring engine should be a class implementing a Protocol in `src/scoring.py`
- It receives: profile (dict of upgrade_id → level) and upgrade data (loaded from JSON)
- It returns: a ranked list of `RankedUpgrade` objects with score, breakdown, and raw numbers
- Must be pure/deterministic — no randomness, no side effects

### To UI Engineer
- Use Flask + Jinja2 + htmx
- Templates go in `templates/`, static in `static/`
- No JS build step — htmx loaded from CDN or vendored
- Route structure: `/`, `/profile/<name>`, `/profile/<name>/recommend`, `/upgrade/<id>`
- htmx for: level input updates, profile switching, expand/collapse categories

### To Reliability Engineer
- Use pytest as test framework
- `tests/` directory already exists
- Need a `tests/fixtures/` with test data subsets
- Pre-commit hooks: ruff (lint), mypy (type check), pytest (fast tests)
- Data validation should run as both a script (`scripts/validate_data.py`) and as pytest tests

## 6. Acceptance Tests

1. `app.py` starts a Flask server that serves the dashboard on `localhost`
2. All source modules are importable with no circular dependencies
3. `data/upgrades.json` loads and validates against `data/schema.json`
4. A test profile can be created, read, updated, and deleted via `ProfileManager`
5. The scoring engine produces a ranked list given any valid profile + data combination
