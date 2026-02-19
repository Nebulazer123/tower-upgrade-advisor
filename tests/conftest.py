"""Shared pytest fixtures for Tower Upgrade Advisor tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.models import Profile, ScoringWeights, UpgradeDatabase

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def test_upgrades_path() -> Path:
    return FIXTURES_DIR / "test_upgrades.json"


@pytest.fixture
def test_upgrades(test_upgrades_path: Path) -> UpgradeDatabase:
    raw = json.loads(test_upgrades_path.read_text(encoding="utf-8"))
    return UpgradeDatabase.model_validate(raw)


@pytest.fixture
def empty_profile() -> Profile:
    """Profile with all upgrades at level 0, 10000 coins."""
    now = datetime.now(UTC)
    return Profile(
        id="test-empty",
        name="Test Empty",
        created_at=now,
        updated_at=now,
        available_coins=10000,
        levels={},
        weights=ScoringWeights(),
    )


@pytest.fixture
def mid_profile() -> Profile:
    """Profile with some upgrades at mid levels."""
    now = datetime.now(UTC)
    return Profile(
        id="test-mid",
        name="Test Mid",
        created_at=now,
        updated_at=now,
        available_coins=5000,
        levels={
            "attack_speed": 2,
            "damage": 3,
            "health": 1,
            "coins_per_kill": 2,
        },
        weights=ScoringWeights(),
    )


@pytest.fixture
def maxed_profile() -> Profile:
    """Profile with all upgrades at max level."""
    now = datetime.now(UTC)
    return Profile(
        id="test-maxed",
        name="Test Maxed",
        created_at=now,
        updated_at=now,
        available_coins=0,
        levels={
            "attack_speed": 5,
            "damage": 5,
            "health": 5,
            "health_regen": 5,
            "coins_per_kill": 5,
            "interest": 5,
        },
        weights=ScoringWeights(),
    )


@pytest.fixture
def offense_weighted_profile() -> Profile:
    """Profile with heavy offense weights."""
    now = datetime.now(UTC)
    return Profile(
        id="test-offense",
        name="Test Offense",
        created_at=now,
        updated_at=now,
        available_coins=10000,
        levels={},
        weights=ScoringWeights(economy=0.5, offense=2.0, defense=0.5),
    )


@pytest.fixture
def tmp_profiles_dir(tmp_path: Path) -> Path:
    """Temporary directory for profile tests."""
    d = tmp_path / "profiles"
    d.mkdir()
    return d
