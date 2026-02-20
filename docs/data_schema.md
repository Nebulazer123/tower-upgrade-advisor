# Data Schema — Tower Upgrade Advisor

## Upgrade Data Schema (`data/upgrades.json`)

```json
{
  "version": "2026-02-19",
  "game_version": "current",
  "source": "game-vault.net/wiki/Workshop",
  "upgrades": [
    {
      "id": "attack_speed",
      "name": "Attack Speed",
      "category": "offense",
      "effect_unit": "attacks/sec",
      "effect_type": "additive",
      "base_value": 1.0,
      "max_level": 99,
      "display_order": 1,
      "levels": [
        {
          "level": 1,
          "coin_cost": 30,
          "cumulative_effect": 1.05,
          "effect_delta": 0.05
        }
      ]
    }
  ]
}
```

## Field Definitions

### Top-Level (`UpgradeDatabase`)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Data version or extraction date |
| `game_version` | string | Yes | Game version this data represents |
| `source` | string | Yes | Where the data came from (e.g., URL) |
| `upgrades` | array[Upgrade] | Yes | Flat list of all upgrade definitions |

### Upgrade (`UpgradeDefinition`)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (snake_case) |
| `name` | string | Yes | Display name |
| `category` | enum | Yes | One of: `offense`, `defense`, `economy`, `utility` |
| `effect_unit` | string | Yes | Unit of the effect (e.g., "attacks/sec", "HP", "coins/kill") |
| `effect_type` | enum | Yes | One of: `multiplicative`, `additive` |
| `base_value` | float | Yes | Value at level 0 (1.0 for multiplicative, 0 for additive) |
| `max_level` | integer | Yes | Maximum upgrade level |
| `display_order` | integer | Yes | Sort order within category (0-based) |
| `levels` | array[Level] | Yes | Per-level data, length must equal `max_level` |

### Level (`UpgradeLevel`)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `level` | integer | Yes | Level number (1-based, sequential) |
| `coin_cost` | integer | Yes | Cost in coins to buy THIS level (strictly increasing) |
| `cumulative_effect` | float | Yes | Total effect at this level |
| `effect_delta` | float | Yes | Marginal effect gained from the previous level |

## Effect Types

| Type | Meaning | Base Value (level 0) | Marginal Benefit |
|------|---------|---------------------|-----------------|
| `multiplicative` | Effect is a multiplier (e.g., 1.05 = +5%) | 1.0 | `next_cumulative - current_cumulative` |
| `additive` | Effect is a flat addition (e.g., +10 damage) | 0 | `next_cumulative - current_cumulative` |

## Profile Schema (`data/profiles/<name>.json`)

```json
{
  "id": "a1b2c3d4-...",
  "name": "My Main Build",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "available_coins": 15000,
  "levels": {
    "attack_speed": 15,
    "damage": 20,
    "critical_chance": 5,
    "health": 18
  },
  "weights": {
    "economy": 1.0,
    "offense": 1.0,
    "defense": 1.0,
    "utility": 1.0
  },
  "tags": ["push build"]
}
```

### Profile Fields (`Profile`)
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | string | Yes | — | Unique identifier (UUID) |
| `name` | string | Yes | — | Profile display name |
| `created_at` | datetime (ISO 8601) | Yes | — | Creation timestamp |
| `updated_at` | datetime (ISO 8601) | Yes | — | Last modification timestamp |
| `available_coins` | integer | No | `0` | Coins available to spend (0 = no affordability filter) |
| `levels` | object | No | `{}` | `{upgrade_id: current_level}` map |
| `weights` | ScoringWeights | No | all 1.0 | User's scoring slider values |
| `tags` | array[string] | No | `[]` | Free-form build tags (e.g., "farm build", "push build") |

### Scoring Weights (`ScoringWeights`)
| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| `economy` | float | 0.0–2.0 | 1.0 | Economy category weight |
| `offense` | float | 0.0–2.0 | 1.0 | Offense category weight |
| `defense` | float | 0.0–2.0 | 1.0 | Defense category weight |
| `utility` | float | 0.0–2.0 | 1.0 | Utility category weight |

### Profile Behavior
- Missing `upgrade_id` in `levels` defaults to level 0
- Unknown `upgrade_id` in `levels` (after game update removes an upgrade) is ignored with a warning
- `available_coins` of 0 means "don't filter by affordability"
- Unknown categories in `ScoringWeights.for_category()` fall back to 1.0 (never silently zeroed)

## Validation Rules Summary

1. All required fields present with correct types
2. No gaps in level sequences (1, 2, 3, ..., max_level)
3. All `coin_cost` > 0
4. All numeric fields are finite (no NaN or Inf)
5. `coin_cost` is strictly monotonically increasing per upgrade
6. `cumulative_effect` non-decreasing is a **warning**, not a hard error (see Decision 8)
7. `effect_delta` consistency checked against cumulative_effect differences
8. No duplicate `id` values across all upgrades
9. `display_order` is unique within each category (warning if duplicated)
10. Level list length must equal `max_level`
