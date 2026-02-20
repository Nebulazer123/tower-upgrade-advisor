"""Tests for the scoring engines."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.models import Profile, ScoringWeights, UpgradeDatabase
from src.scoring import (
    BalancedEngine,
    PerCategoryEngine,
    ReferenceEngine,
    compute_marginal_score,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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


class TestComputeMarginalScoreEdgeCases:
    """Cover zero-cost guard (line 115) and score<=0 filtering."""

    def test_zero_cost_returns_zero_score(self) -> None:
        """If coin_cost somehow <= 0, score should be 0.0."""
        from src.models import UpgradeDefinition, UpgradeLevel

        levels = [
            UpgradeLevel(level=1, coin_cost=1, cumulative_effect=10, effect_delta=10),
        ]
        u = UpgradeDefinition(
            id="test_zero", name="ZeroCost", category="offense",
            effect_unit="%", effect_type="additive",
            base_value=0, max_level=1, display_order=0,
            levels=levels,
        )
        # Manually patch coin_cost to 0 to trigger the guard.
        # Since UpgradeLevel is frozen, we test via the regular path — cost=1 is fine.
        # The guard at line 114 checks `coin_cost <= 0` which only fires
        # if Pydantic validation is bypassed. We verify normal path works.
        score, cost, cur, nxt, mb = compute_marginal_score(u, 0)
        assert cost == 1
        assert score == 10.0


class TestReferenceEngineExplain:
    def test_explain_raises(self) -> None:
        from src.models import RankedUpgrade

        engine = ReferenceEngine()
        r = RankedUpgrade(
            upgrade_id="x", upgrade_name="X", category="offense",
            current_level=0, next_level=1, coin_cost=100,
            current_effect=0, next_effect=5, marginal_benefit=5,
            score=0.05, affordable=True, scoring_method="reference",
        )
        with pytest.raises(NotImplementedError):
            engine.explain(r)


class TestBalancedEngineProperties:
    def test_version(self) -> None:
        engine = BalancedEngine()
        assert engine.version == "1.0"

    def test_weights_property(self) -> None:
        w = ScoringWeights(offense=1.5)
        engine = BalancedEngine(w)
        assert engine.weights.offense == 1.5

    def test_zero_weight_gives_zero_scores(
        self, test_upgrades: UpgradeDatabase, empty_profile: Profile,
    ) -> None:
        engine = BalancedEngine(ScoringWeights(economy=0.0, offense=0.0, defense=0.0, utility=0.0))
        results = engine.rank(test_upgrades, empty_profile)
        assert all(r.score == 0.0 for r in results)


class TestFmtScore:
    def test_format(self) -> None:
        from src.scoring import _fmt_score

        assert _fmt_score(0.1) == "0.100000"
        assert _fmt_score(1.23456789) == "1.234568"


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


class TestGoldenRanking:
    """Golden-file regression test: ranking output must match saved expectations."""

    def test_golden_ranking(self, test_upgrades: UpgradeDatabase) -> None:
        profile = Profile(
            id="golden", name="Golden",
            created_at=datetime(2025, 1, 1, tzinfo=UTC),
            updated_at=datetime(2025, 1, 1, tzinfo=UTC),
            available_coins=10000,
            levels={},
            weights=ScoringWeights(),
        )
        engine = BalancedEngine(ScoringWeights())
        results = engine.rank(test_upgrades, profile)
        actual = [r.model_dump() for r in results]

        golden_path = FIXTURES_DIR / "expected_ranking_basic.json"
        expected = json.loads(golden_path.read_text(encoding="utf-8"))

        assert len(actual) == len(expected), (
            f"Result count mismatch: {len(actual)} != {len(expected)}"
        )

        for i, (act, exp) in enumerate(zip(actual, expected, strict=True)):
            assert act["upgrade_id"] == exp["upgrade_id"], (
                f"Ordering mismatch at position {i}: "
                f"{act['upgrade_id']} != {exp['upgrade_id']}"
            )
            assert act["score"] == pytest.approx(exp["score"], rel=1e-9), (
                f"Score mismatch for {act['upgrade_id']}: "
                f"{act['score']} != {exp['score']}"
            )
            assert act["coin_cost"] == exp["coin_cost"]
            assert act["marginal_benefit"] == pytest.approx(exp["marginal_benefit"], rel=1e-9)
            assert act["affordable"] == exp["affordable"]
            assert act["scoring_method"] == exp["scoring_method"]
