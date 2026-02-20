"""End-to-end integration tests for the Tower Upgrade Advisor pipeline."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.data_loader import load_upgrades, save_upgrades, validate_upgrade_data
from src.models import Profile, RankedUpgrade, ScoringWeights, UpgradeDatabase
from src.profile_manager import ProfileManager
from src.scoring import BalancedEngine, PerCategoryEngine


@pytest.mark.integration
class TestEndToEndPipeline:
    """Integration tests that exercise the full load → profile → score pipeline."""

    # ------------------------------------------------------------------
    # 1. Per-category scoring returns one result per category
    # ------------------------------------------------------------------

    def test_load_and_score_per_category(
        self, test_upgrades: UpgradeDatabase, tmp_profiles_dir: Path
    ) -> None:
        pm = ProfileManager(profiles_dir=tmp_profiles_dir)
        profile = pm.create_profile("integration-per-cat")

        profile = profile.model_copy(update={"available_coins": 10_000})

        engine = PerCategoryEngine()
        results = engine.rank(test_upgrades, profile)

        assert isinstance(results, list)
        assert all(isinstance(r, RankedUpgrade) for r in results)

        categories_in_data = {u.category for u in test_upgrades.upgrades}
        result_categories = {r.category for r in results}
        assert result_categories == categories_in_data

        for r in results:
            assert r.score > 0
            assert r.upgrade_id
            assert r.upgrade_name
            assert r.category
            assert r.coin_cost > 0
            assert r.next_level == r.current_level + 1
            assert r.scoring_method == "per_category_best"

    # ------------------------------------------------------------------
    # 2. Balanced scoring returns sorted ranked list
    # ------------------------------------------------------------------

    def test_load_and_score_balanced(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, empty_profile)

        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, RankedUpgrade) for r in results)

        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

        for r in results:
            assert r.upgrade_id
            assert r.upgrade_name
            assert r.category
            assert r.coin_cost > 0
            assert r.score > 0
            assert r.scoring_method == "balanced"

    # ------------------------------------------------------------------
    # 3. Different weights produce different rankings
    # ------------------------------------------------------------------

    def test_weighted_scoring_changes_ranking(
        self,
        test_upgrades: UpgradeDatabase,
        empty_profile: Profile,
        offense_weighted_profile: Profile,
    ) -> None:
        engine_default = BalancedEngine(weights=ScoringWeights())
        engine_offense = BalancedEngine(
            weights=offense_weighted_profile.weights,
        )

        results_default = engine_default.rank(test_upgrades, empty_profile)
        results_offense = engine_offense.rank(test_upgrades, empty_profile)

        ids_default = [r.upgrade_id for r in results_default]
        ids_offense = [r.upgrade_id for r in results_offense]

        assert ids_default != ids_offense, (
            "Offense-heavy weights should reorder upgrades relative to equal weights"
        )

    # ------------------------------------------------------------------
    # 4. Profile CRUD → scoring reflects updated levels
    # ------------------------------------------------------------------

    def test_profile_crud_and_score(
        self, test_upgrades: UpgradeDatabase, tmp_profiles_dir: Path
    ) -> None:
        pm = ProfileManager(profiles_dir=tmp_profiles_dir)
        profile = pm.create_profile("crud-test")

        engine = BalancedEngine()
        initial_results = engine.rank(test_upgrades, profile)
        assert len(initial_results) > 0

        pm.update_level(profile.id, "attack_speed", 3)
        pm.update_coins(profile.id, 50_000)
        updated = pm.get_profile(profile.id)
        assert updated is not None
        assert updated.get_level("attack_speed") == 3
        assert updated.available_coins == 50_000

        updated_results = engine.rank(test_upgrades, updated)

        atk_initial = next(
            (r for r in initial_results if r.upgrade_id == "attack_speed"), None,
        )
        atk_updated = next(
            (r for r in updated_results if r.upgrade_id == "attack_speed"), None,
        )

        assert atk_initial is not None
        assert atk_updated is not None
        assert atk_updated.current_level == 3
        assert atk_updated.next_level == 4
        assert atk_initial.current_level == 0
        assert atk_initial.next_level == 1

    # ------------------------------------------------------------------
    # 5. Maxed profile → empty results
    # ------------------------------------------------------------------

    def test_maxed_profile_empty_results(
        self, test_upgrades: UpgradeDatabase, maxed_profile: Profile
    ) -> None:
        engine_per_cat = PerCategoryEngine()
        engine_balanced = BalancedEngine()

        assert engine_per_cat.rank(test_upgrades, maxed_profile) == []
        assert engine_balanced.rank(test_upgrades, maxed_profile) == []

    # ------------------------------------------------------------------
    # 6. Data round-trip: save → reload → identical
    # ------------------------------------------------------------------

    def test_data_round_trip(
        self, test_upgrades: UpgradeDatabase, tmp_path: Path
    ) -> None:
        out = tmp_path / "round_trip.json"
        save_upgrades(test_upgrades, out)

        reloaded = load_upgrades(out)

        assert reloaded.version == test_upgrades.version
        assert reloaded.game_version == test_upgrades.game_version
        assert reloaded.source == test_upgrades.source
        assert len(reloaded.upgrades) == len(test_upgrades.upgrades)

        for orig, loaded in zip(test_upgrades.upgrades, reloaded.upgrades, strict=True):
            assert orig.id == loaded.id
            assert orig.name == loaded.name
            assert orig.category == loaded.category
            assert orig.max_level == loaded.max_level
            assert orig.base_value == loaded.base_value
            assert len(orig.levels) == len(loaded.levels)
            for ol, ll in zip(orig.levels, loaded.levels, strict=True):
                assert ol.level == ll.level
                assert ol.coin_cost == ll.coin_cost
                assert ol.cumulative_effect == ll.cumulative_effect
                assert ol.effect_delta == ll.effect_delta

        vr = validate_upgrade_data(reloaded)
        assert vr.ok

    # ------------------------------------------------------------------
    # 7. Scoring is deterministic across 100 runs
    # ------------------------------------------------------------------

    def test_scoring_determinism(
        self, test_upgrades: UpgradeDatabase, mid_profile: Profile
    ) -> None:
        engine = BalancedEngine()

        reference = engine.rank(test_upgrades, mid_profile)
        ref_tuples = [
            (r.upgrade_id, r.score, r.coin_cost, r.marginal_benefit)
            for r in reference
        ]

        for _ in range(99):
            run = engine.rank(test_upgrades, mid_profile)
            run_tuples = [
                (r.upgrade_id, r.score, r.coin_cost, r.marginal_benefit)
                for r in run
            ]
            assert run_tuples == ref_tuples
