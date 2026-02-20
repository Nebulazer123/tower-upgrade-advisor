"""Flask web application for the Tower Upgrade Advisor."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

from src.data_loader import UPGRADES_PATH, load_upgrades
from src.models import ScoringWeights, UpgradeDatabase
from src.profile_manager import ProfileManager
from src.scoring import BalancedEngine, PerCategoryEngine

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "tower-upgrade-advisor-dev-key")

_upgrades: UpgradeDatabase | None = None
_using_test_data: bool = False
_pm = ProfileManager()

_TEST_FIXTURES = Path(__file__).resolve().parent / "tests" / "fixtures" / "test_upgrades.json"

_CATEGORY_ORDER = {"offense": 0, "defense": 1, "economy": 2, "utility": 3}


def get_upgrades() -> UpgradeDatabase:
    """Load upgrade data, falling back to test fixtures if real data is missing."""
    global _upgrades, _using_test_data
    if _upgrades is not None:
        return _upgrades
    try:
        _upgrades = load_upgrades()
        _using_test_data = False
    except FileNotFoundError:
        _upgrades = load_upgrades(_TEST_FIXTURES)
        _using_test_data = True
    return _upgrades


def ordered_categories(db: UpgradeDatabase) -> list[str]:
    cats = sorted(
        {u.category for u in db.upgrades},
        key=lambda c: _CATEGORY_ORDER.get(c, 99),
    )
    return cats


def upgrades_by_category(db: UpgradeDatabase) -> dict[str, list]:
    result: dict[str, list] = {}
    for cat in ordered_categories(db):
        result[cat] = sorted(db.get_by_category(cat), key=lambda u: u.display_order)
    return result


# ── Template helpers ─────────────────────────────────────────────────────────


@app.template_filter("fmt")
def fmt_number(value) -> str:
    if isinstance(value, float):
        if value == int(value):
            return f"{int(value):,}"
        return f"{value:,.4f}"
    return f"{value:,}"


@app.template_filter("fmt_score")
def fmt_score(value) -> str:
    if value == 0:
        return "0"
    return f"{value:.6f}"


@app.template_filter("fmt_effect")
def fmt_effect(value) -> str:
    if isinstance(value, float):
        if value == int(value):
            return f"{int(value):,}"
        trimmed = f"{value:.6f}".rstrip("0").rstrip(".")
        return trimmed
    return f"{value:,}"


@app.context_processor
def inject_globals():
    return {"using_test_data": _using_test_data}


# ── Routes ───────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    get_upgrades()
    profiles = _pm.list_profiles()
    return render_template("index.html", profiles=profiles)


@app.route("/profile/<profile_id>")
def dashboard(profile_id: str):
    db = get_upgrades()
    profile = _pm.get_profile(profile_id)
    if profile is None:
        flash("Profile not found.", "error")
        return redirect(url_for("index"))

    cats = ordered_categories(db)
    by_cat = upgrades_by_category(db)

    return render_template(
        "dashboard.html",
        profile=profile,
        categories=cats,
        upgrades_by_cat=by_cat,
        db=db,
    )


@app.route("/profile/<profile_id>/level", methods=["POST"])
def update_level(profile_id: str):
    db = get_upgrades()
    upgrade_id = request.form.get("upgrade_id", "")
    try:
        level = int(request.form.get("level", 0))
    except (ValueError, TypeError):
        level = 0

    upgrade = db.get_upgrade(upgrade_id)
    if upgrade:
        level = max(0, min(level, upgrade.max_level))

    profile = _pm.update_level(profile_id, upgrade_id, level)
    if profile is None:
        return "Profile not found", 404

    if upgrade:
        return render_template(
            "partials/upgrade_row.html", profile=profile, upgrade=upgrade,
        )
    return "", 200


@app.route("/profile/<profile_id>/coins", methods=["POST"])
def update_coins(profile_id: str):
    try:
        coins = int(request.form.get("coins", 0))
    except (ValueError, TypeError):
        coins = 0
    coins = max(0, coins)

    profile = _pm.update_coins(profile_id, coins)
    if profile is None:
        return "Profile not found", 404
    return render_template("partials/coins_display.html", profile=profile)


@app.route("/profile/<profile_id>/weights", methods=["POST"])
def update_weights(profile_id: str):
    def _float(key: str, default: float = 1.0) -> float:
        try:
            v = float(request.form.get(key, default))
            return max(0.0, min(2.0, v))
        except (ValueError, TypeError):
            return default

    weights = ScoringWeights(
        economy=_float("economy"),
        offense=_float("offense"),
        defense=_float("defense"),
        utility=_float("utility"),
    )
    profile = _pm.update_weights(profile_id, weights)
    if profile is None:
        return "Profile not found", 404

    db = get_upgrades()
    engine = BalancedEngine(weights)
    rankings = engine.rank(db, profile)
    per_cat = PerCategoryEngine().rank(db, profile)

    return render_template(
        "partials/recommendation_results.html",
        profile=profile,
        rankings=rankings,
        per_cat=per_cat,
        engine=engine,
        db=db,
    )


@app.route("/profile/<profile_id>/recommend")
def recommend(profile_id: str):
    db = get_upgrades()
    profile = _pm.get_profile(profile_id)
    if profile is None:
        flash("Profile not found.", "error")
        return redirect(url_for("index"))

    engine = BalancedEngine(profile.weights)
    rankings = engine.rank(db, profile)
    per_cat = PerCategoryEngine().rank(db, profile)

    return render_template(
        "recommend.html",
        profile=profile,
        rankings=rankings,
        per_cat=per_cat,
        engine=engine,
        db=db,
    )


@app.route("/profile/new", methods=["POST"])
def create_profile():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Profile name is required.", "error")
        return redirect(url_for("index"))

    profile = _pm.create_profile(name)
    flash(f"Profile '{profile.name}' created.", "success")
    return redirect(url_for("dashboard", profile_id=profile.id))


@app.route("/profile/<profile_id>/delete", methods=["POST"])
def delete_profile(profile_id: str):
    profile = _pm.get_profile(profile_id)
    name = profile.name if profile else "Unknown"
    deleted = _pm.delete_profile(profile_id)
    if deleted:
        flash(f"Profile '{name}' deleted.", "success")
    else:
        flash("Profile not found.", "error")
    return redirect(url_for("index"))


@app.route("/upgrade/<upgrade_id>")
def upgrade_detail(upgrade_id: str):
    db = get_upgrades()
    upgrade = db.get_upgrade(upgrade_id)
    if upgrade is None:
        flash("Upgrade not found.", "error")
        return redirect(url_for("index"))

    profile_id = request.args.get("profile")
    profile = _pm.get_profile(profile_id) if profile_id else None
    current_level = profile.get_level(upgrade_id) if profile else 0

    cum_costs: list[int] = []
    running = 0
    for lv in upgrade.levels:
        running += lv.coin_cost
        cum_costs.append(running)

    return render_template(
        "upgrade_detail.html",
        upgrade=upgrade,
        profile=profile,
        current_level=current_level,
        cum_costs=cum_costs,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5001)
