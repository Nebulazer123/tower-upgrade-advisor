"""Scoring engines for the Tower Upgrade Advisor.

Three modes:

1. **PerCategoryEngine**  -- best next upgrade within each category independently
   (no cross-category weights).
2. **BalancedEngine**     -- user-adjustable Attack / Defense / Utility sliders
   for global cross-category ranking.
3. **ReferenceEngine**    -- replicates the reference calculator's DPS-based
   efficiency ranking for attack upgrades, with marginal-benefit fallback
   for defense/utility.

All engines conform to the :class:`ScoringEngine` protocol and are fully
deterministic: identical inputs always produce identical outputs.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from src.models import (
    LabResearchDatabase,
    Profile,
    RankedUpgrade,
    ScoringWeights,
    UpgradeDatabase,
    UpgradeDefinition,
)

__all__ = [
    "ScoringEngine",
    "compute_marginal_score",
    "compute_dps",
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
        self,
        upgrades: UpgradeDatabase,
        profile: Profile,
    ) -> list[RankedUpgrade]: ...

    def explain(self, ranked: RankedUpgrade) -> str: ...


# ---------------------------------------------------------------------------
# Pure helper: compute_marginal_score
# ---------------------------------------------------------------------------


def compute_marginal_score(
    upgrade: UpgradeDefinition,
    current_level: int,
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
        self,
        upgrades: UpgradeDatabase,
        profile: Profile,
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
                u,
                current_level,
            )
            if score <= 0:
                continue

            candidate = _build_ranked(
                u,
                profile,
                score,
                cost,
                cur_eff,
                nxt_eff,
                mb,
                self.name,
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
            f"{ranked.upgrade_name} (level {ranked.current_level} \u2192 {ranked.next_level})",
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
        self,
        upgrades: UpgradeDatabase,
        profile: Profile,
    ) -> list[RankedUpgrade]:
        """Return all non-maxed upgrades ranked globally by weighted score."""
        results: list[RankedUpgrade] = []

        for u in upgrades.upgrades:
            current_level = profile.get_level(u.id)
            if current_level >= u.max_level:
                continue

            base_score, cost, cur_eff, nxt_eff, mb = compute_marginal_score(
                u,
                current_level,
            )
            if base_score <= 0:
                continue

            weight: float = self._weights.for_category(u.category)
            weighted_score: float = base_score * weight

            results.append(
                _build_ranked(
                    u,
                    profile,
                    weighted_score,
                    cost,
                    cur_eff,
                    nxt_eff,
                    mb,
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
            f"{ranked.upgrade_name} (level {ranked.current_level} \u2192 {ranked.next_level})",
            f"  Cost: {ranked.coin_cost:,} coins",
            f"  Effect: {ranked.current_effect} \u2192 {ranked.next_effect}",
            f"  Marginal Benefit: {ranked.marginal_benefit}",
            (
                f"  Score: {ranked.marginal_benefit} / {ranked.coin_cost}"
                f" * {weight} = {_fmt_score(ranked.score)}"
            ),
            (f"  Mode: {self.name} (Attack={w.attack}, Defense={w.defense}, Utility={w.utility})"),
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# DPS calculation (ported from jacoelt/tower-calculator AttackUpgrades.tsx)
# ---------------------------------------------------------------------------

_RAPID_FIRE_BONUS = Decimal(4)
_RAPID_FIRE_DURATION = Decimal(1)

_DPS_UPGRADE_IDS = frozenset(
    {
        "damage",
        "attack_speed",
        "crit_chance",
        "crit_factor",
        "multishot_chance",
        "multishot_targets",
        "rapid_fire_chance",
        "bounce_chance",
        "bounce_targets",
    }
)

# Maps lab research IDs to the workshop upgrade IDs they boost.
_LAB_BOOST_MAP: dict[str, str] = {
    "lab_damage": "damage",
    "lab_crit_factor": "crit_factor",
    "lab_attack_speed": "attack_speed",
    "lab_defense_flat": "defense_absolute",
    "lab_defense_percent": "defense_percent",
}


def _get_upgrade_value(
    upgrades: UpgradeDatabase,
    upgrade_id: str,
    level: int,
) -> float:
    """Get the cumulative_effect for a given upgrade at a given level."""
    u = upgrades.get_upgrade(upgrade_id)
    if u is None:
        return 0.0
    if level <= 0:
        return u.base_value
    if level > u.max_level:
        level = u.max_level
    return u.levels[level - 1].cumulative_effect


def _get_lab_multiplier(
    lab: LabResearchDatabase | None,
    profile: Profile,
    workshop_upgrade_id: str,
) -> float:
    """Get the lab research multiplier that applies to a workshop upgrade."""
    if lab is None:
        return 1.0
    for lab_id, ws_id in _LAB_BOOST_MAP.items():
        if ws_id == workshop_upgrade_id:
            level = profile.lab_levels.get(lab_id, 0)
            if level <= 0:
                research = lab.get_research(lab_id)
                if research and research.boost_type == "additive":
                    return 0.0
                return 1.0
            return lab.get_value(lab_id, level)
    return 1.0


class _DPSState:
    """Snapshot of all attack stat values needed for DPS calculation."""

    __slots__ = (
        "damage",
        "attack_speed",
        "crit_chance",
        "crit_factor",
        "multishot_chance",
        "multishot_targets",
        "rapid_fire_chance",
        "bounce_chance",
        "bounce_targets",
    )

    def __init__(
        self,
        upgrades: UpgradeDatabase,
        profile: Profile,
        lab: LabResearchDatabase | None = None,
    ) -> None:
        self.damage = _get_upgrade_value(upgrades, "damage", profile.get_level("damage"))
        self.attack_speed = _get_upgrade_value(
            upgrades,
            "attack_speed",
            profile.get_level("attack_speed"),
        )
        self.crit_chance = _get_upgrade_value(
            upgrades,
            "crit_chance",
            profile.get_level("crit_chance"),
        )
        self.crit_factor = _get_upgrade_value(
            upgrades,
            "crit_factor",
            profile.get_level("crit_factor"),
        )
        self.multishot_chance = _get_upgrade_value(
            upgrades,
            "multishot_chance",
            profile.get_level("multishot_chance"),
        )
        self.multishot_targets = _get_upgrade_value(
            upgrades,
            "multishot_targets",
            profile.get_level("multishot_targets"),
        )
        self.rapid_fire_chance = _get_upgrade_value(
            upgrades,
            "rapid_fire_chance",
            profile.get_level("rapid_fire_chance"),
        )
        self.bounce_chance = _get_upgrade_value(
            upgrades,
            "bounce_chance",
            profile.get_level("bounce_chance"),
        )
        self.bounce_targets = _get_upgrade_value(
            upgrades,
            "bounce_targets",
            profile.get_level("bounce_targets"),
        )

        # Apply lab multipliers to stats that have lab boosts.
        if lab:
            self.damage *= _get_lab_multiplier(lab, profile, "damage")
            self.attack_speed *= _get_lab_multiplier(lab, profile, "attack_speed")
            self.crit_factor *= _get_lab_multiplier(lab, profile, "crit_factor")

    def with_override(self, upgrade_id: str, value: float) -> _DPSState:
        """Return a copy with one stat overridden (pre-lab-boost value)."""
        clone = _DPSState.__new__(_DPSState)
        for attr in _DPSState.__slots__:
            setattr(clone, attr, getattr(self, attr))
        if hasattr(clone, upgrade_id):
            setattr(clone, upgrade_id, value)
        return clone


def compute_dps(state: _DPSState) -> Decimal:
    """Compute DPS from attack stat values.

    Replicates the ``calculateDps()`` function from the reference calculator.
    Uses Decimal for precision matching.

    Formula::

        DPS = damage * attack_speed_final * crit_mult * multishot_mult * bounce_mult

    Where multipliers use the expected-value formula:
        mult = 1 - (chance/100) + (chance/100) * factor
    """
    damage = Decimal(str(state.damage))
    attack_speed = Decimal(str(state.attack_speed))
    crit_chance = Decimal(str(state.crit_chance))
    crit_factor = Decimal(str(state.crit_factor))
    ms_chance = Decimal(str(state.multishot_chance))
    ms_targets = Decimal(str(state.multishot_targets))
    rf_chance = Decimal(str(state.rapid_fire_chance))
    bounce_chance = Decimal(str(state.bounce_chance))
    bounce_targets = Decimal(str(state.bounce_targets))

    hundred = Decimal(100)
    one = Decimal(1)

    crit_mult = one - (crit_chance / hundred) + (crit_chance / hundred) * crit_factor
    ms_mult = one - (ms_chance / hundred) + (ms_chance / hundred) * ms_targets
    bounce_mult = one - (bounce_chance / hundred) + (bounce_chance / hundred) * bounce_targets

    # Rapid fire: average DPS boost from periodic 400% attack speed procs
    if rf_chance > 0 and attack_speed > 0:
        avg_time_between_procs = (one / attack_speed) * (hundred / rf_chance)
        avg_increase = (_RAPID_FIRE_BONUS * _RAPID_FIRE_DURATION) / (
            _RAPID_FIRE_DURATION + avg_time_between_procs
        )
        attack_speed_final = attack_speed * (one + avg_increase / hundred)
    else:
        attack_speed_final = attack_speed

    return damage * attack_speed_final * crit_mult * ms_mult * bounce_mult


# ---------------------------------------------------------------------------
# Engine 3: Reference (DPS-based efficiency scoring)
# ---------------------------------------------------------------------------


class ReferenceEngine:
    """DPS-efficiency scoring engine ported from the reference calculator.

    For attack upgrades: ranks by ``(DPS_after - DPS_before) / coin_cost``.
    For defense/utility: falls back to ``marginal_benefit / coin_cost``.

    Lab research multipliers are applied when a ``LabResearchDatabase`` is
    provided, matching how the reference tool adjusts values.
    """

    def __init__(self, lab: LabResearchDatabase | None = None) -> None:
        self._lab = lab

    @property
    def name(self) -> str:
        return "reference"

    @property
    def version(self) -> str:
        return "1.0"

    def rank(
        self,
        upgrades: UpgradeDatabase,
        profile: Profile,
    ) -> list[RankedUpgrade]:
        """Return all non-maxed upgrades ranked by DPS efficiency."""
        current_state = _DPSState(upgrades, profile, self._lab)
        current_dps = compute_dps(current_state)

        results: list[RankedUpgrade] = []

        for u in upgrades.upgrades:
            current_level = profile.get_level(u.id)
            if current_level >= u.max_level:
                continue

            next_level_data = u.levels[current_level]
            coin_cost = next_level_data.coin_cost
            if coin_cost <= 0:
                continue

            next_effect = next_level_data.cumulative_effect
            if current_level <= 0:
                current_effect = u.base_value
            else:
                current_effect = u.levels[current_level - 1].cumulative_effect
            marginal_benefit = next_effect - current_effect

            if u.id in _DPS_UPGRADE_IDS:
                # Apply lab multiplier to the next value for DPS calc
                next_val_with_lab = next_effect
                lab_mult = _get_lab_multiplier(self._lab, profile, u.id)
                if u.id in ("damage", "attack_speed", "crit_factor"):
                    next_val_with_lab = next_effect * lab_mult

                next_state = current_state.with_override(u.id, next_val_with_lab)
                next_dps = compute_dps(next_state)
                dps_increase = next_dps - current_dps
                score = float(dps_increase / Decimal(str(coin_cost)))
            else:
                if marginal_benefit <= 0:
                    continue
                score = marginal_benefit / coin_cost

            if score <= 0:
                continue

            results.append(
                _build_ranked(
                    u,
                    profile,
                    score,
                    coin_cost,
                    current_effect,
                    next_effect,
                    marginal_benefit,
                    self.name,
                )
            )

        results.sort(key=_sort_key)
        return results

    def explain(self, ranked: RankedUpgrade) -> str:
        """Return a human-readable breakdown of the DPS efficiency."""
        is_dps = ranked.upgrade_id in _DPS_UPGRADE_IDS
        method_detail = "DPS efficiency" if is_dps else "marginal benefit / cost"
        lines = [
            f"{ranked.upgrade_name} (level {ranked.current_level} \u2192 {ranked.next_level})",
            f"  Cost: {ranked.coin_cost:,} coins",
            f"  Effect: {ranked.current_effect} \u2192 {ranked.next_effect}",
            f"  Marginal Benefit: {ranked.marginal_benefit}",
            f"  Score: {_fmt_score(ranked.score)} ({method_detail})",
            f"  Mode: {self.name}",
        ]
        return "\n".join(lines)
