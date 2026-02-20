"""Tests for Pydantic models."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models import (
    LabResearchDatabase,
    LabResearchDefinition,
    LabResearchLevel,
    Profile,
    RankedUpgrade,
    ScoringWeights,
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
            id="test",
            name="Test",
            category="attack",
            effect_unit="%",
            effect_type="multiplicative",
            base_value=1.0,
            max_level=3,
            display_order=1,
            levels=self._make_levels(3),
        )
        assert u.id == "test"
        assert len(u.levels) == 3

    def test_level_count_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="max_level"):
            UpgradeDefinition(
                id="test",
                name="Test",
                category="attack",
                effect_unit="%",
                effect_type="multiplicative",
                base_value=1.0,
                max_level=5,
                display_order=1,
                levels=self._make_levels(3),
            )

    def test_non_monotonic_cost_rejected(self) -> None:
        levels = self._make_levels(3)
        levels[2]["coin_cost"] = 50
        with pytest.raises(ValidationError, match="monotonically increasing"):
            UpgradeDefinition(
                id="test",
                name="Test",
                category="attack",
                effect_unit="%",
                effect_type="multiplicative",
                base_value=1.0,
                max_level=3,
                display_order=1,
                levels=levels,
            )

    def test_invalid_category_rejected(self) -> None:
        with pytest.raises(ValidationError):
            UpgradeDefinition(
                id="test",
                name="Test",
                category="special",
                effect_unit="%",
                effect_type="multiplicative",
                base_value=1.0,
                max_level=3,
                display_order=1,
                levels=self._make_levels(3),
            )

    def test_game_categories_accepted(self) -> None:
        for cat in ("attack", "defense", "utility"):
            u = UpgradeDefinition(
                id=f"test_{cat}",
                name=f"Test {cat}",
                category=cat,
                effect_unit="%",
                effect_type="additive",
                base_value=0,
                max_level=1,
                display_order=0,
                levels=[{"level": 1, "coin_cost": 10, "cumulative_effect": 1, "effect_delta": 1}],
            )
            assert u.category == cat


class TestScoringWeights:
    def test_defaults(self) -> None:
        w = ScoringWeights()
        assert w.attack == 1.0
        assert w.defense == 1.0
        assert w.utility == 1.0

    def test_for_category(self) -> None:
        w = ScoringWeights(attack=2.0, defense=1.5, utility=0.8)
        assert w.for_category("attack") == 2.0
        assert w.for_category("defense") == 1.5
        assert w.for_category("utility") == 0.8

    def test_unknown_category_falls_back_to_one(self) -> None:
        w = ScoringWeights()
        assert w.for_category("future_category") == 1.0

    def test_out_of_range_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ScoringWeights(attack=3.0)
        with pytest.raises(ValidationError):
            ScoringWeights(defense=-0.1)


class TestProfile:
    def test_get_level_default(self) -> None:
        p = Profile(
            id="t",
            name="t",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        assert p.get_level("unknown") == 0

    def test_get_level_set(self) -> None:
        p = Profile(
            id="t",
            name="t",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            levels={"damage": 5},
        )
        assert p.get_level("damage") == 5

    def test_negative_level_rejected(self) -> None:
        with pytest.raises(ValidationError, match=">= 0"):
            Profile(
                id="t",
                name="t",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                levels={"damage": -1},
            )

    def test_lab_levels(self) -> None:
        p = Profile(
            id="t",
            name="t",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            lab_levels={"lab_damage": 50},
        )
        assert p.lab_levels["lab_damage"] == 50


class TestLabResearch:
    def test_lab_level(self) -> None:
        lv = LabResearchLevel(level=1, value=1.02)
        assert lv.level == 1
        assert lv.value == 1.02

    def test_lab_definition(self) -> None:
        defn = LabResearchDefinition(
            id="lab_damage",
            name="Lab Damage",
            boost_type="multiplicative",
            max_level=2,
            levels=[
                LabResearchLevel(level=1, value=1.02),
                LabResearchLevel(level=2, value=1.04),
            ],
        )
        assert defn.max_level == 2

    def test_lab_definition_level_count_mismatch_rejected(self) -> None:
        """len(levels) must equal max_level."""
        with pytest.raises(ValidationError, match="levels list length.*max_level"):
            LabResearchDefinition(
                id="lab_damage",
                name="Lab Damage",
                boost_type="multiplicative",
                max_level=5,
                levels=[
                    LabResearchLevel(level=1, value=1.02),
                    LabResearchLevel(level=2, value=1.04),
                    LabResearchLevel(level=3, value=1.06),
                ],
            )

    def test_lab_database_get_value(self) -> None:
        db = LabResearchDatabase(
            researches=[
                LabResearchDefinition(
                    id="lab_damage",
                    name="Lab Damage",
                    boost_type="multiplicative",
                    max_level=3,
                    levels=[
                        LabResearchLevel(level=1, value=1.02),
                        LabResearchLevel(level=2, value=1.04),
                        LabResearchLevel(level=3, value=1.06),
                    ],
                ),
            ]
        )
        assert db.get_value("lab_damage", 0) == 1.0
        assert db.get_value("lab_damage", 1) == 1.02
        assert db.get_value("lab_damage", 2) == 1.04
        assert db.get_value("lab_damage", 99) == 1.06


class TestRankedUpgrade:
    def test_frozen(self) -> None:
        r = RankedUpgrade(
            upgrade_id="test",
            upgrade_name="Test",
            category="attack",
            current_level=0,
            next_level=1,
            coin_cost=100,
            current_effect=0,
            next_effect=5,
            marginal_benefit=5,
            score=0.05,
            affordable=True,
            scoring_method="test",
        )
        with pytest.raises(ValidationError):
            r.score = 1.0  # type: ignore[misc]
