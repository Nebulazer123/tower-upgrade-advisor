"""Profile management: CRUD operations with atomic file writes."""

from __future__ import annotations

import json
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from src.models import Profile, ScoringWeights

__all__ = [
    "ProfileManager",
    "PROFILES_DIR",
]

PROFILES_DIR = Path(__file__).resolve().parent.parent / "data" / "profiles"


class ProfileManager:
    """Manages user profiles stored as individual JSON files.

    Each profile is stored as `{profiles_dir}/{profile_id}.json`.
    Writes are atomic (write to .tmp, rename) to prevent corruption.
    """

    def __init__(self, profiles_dir: Path | None = None) -> None:
        self.profiles_dir = profiles_dir or PROFILES_DIR
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, profile_id: str) -> Path:
        return self.profiles_dir / f"{profile_id}.json"

    def list_profiles(self) -> list[Profile]:
        """Return all profiles, sorted by name."""
        profiles: list[Profile] = []
        for p in sorted(self.profiles_dir.glob("*.json")):
            if p.name.startswith("."):
                continue
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                profiles.append(Profile.model_validate(raw))
            except (json.JSONDecodeError, ValidationError):
                # Skip corrupt profiles, don't crash
                continue
        profiles.sort(key=lambda p: p.name.lower())
        return profiles

    def get_profile(self, profile_id: str) -> Profile | None:
        """Load a single profile by ID. Returns None if not found."""
        path = self._path_for(profile_id)
        if not path.exists():
            return None
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return Profile.model_validate(raw)
        except (json.JSONDecodeError, ValidationError):
            return None

    def create_profile(self, name: str) -> Profile:
        """Create a new profile with the given name and default values."""
        now = datetime.now(UTC)
        profile = Profile(
            id=str(uuid.uuid4()),
            name=name.strip(),
            created_at=now,
            updated_at=now,
            available_coins=0,
            levels={},
            weights=ScoringWeights(),
        )
        self._save(profile)
        return profile

    def save_profile(self, profile: Profile) -> Profile:
        """Save an existing profile, updating the timestamp."""
        updated = profile.model_copy(update={"updated_at": datetime.now(UTC)})
        self._save(updated)
        return updated

    def delete_profile(self, profile_id: str) -> bool:
        """Delete a profile. Returns True if deleted, False if not found."""
        path = self._path_for(profile_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def duplicate_profile(self, profile_id: str, new_name: str) -> Profile | None:
        """Duplicate a profile with a new name and ID."""
        original = self.get_profile(profile_id)
        if original is None:
            return None

        now = datetime.now(UTC)
        copy = original.model_copy(
            update={
                "id": str(uuid.uuid4()),
                "name": new_name.strip(),
                "created_at": now,
                "updated_at": now,
            }
        )
        self._save(copy)
        return copy

    def update_level(self, profile_id: str, upgrade_id: str, level: int) -> Profile | None:
        """Update a single upgrade level in a profile."""
        profile = self.get_profile(profile_id)
        if profile is None:
            return None

        if level < 0:
            raise ValueError(f"Level must be >= 0, got {level}")

        new_levels = dict(profile.levels)
        if level == 0:
            new_levels.pop(upgrade_id, None)
        else:
            new_levels[upgrade_id] = level

        updated = profile.model_copy(
            update={
                "levels": new_levels,
                "updated_at": datetime.now(UTC),
            }
        )
        self._save(updated)
        return updated

    def update_coins(self, profile_id: str, coins: int) -> Profile | None:
        """Update available coins for a profile."""
        profile = self.get_profile(profile_id)
        if profile is None:
            return None

        if coins < 0:
            raise ValueError(f"Coins must be >= 0, got {coins}")

        updated = profile.model_copy(
            update={
                "available_coins": coins,
                "updated_at": datetime.now(UTC),
            }
        )
        self._save(updated)
        return updated

    def update_weights(self, profile_id: str, weights: ScoringWeights) -> Profile | None:
        """Update scoring weights for a profile."""
        profile = self.get_profile(profile_id)
        if profile is None:
            return None

        updated = profile.model_copy(
            update={
                "weights": weights,
                "updated_at": datetime.now(UTC),
            }
        )
        self._save(updated)
        return updated

    def backup_profile(self, profile_id: str) -> Path | None:
        """Create a timestamped backup of a profile."""
        path = self._path_for(profile_id)
        if not path.exists():
            return None

        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_dir = self.profiles_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        backup_path = backup_dir / f"{profile_id}_{ts}.json"
        shutil.copy2(path, backup_path)
        return backup_path

    def _save(self, profile: Profile) -> None:
        """Atomic write: write to .tmp then rename."""
        path = self._path_for(profile.id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            profile.model_dump_json(indent=2),
            encoding="utf-8",
        )
        tmp.rename(path)
