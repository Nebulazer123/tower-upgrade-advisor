"""Tests for the scoring engines."""

from __future__ import annotations

from decimal import Decimal

import pytest

from src.models import Profile, ScoringWeights, UpgradeDatabase
from src.scoring import (
    BalancedEngine,
    PerCategoryEngine,
    ReferenceEngine,
    _DPSState,
    compute_dps,
    compute_marginal_score,
)


class TestComputeMarginalScore:
    def test_level_zero(self, test_upgrades: UpgradeDatabase) -> None:
        u = test_upgrades.get_upgrade("damage")
        assert u is not None
        score, cost, cur, nxt, mb = compute_marginal_score(u, 0)
        assert cost == 50
        assert cur == 0
        assert nxt == 5
        assert mb == 5
        assert score == pytest.approx(5 / 50)

    def test_mid_level(self, test_upgrades: UpgradeDatabase) -> None:
        u = test_upgrades.get_upgrade("attack_speed")
        assert u is not None
        score, cost, cur, nxt, mb = compute_marginal_score(u, 2)
        assert cost == 500
        assert cur == pytest.approx(1.2)
        assert nxt == pytest.approx(1.3)
        assert mb == pytest.approx(0.1)
        assert score == pytest.approx(0.1 / 500)

    def test_max_level(self, test_upgrades: UpgradeDatabase) -> None:
        u = test_upgrades.get_upgrade("damage")
        assert u is not None
        score, cost, cur, nxt, mb = compute_marginal_score(u, 5)
        assert score == 0.0
        assert mb == 0.0

    def test_beyond_max_level(self, test_upgrades: UpgradeDatabase) -> None:
        u = test_upgrades.get_upgrade("damage")
        assert u is not None
        score, cost, cur, nxt, mb = compute_marginal_score(u, 99)
        assert score == 0.0


