"""Tower Upgrade Advisor — Flask web application."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, url_for
from werkzeug.wrappers import Response

from src.data_loader import load_lab_research, load_upgrades
from src.models import (
    LabResearchDatabase,
    Profile,
    RankedUpgrade,
    ScoringWeights,
    UpgradeDatabase,
    UpgradeDefinition,
    UpgradeLevel,
)
from src.profile_manager import ProfileManager
from src.reference_coverage import CoverageReport, compute_coverage
from src.scoring import BalancedEngine, ReferenceEngine

app = Flask(__name__)
REFERENCE_LINKS = {
    "lab": "https://tower-lab-calculator.netlify.app/",
    "workshop": "https://tower-workshop-calculator.netlify.app/",
    "dps_source": "https://github.com/jacoelt/tower-calculator",
}

# ---------------------------------------------------------------------------
# Startup: load game data and initialise services
# ---------------------------------------------------------------------------

_upgrades: UpgradeDatabase = load_upgrades()
_lab_research: LabResearchDatabase = load_lab_research()
_coverage: CoverageReport = compute_coverage(_upgrades)


def _profile_storage_dir() -> Path | None:
    """Use ephemeral storage on Vercel so local profile files are never deployed."""
    if os.getenv("VERCEL"):
        return Path("/tmp/tower-upgrade-advisor/profiles")
    return None


_profiles = ProfileManager(_profile_storage_dir())
UpgradeRow = dict[str, object]
ProfileSummary = dict[str, int]
RecommendationSummary = dict[str, int]


def _get_categories() -> list[str]:
    """Return ordered unique categories from upgrade data."""
    seen: set[str] = set()
    cats: list[str] = []
    for u in sorted(_upgrades.upgrades, key=lambda x: x.display_order):
        if u.category not in seen:
            seen.add(u.category)
            cats.append(u.category)
    return cats


def _form_int(name: str, default: int = 0) -> int:
    value = request.form.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _form_float(name: str, default: float = 1.0) -> float:
    value = request.form.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _query_int(name: str, default: int = 1) -> int:
    value = request.args.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _clamp_level(level: int, upgrade: UpgradeDefinition) -> int:
    return max(0, min(level, upgrade.max_level))


def _build_upgrade_row(upgrade: UpgradeDefinition, profile: Profile) -> UpgradeRow:
    current_level = _clamp_level(profile.get_level(upgrade.id), upgrade)
    maxed = current_level >= upgrade.max_level
    current_effect = (
        upgrade.base_value
        if current_level == 0
        else upgrade.levels[current_level - 1].cumulative_effect
    )
    next_cost = None
    next_delta = None
    if not maxed:
        next_level = upgrade.levels[current_level]
        next_cost = next_level.coin_cost
        next_delta = next_level.effect_delta

    return {
        "upgrade": upgrade,
        "current_level": current_level,
        "current_effect": current_effect,
        "maxed": maxed,
        "next_cost": next_cost,
        "next_delta": next_delta,
    }


def _recommendation_context(
    profile: Profile,
) -> tuple[BalancedEngine, RankedUpgrade | None, list[RankedUpgrade], list[RankedUpgrade]]:
    engine = BalancedEngine(profile.weights)
    ranked = engine.rank(_upgrades, profile)
    top = ranked[0] if ranked else None
    alternatives = ranked[1:11] if len(ranked) > 1 else []
    return engine, top, alternatives, ranked


def _reference_context(profile: Profile) -> tuple[ReferenceEngine, RankedUpgrade | None]:
    engine = ReferenceEngine(_lab_research)
    ranked = engine.rank(_upgrades, profile)
    return engine, ranked[0] if ranked else None


def _profile_summary(profile: Profile) -> ProfileSummary:
    rows = [_build_upgrade_row(upgrade, profile) for upgrade in _upgrades.upgrades]
    active = sum(
        1 for row in rows if isinstance(row["current_level"], int) and row["current_level"] > 0
    )
    maxed = sum(1 for row in rows if row["maxed"])
    affordable_next = sum(
        1
        for row in rows
        if isinstance(row["next_cost"], int) and row["next_cost"] <= profile.available_coins
    )
    return {
        "total": len(rows),
        "active": active,
        "maxed": maxed,
        "affordable_next": affordable_next,
    }


def _recommendation_summary(
    ranked: list[RankedUpgrade],
    alternatives: list[RankedUpgrade],
) -> RecommendationSummary:
    candidates = ranked[: len(alternatives) + 1]
    return {
        "ranked": len(ranked),
        "shown": len(candidates),
        "affordable": sum(1 for row in candidates if row.affordable),
    }


@app.context_processor
def _shared_template_context() -> dict[str, object]:
    return {
        "reference_links": REFERENCE_LINKS,
        "data_coverage": _coverage,
    }


# ---------------------------------------------------------------------------
# Jinja2 helpers
# ---------------------------------------------------------------------------


@app.template_filter("commas")
def _commas_filter(value: int | float) -> str:
    if isinstance(value, float):
        if value == int(value):
            return f"{int(value):,}"
        return f"{value:,.2f}"
    return f"{value:,}"


@app.template_filter("score_fmt")
def _score_filter(value: float) -> str:
    if value == 0:
        return "0"
    if abs(value) >= 0.01:
        return f"{value:.3f}"
    return f"{value:.2e}"


@app.template_filter("iso_datetime")
def _iso_datetime_filter(value: datetime) -> str:
    return value.isoformat()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


PAGES_PER_LEVEL_TABLE: int = 50


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/data")
def data() -> str:
    """Data tab: view all upgrade levels per category (reference, no profile)."""
    categories = _get_categories()
    selected_category = request.args.get("category", categories[0] if categories else "")
    if selected_category not in categories:
        selected_category = categories[0] if categories else ""

    upgrades: list[UpgradeDefinition] = sorted(
        _upgrades.get_by_category(selected_category),
        key=lambda u: u.display_order,
    )
    selected_upgrade_id = request.args.get("upgrade", "")
    upgrade = next((u for u in upgrades if u.id == selected_upgrade_id), None)
    if upgrade is None and upgrades:
        upgrade = upgrades[0]
        selected_upgrade_id = upgrade.id

    levels_page: list[UpgradeLevel] = []
    total_pages = 1
    page = 1
    if upgrade:
        page = max(1, _query_int("page", 1))
        total_levels = len(upgrade.levels)
        total_pages = max(1, (total_levels + PAGES_PER_LEVEL_TABLE - 1) // PAGES_PER_LEVEL_TABLE)
        page = min(page, total_pages)
        start = (page - 1) * PAGES_PER_LEVEL_TABLE
        end = start + PAGES_PER_LEVEL_TABLE
        levels_page = upgrade.levels[start:end]

    return render_template(
        "data.html",
        categories=categories,
        selected_category=selected_category,
        upgrades=upgrades,
        selected_upgrade_id=selected_upgrade_id,
        upgrade=upgrade,
        levels_page=levels_page,
        page=page,
        total_pages=total_pages,
    )


@app.get("/")
def index() -> str:
    profiles = _profiles.list_profiles()
    return render_template("index.html", profiles=profiles, upgrade_count=len(_upgrades.upgrades))


@app.post("/profile/new")
def profile_new() -> Response:
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("index"))
    profile = _profiles.create_profile(name)
    return redirect(url_for("dashboard", profile_id=profile.id))


@app.post("/profile/<profile_id>/delete")
def profile_delete(profile_id: str) -> Response:
    _profiles.delete_profile(profile_id)
    return redirect(url_for("index"))


@app.get("/profile/<profile_id>")
def dashboard(profile_id: str) -> str:
    profile = _profiles.get_profile(profile_id)
    if profile is None:
        abort(404)

    categories = _get_categories()
    upgrades_by_cat: dict[str, list[UpgradeRow]] = {}
    for cat in categories:
        cat_upgrades = sorted(_upgrades.get_by_category(cat), key=lambda u: u.display_order)
        rows = [_build_upgrade_row(upgrade, profile) for upgrade in cat_upgrades]
        upgrades_by_cat[cat] = rows

    return render_template(
        "dashboard.html",
        profile=profile,
        categories=categories,
        upgrades_by_cat=upgrades_by_cat,
        profile_summary=_profile_summary(profile),
    )


@app.post("/profile/<profile_id>/level")
def update_level(profile_id: str) -> str:
    """htmx endpoint: update a single upgrade level, return the updated row."""
    upgrade_id = request.form.get("upgrade_id", "")

    upgrade = _upgrades.get_upgrade(upgrade_id)
    if upgrade is None:
        abort(400)

    level = _clamp_level(_form_int("level"), upgrade)
    profile = _profiles.update_level(profile_id, upgrade_id, level)
    if profile is None:
        abort(404)

    return render_template(
        "partials/upgrade_row.html",
        profile=profile,
        row=_build_upgrade_row(upgrade, profile),
    )


@app.post("/profile/<profile_id>/coins")
def update_coins(profile_id: str) -> str:
    """htmx endpoint: update available coins."""
    coins = max(0, _form_int("coins"))

    profile = _profiles.update_coins(profile_id, coins)
    if profile is None:
        abort(404)
    return render_template("partials/coins_display.html", profile=profile)


@app.post("/profile/<profile_id>/coins-and-recommend")
def update_coins_and_recommend(profile_id: str) -> str:
    """htmx endpoint: update coins, re-rank, return updated coins + recommendation table (OOB)."""
    coins = max(0, _form_int("coins"))

    profile = _profiles.update_coins(profile_id, coins)
    if profile is None:
        abort(404)

    engine, top, alternatives, ranked = _recommendation_context(profile)
    reference_engine, reference_top = _reference_context(profile)

    return render_template(
        "partials/coins_and_recommend.html",
        profile=profile,
        engine=engine,
        top=top,
        alternatives=alternatives,
        reference_engine=reference_engine,
        reference_top=reference_top,
        recommendation_summary=_recommendation_summary(ranked, alternatives),
        is_htmx=True,
    )


@app.get("/profile/<profile_id>/recommend")
def recommend(profile_id: str) -> str:
    profile = _profiles.get_profile(profile_id)
    if profile is None:
        abort(404)

    engine, top, alternatives, ranked = _recommendation_context(profile)
    reference_engine, reference_top = _reference_context(profile)

    return render_template(
        "recommend.html",
        profile=profile,
        engine=engine,
        top=top,
        alternatives=alternatives,
        reference_engine=reference_engine,
        reference_top=reference_top,
        all_ranked=ranked[:20],
        recommendation_summary=_recommendation_summary(ranked, alternatives),
        is_htmx=False,
    )


@app.post("/profile/<profile_id>/weights")
def update_weights(profile_id: str) -> str:
    """htmx endpoint: update weights, re-rank, return new recommendation table."""
    weights = ScoringWeights(
        attack=max(0.0, min(2.0, _form_float("attack"))),
        defense=max(0.0, min(2.0, _form_float("defense"))),
        utility=max(0.0, min(2.0, _form_float("utility"))),
    )

    profile = _profiles.update_weights(profile_id, weights)
    if profile is None:
        abort(404)

    engine, top, alternatives, ranked = _recommendation_context(profile)
    reference_engine, reference_top = _reference_context(profile)

    return render_template(
        "partials/recommendation_table.html",
        profile=profile,
        engine=engine,
        top=top,
        alternatives=alternatives,
        reference_engine=reference_engine,
        reference_top=reference_top,
        all_ranked=ranked[:20],
        recommendation_summary=_recommendation_summary(ranked, alternatives),
        is_htmx=True,
    )


@app.post("/profile/<profile_id>/level-recommend")
def update_level_recommend(profile_id: str) -> str:
    """htmx endpoint: update level and return updated recommendation table."""
    upgrade_id = request.form.get("upgrade_id", "")

    upgrade = _upgrades.get_upgrade(upgrade_id)
    if upgrade is None:
        abort(400)

    level = _clamp_level(_form_int("level"), upgrade)
    profile = _profiles.update_level(profile_id, upgrade_id, level)
    if profile is None:
        abort(404)

    engine, top, alternatives, ranked = _recommendation_context(profile)
    reference_engine, reference_top = _reference_context(profile)

    return render_template(
        "partials/recommendation_table.html",
        profile=profile,
        engine=engine,
        top=top,
        alternatives=alternatives,
        reference_engine=reference_engine,
        reference_top=reference_top,
        all_ranked=ranked[:20],
        recommendation_summary=_recommendation_summary(ranked, alternatives),
        is_htmx=True,
    )


if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "0") == "1",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
    )
