# UI Engineer Plan — Tower Upgrade Advisor

## 1. UI Framework Evaluation

| Framework | Pros | Cons | V1 Fit |
|-----------|------|------|--------|
| **Textual (TUI)** | Zero deps, fast, terminal-native, no browser | Poor table sorting, limited visual richness, awkward for data-heavy views | Low-Medium |
| **Streamlit** | Fastest to prototype, nice widgets | Re-render model is janky, poor profile CRUD, limited customization, "restart on every click" feel | Medium |
| **Flask + htmx** | Full HTML/CSS control, stable, local server, great table support, htmx for interactivity | Requires HTML/CSS work, two languages | High |
| **NiceGUI** | Python-native web UI, easy binding | Smaller community, less battle-tested, unexpected behaviors | Medium |
| **PyQt/PySide** | True native desktop, full control | Heavy dependency, complex, slow development, overkill for V1 | Low |

### Recommendation: Flask + htmx

**Rationale:**
1. **Tables are the core UI element** — HTML tables with CSS are the best way to show upgrade data with sorting, highlighting, and inline editing
2. **htmx eliminates the need for JS build tooling** while still providing smooth interactivity (inline level editing, live search, category expand/collapse)
3. **Stable and battle-tested** — Flask has been production-grade since 2010
4. **Daily use experience** — opens in any browser, bookmark-able, familiar
5. **Easy to test** — Flask test client for integration tests, templates are just HTML

### DISAGREEMENT: Streamlit would be a mistake
Streamlit's re-render-on-every-interaction model is painful for a tool where you:
- Edit 20+ upgrade levels
- Switch between profiles
- Compare alternatives

Each interaction causes a full page re-render, losing scroll position and focus. For daily use, this produces a frustrating experience. Flask + htmx gives precise control over what updates.

## 2. Screen/View Design

### Screen 1: Profile Selector (`/`)

```
┌──────────────────────────────────────────────┐
│  Tower Upgrade Advisor                        │
│                                               │
│  Select Profile:                              │
│  ┌─────────────────────────────────────────┐  │
│  │ ● My Main Build        (modified today) │  │
│  │ ○ Speedrun Build        (modified 3d)   │  │
│  │ ○ New Player Guide      (modified 1w)   │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  [Open]  [New Profile]  [Delete]              │
│                                               │
└──────────────────────────────────────────────┘
```

**Data shown:** Profile name, last modified timestamp
**User interactions:** Select profile, create new, delete (with confirmation), open selected

### Screen 2: Upgrade Dashboard (`/profile/<name>`)

```
┌──────────────────────────────────────────────────────────┐
│  My Main Build                [Recommend] [Save] [Back]  │
│  Available Coins: [  15,000  ]                           │
│                                                          │
│  ┌─ ATTACK ────────────────────────────────────────────┐ │
│  │  Upgrade        Level   Next Cost   Next Effect  Δ  │ │
│  │  Attack Speed   [ 15]   12,500      +0.05 atk/s    │ │
│  │  Damage         [ 20]   14,000      +10 dmg        │ │
│  │  Crit Chance    [  5]    8,500      +1% chance      │ │
│  │  Crit Factor    [ 10]   11,000      +0.1x multi    │ │
│  └─────────────────────────────────────────────────────┘ │
│  ┌─ DEFENSE ───────────────────────────────────────────┐ │
│  │  Health         [ 18]   11,000      +50 HP          │ │
│  │  Health Regen   [ 12]    9,000      +2 HP/s         │ │
│  │  ...                                                  │ │
│  └─────────────────────────────────────────────────────┘ │
│  ┌─ UTILITY ───────────────────────────────────────────┐ │
│  │  ...                                                  │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**Data shown:** All upgrades grouped by category, current level (editable), next level cost, next level effect delta
**User interactions:**
- Edit level numbers inline (htmx: on blur/enter, POST to update)
- Edit available coins
- Click [Recommend] to get recommendation
- Click [Save] to persist profile
- Expand/collapse category sections

### Screen 3: Recommendation View (`/profile/<name>/recommend`)

```
┌──────────────────────────────────────────────────────────┐
│  RECOMMENDATION for My Main Build              [Back]    │
│                                                          │
│  ╔═══════════════════════════════════════════════════╗    │
│  ║  #1 BEST: Damage (level 20 → 21)                ║    │
│  ║  Cost: 14,000 coins   |   You have: 15,000 ✓    ║    │
│  ║  Benefit: +10 damage  |   Score: 0.000714        ║    │
│  ║  Formula: (360-350) / 14,000 × 1.0              ║    │
│  ╚═══════════════════════════════════════════════════╝    │
│                                                          │
│  Top 5 Alternatives:                                     │
│  ┌────┬──────────────┬────────┬────────┬──────────────┐  │
│  │ #  │ Upgrade      │  Cost  │ Score  │ Affordable?  │  │
│  ├────┼──────────────┼────────┼────────┼──────────────┤  │
│  │ 2  │ Atk Speed    │ 12,500 │ 0.0007 │ Yes          │  │
│  │ 3  │ Health       │ 11,000 │ 0.0006 │ Yes          │  │
│  │ 4  │ Crit Chance  │  8,500 │ 0.0005 │ Yes          │  │
│  │ 5  │ Coins/Kill   │  9,200 │ 0.0004 │ Yes          │  │
│  └────┴──────────────┴────────┴────────┴──────────────┘  │
│                                                          │
│  Category Weights: Attack [1.0] Defense [1.0] Util [1.0] │
│  Scoring Method: marginal_benefit_per_coin v1            │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Data shown:** #1 recommendation with full breakdown, top 5 alternatives, scoring metadata
**User interactions:** Adjust category weights (re-ranks live via htmx), click any upgrade for detail view

