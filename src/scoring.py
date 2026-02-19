"""Scoring engines for the Tower Upgrade Advisor.

Three modes (per approved plan):

1. **PerCategoryEngine**  -- best next upgrade within each category independently
   (no cross-category weights).
2. **BalancedEngine**     -- user-adjustable Economy / Offense / Defense sliders
   for global cross-category ranking.
3. **ReferenceEngine**    -- stub for replicated reference-tool logic (not yet
   implemented).

All engines conform to the :class:`ScoringEngine` protocol and are fully
deterministic: identical inputs always produce identical outputs.
"""

from __future__ import annotations

from typing import Protocol

from src.models import (
    Profile,
    RankedUpgrade,
    ScoringWeights,
    UpgradeDatabase,
    UpgradeDefinition,
)

__all__ = [
    "ScoringEngine",
    "compute_marginal_score",
    "PerCategoryEngine",
    "BalancedEngine",
    "ReferenceEngine",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Decimal places used when rounding scores for stable floating-point comparison.
_SCORE_PRECISION: int = 12

# Decimal places shown when formatting a score value for human display.
_DISPLAY_DECIMALS: int = 6


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------

class ScoringEngine(Protocol):
    """Common interface that every scoring engine must satisfy."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    def rank(
        self, upgrades: UpgradeDatabase, profile: Profile,
    ) -> list[RankedUpgrade]: ...

    def explain(self, ranked: RankedUpgrade) -> str: ...


# ---------------------------------------------------------------------------
# Pure helper: compute_marginal_score
# ---------------------------------------------------------------------------

def compute_marginal_score(
    upgrade: UpgradeDefinition, current_level: int,
) -> tuple[float, int, float, float, float]:
    """Compute the marginal-benefit-per-coin score for the next level.

    Parameters
    ----------
    upgrade:
        The upgrade definition containing per-level data.
    current_level:
        The player's current level for this upgrade (0 = not yet purchased).

    Returns
    -------
    ``(score, coin_cost, current_effect, next_effect, marginal_benefit)``

    *score* equals ``marginal_benefit / coin_cost``.

    Returns ``(0.0, 0, current_effect, current_effect, 0.0)`` when
    *current_level* ``>=`` *upgrade.max_level* (upgrade already maxed).
    """
    # --- maxed check (do this first to avoid index errors when
    #     current_level > max_level due to a data migration) ---------------
    if current_level >= upgrade.max_level:
        eff = upgrade.levels[-1].cumulative_effect if upgrade.levels else upgrade.base_value
        return (0.0, 0, eff, eff, 0.0)

    # --- current cumulative effect ----------------------------------------
    if current_level <= 0:
        current_effect: float = upgrade.base_value
    else:
        current_effect = upgrade.levels[current_level - 1].cumulative_effect

    # --- next-level data --------------------------------------------------
    # ``upgrade.levels`` is 0-indexed: index *i* holds data for level *i + 1*.
    # So the data for ``current_level + 1`` lives at index ``current_level``.
    next_level_data = upgrade.levels[current_level]
    coin_cost: int = next_level_data.coin_cost
    next_effect: float = next_level_data.cumulative_effect
    marginal_benefit: float = next_effect - current_effect

    # Guard against zero / negative cost (should not happen with validated data).
    if coin_cost <= 0:
        return (0.0, coin_cost, current_effect, next_effect, marginal_benefit)

    score: float = marginal_benefit / coin_cost
    return (score, coin_cost, current_effect, next_effect, marginal_benefit)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sort_key(r: RankedUpgrade) -> tuple[float, int, str]:
    """Deterministic sort key: score **descending**, cost ascending, name ascending."""
    return (-round(r.score, _SCORE_PRECISION), r.coin_cost, r.upgrade_name)


def _build_ranked(
    upgrade: UpgradeDefinition,
    profile: Profile,
    score: float,
    coin_cost: int,
    current_effect: float,
    next_effect: float,
    marginal_benefit: float,
    method: str,
) -> RankedUpgrade:
    """Construct a :class:`RankedUpgrade` from computed scoring values."""
    current_level = profile.get_level(upgrade.id)
    return RankedUpgrade(
        upgrade_id=upgrade.id,
        upgrade_name=upgrade.name,
        category=upgrade.category,
        current_level=current_level,
        next_level=current_level + 1,
        coin_cost=coin_cost,
        current_effect=current_effect,
        next_effect=next_effect,
        marginal_benefit=marginal_benefit,
        score=round(score, _SCORE_PRECISION),
        affordable=profile.available_coins >= coin_cost,
        scoring_method=method,
    )


def _fmt_score(value: float) -> str:
    """Format a score value for human-readable display."""
    return f"{value:.{_DISPLAY_DECIMALS}f}"


# ---------------------------------------------------------------------------
# Engine 1: Per-Category Best
# ---------------------------------------------------------------------------

class PerCategoryEngine:
    """Returns the single best next upgrade within each category.

    No cross-category comparison -- one result per category.  Upgrades at
    max level are excluded.  Within each category, upgrades are scored by
    ``marginal_benefit / cost``.

    Tie-break: lower cost first, then alphabetical by upgrade name.
    """

    @property
    def name(self) -> str:
        return "per_category_best"

    @property
    def version(self) -> str:
        return "1.0"

    # ----- ranking -----------------------------------------------------------

    def rank(
        self, upgrades: UpgradeDatabase, profile: Profile,
    ) -> list[RankedUpgrade]:
        """Return the best upgrade for each category that has available upgrades.

        Categories are discovered from the data (not hard-coded).  The
        returned list contains at most one :class:`RankedUpgrade` per
        category, sorted by score descending with the standard tie-break.
        """
        best: dict[str, RankedUpgrade] = {}
        best_key: dict[str, tuple[float, int, str]] = {}

        for u in upgrades.upgrades:
            current_level = profile.get_level(u.id)
            if current_level >= u.max_level:
                continue

            score, cost, cur_eff, nxt_eff, mb = compute_marginal_score(
                u, current_level,
            )
            if score <= 0:
                continue

            candidate = _build_ranked(
                u, profile, score, cost, cur_eff, nxt_eff, mb, self.name,
            )
            key = _sort_key(candidate)
            cat = u.category

            if cat not in best or key < best_key[cat]:
                best[cat] = candidate
                best_key[cat] = key

        result = sorted(best.values(), key=_sort_key)
        return result

    # ----- explanation -------------------------------------------------------

    def explain(self, ranked: RankedUpgrade) -> str:
        """Return a human-readable breakdown for a single ranked upgrade.

        Format::

            Attack Speed (level 5 \u2192 6)
              Cost: 1,234 coins
              Effect: 1.5 \u2192 1.6
              Marginal Benefit: 0.1
              Score: 0.1 / 1234 = 0.000081
              Mode: per_category_best
        """
        lines = [
            f"{ranked.upgrade_name} (level {ranked.current_level}"
            f" \u2192 {ranked.next_level})",
            f"  Cost: {ranked.coin_cost:,} coins",
            f"  Effect: {ranked.current_effect} \u2192 {ranked.next_effect}",
            f"  Marginal Benefit: {ranked.marginal_benefit}",
            (
                f"  Score: {ranked.marginal_benefit} / {ranked.coin_cost}"
                f" = {_fmt_score(ranked.score)}"
            ),
            f"  Mode: {self.name}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Engine 2: Balanced (user-adjustable sliders)
# ---------------------------------------------------------------------------

class BalancedEngine:
    """Ranks **all** non-maxed upgrades globally using category weights.

    ``score = marginal_benefit / cost * weight_for_category``

    Weights are provided via a :class:`ScoringWeights` instance whose
    :meth:`~ScoringWeights.for_category` method maps each upgrade category
    to the appropriate slider value (economy, offense, or defense).

    Slider defaults are 1.0 (equal weight).  Upgrades at max level are
    excluded.

    Tie-break: lower cost first, then alphabetical by upgrade name.
    """

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self._weights: ScoringWeights = weights or ScoringWeights()

    @property
    def name(self) -> str:
        return "balanced"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def weights(self) -> ScoringWeights:
        """The category weights used for scoring."""
        return self._weights

    # ----- ranking -----------------------------------------------------------

    def rank(
        self, upgrades: UpgradeDatabase, profile: Profile,
    ) -> list[RankedUpgrade]:
        """Return all non-maxed upgrades ranked globally by weighted score."""
        results: list[RankedUpgrade] = []

        for u in upgrades.upgrades:
            current_level = profile.get_level(u.id)
            if current_level >= u.max_level:
                continue

            base_score, cost, cur_eff, nxt_eff, mb = compute_marginal_score(
                u, current_level,
            )
            if base_score <= 0:
                continue

            weight: float = self._weights.for_category(u.category)
            weighted_score: float = base_score * weight

            results.append(
                _build_ranked(
                    u, profile, weighted_score, cost, cur_eff, nxt_eff, mb,
                    self.name,
                ),
            )

        results.sort(key=_sort_key)
        return results

    # ----- explanation -------------------------------------------------------

    def explain(self, ranked: RankedUpgrade) -> str:
        """Return a human-readable breakdown including the applied weight.

        Format::

            Attack Speed (level 5 \u2192 6)
              Cost: 1,234 coins
              Effect: 1.5 \u2192 1.6
              Marginal Benefit: 0.1
              Score: 0.1 / 1234 * 1.2 = 0.000097
              Mode: balanced (Economy=1.0, Offense=1.2, Defense=0.8)
        """
        w = self._weights
        weight: float = w.for_category(ranked.category)
        lines = [
            f"{ranked.upgrade_name} (level {ranked.current_level}"
            f" \u2192 {ranked.next_level})",
            f"  Cost: {ranked.coin_cost:,} coins",
            f"  Effect: {ranked.current_effect} \u2192 {ranked.next_effect}",
            f"  Marginal Benefit: {ranked.marginal_benefit}",
            (
                f"  Score: {ranked.marginal_benefit} / {ranked.coin_cost}"
                f" * {weight} = {_fmt_score(ranked.score)}"
            ),
            (
                f"  Mode: {self.name}"
                f" (Economy={w.economy}, Offense={w.offense},"
                f" Defense={w.defense})"
            ),
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Engine 3: Reference (stub -- not yet implemented)
# ---------------------------------------------------------------------------

class ReferenceEngine:
    """Placeholder for replicated reference-tool scoring logic.

    This engine is **not implemented**.  Calling :meth:`rank` or
    :meth:`explain` raises :exc:`NotImplementedError` with a message
    directing users to the available engines.
    """

    @property
    def name(self) -> str:
        return "reference"

    @property
    def version(self) -> str:
        return "0.0"

    def rank(
        self, upgrades: UpgradeDatabase, profile: Profile,
    ) -> list[RankedUpgrade]:
        raise NotImplementedError(
            "Reference scoring engine is not yet implemented. "
            "The reference tool's scoring logic has not been reverse-engineered. "
            "Use PerCategoryEngine or BalancedEngine instead."
        )

    def explain(self, ranked: RankedUpgrade) -> str:
        raise NotImplementedError(
            "Reference scoring engine is not yet implemented. "
            "Use PerCategoryEngine or BalancedEngine instead."
        )
