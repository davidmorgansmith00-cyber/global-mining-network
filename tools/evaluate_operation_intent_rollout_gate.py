from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate operation-intent rollout promotion readiness from "
            "build_operation_intent_rollout_bundle.py output."
        )
    )
    parser.add_argument("--bundle", required=True, help="Path to rollout bundle JSON")
    parser.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help="Exit with status 1 when one or more threshold checks fail",
    )
    parser.add_argument("--output", default="", help="Optional output path for evaluation JSON")
    return parser.parse_args()


def _load_bundle(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Bundle file is not a JSON object")
    return payload


def _bool_value(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return False


def _build_evaluation(bundle: dict[str, object], bundle_path: Path) -> dict[str, object]:
    threshold_checks = bundle.get("threshold_checks", {})
    if not isinstance(threshold_checks, dict):
        threshold_checks = {}

    check_names = [
        "query_share_window_pass",
        "strict_rejection_window_pass",
        "mismatch_rate_window_pass",
    ]

    checks: list[dict[str, object]] = []
    failed_checks: list[str] = []
    for name in check_names:
        passed = _bool_value(threshold_checks.get(name))
        rule = threshold_checks.get(name.replace("_pass", "_rule"), "")
        checks.append({"name": name, "passed": passed, "rule": rule})
        if not passed:
            failed_checks.append(name)

    promotion_ready = len(failed_checks) == 0
    decision = "promote_candidate" if promotion_ready else "hold_candidate"

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_bundle": str(bundle_path).replace("\\", "/"),
        "promotion_ready": promotion_ready,
        "decision": decision,
        "failed_checks": failed_checks,
        "checks": checks,
    }


def main() -> int:
    args = _parse_args()
    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        raise RuntimeError(f"Bundle file does not exist: {bundle_path}")

    bundle = _load_bundle(bundle_path)
    evaluation = _build_evaluation(bundle, bundle_path)

    text = json.dumps(evaluation, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")

    print(text)
    if args.fail_on_blocked and not bool(evaluation.get("promotion_ready", False)):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