### Screen 4: Upgrade Detail (`/upgrade/<id>?profile=<name>`)

```
┌──────────────────────────────────────────────────────────┐
│  Upgrade: Damage                              [Back]     │
│  Category: Attack | Type: Additive | Max Level: 100     │
│                                                          │
│  Your Level: 20 / 100                                    │
│                                                          │
│  Level Table:                                            │
│  ┌───────┬──────────┬─────────┬──────────┬────────────┐  │
│  │ Level │ Cost     │ Effect  │ Cum.Cost │ Cum.Effect │  │
│  ├───────┼──────────┼─────────┼──────────┼────────────┤  │
│  │  18   │  12,000  │  +10    │ 150,000  │   340      │  │
│  │  19   │  13,000  │  +10    │ 163,000  │   350      │  │
│  │→ 20   │  14,000  │  +10    │ 177,000  │   360   ← │  │
│  │  21   │  15,000  │  +10    │ 192,000  │   370      │  │
│  │  22   │  16,500  │  +10    │ 208,500  │   380      │  │
│  └───────┴──────────┴─────────┴──────────┴────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## 3. Upgrade Ordering and Grouping

Upgrades are grouped by category in the same order as in-game:
1. **Attack** (display_order: 1)
2. **Defense** (display_order: 2)
3. **Utility** (display_order: 3)
4. **Special** (display_order: 4, if applicable)

Within each category, upgrades follow `display_order` from the data.

**Implementation:**
- Data schema includes `category.display_order` and `upgrade.display_order`
- Templates iterate categories in order, then upgrades within each
- No client-side sorting needed — server renders in correct order

## 4. Profile Management

### CRUD Operations
- **Create**: `/profile/new` — name + optional starting template
- **Read**: `/profile/<name>` — loads dashboard
- **Update**: Inline level edits saved via htmx POST; explicit [Save] button for full save
- **Delete**: `/profile/<name>/delete` with confirmation modal

### Storage
- One JSON file per profile in `data/profiles/`
- Filename: slugified profile name (e.g., `my-main-build.json`)
- PoAtmic writes: write to `.tmp` file, then rename (prevents corruption)

### Profile Contents
```json
{
  "profile_version": "1.0.0",
  "name": "My Main Build",
  "created_at": "2025-01-01T00:00:00Z",
  "modified_at": "2025-01-15T10:30:00Z",
  "available_coins": 15000,
  "levels": {"attack_speed": 15, "damage": 20, ...},
  "category_weights": {"attack": 1.0, "defense": 1.0, "utility": 1.0, "special": 0.5},
  "notes": ""
}
```

## 5. Data Input Flow

### Primary: Manual Entry per Upgrade
- Dashboard shows all upgrades with editable level inputs
- User types current level for each upgrade
- htmx sends individual updates (debounced) — no full-page refresh
- Auto-save indicator shows "Saved" / "Unsaved changes"

### Future: Bulk Operations
- "Set all to 0" button for new profiles
- "Import from text" — paste tab-separated values
- Screenshot OCR — future feature, not V1

### New Profile Default
- All upgrade levels default to 0
- Available coins default to 0
- Category weights default to 1.0

## 6. Risks and Unknowns

1. **Level input ergonomics**: Editing 30+ level fields is tedious; need good tab-order and auto-advance
2. **Data rendering performance**: If there are 50+ upgrades with level tables, initial load could be slow
3. **htmx complexity**: Complex interactions may push htmx beyond its sweet spot
4. **Browser dependency**: User must open a browser; terminal-only users may prefer TUI
5. **No offline mode**: Flask server must be running; startup friction
6. **Number formatting**: Large coin values (1,000,000+) need readable formatting (commas, abbreviations)
7. **Mobile access**: Brief says non-goal, but user might try on phone — layout will break

## 7. Messages to Other Teammates

### To Architect
I agree with Flask + htmx recommendation. Additional needs:
- `templates/` directory for Jinja2
- `static/` directory for CSS and vendored htmx.js
- Consider adding a `Makefile` or `run.sh` for easy startup (`python app.py` or `flask run`)

### To Algorithm Engineer
I need the ranking output as `list[RankedUpgrade]` with:
- `rank`, `upgrade_id`, `upgrade_name`, `category_id`, `score`, `affordable`
- `breakdown.formula_description` as a pre-formatted string for display
- All numbers as actual numbers (not pre-formatted strings) so I can format them in templates

### To Data Engineer
I need per-upgrade metadata for display:
- `name`, `category_id`, `description` (short), `effect_unit`
- Category names and display orders
- I'll display upgrades in the order specified by `display_order`

### To Reliability Engineer
UI testability:
- Flask test client can test all routes
- htmx endpoints are just HTTP — testable without a browser
- Consider Playwright for end-to-end UI tests if time permits
- Every route should return proper HTTP status codes (404 for missing profiles, etc.)

## 8. Acceptance Tests

1. Dashboard renders all upgrades grouped by category in correct order
2. Level inputs are editable and persist via htmx without full page reload
3. Recommendation view shows #1 pick with complete breakdown and top 5 alternatives
4. Profile creation, selection, and deletion work correctly
5. Number formatting is readable (commas for thousands, proper decimal places)
