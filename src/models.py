"""Pydantic v2 data models for the Tower Upgrade Advisor project."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = [
    "UpgradeLevel",
    "UpgradeDefinition",
    "UpgradeDatabase",
    "ScoringWeights",
    "Profile",
    "RankedUpgrade",
]


# ---------------------------------------------------------------------------
# 1. UpgradeLevel
# ---------------------------------------------------------------------------

class UpgradeLevel(BaseModel):
    """Per-level data for a single upgrade."""

    model_config = ConfigDict(frozen=True)

    level: int = Field(..., ge=1, description="Level number (1-indexed)")
    coin_cost: int = Field(..., gt=0, description="Cost in coins to reach this level")
    cumulative_effect: float = Field(
        ..., description="Total effect at this level"
    )
    effect_delta: float = Field(
        ..., description="Marginal effect gained from the previous level"
    )

    @field_validator("cumulative_effect", "effect_delta")
    @classmethod
    def _no_nan_or_inf(cls, v: float, info) -> float:  # noqa: ANN001
        if math.isnan(v) or math.isinf(v):
            raise ValueError(
                f"{info.field_name} must be a finite number, got {v}"
            )
        return v


# ---------------------------------------------------------------------------
# 2. UpgradeDefinition
# ---------------------------------------------------------------------------

class UpgradeDefinition(BaseModel):
    """Full definition of one workshop upgrade."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(
        ..., min_length=1, description="Stable snake_case identifier"
    )
    name: str = Field(..., min_length=1, description="Display name")
    category: Literal["offense", "defense", "economy", "utility"] = Field(
        ...,
        description=(
            "Upgrade category. Known values: 'offense', 'defense', 'economy', 'utility'. "
            "Exact names come from the reference tool extract; update this Literal "
            "if extraction reveals different groupings."
        ),
    )
    effect_unit: str = Field(
        ..., min_length=1, description="What the effect measures"
    )
    effect_type: Literal["multiplicative", "additive"] = Field(
        ..., description="How the effect compounds"
    )
    base_value: float = Field(
        ..., description="Value at level 0 (1.0 for multiplicative, 0 for additive)"
    )
    max_level: int = Field(..., ge=1, description="Maximum achievable level")
    display_order: int = Field(
        ..., ge=0, description="Ordering within category"
    )
    levels: list[UpgradeLevel] = Field(
        ..., description="Per-level data, indexed 1..max_level"
    )

    @field_validator("base_value")
    @classmethod
    def _base_value_finite(cls, v: float) -> float:
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"base_value must be a finite number, got {v}")
        return v

    @model_validator(mode="after")
    def _validate_levels(self) -> UpgradeDefinition:
        levels = self.levels

        # Length must equal max_level
        if len(levels) != self.max_level:
            raise ValueError(
                f"levels list length ({len(levels)}) must equal "
                f"max_level ({self.max_level})"
            )

        # Levels must be sorted by level number
        for i, lvl in enumerate(levels):
            if lvl.level != i + 1:
                raise ValueError(
                    f"levels must be sorted by level: expected level {i + 1} "
                    f"at index {i}, got {lvl.level}"
                )

        # coin_cost must be monotonically increasing (hard rule: structural integrity)
        for i in range(1, len(levels)):
            if levels[i].coin_cost <= levels[i - 1].coin_cost:
                raise ValueError(
                    f"coin_cost must be monotonically increasing: "
                    f"level {levels[i].level} cost ({levels[i].coin_cost}) "
                    f"<= level {levels[i - 1].level} cost "
                    f"({levels[i - 1].coin_cost})"
                )

        # NOTE: cumulative_effect monotonicity is intentionally NOT enforced here.
        # Some upgrades may legitimately have non-monotonic effects (e.g. percentage
        # upgrades with fixed deltas that appear to be equal or platform-rounded).
        # Monotonicity anomalies are logged as warnings in data_loader.validate_upgrade_data().
        # See docs/game_and_project_context.md §10 for rationale.

        return self


# ---------------------------------------------------------------------------
# 3. UpgradeDatabase
# ---------------------------------------------------------------------------

