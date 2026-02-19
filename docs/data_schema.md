# Data Schema — Tower Upgrade Advisor

## Upgrade Data Schema (`data/upgrades.json`)

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

## Field Definitions

### Top-Level
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string (semver) | Yes | Schema version for migration |
| `game_version` | string | Yes | Game version data was extracted from |
| `extracted_at` | string (ISO 8601) | Yes | When data was extracted |
| `extraction_method` | string | Yes | How data was obtained |
| `categories` | array[Category] | Yes | List of upgrade categories |

### Category
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (snake_case) |
| `name` | string | Yes | Display name |
| `display_order` | integer | Yes | Sort order (1-based) |
| `upgrades` | array[Upgrade] | Yes | Upgrades in this category |

### Upgrade
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (snake_case) |
| `name` | string | Yes | Display name |
| `category_id` | string | Yes | Parent category reference |
| `display_order` | integer | Yes | Sort order within category |
| `description` | string | Yes | Short description of the upgrade |
| `effect_unit` | string | Yes | Unit of the effect (e.g., "attacks/sec", "HP", "coins/kill") |
| `effect_type` | enum | Yes | One of: `multiplicative`, `additive`, `special` |
| `max_level` | integer | Yes | Maximum upgrade level |
| `levels` | array[Level] | Yes | Per-level data |

### Level
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `level` | integer | Yes | Level number (1-based) |
| `coin_cost` | number | Yes | Cost in coins to buy THIS level |
| `effect_value` | number | Yes | Effect gained from THIS level (delta) |
| `cumulative_cost` | number | Yes | Total coins spent to reach this level |
| `cumulative_effect` | number | Yes | Total effect at this level |

## Effect Types

| Type | Meaning | Base Value (level 0) | Marginal Benefit |
|------|---------|---------------------|-----------------|
| `multiplicative` | Effect is a multiplier (e.g., 1.05 = +5%) | 1.0 | `next_cumulative - current_cumulative` |
| `additive` | Effect is a flat addition (e.g., +10 damage) | 0 | `next_cumulative - current_cumulative` |
| `special` | Non-standard effect (e.g., chance-based) | 0 | Manually weighted |

## Profile Schema (`data/profiles/<name>.json`)

```json
{
  "profile_version": "1.0.0",
  "name": "My Main Build",
  "created_at": "2025-01-01T00:00:00Z",
  "modified_at": "2025-01-15T10:30:00Z",
  "available_coins": 15000,
  "levels": {
    "attack_speed": 15,
    "damage": 20,
    "critical_chance": 5,
    "health": 18
  },
  "category_weights": {
    "attack": 1.0,
    "defense": 1.0,
    "utility": 1.0,
    "special": 0.5
  },
  "notes": "Focus on attack upgrades"
}
```

### Profile Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `profile_version` | string | Yes | Profile schema version |
| `name` | string | Yes | Profile display name |
| `created_at` | string (ISO 8601) | Yes | Creation timestamp |
| `modified_at` | string (ISO 8601) | Yes | Last modification timestamp |
| `available_coins` | number | Yes | Current available coins |
| `levels` | object | Yes | `{upgrade_id: current_level}` map |
| `category_weights` | object | Yes | `{category_id: weight}` map |
| `notes` | string | No | User notes |

### Profile Behavior
- Missing `upgrade_id` in `levels` defaults to level 0
- Unknown `upgrade_id` in `levels` (after game update removes an upgrade) is ignored with a warning
- `available_coins` of 0 means "don't filter by affordability"

## Validation Rules Summary

1. All required fields present with correct types
2. No gaps in level sequences (1, 2, 3, ... max_level)
3. All `coin_cost` > 0
4. All numeric fields are actual numbers (no strings)
5. `coin_cost` is strictly monotonically increasing per upgrade
6. `cumulative_cost` is strictly monotonically increasing
7. `effect_value` is non-decreasing (with documented exceptions)
8. No duplicate `id` values across all upgrades
9. All `category_id` references match a defined category
10. `display_order` is unique within each category
