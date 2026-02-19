# Algorithm Engineer Plan — Tower Upgrade Advisor

## 1. Scoring Interface

```python
from dataclasses import dataclass, field
from typing import Protocol

@dataclass
class UpgradeLevel:
    level: int
    coin_cost: float
    effect_value: float
    cumulative_cost: float
    cumulative_effect: float

@dataclass
class UpgradeInfo:
    id: str
    name: str
    category_id: str
    effect_unit: str
    effect_type: str          # "multiplicative" | "additive" | "special"
    max_level: int
    levels: list[UpgradeLevel]

@dataclass
class UpgradeData:
    upgrades: dict[str, UpgradeInfo]   # keyed by upgrade_id
    categories: dict[str, str]          # category_id -> category_name

@dataclass
class Profile:
    name: str
    levels: dict[str, int]             # upgrade_id -> current_level
    available_coins: float

@dataclass
class ScoreBreakdown:
    marginal_benefit: float
    coin_cost: float
    raw_score: float
    normalized_score: float
    effect_unit: str
    current_level: int
    next_level: int
    current_effect: float
    next_effect: float
    formula_description: str

@dataclass
class RankedUpgrade:
    rank: int
    upgrade_id: str
    upgrade_name: str
    category_id: str
    score: float
    breakdown: ScoreBreakdown
    affordable: bool

class ScoringEngine(Protocol):
    def score_upgrade(
        self,
        upgrade_id: str,
        profile: Profile,
        data: UpgradeData,
    ) -> ScoreBreakdown: ...

    def rank_upgrades(
        self,
        profile: Profile,
        data: UpgradeData,
    ) -> list[RankedUpgrade]: ...

    def explain(self) -> str:
        """Return a human-readable description of the scoring method."""
        ...
```

## 2. Initial Scoring Algorithm: Marginal Benefit per Coin

### V1 Formula

```
score(upgrade, current_level) = marginal_benefit / coin_cost_next_level
```

Where:
- `coin_cost_next_level = levels[current_level + 1].coin_cost`
- `marginal_benefit = effect_at(current_level + 1) - effect_at(current_level)`

### Defining "Marginal Benefit" by Effect Type

| Effect Type | Marginal Benefit | Example |
|-------------|-----------------|---------|
| **Multiplicative** | `next_effect - current_effect` (the delta in multiplier) | Attack Speed: 1.20 → 1.25 = 0.05 benefit |
| **Additive** | `next_effect - current_effect` (flat increase) | Damage: +100 → +110 = 10 benefit |
| **Special** | Manually assigned weight or treated as additive delta | Death Defy: level-based discrete benefit |

### DISAGREEMENT: Marginal Benefit per Coin is the right starting metric

Some might argue for other metrics:
- **Total value per coin** (cumulative effect / cumulative cost): Penalizes high-level upgrades unfairly
- **Percentage improvement**: `(next - current) / current` — better if effects are multiplicative, but breaks at level 0
- **Expected value**: Requires game simulation, too complex for V1

**Marginal benefit per coin is correct for V1** because:
1. It answers the exact question: "What do I get for my next coin?"
2. It's simple, transparent, and explainable
3. It naturally handles diminishing returns (marginal benefit decreases as cost increases)
4. It's the standard efficiency metric in economics (marginal utility per dollar)

## 3. Normalization Challenge

### The Core Problem
Upgrades affect different dimensions:
- Attack Speed (attacks/sec) vs Damage (flat) vs Health (HP) vs Coins/Kill (economy)
- How to compare "+0.05 attacks/sec" vs "+10 damage" vs "+50 HP"?

### Approach A: Category-Separate Rankings
Rank upgrades only within their category:
- "Best attack upgrade: Damage (level 20→21, score 0.0045)"
- "Best defense upgrade: Health (level 15→16, score 0.0032)"
- "Best economy upgrade: Coins/Kill (level 10→11, score 0.0028)"

**Pros:** No normalization needed; each comparison is apples-to-apples
**Cons:** Doesn't answer "which single upgrade is best?"

### Approach B: User-Configurable Category Weights
Let users assign weights: Attack=1.0, Defense=0.8, Economy=1.2.
`final_score = raw_score * category_weight`

**Pros:** Respects player strategy; simple to implement
**Cons:** Users may not know good weights; adds config complexity

### Approach C: Percentage Improvement Normalization
`normalized_score = (next_effect - current_effect) / current_effect / coin_cost`
Treats all upgrades as "% improvement per coin."

**Pros:** Unit-agnostic
**Cons:** Breaks at level 0; treats 5% damage increase same as 5% health increase (questionable)

### V1 Recommendation: Approach B with sensible defaults

**Rationale:**
1. Category-separate rankings (A) don't answer the core question
2. Percentage normalization (C) is fragile at low levels
3. Weights (B) let the user control strategy while providing defaults
4. Default weights: `{attack: 1.0, defense: 1.0, utility: 1.0, special: 0.5}`
5. UI shows both: category-best AND overall-best-with-weights

The UI displays: "#1 Overall: Damage (score 4.5)" AND "Best per category" table.

## 4. Transparency Requirements

Every recommendation must display:

