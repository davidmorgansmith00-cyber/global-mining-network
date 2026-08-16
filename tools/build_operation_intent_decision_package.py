from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a complete operation-intent rollout decision package from one or more "
            "capture_operation_intent_transport_metrics.py output files."
        )
    )
    parser.add_argument(
        "--input-glob",
        required=True,
        help="Glob for capture JSON files (example: artifacts/intent-transport-day*.json)",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/operation-intent-decision-package",
        help="Directory to write generated decision artifacts",
    )
    parser.add_argument(
        "--query-threshold-percent",
        type=float,
        default=1.0,
        help="Threshold used when building rollout bundle (default: 1.0)",
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
        default="pre-prod-canary",
        help="Environment scope for memo prefill (default: pre-prod-canary)",
    )
    parser.add_argument(
        "--decision-owner",
        default="backend-oncall",
        help="Decision owner for memo prefill (default: backend-oncall)",
    )
    parser.add_argument(
        "--fail-on-blocked",
        action="store_true",
        help="Exit non-zero when rollout gate evaluation is not promotion-ready",
    )
    parser.add_argument(
        "--manifest-name",
        default="intent-transport-decision-package-manifest.json",
        help="Filename for generated package manifest inside output-dir",
    )
    return parser.parse_args()


def _run_command(command: list[str]) -> None:
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


def main() -> int:
    args = _parse_args()

    root = Path(__file__).resolve().parents[1]
    output_dir = (root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    bundle_path = output_dir / "intent-transport-rollout-bundle.json"
    evaluation_path = output_dir / "intent-transport-rollout-evaluation.json"
    memo_draft_path = output_dir / "intent-transport-decision-memo-draft.json"
    memo_markdown_path = output_dir / "intent-transport-decision-memo.md"
    manifest_path = output_dir / args.manifest_name
    verification_path = output_dir / "intent-transport-decision-package-verification.json"

    _run_command(
        [
            sys.executable,
            str(root / "tools" / "build_operation_intent_rollout_bundle.py"),
            "--input-glob",
            args.input_glob,
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

    evaluate_command = [
        sys.executable,
        str(root / "tools" / "evaluate_operation_intent_rollout_gate.py"),
        "--bundle",
        str(bundle_path),
        "--output",
        str(evaluation_path),
    ]
    if args.fail_on_blocked:
        evaluate_command.append("--fail-on-blocked")

    _run_command(evaluate_command)

    _run_command(
        [
            sys.executable,
            str(root / "tools" / "prefill_operation_intent_decision_memo.py"),
            "--bundle",
            str(bundle_path),
            "--evaluation",
            str(evaluation_path),
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
            "--output",
            str(memo_markdown_path),
        ]
    )

    manifest = {
        "manifest_schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs": {
            "input_glob": args.input_glob,
            "query_threshold_percent": args.query_threshold_percent,
            "strict_rejection_max_delta": args.strict_rejection_max_delta,
            "mismatch_rate_max_per_minute": args.mismatch_rate_max_per_minute,
            "environment_scope": args.environment_scope,
            "decision_owner": args.decision_owner,
            "fail_on_blocked": args.fail_on_blocked,
        },
        "artifacts": {
            "bundle_file": str(bundle_path).replace("\\", "/"),
            "evaluation_file": str(evaluation_path).replace("\\", "/"),
            "memo_draft_file": str(memo_draft_path).replace("\\", "/"),
            "memo_markdown_file": str(memo_markdown_path).replace("\\", "/"),
            "verification_file": str(verification_path).replace("\\", "/"),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    _run_command(
        [
            sys.executable,
            str(root / "tools" / "verify_operation_intent_decision_package.py"),
            "--manifest",
            str(manifest_path),
            "--output",
            str(verification_path),
        ]
    )

    summary = {
        "output_dir": str(output_dir).replace("\\", "/"),
        "bundle_file": str(bundle_path).replace("\\", "/"),
        "evaluation_file": str(evaluation_path).replace("\\", "/"),
        "memo_draft_file": str(memo_draft_path).replace("\\", "/"),
        "memo_markdown_file": str(memo_markdown_path).replace("\\", "/"),
        "manifest_file": str(manifest_path).replace("\\", "/"),
        "verification_file": str(verification_path).replace("\\", "/"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
