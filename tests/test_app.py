"""Route tests for the Flask web interface."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from flask.testing import FlaskClient

import app as app_module
from src.profile_manager import ProfileManager


@pytest.fixture
def web_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[FlaskClient]:
    manager = ProfileManager(tmp_path / "profiles")
    monkeypatch.setattr(app_module, "_profiles", manager)
    app_module.app.config.update(TESTING=True)
    with app_module.app.test_client() as client:
        yield client


def test_index_empty_state(web_client: FlaskClient) -> None:
    response = web_client.get("/")

    assert response.status_code == 200
    assert b"No profiles yet" in response.data
    assert b"/static/vendor/htmx.min.js" in response.data
    assert b"tower-workshop-calculator.netlify.app" in response.data
    assert b"48/48" in response.data
    assert b"Complete against the public workshop selector" in response.data


def test_vercel_uses_ephemeral_profile_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VERCEL", "1")

    assert str(app_module._profile_storage_dir()) == "/tmp/tower-upgrade-advisor/profiles"


def test_create_profile_redirects_to_dashboard(web_client: FlaskClient) -> None:
    response = web_client.post("/profile/new", data={"name": "Farm build"}, follow_redirects=True)

    assert response.status_code == 200
    assert b"Farm build" in response.data
    assert b"Available Coins" in response.data
    assert b"+-0.15" not in response.data
    assert b"-0.15" in response.data


def test_data_route_handles_bad_query_values(web_client: FlaskClient) -> None:
    response = web_client.get("/data?category=missing&page=not-a-number&upgrade=missing")

    assert response.status_code == 200
    assert b"Upgrade Data" in response.data
    assert b"Coin Cost" in response.data
    assert b"No missing upgrades in this category" in response.data


def test_dashboard_clamps_out_of_range_profile_levels(web_client: FlaskClient) -> None:
    manager = app_module._profiles
    profile = manager.create_profile("Migrated profile")
    manager.save_profile(profile.model_copy(update={"levels": {"damage": 999_999}}))
    damage = app_module._upgrades.get_upgrade("damage")
    assert damage is not None

    response = web_client.get(f"/profile/{profile.id}")

    assert response.status_code == 200
    assert f'value="{damage.max_level}"'.encode() in response.data
    assert b"MAX" in response.data


def test_update_level_clamps_and_returns_updated_row(web_client: FlaskClient) -> None:
    manager = app_module._profiles
    profile = manager.create_profile("Clamp test")
    damage = app_module._upgrades.get_upgrade("damage")
    assert damage is not None

    response = web_client.post(
        f"/profile/{profile.id}/level",
        data={"upgrade_id": "damage", "level": damage.max_level + 50},
    )

    updated = manager.get_profile(profile.id)
    assert updated is not None
    assert response.status_code == 200
    assert updated.levels["damage"] == damage.max_level
    assert f'value="{damage.max_level}"'.encode() in response.data
    assert b"MAX" in response.data


def test_recommendation_htmx_updates_coins_and_weights(web_client: FlaskClient) -> None:
    manager = app_module._profiles
    profile = manager.create_profile("Recommendation test")

    coins_response = web_client.post(
        f"/profile/{profile.id}/coins-and-recommend",
        data={"coins": "12345"},
    )
    weights_response = web_client.post(
        f"/profile/{profile.id}/weights",
        data={"attack": "9", "defense": "-1", "utility": "bad"},
    )

    updated = manager.get_profile(profile.id)
    assert updated is not None
    assert coins_response.status_code == 200
    assert weights_response.status_code == 200
    assert updated.available_coins == 12345
    assert updated.weights.attack == 2.0
    assert updated.weights.defense == 0.0
    assert updated.weights.utility == 1.0
    assert b'hx-swap-oob="true"' in coins_response.data
    assert b"Best" in weights_response.data or b"#1" in weights_response.data
    assert b"Reference Check" in weights_response.data


def test_recommendation_page_shows_reference_check(web_client: FlaskClient) -> None:
    manager = app_module._profiles
    profile = manager.create_profile("Reference page")

    response = web_client.get(f"/profile/{profile.id}/recommend")

    assert response.status_code == 200
    assert b"Reference Check" in response.data
    assert b"DPS source" in response.data
