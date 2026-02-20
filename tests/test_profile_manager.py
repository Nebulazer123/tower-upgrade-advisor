"""Tests for the profile manager."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.models import ScoringWeights
from src.profile_manager import ProfileManager


class TestProfileCRUD:
    def test_create_profile(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("My Build")
        assert p.name == "My Build"
        assert p.id
        assert p.available_coins == 0
        assert p.levels == {}

    def test_get_profile(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        created = pm.create_profile("Test")
        loaded = pm.get_profile(created.id)
        assert loaded is not None
        assert loaded.id == created.id
        assert loaded.name == "Test"

    def test_get_missing_profile(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        assert pm.get_profile("nonexistent-id") is None

    def test_list_profiles(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        pm.create_profile("Bravo")
        pm.create_profile("Alpha")
        profiles = pm.list_profiles()
        assert len(profiles) == 2
        assert profiles[0].name == "Alpha"  # sorted by name
        assert profiles[1].name == "Bravo"

    def test_delete_profile(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("ToDelete")
        assert pm.delete_profile(p.id)
        assert pm.get_profile(p.id) is None
        assert not pm.delete_profile(p.id)  # already deleted

    def test_duplicate_profile(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        orig = pm.create_profile("Original")
        pm.update_level(orig.id, "damage", 3)
        copy = pm.duplicate_profile(orig.id, "Copy")
        assert copy is not None
        assert copy.id != orig.id
        assert copy.name == "Copy"
        assert copy.levels.get("damage") == 3


class TestProfileUpdates:
    def test_update_level(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("Test")
        updated = pm.update_level(p.id, "attack_speed", 3)
        assert updated is not None
        assert updated.levels["attack_speed"] == 3

    def test_update_level_to_zero_removes(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("Test")
        pm.update_level(p.id, "attack_speed", 3)
        updated = pm.update_level(p.id, "attack_speed", 0)
        assert updated is not None
        assert "attack_speed" not in updated.levels

    def test_update_level_negative_raises(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("Test")
        with pytest.raises(ValueError, match=">= 0"):
            pm.update_level(p.id, "attack_speed", -1)

    def test_update_coins(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("Test")
        updated = pm.update_coins(p.id, 5000)
        assert updated is not None
        assert updated.available_coins == 5000

    def test_update_coins_negative_raises(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("Test")
        with pytest.raises(ValueError, match=">= 0"):
            pm.update_coins(p.id, -100)

    def test_update_weights(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("Test")
        new_weights = ScoringWeights(attack=2.0, defense=1.5, utility=0.5)
        updated = pm.update_weights(p.id, new_weights)
        assert updated is not None
        assert updated.weights.attack == 2.0


class TestProfilePersistence:
    def test_save_and_reload(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("Persist")
        pm.update_level(p.id, "damage", 5)
        pm.update_coins(p.id, 9999)

        # Create new manager — forces reload from disk
        pm2 = ProfileManager(tmp_profiles_dir)
        loaded = pm2.get_profile(p.id)
        assert loaded is not None
        assert loaded.levels["damage"] == 5
        assert loaded.available_coins == 9999

    def test_corrupt_file_skipped(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        pm.create_profile("Good")
        # Write a corrupt file
        bad_path = tmp_profiles_dir / "corrupt.json"
        bad_path.write_text("not valid json", encoding="utf-8")
        profiles = pm.list_profiles()
        assert len(profiles) == 1  # corrupt file skipped
        assert profiles[0].name == "Good"

    def test_backup(self, tmp_profiles_dir: Path) -> None:
        pm = ProfileManager(tmp_profiles_dir)
        p = pm.create_profile("Backup Test")
        backup_path = pm.backup_profile(p.id)
        assert backup_path is not None
        assert backup_path.exists()
