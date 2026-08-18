"""
Load test runner.

Usage:
    python run_load_test.py --users=1000 --duration=300 --scenario=mining \
        --target=local --ramp-up=30 --ramp-down=30

Outputs:
    load_test_results.json  — raw metrics
    load_test_report.html   — human-readable report
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import random
import threading
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.load.metrics import MetricsAggregator
from tests.load.report_generator import generate_html_report


# ---------------------------------------------------------------------------
# Simulated scenario functions (replace HTTP calls for unit tests)
# ---------------------------------------------------------------------------
def _simulate_request(
    target_url: str,
    path: str,
    method: str = "GET",
    payload: dict | None = None,
) -> tuple[float, int]:
    """Simulate an HTTP request; returns (latency_ms, status_code)."""
    import urllib.request
    import urllib.error

    url = f"{target_url}{path}"
    start = time.monotonic()
    try:
        if method == "POST":
            data = json.dumps(payload or {}).encode()
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
        else:
            req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            status_code = resp.status
    except urllib.error.HTTPError as exc:
        status_code = exc.code
    except Exception:
        status_code = 0  # timeout / connection error
    latency_ms = (time.monotonic() - start) * 1000
    return latency_ms, status_code


SCENARIO_WEIGHTS = {
    "login": 10,
    "mining": 80,
    "reward_check": 5,
    "leaderboard": 10,
    "marketplace": 5,
}


def _pick_scenario() -> str:
    choices = []
    for name, weight in SCENARIO_WEIGHTS.items():
        choices.extend([name] * weight)
    return random.choice(choices)


def _run_scenario(scenario: str, target_url: str, metrics: MetricsAggregator) -> None:
    if scenario == "login":
        username = os.getenv("LOAD_TEST_USERNAME", "load_test_user")
        password = os.getenv("LOAD_TEST_PASSWORD", "load_test_pass")
        lat, code = _simulate_request(target_url, "/api/v1/auth/login", "POST", {"username": username, "password": password})
        metrics.record("POST:/api/v1/auth/login", lat, code)
    elif scenario == "mining":
        lat, code = _simulate_request(target_url, "/api/v1/blockchain/status")
        metrics.record("GET:/api/v1/blockchain/status", lat, code)
    elif scenario == "reward_check":
        lat, code = _simulate_request(target_url, "/api/v1/players/balance")
        metrics.record("GET:/api/v1/players/balance", lat, code)
    elif scenario == "leaderboard":
        lat, code = _simulate_request(target_url, "/api/v1/leaderboards/global")
        metrics.record("GET:/api/v1/leaderboards/global", lat, code)
    elif scenario == "marketplace":
        lat, code = _simulate_request(target_url, "/api/v1/marketplace/listings")
        metrics.record("GET:/api/v1/marketplace/listings", lat, code)


def _worker(target_url: str, metrics: MetricsAggregator, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        scenario = _pick_scenario()
        _run_scenario(scenario, target_url, metrics)
        time.sleep(random.uniform(0.01, 0.1))


TARGET_URLS = {
    "local": "http://localhost:8000",
    "staging": os.getenv("STAGING_URL", "http://staging.example.com"),
    "prod": os.getenv("PROD_URL", "http://prod.example.com"),
}


def run_load_test(
    users: int,
    duration: int,
    scenario: str,
    target: str = "local",
    ramp_up: int = 30,
    ramp_down: int = 30,
    output_json: str = "load_test_results.json",
    output_html: str = "load_test_report.html",
) -> MetricsAggregator:
    target_url = TARGET_URLS.get(target, TARGET_URLS["local"])
    metrics = MetricsAggregator()
    stop_event = threading.Event()
    threads: list[threading.Thread] = []

    print(f"[load-test] Starting {users} users, {duration}s, scenario={scenario}, target={target_url}")

    # Ramp up
    ramp_interval = ramp_up / max(users, 1)
    for i in range(users):
        t = threading.Thread(target=_worker, args=(target_url, metrics, stop_event), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(ramp_interval)

    # Hold
    hold_duration = max(duration - ramp_up - ramp_down, 0)
    time.sleep(hold_duration)

    # Ramp down
    stop_event.set()
    for t in threads:
        t.join(timeout=2)

    metrics.finish()

    summary = metrics.summary()
    Path(output_json).write_text(json.dumps(summary, indent=2))
    print(f"[load-test] Results written to {output_json}")

    generate_html_report(summary, output_html)
    print(f"[load-test] HTML report written to {output_html}")

    sla_ok = metrics.meets_sla()
    print(f"[load-test] SLA met: {sla_ok}")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="GMN Load Test Runner")
    parser.add_argument("--users", type=int, default=1000)
    parser.add_argument("--duration", type=int, default=300)
    parser.add_argument("--scenario", default="mining")
    parser.add_argument("--target", default="local")
    parser.add_argument("--ramp-up", type=int, default=30)
    parser.add_argument("--ramp-down", type=int, default=30)
    args = parser.parse_args()

    metrics = run_load_test(
        users=args.users,
        duration=args.duration,
        scenario=args.scenario,
        target=args.target,
        ramp_up=args.ramp_up,
        ramp_down=args.ramp_down,
    )
    if not metrics.meets_sla():
        print("[load-test] WARNING: SLA thresholds not met!")
        sys.exit(1)


if __name__ == "__main__":
    main()
