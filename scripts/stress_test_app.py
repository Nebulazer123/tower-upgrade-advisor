#!/usr/bin/env python3
"""Exercise the Flask app and HTMX endpoints under repeated concurrent traffic."""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as app_module  # noqa: E402
from src.profile_manager import ProfileManager  # noqa: E402


def request_ok(status_code: int) -> bool:
    return 200 <= status_code < 400


def run_worker(profile_id: str, rounds: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    latencies: list[float] = []
    errors: list[dict[str, Any]] = []
    upgrades = [upgrade.id for upgrade in app_module._upgrades.upgrades]

    with app_module.app.test_client() as client:
        for index in range(rounds):
            action = rng.choice(("dashboard", "recommend", "data", "coins", "weights", "level"))
            started = time.perf_counter()

            if action == "dashboard":
                response = client.get(f"/profile/{profile_id}")
            elif action == "recommend":
                response = client.get(f"/profile/{profile_id}/recommend")
            elif action == "data":
                category = rng.choice(("attack", "defense", "utility"))
                page = rng.randint(-5, 999)
                response = client.get(f"/data?category={category}&page={page}")
            elif action == "coins":
                response = client.post(
                    f"/profile/{profile_id}/coins-and-recommend",
                    data={"coins": str(rng.randint(0, 10_000_000))},
                )
            elif action == "weights":
                response = client.post(
                    f"/profile/{profile_id}/weights",
                    data={
                        "attack": f"{rng.uniform(0, 2):.2f}",
                        "defense": f"{rng.uniform(0, 2):.2f}",
                        "utility": f"{rng.uniform(0, 2):.2f}",
                    },
                )
            else:
                upgrade_id = rng.choice(upgrades)
                upgrade = app_module._upgrades.get_upgrade(upgrade_id)
                max_level = upgrade.max_level if upgrade else 1
                response = client.post(
                    f"/profile/{profile_id}/level-recommend",
                    data={"upgrade_id": upgrade_id, "level": str(rng.randint(-20, max_level + 20))},
                )

            latencies.append((time.perf_counter() - started) * 1000)
            if not request_ok(response.status_code):
                errors.append(
                    {
                        "round": index,
                        "action": action,
                        "status": response.status_code,
                        "body": response.data[:240].decode("utf-8", errors="replace"),
                    }
                )

    return {
        "profile_id": profile_id,
        "requests": rounds,
        "errors": errors,
        "latencies_ms": latencies,
    }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profiles", type=int, default=16)
    parser.add_argument("--rounds", type=int, default=40, help="Requests per profile.")
    parser.add_argument("--seed", type=int, default=20260615)
    args = parser.parse_args()

    app_module.app.config.update(TESTING=True)
    with tempfile.TemporaryDirectory(prefix="tower-advisor-stress-") as tmp:
        manager = ProfileManager(Path(tmp) / "profiles")
        app_module._profiles = manager
        profiles = [manager.create_profile(f"Stress {i + 1}") for i in range(args.profiles)]

        started = time.perf_counter()
        results = []
        with ThreadPoolExecutor(max_workers=args.profiles) as executor:
            futures = [
                executor.submit(run_worker, profile.id, args.rounds, args.seed + i)
                for i, profile in enumerate(profiles)
            ]
            for future in as_completed(futures):
                results.append(future.result())

    latencies = [latency for result in results for latency in result["latencies_ms"]]
    errors = [error for result in results for error in result["errors"]]
    report = {
        "profiles": args.profiles,
        "rounds_per_profile": args.rounds,
        "requests": len(latencies),
        "errors": errors,
        "duration_seconds": round(time.perf_counter() - started, 3),
        "latency_ms": {
            "min": round(min(latencies), 3) if latencies else 0,
            "mean": round(statistics.fmean(latencies), 3) if latencies else 0,
            "p95": round(percentile(latencies, 95), 3),
            "max": round(max(latencies), 3) if latencies else 0,
        },
    }
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
