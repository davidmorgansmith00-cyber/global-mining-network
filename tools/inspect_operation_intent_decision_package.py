from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Print a compact one-line summary from an operation-intent decision package "
            "manifest, evaluation, and verification artifacts."
        )
    )
    parser.add_argument("--manifest", required=True, help="Path to decision package manifest JSON")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--fail-on-unverified",
        action="store_true",
        help="Exit non-zero when verification status is not true",
    )
    parser.add_argument(
        "--verify-before-inspect",
        action="store_true",
        help=(
            "Recompute verification via verify_operation_intent_decision_package.py before "
            "rendering summary output"
        ),
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional file path to write inspector output payload",
    )
    return parser.parse_args()


def _load_json(path: Path, label: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} is not a JSON object: {path}")
    return payload


def _resolve_artifact(path_text: str, parent: Path) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    return (parent / candidate).resolve()


def _normalize_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _refresh_verification(manifest_path: Path, verification_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).resolve().parents[1] / "tools" / "verify_operation_intent_decision_package.py"),
            "--manifest",
            str(manifest_path),
            "--output",
            str(verification_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in (0, 1):
        message = "\n".join(
            [
                "Verification refresh command failed:",
                completed.stdout.strip(),
                completed.stderr.strip(),
            ]
        )
        raise RuntimeError(message)

    if not verification_path.exists():
        raise RuntimeError(f"Verification refresh did not write expected output file: {verification_path}")


def main() -> int:
    args = _parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise RuntimeError(f"Manifest file does not exist: {manifest_path}")

    manifest = _load_json(manifest_path, "Manifest")
    artifacts = manifest.get("artifacts", {})
    if not isinstance(artifacts, dict):
        raise RuntimeError("Manifest missing artifacts object")

    manifest_parent = manifest_path.resolve().parent
    evaluation_path_text = str(artifacts.get("evaluation_file", ""))
    verification_path_text = str(artifacts.get("verification_file", ""))
    if not evaluation_path_text:
        raise RuntimeError("Manifest artifacts missing evaluation_file")
    if not verification_path_text:
        raise RuntimeError("Manifest artifacts missing verification_file")

    evaluation_path = _resolve_artifact(evaluation_path_text, manifest_parent)
    verification_path = _resolve_artifact(verification_path_text, manifest_parent)

    if not evaluation_path.exists():
        raise RuntimeError(f"Evaluation file does not exist: {evaluation_path}")
    if not verification_path.exists():
        raise RuntimeError(f"Verification file does not exist: {verification_path}")

    if args.verify_before_inspect:
        _refresh_verification(manifest_path.resolve(), verification_path)

    evaluation = _load_json(evaluation_path, "Evaluation")
    verification = _load_json(verification_path, "Verification")
    compact_summary_mismatch_details = _normalize_string_list(
        verification.get("compact_summary_mismatch_details", [])
    )
    compact_summary_mismatch_count = int(
        verification.get("compact_summary_mismatch_count", len(compact_summary_mismatch_details))
    )
    checks = evaluation.get("checks", [])
    if not isinstance(checks, list):
        checks = [checks]

    summary = {
        "manifest": str(manifest_path.resolve()).replace("\\", "/"),
        "decision": str(evaluation.get("decision", "")),
        "promotion_ready": bool(evaluation.get("promotion_ready", False)),
        "passed_checks": int(evaluation.get("passed_checks", 0)),
        "total_checks": int(evaluation.get("total_checks", 0)),
        "checks": checks,
        "verified": bool(verification.get("verified", False)),
        "schema_supported": bool(verification.get("schema_supported", False)),
        "compact_summary_artifacts_present": bool(
            verification.get("compact_summary_artifacts_present", False)
        ),
        "compact_summary_checks_performed": bool(
            verification.get("compact_summary_checks_performed", False)
        ),
        "compact_summary_checks_skipped": bool(
            verification.get("compact_summary_checks_skipped", False)
        ),
        "compact_summary_mismatch_count": compact_summary_mismatch_count,
        "compact_summary_mismatch_details": compact_summary_mismatch_details,
        "failed_checks": evaluation.get("failed_checks", []),
    }

    if args.format == "json":
        rendered = json.dumps(summary, sort_keys=True)
    else:
        failed_checks = summary["failed_checks"]
        failed_checks_text = ",".join(failed_checks) if isinstance(failed_checks, list) else str(failed_checks)
        rendered = (
            "decision={decision} promotion_ready={promotion_ready} checks={passed_checks}/{total_checks} "
            "verified={verified} schema_supported={schema_supported} "
            "summary_artifacts_present={summary_artifacts_present} "
            "summary_checks_performed={summary_checks_performed} "
            "summary_checks_skipped={summary_checks_skipped} "
            "summary_mismatch_count={summary_mismatch_count} failed_checks={failed_checks}".format(
                decision=summary["decision"],
                promotion_ready=str(summary["promotion_ready"]).lower(),
                passed_checks=summary["passed_checks"],
                total_checks=summary["total_checks"],
                verified=str(summary["verified"]).lower(),
                schema_supported=str(summary["schema_supported"]).lower(),
                summary_artifacts_present=str(summary["compact_summary_artifacts_present"]).lower(),
                summary_checks_performed=str(summary["compact_summary_checks_performed"]).lower(),
                summary_checks_skipped=str(summary["compact_summary_checks_skipped"]).lower(),
                summary_mismatch_count=summary["compact_summary_mismatch_count"],
                failed_checks=failed_checks_text,
            )
        )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(rendered)

    if args.fail_on_unverified and not summary["verified"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
