# Scoring Definition — Tower Upgrade Advisor

## APPROVED MODIFICATION (Phase 1 Approval)

No hardcoded category weights as default "truth." Two scoring modes:
1. **Reference-mode**: Replicate the reference tool's logic where a public source is available.
2. **Balanced-mode**: User-adjustable weights via 3 sliders (Attack/Defense/Utility)

If reference logic is NOT discovered, the UI shows:
- Best next upgrade **per category** (no cross-category comparison needed)
- Balanced recommendation **only** with user-declared weights (visible sliders)

---

## Scoring Protocol (Interface)

All scoring engines implement `ScoringEngine`:

```python
class ScoringEngine(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def version(self) -> str: ...
    def rank(self, upgrades: UpgradeDatabase, profile: Profile) -> list[RankedUpgrade]: ...
    def explain(self, ranked: RankedUpgrade) -> str: ...
```

### Mode 1: Per-Category Best (Always Available)

For each category independently, find the best next upgrade:
```
score(upgrade) = marginal_benefit(upgrade) / cost(upgrade)
```

No cross-category weights needed. Returns one recommendation per category.

### Mode 2: Balanced Mode (User-Adjustable Sliders)

Three sliders control relative priority:
- **Attack** (0.0 - 2.0, default 1.0): Damage, Attack Speed, Critical Chance, etc.
- **Defense** (0.0 - 2.0, default 1.0): Health, Health Regen, Defense %, etc.
- **Utility** (0.0 - 2.0, default 1.0): Cash, coins, recovery packages, level skip, etc.

Slider defaults are 1.0 (equal priority) and are **always visible** so the user knows what weights produced the recommendation.

```
score(upgrade) = marginal_benefit(upgrade) / cost(upgrade) * slider_weight(category)
```

### Mode 3: Reference Mode

Implemented as `ReferenceEngine`.

- Attack upgrades are ranked by DPS increase per coin, ported from the public source at https://github.com/jacoelt/tower-calculator.
- Defense and utility upgrades fall back to marginal benefit per coin because the public attack-DPS model does not provide equivalent cross-category simulation.
- The recommendation page shows this as a "Reference Check" next to the weighted balanced controls.
- Lab multipliers are loaded from `data/lab_research.json` and applied to the attack stats supported by the public source model.

Reference assumptions from the public source:

- DPS is calculated for an optimal number of valid targets.
- Bounce Shot Range is assumed high enough for all bounces.
- Multishot is assumed to fire the maximum number of shots.
- Rapid Fire can only trigger from normal bullets.
- Damage per meter is ignored by design.
- Rapid Fire duration is fixed at 1 second.

### Core Formulas

For any upgrade:
- `current_level = profile.levels[upgrade_id]` (default: 0)
- `next_level = current_level + 1`
- `cost = upgrades[upgrade_id].levels[next_level].coin_cost`
- `current_effect = upgrades[upgrade_id].levels[current_level].cumulative_effect` (or base value if level 0)
- `next_effect = upgrades[upgrade_id].levels[next_level].cumulative_effect`
- `marginal_benefit = next_effect - current_effect`
- For lower-is-better upgrades (`shockwave_frequency`, `wall_rebuild`), `marginal_benefit = current_effect - next_effect`

### Base Values (Level 0)
| Effect Type | Base Value |
|-------------|-----------|
| Multiplicative | 1.0 |
| Additive | 0 |

## Ranking Process

1. **Filter:** Remove upgrades at max level
2. **Score:** Calculate score for each remaining upgrade
3. **Sort:** Descending by score
4. **Tie-break:** Lower cost first, then alphabetical by upgrade name
5. **Annotate:** Mark each as `affordable` based on `profile.available_coins >= cost`
6. **Return:** Full ranked list as `list[RankedUpgrade]`

## Transparency Output

Every recommendation includes:

```
Recommendation #1: {upgrade_name} (level {current} → {next})
  Cost:             {coin_cost:,} coins
  Effect:           {current_effect} → {next_effect} ({effect_unit})
  Marginal Benefit: {marginal_benefit}
  Mode:             {per_category | balanced | reference}
  Weights:          Attack={a} Defense={d} Utility={u}  (shown only in balanced mode)
  Score:            {formula_used} = {score}
  Affordable:       {yes/no} (you have {available_coins:,} coins)
```

## Known Limitations

1. **Cross-category comparison is inherently approximate.** Balanced mode makes the weights transparent and user-controlled, not hidden.
2. **No synergy modeling.** Critical Chance and Critical Factor are more valuable together than separately. V1 does not account for synergies.
3. **No game-state awareness.** Recommendations are based purely on upgrade efficiency.
4. **Assumes linear benefit.** Each point of effect is treated equally.

## Future Scoring Methods

| Method | Description | Complexity |
|--------|-------------|-----------|
| `per_category_best` | Best in each category (no weights) | V1 |
| `balanced_marginal_per_coin` | Weighted by user sliders | V1 |
| `reference_mode` | Replicate reference tool (if discovered) | V1 (if feasible) |
| `percentage_improvement` | `(delta / current) / cost * weight` | Simple |
| `budget_optimizer` | Greedy: best N upgrades within budget | Medium |
| `synergy_aware` | crit chance x crit factor interactions | Medium |

All methods implement the `ScoringEngine` Protocol and are swappable.
