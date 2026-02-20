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
        assert len(db.upgrades) == 8

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
        cat_warnings = [w for w in result.warnings if "Missing expected category" in w]
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
        assert not result.ok


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
                    "levels": [{"coin_cost": "1.2M", "cumulative_effect": 1, "effect_delta": 1}],
                }
            ]
        }
        result = validate_raw_json(raw)
        assert not result.ok
        assert any("string value" in e for e in result.errors)

    def test_non_dict_rejected(self) -> None:
        result = validate_raw_json([])
        assert not result.ok


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
