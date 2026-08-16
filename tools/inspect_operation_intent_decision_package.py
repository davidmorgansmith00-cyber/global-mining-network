from __future__ import annotations

import argparse
import json
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

    evaluation = _load_json(evaluation_path, "Evaluation")
    verification = _load_json(verification_path, "Verification")

    summary = {
        "manifest": str(manifest_path.resolve()).replace("\\", "/"),
        "decision": str(evaluation.get("decision", "")),
        "promotion_ready": bool(evaluation.get("promotion_ready", False)),
        "passed_checks": int(evaluation.get("passed_checks", 0)),
        "total_checks": int(evaluation.get("total_checks", 0)),
        "verified": bool(verification.get("verified", False)),
        "schema_supported": bool(verification.get("schema_supported", False)),
        "compact_summary_checks_performed": bool(
            verification.get("compact_summary_checks_performed", False)
        ),
        "compact_summary_checks_skipped": bool(
            verification.get("compact_summary_checks_skipped", False)
        ),
        "failed_checks": evaluation.get("failed_checks", []),
    }

    if args.format == "json":
        print(json.dumps(summary, sort_keys=True))
    else:
        failed_checks = summary["failed_checks"]
        failed_checks_text = ",".join(failed_checks) if isinstance(failed_checks, list) else str(failed_checks)
        print(
            "decision={decision} promotion_ready={promotion_ready} checks={passed_checks}/{total_checks} "
            "verified={verified} schema_supported={schema_supported} failed_checks={failed_checks}".format(
                decision=summary["decision"],
                promotion_ready=str(summary["promotion_ready"]).lower(),
                passed_checks=summary["passed_checks"],
                total_checks=summary["total_checks"],
                verified=str(summary["verified"]).lower(),
                schema_supported=str(summary["schema_supported"]).lower(),
                failed_checks=failed_checks_text,
            )
        )

    if args.fail_on_unverified and not summary["verified"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