class UpgradeDatabase(BaseModel):
    """Top-level container for all upgrade data."""

    model_config = ConfigDict(str_strip_whitespace=True)

    version: str = Field(..., min_length=1, description="Data version / extraction date")
    game_version: str = Field(
        ..., min_length=1, description="Game version this data represents"
    )
    source: str = Field(
        ..., min_length=1, description="Where the data came from"
    )
    upgrades: list[UpgradeDefinition] = Field(
        ..., description="All upgrade definitions"
    )

    def get_upgrade(self, upgrade_id: str) -> UpgradeDefinition | None:
        """Return the upgrade with the given id, or ``None`` if not found."""
        for upgrade in self.upgrades:
            if upgrade.id == upgrade_id:
                return upgrade
        return None

    def get_by_category(self, category: str) -> list[UpgradeDefinition]:
        """Return all upgrades belonging to *category*."""
        return [u for u in self.upgrades if u.category == category]

    def upgrade_ids(self) -> list[str]:
        """Return a list of all upgrade ids."""
        return [u.id for u in self.upgrades]


# ---------------------------------------------------------------------------
# 4. ScoringWeights
# ---------------------------------------------------------------------------

class ScoringWeights(BaseModel):
    """User-adjustable sliders for the four upgrade categories.

    Three main sliders (Economy / Offense / Defense) are always shown in the UI.
    The utility slider bridges upgrades whose category is 'utility' (e.g. land
    mines, orbs) which are harder to compare against core stats. Defaults to 1.0
    (equal footing) so it never silently deprioritizes anything.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    economy: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Economy weight"
    )
    offense: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Offense weight"
    )
    defense: float = Field(
        default=1.0, ge=0.0, le=2.0, description="Defense weight"
    )
    utility: float = Field(
        default=1.0, ge=0.0, le=2.0,
        description="Utility weight (situational upgrades: land mines, orbs, etc.)",
    )

    def for_category(self, category: str) -> float:
        """Return the weight for the given *category*.

        Falls back to 1.0 and does NOT raise for unknown categories so that
        new categories introduced by a game update are never silently zeroed
        out. Unknown categories are logged by the caller if needed.
        """
        return getattr(self, category, 1.0)


# ---------------------------------------------------------------------------
# 5. Profile
# ---------------------------------------------------------------------------

class Profile(BaseModel):
    """A user profile containing current upgrade levels and preferences."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(
        ..., min_length=1, description="Unique identifier (UUID)"
    )
    name: str = Field(..., min_length=1, description="Display name")
    created_at: datetime = Field(..., description="When the profile was created")
    updated_at: datetime = Field(..., description="When the profile was last updated")
    available_coins: int = Field(
        default=0, ge=0, description="Coins available to spend"
    )
    levels: dict[str, int] = Field(
        default_factory=dict,
        description="Mapping of upgrade_id -> current level",
    )
    weights: ScoringWeights = Field(
        default_factory=ScoringWeights,
        description="User's scoring slider values",
    )
    tags: list[str] = Field(
        default_factory=list,
        description=(
            "Optional build tags, e.g. ['farm build', 'push build', 'balanced build']. "
            "Free-form strings for the user's own organisation."
        ),
    )

    @field_validator("levels")
    @classmethod
    def _levels_non_negative(cls, v: dict[str, int]) -> dict[str, int]:
        for upgrade_id, level in v.items():
            if level < 0:
                raise ValueError(
                    f"Level for upgrade {upgrade_id!r} must be >= 0, got {level}"
                )
        return v

    def get_level(self, upgrade_id: str) -> int:
        """Return the current level for *upgrade_id*, defaulting to 0."""
        return self.levels.get(upgrade_id, 0)


# ---------------------------------------------------------------------------
# 6. RankedUpgrade
# ---------------------------------------------------------------------------

class RankedUpgrade(BaseModel):
    """Output of the scoring engine — one scored upgrade recommendation."""

    model_config = ConfigDict(frozen=True)

    upgrade_id: str
    upgrade_name: str
    category: str
    current_level: int
    next_level: int
    coin_cost: int
    current_effect: float
    next_effect: float
    marginal_benefit: float
    score: float
    affordable: bool
    scoring_method: str = Field(
        ..., description="Name of the engine that produced this ranking"
    )
