"""Tower Upgrade Advisor — Flask web application."""

from __future__ import annotations

from flask import Flask, abort, redirect, render_template, request, url_for

from src.data_loader import load_upgrades
from src.models import ScoringWeights, UpgradeDatabase
from src.profile_manager import ProfileManager
from src.scoring import BalancedEngine

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Startup: load game data and initialise services
# ---------------------------------------------------------------------------

_upgrades: UpgradeDatabase = load_upgrades()
_profiles = ProfileManager()


def _get_categories() -> list[str]:
    """Return ordered unique categories from upgrade data."""
    seen: set[str] = set()
    cats: list[str] = []
    for u in sorted(_upgrades.upgrades, key=lambda x: x.display_order):
        if u.category not in seen:
            seen.add(u.category)
            cats.append(u.category)
    return cats


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
    return f"{value * 100:.1f}%"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def index():
    profiles = _profiles.list_profiles()
    return render_template("index.html", profiles=profiles)


@app.post("/profile/new")
def profile_new():
    name = request.form.get("name", "").strip()
    if not name:
        return redirect(url_for("index"))
    profile = _profiles.create_profile(name)
    return redirect(url_for("dashboard", profile_id=profile.id))


@app.post("/profile/<profile_id>/delete")
def profile_delete(profile_id: str):
    _profiles.delete_profile(profile_id)
    return redirect(url_for("index"))


@app.get("/profile/<profile_id>")
def dashboard(profile_id: str):
    profile = _profiles.get_profile(profile_id)
    if profile is None:
        abort(404)

    categories = _get_categories()
    upgrades_by_cat: dict[str, list] = {}
    for cat in categories:
        cat_upgrades = sorted(_upgrades.get_by_category(cat), key=lambda u: u.display_order)
        rows = []
        for u in cat_upgrades:
            cur = profile.get_level(u.id)
            maxed = cur >= u.max_level
            current_effect = u.base_value if cur == 0 else u.levels[cur - 1].cumulative_effect
            next_cost = None
            next_delta = None
            if not maxed:
                nl = u.levels[cur]
                next_cost = nl.coin_cost
                next_delta = nl.effect_delta
            rows.append(
                {
                    "upgrade": u,
                    "current_level": cur,
                    "current_effect": current_effect,
                    "maxed": maxed,
                    "next_cost": next_cost,
                    "next_delta": next_delta,
                }
            )
        upgrades_by_cat[cat] = rows

    return render_template(
        "dashboard.html",
        profile=profile,
        categories=categories,
        upgrades_by_cat=upgrades_by_cat,
    )


@app.post("/profile/<profile_id>/level")
def update_level(profile_id: str):
    """htmx endpoint: update a single upgrade level, return the updated row."""
    upgrade_id = request.form.get("upgrade_id", "")
    try:
        level = int(request.form.get("level", 0))
    except (ValueError, TypeError):
        level = 0

    upgrade = _upgrades.get_upgrade(upgrade_id)
    if upgrade is None:
        abort(400)

    level = max(0, min(level, upgrade.max_level))
    profile = _profiles.update_level(profile_id, upgrade_id, level)
    if profile is None:
        abort(404)

    maxed = level >= upgrade.max_level
    current_effect = upgrade.base_value if level == 0 else upgrade.levels[level - 1].cumulative_effect
    next_cost = None
    next_delta = None
    if not maxed:
        nl = upgrade.levels[level]
        next_cost = nl.coin_cost
        next_delta = nl.effect_delta

    return render_template(
        "partials/upgrade_row.html",
        profile=profile,
        row={
            "upgrade": upgrade,
            "current_level": level,
            "current_effect": current_effect,
            "maxed": maxed,
            "next_cost": next_cost,
            "next_delta": next_delta,
        },
    )


@app.post("/profile/<profile_id>/coins")
def update_coins(profile_id: str):
    """htmx endpoint: update available coins."""
    try:
        coins = int(request.form.get("coins", 0))
    except (ValueError, TypeError):
        coins = 0
    coins = max(0, coins)

    profile = _profiles.update_coins(profile_id, coins)
    if profile is None:
        abort(404)
    return render_template("partials/coins_display.html", profile=profile)


@app.post("/profile/<profile_id>/coins-and-recommend")
def update_coins_and_recommend(profile_id: str):
    """htmx endpoint: update coins, re-rank, return updated coins + recommendation table (OOB)."""
    try:
        coins = int(request.form.get("coins", 0))
    except (ValueError, TypeError):
        coins = 0
    coins = max(0, coins)

    profile = _profiles.update_coins(profile_id, coins)
    if profile is None:
        abort(404)

    engine = BalancedEngine(profile.weights)
    ranked = engine.rank(_upgrades, profile)
    top = ranked[0] if ranked else None
    alternatives = ranked[1:11] if len(ranked) > 1 else []

    return render_template(
        "partials/coins_and_recommend.html",
        profile=profile,
        engine=engine,
        top=top,
        alternatives=alternatives,
    )


@app.get("/profile/<profile_id>/recommend")
def recommend(profile_id: str):
    profile = _profiles.get_profile(profile_id)
    if profile is None:
        abort(404)

    engine = BalancedEngine(profile.weights)
    ranked = engine.rank(_upgrades, profile)

    top = ranked[0] if ranked else None
    alternatives = ranked[1:11] if len(ranked) > 1 else []

    return render_template(
        "recommend.html",
        profile=profile,
        engine=engine,
        top=top,
        alternatives=alternatives,
        all_ranked=ranked[:20],
    )


@app.post("/profile/<profile_id>/weights")
def update_weights(profile_id: str):
    """htmx endpoint: update weights, re-rank, return new recommendation table."""
    try:
        attack = float(request.form.get("attack", 1.0))
        defense = float(request.form.get("defense", 1.0))
        utility = float(request.form.get("utility", 1.0))
    except (ValueError, TypeError):
        attack = defense = utility = 1.0

    weights = ScoringWeights(
        attack=max(0.0, min(2.0, attack)),
        defense=max(0.0, min(2.0, defense)),
        utility=max(0.0, min(2.0, utility)),
    )

    profile = _profiles.update_weights(profile_id, weights)
    if profile is None:
        abort(404)

    engine = BalancedEngine(weights)
    ranked = engine.rank(_upgrades, profile)

    top = ranked[0] if ranked else None
    alternatives = ranked[1:11] if len(ranked) > 1 else []

    return render_template(
        "partials/recommendation_table.html",
        profile=profile,
        engine=engine,
        top=top,
        alternatives=alternatives,
        all_ranked=ranked[:20],
    )


@app.post("/profile/<profile_id>/level-recommend")
def update_level_recommend(profile_id: str):
    """htmx endpoint: update level and return updated recommendation table."""
    upgrade_id = request.form.get("upgrade_id", "")
    try:
        level = int(request.form.get("level", 0))
    except (ValueError, TypeError):
        level = 0

    upgrade = _upgrades.get_upgrade(upgrade_id)
    if upgrade is None:
        abort(400)

    level = max(0, min(level, upgrade.max_level))
    profile = _profiles.update_level(profile_id, upgrade_id, level)
    if profile is None:
        abort(404)

    engine = BalancedEngine(profile.weights)
    ranked = engine.rank(_upgrades, profile)
    top = ranked[0] if ranked else None
    alternatives = ranked[1:11] if len(ranked) > 1 else []

    return render_template(
        "partials/recommendation_table.html",
        profile=profile,
        engine=engine,
        top=top,
        alternatives=alternatives,
        all_ranked=ranked[:20],
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
