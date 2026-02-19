# Data Engineer Plan — Tower Upgrade Advisor

## 1. Data Extraction Strategy

### Priority 1: Browser Automation (Playwright)

**Approach:** Use Python Playwright to load the reference site, interact with the DOM, and extract rendered upgrade data.

**Steps:**
1. Install Playwright: `pip install playwright && playwright install chromium`
2. Navigate to `https://tower-workshop-calculator.netlify.app/`
3. Wait for JS rendering (wait for `.upgrade` or `.category` elements)
4. Extract upgrade structure using CSS selectors discovered from the site's CSS:
   - Categories: `.category` elements with `.attack`, `.defense`, `.utility` classes
   - Upgrades: `.upgrade` elements within each category
   - Values: `.upgrade-value`, `.cost`, `.level`, `.current`, `.target` elements
5. For each upgrade, iterate through levels to extract cost and effect data
6. Export to JSON

**Known CSS selectors from reference site:**
- `.categories`, `.category`, `.category-name`, `.category-upgrades`
- `.upgrade`, `.upgrade-section`, `.upgrade-list`, `.upgrade-value`, `.upgrade-wrapper`
- `.cost`, `.coins`, `.cash`, `.level`, `.current`, `.target`
- `.roi-section`, `.best-option`, `.resource-analysis`
- `.at-target`, `.maxed`
- `#overview`, `#analysis`

**Tooling:** Python 3.11+, Playwright, json
**Output:** `data/upgrades_raw.json` (raw extraction), processed to `data/upgrades.json`
**Risks:** Site structure may change; JS may require interaction to reveal all data; rate limiting

### Priority 2: JS Bundle Reverse-Engineering

**Approach:** Download `main.ef115c63.js` (7.2MB bundle), use regex/AST parsing to find embedded data structures.

**Steps:**
1. `curl -o bundle.js https://tower-workshop-calculator.netlify.app/static/js/main.ef115c63.js`
2. Search for string patterns: upgrade names, numeric arrays, object literals
3. Use `js-beautify` to deobfuscate
4. Extract data constants with regex or manual inspection
5. The bundle is 7.2MB — likely contains embedded data rather than fetching from an API

**Risks:** Heavily minified; data may be computed rather than static; fragile extraction

### Priority 3: Assisted Manual Import with Validation

**Approach:** Community-sourced data or manual entry, with strong automated validation.

**Steps:**
1. Create a template JSON with all known upgrade names and categories
2. User fills in cost/effect values per level from in-game observation
3. Run validation suite to catch errors
4. Cross-reference against reference site by spot-checking

**This is the fallback, not the preferred approach.**

### DISAGREEMENT: Start with assisted manual + validation

I disagree with the implied preference for scraping first. Here's why:
- Playwright extraction gives us ONE snapshot of the reference site, which itself may have errors
- The reference site may not expose per-level data in a scrapeable format (it may compute costs client-side from formulas)
- A well-validated manual/community dataset with formulas is MORE trustworthy than scraped HTML
- **Recommendation:** Start with the known upgrade list + cost formulas from game knowledge, validate exhaustively, and use Playwright as a verification tool rather than a primary source

However, I'll implement Playwright extraction as the first attempt per the brief's priority order.

## 2. Normalized Data Schema

```json
{
  "schema_version": "1.0.0",
  "game_version": "unknown",
  "extracted_at": "2025-01-01T00:00:00Z",
  "extraction_method": "playwright|manual|bundle",
  "categories": [
    {
      "id": "attack",
      "name": "Attack",
      "display_order": 1,
      "upgrades": [
        {
          "id": "attack_speed",
          "name": "Attack Speed",
          "category_id": "attack",
          "display_order": 1,
          "description": "Increases tower attack speed",
          "effect_unit": "attacks/sec",
          "effect_type": "multiplicative",
          "max_level": 100,
          "cost_formula": null,
          "effect_formula": null,
          "levels": [
            {
              "level": 1,
              "coin_cost": 100,
              "effect_value": 1.05,
              "cumulative_cost": 100,
              "cumulative_effect": 1.05
            }
          ]
        }
      ]
    }
  ]
}
```

### Key Design Decisions:
- **Nested structure**: Categories contain upgrades contain levels (matches UI grouping)
- **Both formulas and tables**: Store raw level data AND formula if discoverable (formulas allow extrapolation; tables are ground truth)
- **Cumulative fields**: Pre-compute cumulative cost and cumulative effect for quick lookups
- **Effect types**: `multiplicative` (1.05 = +5%), `additive` (flat +10), `special` (Death Defy = chance-based)
- **Schema version**: Required for data migration when game updates

