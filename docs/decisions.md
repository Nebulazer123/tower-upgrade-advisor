# Decisions Log — Tower Upgrade Advisor

## Decision 1: Stack Choice

**Decision:** Python + Flask + htmx + Pydantic

**Alternatives Considered:**
| Option | Verdict | Reason |
|--------|---------|--------|
| Python + Streamlit | Rejected | Re-render model is painful for editing 30+ fields daily |
| Python + Textual TUI | Rejected | Insufficient visual richness for data-heavy tables |
| TypeScript / Electron | Rejected | Doesn't match Python scaffolding; overkill for V1 |
| Python + NiceGUI | Rejected | Smaller community; less battle-tested |

**Rationale:**
- Flask is stable, battle-tested, and gives full control over HTML/CSS layout
- htmx provides smooth interactivity without JS build tooling
- Pydantic v2 enforces types at runtime, critical for data integrity
- Matches existing Python scaffolding (`.gitignore`, `app.py`)
- Easily extensible to hosted version later

**Cross-team agreement:** All teammates agree on Python. Architect and UI Engineer both independently recommended Flask + htmx. Data Engineer prefers Pydantic for schema validation.

---

## Decision 2: Data Storage Format

**Decision:** JSON files (not SQLite)

**Rationale:**
- Upgrade data is read-heavy, rarely written (~30 upgrades, ~100 levels each)
- JSON is human-readable, git-diffable, and easy to edit manually
- Profile data is small (one dict of ~30 key-value pairs per profile)
- SQLite adds complexity with no V1 benefit
- Will revisit if profile count > 100 or if we need query capabilities

**Data Engineer had a partial disagreement:** Argued SQLite is better for data integrity, but conceded JSON + Pydantic validation achieves the same for V1 scale.

---

## Decision 3: Scoring Algorithm V1 (MODIFIED per approval)

**Decision:** Two scoring modes, no hardcoded category weights as "truth"

**Mode 1 — Per-Category Best (always available):**
```
score = marginal_benefit / cost    (within each category independently)
```
Returns one best-next-upgrade per category. No cross-category comparison needed.

**Mode 2 — Balanced Mode (user-adjustable sliders):**
```
score = marginal_benefit / cost * slider_weight(category)
```
Three sliders: Economy (0-2, default 1.0), Offense (0-2, default 1.0), Defense (0-2, default 1.0).
Sliders are **always visible** so users see what produced the recommendation.

**Mode 3 — Reference Mode (if discoverable):**
Replicate the reference tool's scoring logic as a separate ScoringEngine.

**Rationale:**
- No hidden weights masquerading as universal truth
- Per-category mode is unambiguous and always useful
- Balanced mode is transparent (user sees and controls the weights)
- Interface supports future scoring methods via Protocol

**Approved modification:** User explicitly required no hardcoded category weights as default "truth."

---

## Decision 4: Data Extraction Approach (MODIFIED per approval)

**Decision:** Three-tier extraction with artifact preservation

**Priority order (approved):**
1. **Playwright network interception** — intercept JSON/XHR responses from the reference tool
2. **JS bundle download + embedded data search** — download and parse the 7.2MB main.js bundle
3. **DOM scraping** — Playwright DOM traversal as last resort

**Artifact management:**
- Store raw extraction artifacts in `data/raw/` (gitignored)
- Store parsed/normalized output in `data/upgrades.json`
- Validators fail fast on missing levels, duplicates, numeric parsing errors

**Repo hygiene (approved modification):**
- `data/raw/` is gitignored (large scraped data should not be committed)
- `data/profiles/` is gitignored (user data)
- `data/upgrades.json` is committed only if small enough; otherwise gitignored with a generation script
- `docs/data_loading.md` documents how to regenerate data

**Known CSS selectors for Playwright DOM scraping (fallback):**
- `.category`, `.category-name`, `.attack`, `.defense`, `.utility`
- `.upgrade`, `.upgrade-value`, `.cost`, `.level`
- `.current`, `.target`, `#overview`, `#analysis`

---

## Decision 5: Test Strategy

**Decision:** pytest with 85% coverage target, Makefile for commands, no pre-commit pytest

**Rationale:**
- pytest is modern Python standard
- 85% coverage is meaningful without being wasteful
- Pre-commit hooks: ruff (lint) + ruff-format (format) only
- Full test suite via `make check` before commits
- Reliability Engineer argued against 100% coverage; team agrees

---

## Decision 6: Profile Management

**Decision:** One JSON file per profile in `data/profiles/`

**Rationale:**
- Simple, human-readable, git-friendly
- Atomic writes (write to .tmp, rename) prevent corruption
- Profile CRUD via Flask routes
- Scale limit: ~100 profiles (sufficient for V1)

---

## Decision 7: Category Naming and Handling (from game_and_project_context.md review)

**Decision:** Categories are `"offense" | "defense" | "economy" | "utility"` — four values, not three.

**Rationale:**
- `docs/game_and_project_context.md` §10 explicitly lists utility as a separate dimension
- Reference site CSS confirms `.attack`, `.defense`, `.utility` groupings (not `.economy`)
- Category names will be locked down after real data extraction — Literal updated to include all known values
- `ScoringWeights.for_category()` falls back to `1.0` for unknown categories instead of raising, so a future game update cannot silently zero out new upgrade types

---

## Decision 8: Cumulative-Effect Monotonicity is a Warning, Not a Hard Error

**Decision:** Non-decreasing `cumulative_effect` is validated as a **warning** in `data_loader`, not as a Pydantic `ValidationError` in the model.

**Rationale:**
- `docs/game_and_project_context.md` §10: *"Do not enforce monotonic rules globally if some upgrades intentionally break that pattern."*
- Some upgrades may have equal effects at adjacent levels due to rounding
- Cost monotonicity remains a hard error (structural data integrity)
- Effect monotonicity anomalies are logged as warnings and must be reviewed, not silently discarded

---

## Decision 9: Profile Tags Field

**Decision:** `Profile.tags` is a free-form `list[str]` (not an enum), default empty list.

**Rationale:**
- `docs/game_and_project_context.md` §11 specifies optional tags (farm build, push build, balanced build)
- Free-form strings let the user define their own vocabulary without a schema update
- Tags are for the user's own organisation; they do not affect scoring logic
