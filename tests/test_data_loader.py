"""Tests for data loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.data_loader import (
    ValidationResult,
    load_upgrades,
    validate_raw_json,
    validate_upgrade_data,
)
from src.models import UpgradeDatabase

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestLoadUpgrades:
    def test_load_valid_file(self, test_upgrades_path: Path) -> None:
        db = load_upgrades(test_upgrades_path)
        assert isinstance(db, UpgradeDatabase)
        assert len(db.upgrades) == 6

    def test_load_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_upgrades(tmp_path / "nonexistent.json")

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load_upgrades(bad)

    def test_load_invalid_schema(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"version": "1", "upgrades": "not a list"}), encoding="utf-8")
        with pytest.raises(ValidationError):
            load_upgrades(bad)


class TestValidateUpgradeData:
    def test_valid_data_passes(self, test_upgrades: UpgradeDatabase) -> None:
        result = validate_upgrade_data(test_upgrades)
        assert result.ok, result.summary()
        assert len(result.errors) == 0

    def test_all_categories_present(self, test_upgrades: UpgradeDatabase) -> None:
        result = validate_upgrade_data(test_upgrades)
        # Fixture has offense, defense, economy. "utility" may be expected
        # by data_loader but our test fixture deliberately omits it.
        cat_warnings = [
            w for w in result.warnings
            if "Missing expected category" in w and "utility" not in w
        ]
        assert len(cat_warnings) == 0

    def test_upgrade_count_warning(self) -> None:
        """Small dataset triggers a warning but not an error."""
        db = UpgradeDatabase(
            version="test",
            game_version="test",
            source="test",
            upgrades=[],
        )
        result = validate_upgrade_data(db)
        assert not result.ok  # "No upgrades" is an error


class TestValidateRawJson:
    def test_valid_raw_json(self, test_upgrades_path: Path) -> None:
        raw = json.loads(test_upgrades_path.read_text(encoding="utf-8"))
        result = validate_raw_json(raw)
        assert result.ok

    def test_string_cost_detected(self) -> None:
        raw = {
            "upgrades": [
                {
                    "name": "Test",
                    "levels": [
                        {"coin_cost": "1.2M", "cumulative_effect": 1, "effect_delta": 1}
                    ],
                }
            ]
        }
        result = validate_raw_json(raw)
        assert not result.ok
        assert any("string value" in e for e in result.errors)

    def test_non_dict_rejected(self) -> None:
        result = validate_raw_json([])
        assert not result.ok


class TestValidateUpgradeDataBranches:
    """Cover duplicate ID, duplicate name, duplicate display_order, missing category."""

    def _make_upgrade_dict(
        self, *, uid: str = "test", name: str = "Test", category: str = "offense",
        display_order: int = 0, max_level: int = 2,
    ) -> dict:
        return {
            "id": uid, "name": name, "category": category,
            "effect_unit": "%", "effect_type": "multiplicative",
            "base_value": 1.0, "max_level": max_level, "display_order": display_order,
            "levels": [
                {"level": i + 1, "coin_cost": (i + 1) * 100,
                 "cumulative_effect": 1.0 + (i + 1) * 0.1, "effect_delta": 0.1}
                for i in range(max_level)
            ],
        }

    def _make_db(self, upgrades: list[dict]) -> UpgradeDatabase:
        return UpgradeDatabase.model_validate({
            "version": "test", "game_version": "test", "source": "test",
            "upgrades": upgrades,
        })

    def test_duplicate_id_error(self) -> None:
        u1 = self._make_upgrade_dict(uid="dup", name="A", display_order=0)
        u2 = self._make_upgrade_dict(uid="dup", name="B", display_order=1)
        db = self._make_db([u1, u2])
        result = validate_upgrade_data(db)
        assert any("Duplicate upgrade ID" in e for e in result.errors)

    def test_duplicate_name_warning(self) -> None:
        u1 = self._make_upgrade_dict(uid="a", name="Same", display_order=0)
        u2 = self._make_upgrade_dict(uid="b", name="Same", display_order=1)
        db = self._make_db([u1, u2])
        result = validate_upgrade_data(db)
        assert any("Duplicate upgrade name" in w for w in result.warnings)

    def test_duplicate_display_order_warning(self) -> None:
        u1 = self._make_upgrade_dict(uid="a", name="A", display_order=0)
        u2 = self._make_upgrade_dict(uid="b", name="B", display_order=0)
        db = self._make_db([u1, u2])
        result = validate_upgrade_data(db)
        assert any("Duplicate display_order" in w for w in result.warnings)

    def test_missing_category_warning(self) -> None:
        u1 = self._make_upgrade_dict(uid="a", name="A", category="offense", display_order=0)
        db = self._make_db([u1])
        result = validate_upgrade_data(db)
        cat_warnings = [w for w in result.warnings if "Missing expected category" in w]
        assert len(cat_warnings) >= 2  # missing defense and economy

    def test_small_dataset_warning(self) -> None:
        u1 = self._make_upgrade_dict(uid="a", name="A", display_order=0)
        db = self._make_db([u1])
        result = validate_upgrade_data(db)
        assert any("Only" in w and "upgrades" in w for w in result.warnings)

    def test_effect_delta_inconsistency_warning(self) -> None:
        upgrade_dict = {
            "id": "bad_delta", "name": "BadDelta", "category": "offense",
            "effect_unit": "%", "effect_type": "multiplicative",
            "base_value": 1.0, "max_level": 2, "display_order": 0,
            "levels": [
                {"level": 1, "coin_cost": 100, "cumulative_effect": 1.1, "effect_delta": 0.1},
                {"level": 2, "coin_cost": 200, "cumulative_effect": 1.2, "effect_delta": 0.5},
            ],
        }
        db = self._make_db([upgrade_dict])
        result = validate_upgrade_data(db)
        assert any("effect_delta" in w for w in result.warnings)

    def test_cumulative_effect_decrease_warning(self) -> None:
        upgrade_dict = {
            "id": "dec", "name": "Decreasing", "category": "offense",
            "effect_unit": "%", "effect_type": "additive",
            "base_value": 0, "max_level": 2, "display_order": 0,
            "levels": [
                {"level": 1, "coin_cost": 100, "cumulative_effect": 10, "effect_delta": 10},
                {"level": 2, "coin_cost": 200, "cumulative_effect": 8, "effect_delta": -2},
            ],
        }
        db = self._make_db([upgrade_dict])
        result = validate_upgrade_data(db)
        assert any("cumulative_effect decreased" in w for w in result.warnings)


class TestValidateRawJsonBranches:
    """Cover additional validate_raw_json branches."""

    def test_upgrades_not_a_list(self) -> None:
        result = validate_raw_json({"upgrades": "not a list"})
        assert not result.ok
        assert any("'upgrades' must be a list" in e for e in result.errors)

    def test_upgrade_item_not_a_dict(self) -> None:
        result = validate_raw_json({"upgrades": ["not a dict"]})
        assert not result.ok
        assert any("must be a dict" in e for e in result.errors)

    def test_levels_not_a_list(self) -> None:
        result = validate_raw_json({"upgrades": [{"name": "X", "levels": "bad"}]})
        assert not result.ok
        assert any("'levels' must be a list" in e for e in result.errors)

    def test_level_item_not_a_dict(self) -> None:
        result = validate_raw_json({"upgrades": [{"name": "X", "levels": ["not a dict"]}]})
        assert not result.ok
        assert any("must be a dict" in e for e in result.errors)

    def test_string_effect_values_detected(self) -> None:
        raw = {
            "upgrades": [{
                "name": "Test",
                "levels": [
                    {"coin_cost": 100, "cumulative_effect": "2x", "effect_delta": "0.5x"},
                ],
            }]
        }
        result = validate_raw_json(raw)
        assert not result.ok
        errors_str = " ".join(result.errors)
        assert "cumulative_effect" in errors_str
        assert "effect_delta" in errors_str


class TestSaveUpgrades:
    def test_round_trip(self, test_upgrades: UpgradeDatabase, tmp_path: Path) -> None:
        from src.data_loader import save_upgrades

        out_path = tmp_path / "round_trip.json"
        save_upgrades(test_upgrades, out_path)
        reloaded = load_upgrades(out_path)
        assert len(reloaded.upgrades) == len(test_upgrades.upgrades)
        assert reloaded.version == test_upgrades.version
        for orig, loaded in zip(test_upgrades.upgrades, reloaded.upgrades, strict=True):
            assert orig.id == loaded.id
            assert orig.max_level == loaded.max_level

    def test_creates_parent_dirs(self, test_upgrades: UpgradeDatabase, tmp_path: Path) -> None:
        from src.data_loader import save_upgrades

        deep = tmp_path / "a" / "b" / "c" / "data.json"
        save_upgrades(test_upgrades, deep)
        assert deep.exists()


class TestValidationResult:
    def test_empty_result_is_ok(self) -> None:
        r = ValidationResult()
        assert r.ok

    def test_error_makes_not_ok(self) -> None:
        r = ValidationResult()
        r.error("something broke")
        assert not r.ok
        assert "something broke" in r.summary()

    def test_warning_still_ok(self) -> None:
        r = ValidationResult()
        r.warn("heads up")
        assert r.ok
        assert "heads up" in r.summary()

    def test_all_checks_passed_summary(self) -> None:
        r = ValidationResult()
        assert "All checks passed" in r.summary()
