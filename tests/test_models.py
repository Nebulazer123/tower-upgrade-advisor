"""Tests for Pydantic models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models import (
    Profile,
    RankedUpgrade,
    ScoringWeights,
    UpgradeDatabase,
    UpgradeDefinition,
    UpgradeLevel,
)


class TestUpgradeLevel:
    def test_valid_level(self) -> None:
        lv = UpgradeLevel(level=1, coin_cost=100, cumulative_effect=1.5, effect_delta=0.5)
        assert lv.level == 1
        assert lv.coin_cost == 100

    def test_frozen(self) -> None:
        lv = UpgradeLevel(level=1, coin_cost=100, cumulative_effect=1.5, effect_delta=0.5)
        with pytest.raises(ValidationError):
            lv.level = 2  # type: ignore[misc]

    def test_negative_cost_rejected(self) -> None:
        with pytest.raises(ValidationError, match="coin_cost"):
            UpgradeLevel(level=1, coin_cost=-10, cumulative_effect=1.0, effect_delta=0.0)

    def test_zero_cost_rejected(self) -> None:
        with pytest.raises(ValidationError, match="coin_cost"):
            UpgradeLevel(level=1, coin_cost=0, cumulative_effect=1.0, effect_delta=0.0)

    def test_nan_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            UpgradeLevel(level=1, coin_cost=100, cumulative_effect=float("nan"), effect_delta=0.0)

    def test_inf_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            UpgradeLevel(level=1, coin_cost=100, cumulative_effect=float("inf"), effect_delta=0.0)


class TestUpgradeDefinition:
    def _make_levels(self, n: int) -> list[dict]:
        return [
            {
                "level": i + 1,
                "coin_cost": (i + 1) * 100,
                "cumulative_effect": (i + 1) * 10,
                "effect_delta": 10,
            }
            for i in range(n)
        ]

    def test_valid_upgrade(self) -> None:
        u = UpgradeDefinition(
            id="test", name="Test", category="offense",
            effect_unit="%", effect_type="multiplicative",
            base_value=1.0, max_level=3, display_order=1,
            levels=self._make_levels(3),
        )
        assert u.id == "test"
        assert len(u.levels) == 3

    def test_level_count_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="max_level"):
            UpgradeDefinition(
                id="test", name="Test", category="offense",
                effect_unit="%", effect_type="multiplicative",
                base_value=1.0, max_level=5, display_order=1,
                levels=self._make_levels(3),
            )

    def test_non_monotonic_cost_rejected(self) -> None:
        levels = self._make_levels(3)
        levels[2]["coin_cost"] = 50  # lower than previous
        with pytest.raises(ValidationError, match="monotonically increasing"):
            UpgradeDefinition(
                id="test", name="Test", category="offense",
                effect_unit="%", effect_type="multiplicative",
                base_value=1.0, max_level=3, display_order=1,
                levels=levels,
            )

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpgradeDefinition(
                id="test", name="Test", category="special",
                effect_unit="%", effect_type="multiplicative",
                base_value=1.0, max_level=3, display_order=1,
                levels=self._make_levels(3),
            )


class TestScoringWeights:
    def test_defaults(self) -> None:
        w = ScoringWeights()
        assert w.economy == 1.0
        assert w.offense == 1.0
        assert w.defense == 1.0
        assert w.utility == 1.0

    def test_for_category(self) -> None:
        w = ScoringWeights(economy=0.5, offense=2.0, defense=1.5, utility=0.8)
        assert w.for_category("economy") == 0.5
        assert w.for_category("offense") == 2.0
        assert w.for_category("defense") == 1.5
        assert w.for_category("utility") == 0.8

    def test_unknown_category_falls_back_to_one(self) -> None:
        # Unknown categories (e.g. from a future game update) return 1.0
        # rather than raising, so they are never silently zeroed out.
        w = ScoringWeights()
        assert w.for_category("future_category") == 1.0

    def test_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScoringWeights(economy=3.0)
        with pytest.raises(ValidationError):
            ScoringWeights(defense=-0.1)


class TestProfile:
    def test_get_level_default(self) -> None:
        p = Profile(
            id="t", name="t",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert p.get_level("unknown") == 0

    def test_get_level_set(self) -> None:
        p = Profile(
            id="t", name="t",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            levels={"damage": 5},
        )
        assert p.get_level("damage") == 5

    def test_negative_level_rejected(self) -> None:
        with pytest.raises(ValidationError, match=">= 0"):
            Profile(
                id="t", name="t",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                levels={"damage": -1},
            )


class TestUpgradeDefinitionEdgeCases:
    """Cover model_validator branches for levels sorting and base_value."""

    def _make_levels(self, n: int) -> list[dict]:
        return [
            {
                "level": i + 1,
                "coin_cost": (i + 1) * 100,
                "cumulative_effect": (i + 1) * 10,
                "effect_delta": 10,
            }
            for i in range(n)
        ]

    def test_unsorted_levels_rejected(self) -> None:
        levels = self._make_levels(3)
        levels[0], levels[1] = levels[1], levels[0]
        with pytest.raises(ValidationError, match="sorted by level"):
            UpgradeDefinition(
                id="test", name="Test", category="offense",
                effect_unit="%", effect_type="multiplicative",
                base_value=1.0, max_level=3, display_order=1,
                levels=levels,
            )

    def test_nan_base_value_rejected(self) -> None:
        levels = self._make_levels(2)
        with pytest.raises(ValidationError, match="finite"):
            UpgradeDefinition(
                id="test", name="Test", category="offense",
                effect_unit="%", effect_type="multiplicative",
                base_value=float("nan"), max_level=2, display_order=1,
                levels=levels,
            )

    def test_inf_base_value_rejected(self) -> None:
        levels = self._make_levels(2)
        with pytest.raises(ValidationError, match="finite"):
            UpgradeDefinition(
                id="test", name="Test", category="offense",
                effect_unit="%", effect_type="multiplicative",
                base_value=float("inf"), max_level=2, display_order=1,
                levels=levels,
            )

    def test_nan_effect_delta_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            UpgradeLevel(
                level=1, coin_cost=100,
                cumulative_effect=1.0, effect_delta=float("nan"),
            )

    def test_inf_effect_delta_rejected(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            UpgradeLevel(
                level=1, coin_cost=100,
                cumulative_effect=1.0, effect_delta=float("inf"),
            )


class TestUpgradeDatabaseMethods:
    """Cover UpgradeDatabase.get_upgrade(None), get_by_category, upgrade_ids."""

    def test_get_upgrade_not_found(self, test_upgrades: UpgradeDatabase) -> None:
        assert test_upgrades.get_upgrade("nonexistent") is None

    def test_get_upgrade_found(self, test_upgrades: UpgradeDatabase) -> None:
        u = test_upgrades.get_upgrade("damage")
        assert u is not None
        assert u.id == "damage"

    def test_get_by_category(self, test_upgrades: UpgradeDatabase) -> None:
        offense = test_upgrades.get_by_category("offense")
        assert len(offense) == 2
        assert all(u.category == "offense" for u in offense)

    def test_get_by_category_empty(self, test_upgrades: UpgradeDatabase) -> None:
        result = test_upgrades.get_by_category("nonexistent")
        assert result == []

    def test_upgrade_ids(self, test_upgrades: UpgradeDatabase) -> None:
        ids = test_upgrades.upgrade_ids()
        assert len(ids) == 6
        assert "damage" in ids
        assert "health" in ids


class TestRankedUpgrade:
    def test_frozen(self) -> None:
        r = RankedUpgrade(
            upgrade_id="test", upgrade_name="Test", category="offense",
            current_level=0, next_level=1, coin_cost=100,
            current_effect=0, next_effect=5, marginal_benefit=5,
            score=0.05, affordable=True, scoring_method="test",
        )
        with pytest.raises(ValidationError):
            r.score = 1.0  # type: ignore[misc]
