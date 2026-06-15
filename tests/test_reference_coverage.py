"""Tests for public workshop coverage reporting."""

from __future__ import annotations

from src.data_loader import load_upgrades
from src.reference_coverage import compute_coverage, load_reference_manifest


def test_reference_manifest_declares_public_workshop_surface() -> None:
    manifest = load_reference_manifest()

    assert manifest["verified_at"] == "2026-06-15"
    assert manifest["source"]["workshop_calculator"].startswith(
        "https://tower-workshop-calculator.netlify.app/"
    )
    assert sum(len(category["upgrades"]) for category in manifest["categories"]) == 48


def test_bundled_data_coverage_is_complete() -> None:
    report = compute_coverage(load_upgrades())

    assert report["loaded"] == 48
    assert report["expected"] == 48
    assert report["missing"] == 0
    assert report["complete"]
    assert report["categories"]["attack"]["loaded"] == 17
    assert report["categories"]["defense"]["loaded"] == 18
    assert report["categories"]["utility"]["loaded"] == 13
