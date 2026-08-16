from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate synthetic operation-intent transport capture artifacts and run "
            "the bundle + memo prefill helpers for an end-to-end dry run."
        )
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/operation-intent-dry-run",
        help="Directory to place generated artifacts",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of synthetic daily captures to generate (default: 14)",
    )
    parser.add_argument(
        "--query-threshold-percent",
        type=float,
        default=1.0,
        help="Threshold used when building the rollout bundle (default: 1.0)",
    )
    parser.add_argument(
        "--strict-rejection-max-delta",
        type=int,
        default=0,
        help="Maximum allowed query_rejected_strict delta over the window (default: 0)",
    )
    parser.add_argument(
        "--mismatch-rate-max-per-minute",
        type=float,
        default=0.1,
        help="Maximum allowed mismatch rate per minute over the window (default: 0.1)",
    )
    parser.add_argument(
        "--environment-scope",
        default="dry-run",
        help="Environment scope value forwarded to memo prefill (default: dry-run)",
    )
    parser.add_argument(
        "--decision-owner",
        default="dry-run-operator",
        help="Decision owner value forwarded to memo prefill (default: dry-run-operator)",
    )
    return parser.parse_args()


def _build_daily_capture(index: int, total_days: int) -> dict[str, object]:
    now = datetime.now(UTC) - timedelta(days=(total_days - index))

    # Synthetic migration profile: query steadily decreases while header usage dominates.
    query_delta = max(1, 12 - index)
    header_delta = 120 + index * 4
    dual_match_delta = 4
    mismatch_delta = 0 if index % 5 else 1
    strict_rejected_delta = 0
    total_transport_delta = query_delta + header_delta + dual_match_delta
    query_share_ratio = query_delta / total_transport_delta

    return {
        "started_at": (now - timedelta(minutes=15)).isoformat(),
        "finished_at": now.isoformat(),
        "elapsed_seconds": 900.0,
        "base_url": "http://127.0.0.1:8000",
        "token_header": "X-Maintenance-Token",
        "samples": 15,
        "interval_seconds": 60.0,
        "snapshots": [
            {
                "sample_index": 0,
                "captured_at": (now - timedelta(minutes=15)).isoformat(),
                "operation_intent_session_header_name": "X-Session-Id",
                "counters": {
                    "query": 1000,
                    "header": 3000,
                    "dual_match": 100,
                    "mismatch": 5,
                    "query_rejected_strict": 0,
                },
            },
            {
                "sample_index": 14,
                "captured_at": now.isoformat(),
                "operation_intent_session_header_name": "X-Session-Id",
                "counters": {
                    "query": 1000 + query_delta,
                    "header": 3000 + header_delta,
                    "dual_match": 100 + dual_match_delta,
                    "mismatch": 5 + mismatch_delta,
                    "query_rejected_strict": strict_rejected_delta,
                },
            },
        ],
        "summary": {
            "query": {
                "first": 1000,
                "last": 1000 + query_delta,
                "delta": query_delta,
                "rate_per_minute": round(query_delta / 15.0, 4),
            },
            "header": {
                "first": 3000,
                "last": 3000 + header_delta,
                "delta": header_delta,
                "rate_per_minute": round(header_delta / 15.0, 4),
            },
            "dual_match": {
                "first": 100,
                "last": 100 + dual_match_delta,
                "delta": dual_match_delta,
                "rate_per_minute": round(dual_match_delta / 15.0, 4),
            },
            "mismatch": {
                "first": 5,
                "last": 5 + mismatch_delta,
                "delta": mismatch_delta,
                "rate_per_minute": round(mismatch_delta / 15.0, 4),
            },
            "query_rejected_strict": {
                "first": 0,
                "last": strict_rejected_delta,
                "delta": strict_rejected_delta,
                "rate_per_minute": 0.0,
            },
        },
        "query_share_from_deltas": {
            "query_delta": query_delta,
            "header_delta": header_delta,
            "dual_match_delta": dual_match_delta,
            "total_transport_delta": total_transport_delta,
            "query_share_ratio": round(query_share_ratio, 6),
            "query_share_percent": round(query_share_ratio * 100.0, 4),
        },
    }


def _run_command(command: list[str]) -> str:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        message = "\n".join(
            [
                "Command failed:",
                " ".join(command),
                completed.stdout.strip(),
                completed.stderr.strip(),
            ]
        )
        raise RuntimeError(message)
    return completed.stdout


