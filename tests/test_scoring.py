"""Tests for the scoring engines."""

from __future__ import annotations

import pytest

from src.models import Profile, ScoringWeights, UpgradeDatabase
from src.scoring import (
    BalancedEngine,
    PerCategoryEngine,
    ReferenceEngine,
    compute_marginal_score,
)


class TestComputeMarginalScore:
    def test_level_zero(self, test_upgrades: UpgradeDatabase) -> None:
        u = test_upgrades.get_upgrade("damage")
        assert u is not None
        score, cost, cur, nxt, mb = compute_marginal_score(u, 0)
        # damage level 1: cost=50, effect goes 0->5, delta=5
        assert cost == 50
        assert cur == 0  # base_value
        assert nxt == 5
        assert mb == 5
        assert score == pytest.approx(5 / 50)

    def test_mid_level(self, test_upgrades: UpgradeDatabase) -> None:
        u = test_upgrades.get_upgrade("attack_speed")
        assert u is not None
        score, cost, cur, nxt, mb = compute_marginal_score(u, 2)
        # level 2->3: cost=500, effect 1.2->1.3, delta=0.1
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
        assert categories == {"offense", "defense", "economy"}
        assert len(results) == 3

    def test_picks_best_in_category(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = PerCategoryEngine()
        results = engine.rank(test_upgrades, empty_profile)
        # In offense at level 0:
        # attack_speed: 0.1/100 = 0.001
        # damage: 5/50 = 0.1
        # damage has higher score
        offense_pick = [r for r in results if r.category == "offense"][0]
        assert offense_pick.upgrade_id == "damage"

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

    def test_explain(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = PerCategoryEngine()
        results = engine.rank(test_upgrades, empty_profile)
        assert len(results) > 0
        text = engine.explain(results[0])
        assert "→" in text
        assert "coins" in text


class TestBalancedEngine:
    def test_ranks_all_upgrades(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, empty_profile)
        # All 6 upgrades available at level 0
        assert len(results) == 6

    def test_equal_weights_matches_raw_score(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine(ScoringWeights(economy=1.0, offense=1.0, defense=1.0))
        results = engine.rank(test_upgrades, empty_profile)
        # With equal weights, health (10/75=0.1333) has highest score
        assert results[0].upgrade_id == "health"

    def test_zero_weight_excludes_category(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine(ScoringWeights(economy=0.0, offense=1.0, defense=1.0))
        results = engine.rank(test_upgrades, empty_profile)
        economy_results = [r for r in results if r.category == "economy"]
        # Economy upgrades should have zero score and be filtered
        assert all(r.score == 0 for r in economy_results) or len(economy_results) == 0

    def test_high_offense_weight_promotes_offense(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine(ScoringWeights(economy=0.1, offense=2.0, defense=0.1))
        results = engine.rank(test_upgrades, empty_profile)
        # Top result should be offense
        assert results[0].category == "offense"

    def test_deterministic(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
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

    def test_mid_profile(
        self, test_upgrades: UpgradeDatabase, mid_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, mid_profile)
        # All 6 upgrades, but some at mid level (none maxed)
        assert len(results) == 6

    def test_affordable_flag(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        # empty_profile has 10000 coins — all level 1 upgrades should be affordable
        results = engine.rank(test_upgrades, empty_profile)
        for r in results:
            assert r.affordable  # All level-1 costs < 10000

    def test_explain(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, empty_profile)
        text = engine.explain(results[0])
        assert "balanced" in text
        assert "Economy=" in text


class TestReferenceEngine:
    def test_raises_not_implemented(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = ReferenceEngine()
        with pytest.raises(NotImplementedError):
            engine.rank(test_upgrades, empty_profile)

    def test_name_and_version(self) -> None:
        engine = ReferenceEngine()
        assert engine.name == "reference"
        assert engine.version == "0.0"


class TestTieBreaking:
    """Verify deterministic tie-breaking: lower cost first, then alphabetical."""

    def test_same_score_different_cost(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile
    ) -> None:
        engine = BalancedEngine()
        results = engine.rank(test_upgrades, empty_profile)
        # If two upgrades have equal scores, lower cost should come first
        for i in range(len(results) - 1):
            if results[i].score == results[i + 1].score:
                assert results[i].coin_cost <= results[i + 1].coin_cost