```
═══════════════════════════════════════
 #1 RECOMMENDED: Damage (level 20 → 21)
═══════════════════════════════════════
 Cost:             12,500 coins
 Effect:           +10 damage (350 → 360)
 Marginal Benefit: 10
 Score:            10 / 12,500 = 0.0008
 Category Weight:  1.0
 Final Score:      0.0008
 Affordable:       YES (you have 15,000 coins)
───────────────────────────────────────
 Method: marginal_benefit_per_coin v1
 Formula: (effect[next] - effect[current]) / cost[next] * weight
═══════════════════════════════════════

Top 5 Alternatives:
 #2  Attack Speed  (23→24)  score: 0.0007  cost: 14,000
 #3  Health        (18→19)  score: 0.0006  cost: 11,000
 #4  Crit Chance   (10→11)  score: 0.0005  cost:  8,500
 #5  Coins/Kill    (12→13)  score: 0.0004  cost:  9,200
```

## 5. Extensibility

The `ScoringEngine` Protocol allows swapping scoring methods:

```python
class MarginalBenefitPerCoin:
    """V1: Simple efficiency metric."""

class WeightedMarginalBenefit:
    """V1.1: Category weights applied."""

class BudgetOptimizer:
    """V2: Multi-step planning with knapsack/greedy."""

class CalibratedScoring:
    """V3: Weights learned from gameplay data."""
```

Each implements the same Protocol. The app injects the active engine. Users could eventually switch engines in settings.

### Future Extension Points:
- `rank_upgrades` returns `list[RankedUpgrade]` — can return top-N or all
- `ScoreBreakdown.formula_description` is human-readable; future engines describe their own logic
- Historical tracking: store `(timestamp, profile_snapshot, recommendation, chosen_upgrade)` to evaluate recommendation quality

## 6. Edge Cases

| Case | Handling |
|------|----------|
| **Tie scores** | Break ties by: 1) lower cost first, 2) alphabetical upgrade name |
| **Best upgrade unaffordable** | Show it as #1 with `affordable: False`; also highlight top affordable option |
| **Upgrade at max level** | Exclude from ranking; show as "MAXED" in UI |
| **Diminishing returns** | Handled naturally — marginal benefit decreases while cost increases, so score drops |
| **All upgrades maxed** | Return empty ranking with message "All upgrades maxed" |
| **Level 0 (not purchased)** | `marginal_benefit = effect[1] - 0` (base effect at level 0 is 0 for additive, 1.0 for multiplicative) |
| **Division by zero** | Impossible if costs are validated as > 0; assert in scoring |
| **Negative benefit** | Should not occur with valid data; log warning and exclude |

## 7. Risks and Unknowns

1. **Category weights are arbitrary**: Default weights may mislead players with specific strategies
2. **Cross-category comparison is fundamentally unsound**: 1 point of damage ≠ 1 point of health in actual gameplay
3. **Effect type handling**: Multiplicative vs additive benefit comparison is not straightforward
4. **Missing game context**: Tool doesn't know player's tower setup, enemy scaling, wave difficulty
5. **Upgrade synergies ignored**: Some upgrades are more valuable together (crit chance + crit factor)
6. **Data precision**: Small floating-point differences could flip rankings
7. **Scoring feels "wrong"**: Users may disagree with recommendations; need easy weight tuning

## 8. Messages to Other Teammates

### To Data Engineer
I need per-upgrade per-level data with these exact fields:
- `upgrade_id`, `level`, `coin_cost`, `effect_value`, `effect_type`, `effect_unit`
- `cumulative_cost`, `cumulative_effect` (pre-computed)
- `max_level` per upgrade
- Level 0 should have `effect_value` = 0 (additive) or 1.0 (multiplicative)

### To Architect
The scoring engine should live in `src/scoring.py`. It must:
- Import types from `src/models.py` (Profile, UpgradeData, etc.)
- Be a class implementing the `ScoringEngine` Protocol
- Be injectable into the Flask app (pass as constructor arg or app config)
- Have no side effects (pure function of inputs)

### To UI Engineer
The ranking output provides:
- `list[RankedUpgrade]` with `rank`, `upgrade_id`, `upgrade_name`, `category_id`, `score`, `affordable`
- Each has `ScoreBreakdown` with all raw numbers for display
- The UI should show: the #1 pick prominently, top 5 alternatives in a table, and per-category bests
- Also expose `engine.explain()` for a "How does scoring work?" help panel

### To Reliability Engineer
Critical tests for scoring:
- **Known-answer test**: Given specific profile + data, ranking must be exactly X
- **Determinism test**: Same inputs always produce same outputs
- **Monotonicity test**: Lowering a cost should increase that upgrade's score
- **Max-level exclusion**: Maxed upgrades must not appear in rankings
- **Empty profile test**: All level-0 profile should produce valid rankings
- **All-maxed test**: Should return empty ranking gracefully

## 9. Acceptance Tests

1. `ScoringEngine.rank_upgrades()` returns a sorted list with the highest-score upgrade first
2. Every `RankedUpgrade` has a complete `ScoreBreakdown` with no None/null fields
3. Given a known test profile and test data, the recommendation matches the expected answer
4. The scoring engine is deterministic: 1000 runs produce identical results
5. Category weights can be changed and produce different rankings appropriately