## 3. Validation Rules

### Structural Validation
- [ ] All required fields present (JSON Schema validation)
- [ ] All field types correct (string, number, array)
- [ ] No null values in required fields
- [ ] `schema_version` is valid semver

### Completeness Validation
- [ ] Total number of upgrades matches expected count (document expected count in assumptions.md)
- [ ] Every upgrade has at least 1 level entry
- [ ] No gaps in level sequences (levels 1, 2, 3... not 1, 3, 5)
- [ ] Level sequences start at 1
- [ ] Max level matches the last level entry

### Numeric Integrity
- [ ] All `coin_cost` values are positive numbers (> 0)
- [ ] All `effect_value` values are numeric (no strings like "1.2M")
- [ ] No NaN or Infinity values
- [ ] No negative costs
- [ ] Costs are integers or float with at most 2 decimal places

### Monotonicity
- [ ] `coin_cost` is strictly increasing per upgrade (level N+1 costs more than level N)
- [ ] `cumulative_cost` is strictly increasing
- [ ] `effect_value` is non-decreasing per upgrade (with documented exceptions)
- [ ] `cumulative_effect` is non-decreasing

### Cross-Upgrade Consistency
- [ ] No duplicate upgrade IDs
- [ ] No duplicate upgrade names within a category
- [ ] Category IDs reference valid categories
- [ ] Display orders are unique within each category and globally

### Parsing Checks
- [ ] No string values where numbers expected (catch "1,234" or "1.2M" leaks)
- [ ] No whitespace in numeric fields
- [ ] No Unicode in numeric fields

## 4. Profile Data Schema

```json
{
  "profile_version": "1.0.0",
  "name": "My Build",
  "created_at": "2025-01-01T00:00:00Z",
  "modified_at": "2025-01-15T10:30:00Z",
  "available_coins": 0,
  "levels": {
    "attack_speed": 15,
    "damage": 20,
    "critical_chance": 5
  },
  "notes": "Focus on attack upgrades"
}
```

**Design decisions:**
- `levels` is a flat dict keyed by `upgrade_id` → `current_level`
- Missing keys default to level 0 (new upgrade added to game)
- `available_coins` stored so recommendations can filter by affordability
- Stored in `data/profiles/<slugified-name>.json`

## 5. Risks and Unknowns

1. **Reference site data format unknown**: We don't know if costs are stored as tables or computed from formulas in JS
2. **JS bundle too large**: 7.2MB minified bundle may be unparseable by simple tools
3. **Game version tracking**: No reliable way to detect game version from reference site
4. **Upgrade list completeness**: We may miss upgrades that require unlocking or are version-specific
5. **Numeric precision**: Floating-point costs could cause comparison issues
6. **Data staleness**: Game updates may change costs/effects; need a re-extraction workflow
7. **Cost formula discovery**: If costs follow a formula (e.g., `base * multiplier^level`), discovering it from data points is unreliable

## 6. Messages to Other Teammates

### To Architect
- I need `data/` directory to support both `upgrades.json` and `profiles/` subdirectory
- Data validation should be runnable as both a standalone script and pytest tests
- Consider adding `data/schema.json` for JSON Schema validation
- I recommend using Pydantic v2 for runtime model validation

### To Algorithm Engineer
- Each upgrade level provides: `upgrade_id`, `level`, `coin_cost`, `effect_value`, `effect_unit`, `effect_type`
- `effect_type` is one of: `multiplicative`, `additive`, `special`
- The scoring engine should handle all three: multiply-based marginal benefit, flat-add marginal benefit, and special-case scoring
- I'll provide `cumulative_cost` and `cumulative_effect` pre-computed for convenience

### To Reliability Engineer
- I need these validation tests automated in pytest
- Data validation should run on every test suite execution
- Need a `tests/fixtures/test_upgrades.json` with a small but valid subset
- Validation errors should produce clear, actionable messages (not just "validation failed")

## 7. Acceptance Tests

1. `data/upgrades.json` exists and passes all validation rules
2. `data/schema.json` exists and `upgrades.json` validates against it
3. The extraction script (`scripts/extract_data.py`) can be run and produces valid output
4. At least one profile can be created, saved, loaded, and deleted
5. All numeric fields are verified as actual numbers (not formatted strings)