class TestPerCategoryEngine:
    def test_returns_one_per_category(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = PerCategoryEngine()
        results = engine.rank(test_upgrades, empty_profile)
        categories = {r.category for r in results}
        assert categories == {"attack", "defense", "utility"}
        assert len(results) == 3

    def test_picks_best_in_category(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = PerCategoryEngine()
        results = engine.rank(test_upgrades, empty_profile)
        # In attack at level 0:
        # attack_speed: 0.1/100 = 0.001
        # damage: 5/50 = 0.1
        # crit_chance: 5/80 = 0.0625
        # crit_factor: 0.1/100 = 0.001
        # damage has highest score
        attack_pick = [r for r in results if r.category == "attack"][0]
        assert attack_pick.upgrade_id == "damage"

    def test_maxed_category_omitted(
        self, test_upgrades: UpgradeDatabase, maxed_profile: Profile
    ) -> None:
        engine = PerCategoryEngine()
        results = engine.rank(test_upgrades, maxed_profile)
        assert len(results) == 0

    def test_name_and_version(self) -> None:
        engine = PerCategoryEngine()
        assert engine.name == "per_category_best"
        assert engine.version == "1.0"

    def test_explain(self, test_upgrades: UpgradeDatabase, empty_profile: Profile) -> None:
        engine = PerCategoryEngine()
        results = engine.rank(test_upgrades, empty_profile)
        assert len(results) > 0
        text = engine.explain(results[0])
        assert "\u2192" in text
        assert "coins" in text


class TestBalancedEngine:
    def test_ranks_all_upgrades(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, empty_profile)
        assert len(results) == 8

    def test_equal_weights_matches_raw_score(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine(ScoringWeights(attack=1.0, defense=1.0, utility=1.0))
        results = engine.rank(test_upgrades, empty_profile)
        # health: 10/75=0.1333 is highest
        assert results[0].upgrade_id == "health"

    def test_zero_weight_excludes_category(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine(ScoringWeights(attack=1.0, defense=1.0, utility=0.0))
        results = engine.rank(test_upgrades, empty_profile)
        utility_results = [r for r in results if r.category == "utility"]
        assert all(r.score == 0 for r in utility_results) or len(utility_results) == 0

    def test_high_attack_weight_promotes_attack(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine(ScoringWeights(attack=2.0, defense=0.1, utility=0.1))
        results = engine.rank(test_upgrades, empty_profile)
        assert results[0].category == "attack"

    def test_deterministic(self, test_upgrades: UpgradeDatabase, empty_profile: Profile) -> None:
        engine = BalancedEngine()
        r1 = engine.rank(test_upgrades, empty_profile)
        r2 = engine.rank(test_upgrades, empty_profile)
        assert [r.upgrade_id for r in r1] == [r.upgrade_id for r in r2]
        assert [r.score for r in r1] == [r.score for r in r2]

    def test_maxed_upgrades_excluded(
        self, test_upgrades: UpgradeDatabase, maxed_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, maxed_profile)
        assert len(results) == 0

    def test_mid_profile(self, test_upgrades: UpgradeDatabase, mid_profile: Profile) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, mid_profile)
        assert len(results) == 8

    def test_affordable_flag(self, test_upgrades: UpgradeDatabase, empty_profile: Profile) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, empty_profile)
        for r in results:
            assert r.affordable

    def test_explain(self, test_upgrades: UpgradeDatabase, empty_profile: Profile) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, empty_profile)
        text = engine.explain(results[0])
        assert "balanced" in text
        assert "Attack=" in text


class TestComputeDPS:
    """Test the DPS formula ported from the reference calculator."""

    def test_base_dps_zero_damage(self) -> None:
        state = _DPSState.__new__(_DPSState)
        state.damage = 0.0
        state.attack_speed = 1.0
        state.crit_chance = 0.0
        state.crit_factor = 1.2
        state.multishot_chance = 0.0
        state.multishot_targets = 2.0
        state.rapid_fire_chance = 0.0
        state.bounce_chance = 0.0
        state.bounce_targets = 1.0
        assert compute_dps(state) == Decimal(0)

    def test_simple_dps(self) -> None:
        state = _DPSState.__new__(_DPSState)
        state.damage = 10.0
        state.attack_speed = 1.0
        state.crit_chance = 0.0
        state.crit_factor = 1.2
        state.multishot_chance = 0.0
        state.multishot_targets = 2.0
        state.rapid_fire_chance = 0.0
        state.bounce_chance = 0.0
        state.bounce_targets = 1.0
        dps = compute_dps(state)
        # All chance stats are 0 => mults = 1.0, no rapid fire
        # DPS = 10 * 1.0 * 1.0 * 1.0 * 1.0 = 10
        assert float(dps) == pytest.approx(10.0)

    def test_crit_multiplier(self) -> None:
        state = _DPSState.__new__(_DPSState)
        state.damage = 10.0
        state.attack_speed = 1.0
        state.crit_chance = 50.0
        state.crit_factor = 2.0
        state.multishot_chance = 0.0
        state.multishot_targets = 2.0
        state.rapid_fire_chance = 0.0
        state.bounce_chance = 0.0
        state.bounce_targets = 1.0
        dps = compute_dps(state)
        # crit_mult = 1 - 0.5 + 0.5 * 2.0 = 1.5
        # DPS = 10 * 1.0 * 1.5 * 1.0 * 1.0 = 15
        assert float(dps) == pytest.approx(15.0)

    def test_multishot_multiplier(self) -> None:
        state = _DPSState.__new__(_DPSState)
        state.damage = 10.0
        state.attack_speed = 2.0
        state.crit_chance = 0.0
        state.crit_factor = 1.2
        state.multishot_chance = 100.0
        state.multishot_targets = 3.0
        state.rapid_fire_chance = 0.0
        state.bounce_chance = 0.0
        state.bounce_targets = 1.0
        dps = compute_dps(state)
        # ms_mult = 1 - 1.0 + 1.0 * 3.0 = 3.0
        # DPS = 10 * 2.0 * 1.0 * 3.0 * 1.0 = 60
        assert float(dps) == pytest.approx(60.0)

    def test_bounce_multiplier(self) -> None:
        state = _DPSState.__new__(_DPSState)
        state.damage = 10.0
        state.attack_speed = 1.0
        state.crit_chance = 0.0
        state.crit_factor = 1.2
        state.multishot_chance = 0.0
        state.multishot_targets = 2.0
        state.rapid_fire_chance = 0.0
        state.bounce_chance = 50.0
        state.bounce_targets = 4.0
        dps = compute_dps(state)
        # bounce_mult = 1 - 0.5 + 0.5 * 4.0 = 2.5
        # DPS = 10 * 1.0 * 1.0 * 1.0 * 2.5 = 25
        assert float(dps) == pytest.approx(25.0)

    def test_rapid_fire(self) -> None:
        state = _DPSState.__new__(_DPSState)
        state.damage = 10.0
        state.attack_speed = 2.0
        state.crit_chance = 0.0
        state.crit_factor = 1.2
        state.multishot_chance = 0.0
        state.multishot_targets = 2.0
        state.rapid_fire_chance = 50.0
        state.bounce_chance = 0.0
        state.bounce_targets = 1.0
        dps = compute_dps(state)
        # avg_time_between_procs = (1/2) * (100/50) = 1.0
        # avg_increase = (4 * 1) / (1 + 1) = 2.0
        # attack_speed_final = 2.0 * (1 + 2.0/100) = 2.04
        # DPS = 10 * 2.04 * 1.0 * 1.0 * 1.0 = 20.4
        assert float(dps) == pytest.approx(20.4)


class TestReferenceEngine:
    def test_name_and_version(self) -> None:
        engine = ReferenceEngine()
        assert engine.name == "reference"
        assert engine.version == "1.0"

    def test_ranks_attack_upgrades_by_dps(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = ReferenceEngine()
        results = engine.rank(test_upgrades, empty_profile)
        attack_results = [r for r in results if r.category == "attack"]
        assert len(attack_results) > 0
        for r in attack_results:
            assert r.scoring_method == "reference"

    def test_includes_defense_and_utility(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = ReferenceEngine()
        results = engine.rank(test_upgrades, empty_profile)
        categories = {r.category for r in results}
        assert "defense" in categories
        assert "utility" in categories

    def test_maxed_excluded(self, test_upgrades: UpgradeDatabase, maxed_profile: Profile) -> None:
        engine = ReferenceEngine()
        results = engine.rank(test_upgrades, maxed_profile)
        assert len(results) == 0

    def test_explain(self, test_upgrades: UpgradeDatabase, empty_profile: Profile) -> None:
        engine = ReferenceEngine()
        results = engine.rank(test_upgrades, empty_profile)
        assert len(results) > 0
        text = engine.explain(results[0])
        assert "reference" in text

    def test_dps_efficiency_ordering(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = ReferenceEngine()
        results = engine.rank(test_upgrades, empty_profile)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)


class TestTieBreaking:
    """Verify deterministic tie-breaking: lower cost first, then alphabetical."""

    def test_same_score_different_cost(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, empty_profile)
        for i in range(len(results) - 1):
            if results[i].score == results[i + 1].score:
                assert results[i].coin_cost <= results[i + 1].coin_cost