def main() -> int:
    args = _parse_args()
    if args.days < 1:
        raise RuntimeError("--days must be >= 1")

    root = Path(__file__).resolve().parents[1]
    output_dir = (root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    for day in range(1, args.days + 1):
        payload = _build_daily_capture(day, args.days)
        path = output_dir / f"intent-transport-day{day:02d}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    bundle_path = output_dir / "intent-transport-rollout-bundle.json"
    memo_draft_path = output_dir / "intent-transport-decision-memo-draft.json"
    memo_markdown_path = output_dir / "intent-transport-decision-memo.md"
    rollout_evaluation_path = output_dir / "intent-transport-rollout-evaluation.json"
    decision_package_dir = output_dir / "decision-package"
    inspector_summary_text_path = decision_package_dir / "intent-transport-decision-package-inspector-summary.txt"
    inspector_summary_json_path = decision_package_dir / "intent-transport-decision-package-inspector-summary.json"

    _run_command(
        [
            sys.executable,
            str(root / "tools" / "build_operation_intent_rollout_bundle.py"),
            "--input-glob",
            str(output_dir / "intent-transport-day*.json"),
            "--query-threshold-percent",
            str(args.query_threshold_percent),
            "--strict-rejection-max-delta",
            str(args.strict_rejection_max_delta),
            "--mismatch-rate-max-per-minute",
            str(args.mismatch_rate_max_per_minute),
            "--output",
            str(bundle_path),
        ]
    )

    _run_command(
        [
            sys.executable,
            str(root / "tools" / "evaluate_operation_intent_rollout_gate.py"),
            "--bundle",
            str(bundle_path),
            "--output",
            str(rollout_evaluation_path),
        ]
    )

    _run_command(
        [
            sys.executable,
            str(root / "tools" / "prefill_operation_intent_decision_memo.py"),
            "--bundle",
            str(bundle_path),
            "--evaluation",
            str(rollout_evaluation_path),
            "--environment-scope",
            args.environment_scope,
            "--decision-owner",
            args.decision_owner,
            "--output",
            str(memo_draft_path),
        ]
    )

    _run_command(
        [
            sys.executable,
            str(root / "tools" / "render_operation_intent_decision_memo.py"),
            "--input",
            str(memo_draft_path),
            "--evaluation",
            str(rollout_evaluation_path),
            "--output",
            str(memo_markdown_path),
        ]
    )

    package_output = _run_command(
        [
            sys.executable,
            str(root / "tools" / "build_operation_intent_decision_package.py"),
            "--input-glob",
            str(output_dir / "intent-transport-day*.json"),
            "--output-dir",
            str(decision_package_dir),
            "--query-threshold-percent",
            str(args.query_threshold_percent),
            "--strict-rejection-max-delta",
            str(args.strict_rejection_max_delta),
            "--mismatch-rate-max-per-minute",
            str(args.mismatch_rate_max_per_minute),
            "--environment-scope",
            args.environment_scope,
            "--decision-owner",
            args.decision_owner,
        ]
    )
    package_summary = json.loads(package_output) if package_output.strip() else {}
    manifest_file = str(package_summary.get("manifest_file", ""))
    if manifest_file:
        _run_command(
            [
                sys.executable,
                str(root / "tools" / "inspect_operation_intent_decision_package.py"),
                "--manifest",
                manifest_file,
                "--verify-before-inspect",
                "--output",
                str(inspector_summary_text_path),
            ]
        )
        _run_command(
            [
                sys.executable,
                str(root / "tools" / "inspect_operation_intent_decision_package.py"),
                "--manifest",
                manifest_file,
                "--verify-before-inspect",
                "--format",
                "json",
                "--output",
                str(inspector_summary_json_path),
            ]
        )

    compact_summary_json_file = str(package_summary.get("compact_summary_json_file", ""))
    compact_summary_json_payload: dict[str, object] = {}
    if compact_summary_json_file:
        compact_summary_path = Path(compact_summary_json_file)
        if compact_summary_path.exists():
            compact_summary_json_payload = json.loads(compact_summary_path.read_text(encoding="utf-8"))

    inspector_summary_json_payload: dict[str, object] = {}
    if inspector_summary_json_path.exists():
        inspector_summary_json_payload = json.loads(inspector_summary_json_path.read_text(encoding="utf-8"))

    result = {
        "output_dir": str(output_dir).replace("\\", "/"),
        "generated_daily_files": args.days,
        "bundle_file": str(bundle_path).replace("\\", "/"),
        "memo_draft_file": str(memo_draft_path).replace("\\", "/"),
        "memo_markdown_file": str(memo_markdown_path).replace("\\", "/"),
        "rollout_evaluation_file": str(rollout_evaluation_path).replace("\\", "/"),
        "decision_package_manifest_file": manifest_file,
        "decision_package_verification_file": str(package_summary.get("verification_file", "")),
        "decision_package_compact_summary_file": str(package_summary.get("compact_summary_file", "")),
        "decision_package_compact_summary_json_file": compact_summary_json_file,
        "decision_package_inspector_summary_file": str(inspector_summary_text_path).replace("\\", "/"),
        "decision_package_inspector_summary_json_file": str(inspector_summary_json_path).replace("\\", "/"),
        "decision_package_decision": str(compact_summary_json_payload.get("decision", "")),
        "decision_package_promotion_ready": bool(compact_summary_json_payload.get("promotion_ready", False)),
        "decision_package_verified": bool(compact_summary_json_payload.get("verified", False)),
        "decision_package_schema_supported": bool(compact_summary_json_payload.get("schema_supported", False)),
        "decision_package_compact_summary_artifacts_present": bool(
            package_summary.get("verification_compact_summary_artifacts_present", False)
        ),
        "decision_package_compact_summary_checks_performed": bool(
            package_summary.get("verification_compact_summary_checks_performed", False)
        ),
        "decision_package_compact_summary_checks_skipped": bool(
            package_summary.get("verification_compact_summary_checks_skipped", False)
        ),
        "decision_package_compact_summary_mismatch_count": int(
            package_summary.get("verification_compact_summary_mismatch_count", 0)
        ),
        "decision_package_compact_summary_mismatch_details": package_summary.get(
            "verification_compact_summary_mismatch_details", []
        ),
        "decision_package_inspector_verified": bool(inspector_summary_json_payload.get("verified", False)),
        "decision_package_inspector_mismatch_count": int(
            inspector_summary_json_payload.get("compact_summary_mismatch_count", 0)
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
