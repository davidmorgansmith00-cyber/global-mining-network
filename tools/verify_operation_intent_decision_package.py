from __future__ import annotations

import argparse
import json
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify an operation-intent decision package manifest by checking artifact "
            "existence and evaluation-to-memo decision consistency."
        )
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to decision package manifest JSON",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write verification JSON output",
    )
    return parser.parse_args()


def _load_json(path: Path, label: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} is not a JSON object: {path}")
    return payload


def _resolve_manifest_artifact(path_str: str, manifest_parent: Path) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate
    return (manifest_parent / candidate).resolve()


def main() -> int:
    args = _parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        raise RuntimeError(f"Manifest file does not exist: {manifest_path}")

    manifest = _load_json(manifest_path, "Manifest")
    schema_version = str(manifest.get("manifest_schema_version", ""))
    supported_schema_versions = {"1.0"}
    artifacts = manifest.get("artifacts", {})
    if not isinstance(artifacts, dict):
        raise RuntimeError("Manifest missing artifacts object")

    required_artifacts = ["bundle_file", "evaluation_file", "memo_draft_file", "memo_markdown_file"]
    manifest_parent = manifest_path.resolve().parent

    artifact_paths: dict[str, Path] = {}
    missing_artifacts: list[str] = []
    for name in required_artifacts:
        value = artifacts.get(name, "")
        if not isinstance(value, str) or not value:
            missing_artifacts.append(name)
            continue
        resolved_path = _resolve_manifest_artifact(value, manifest_parent)
        artifact_paths[name] = resolved_path
        if not resolved_path.exists():
            missing_artifacts.append(name)

    optional_artifacts = ["verification_file", "compact_summary_file", "compact_summary_json_file"]
    output_target = Path(args.output).resolve() if args.output else None
    for name in optional_artifacts:
        value = artifacts.get(name, "")
        if not isinstance(value, str) or not value:
            continue
        resolved_path = _resolve_manifest_artifact(value, manifest_parent)
        artifact_paths[name] = resolved_path
        if output_target and name == "verification_file" and resolved_path == output_target:
            # The verifier may be generating this file in the current run.
            continue
        if not resolved_path.exists():
            missing_artifacts.append(name)

    evaluation_matches_memo = False
    compact_summary_text_matches = True
    compact_summary_json_matches = True
    compact_summary_checks_performed = False
    compact_summary_artifacts_present = False
    compact_summary_mismatch_details: list[str] = []
    mismatch_details = ""
    if not missing_artifacts:
        evaluation = _load_json(artifact_paths["evaluation_file"], "Evaluation")
        memo_draft = _load_json(artifact_paths["memo_draft_file"], "Memo draft")
        verification_payload: dict[str, object] | None = None
        verification_path = artifact_paths.get("verification_file")
        if isinstance(verification_path, Path) and verification_path.exists():
            verification_payload = _load_json(verification_path, "Verification")
        embedded = memo_draft.get("rollout_gate_evaluation", {})
        if not isinstance(embedded, dict):
            embedded = {}

        evaluation_view = {
            "decision": evaluation.get("decision"),
            "promotion_ready": evaluation.get("promotion_ready"),
            "failed_checks": evaluation.get("failed_checks"),
        }
        embedded_view = {
            "decision": embedded.get("decision"),
            "promotion_ready": embedded.get("promotion_ready"),
            "failed_checks": embedded.get("failed_checks"),
        }

        evaluation_matches_memo = evaluation_view == embedded_view
        if not evaluation_matches_memo:
            mismatch_details = (
                "evaluation and embedded memo rollout_gate_evaluation differ: "
                f"evaluation={evaluation_view}, memo={embedded_view}"
            )

        if verification_payload is not None:
            compact_summary_artifacts_present = (
                "compact_summary_file" in artifact_paths
                or "compact_summary_json_file" in artifact_paths
            )
            compact_summary_checks_performed = compact_summary_artifacts_present
            decision = str(evaluation.get("decision", ""))
            promotion_ready = str(bool(evaluation.get("promotion_ready", False))).lower()
            passed_checks = int(evaluation.get("passed_checks", 0))
            total_checks = int(evaluation.get("total_checks", 0))
            verification_verified = bool(verification_payload.get("verified", False))
            verification_schema_supported = bool(verification_payload.get("schema_supported", False))
            verification_compact_summary_artifacts_present = bool(
                verification_payload.get("compact_summary_artifacts_present", False)
            )
            verification_compact_summary_checks_performed = bool(
                verification_payload.get("compact_summary_checks_performed", False)
            )
            verification_compact_summary_checks_skipped = bool(
                verification_payload.get("compact_summary_checks_skipped", False)
            )
            verification_compact_summary_mismatch_details = verification_payload.get(
                "compact_summary_mismatch_details", []
            )
            if not isinstance(verification_compact_summary_mismatch_details, list):
                verification_compact_summary_mismatch_details = [
                    str(verification_compact_summary_mismatch_details)
                ]
            failed_checks_payload = evaluation.get("failed_checks", [])
            failed_checks = (
                ",".join(failed_checks_payload)
                if isinstance(failed_checks_payload, list)
                else str(failed_checks_payload)
            )

            compact_summary_text_expected = (
                f"decision={decision} promotion_ready={promotion_ready} "
                f"checks={passed_checks}/{total_checks} verified={str(verification_verified).lower()} "
                f"schema_supported={str(verification_schema_supported).lower()} "
                f"summary_artifacts_present={str(verification_compact_summary_artifacts_present).lower()} "
                f"summary_checks_performed={str(verification_compact_summary_checks_performed).lower()} "
                f"summary_checks_skipped={str(verification_compact_summary_checks_skipped).lower()} "
                f"summary_mismatch_count={len(verification_compact_summary_mismatch_details)} "
                f"failed_checks={failed_checks}"
            )
            compact_summary_json_expected = {
                "manifest": str(manifest_path.resolve()).replace("\\", "/"),
                "decision": decision,
                "promotion_ready": bool(evaluation.get("promotion_ready", False)),
                "passed_checks": passed_checks,
                "total_checks": total_checks,
                "verified": verification_verified,
                "schema_supported": verification_schema_supported,
                "compact_summary_artifacts_present": verification_compact_summary_artifacts_present,
                "compact_summary_checks_performed": bool(
                    verification_payload.get("compact_summary_checks_performed", False)
                ),
                "compact_summary_checks_skipped": bool(
                    verification_payload.get("compact_summary_checks_skipped", False)
                ),
                "compact_summary_mismatch_count": len(verification_compact_summary_mismatch_details),
                "compact_summary_mismatch_details": verification_compact_summary_mismatch_details,
                "failed_checks": failed_checks_payload,
            }

            if compact_summary_artifacts_present:
                text_summary_path = artifact_paths.get("compact_summary_file")
                if isinstance(text_summary_path, Path):
                    compact_summary_text_actual = text_summary_path.read_text(encoding="utf-8").strip()
                    compact_summary_text_matches = compact_summary_text_actual == compact_summary_text_expected
                    if not compact_summary_text_matches:
                        compact_summary_mismatch_details.append(
                            "compact_summary_file content does not match expected inspector text summary"
                        )

                json_summary_path = artifact_paths.get("compact_summary_json_file")
                if isinstance(json_summary_path, Path):
                    try:
                        compact_summary_json_actual = _load_json(json_summary_path, "Compact summary JSON")
                    except Exception as exc:  # noqa: BLE001
                        compact_summary_json_matches = False
                        compact_summary_mismatch_details.append(
                            f"compact_summary_json_file could not be parsed: {exc}"
                        )
                    else:
                        compact_summary_json_matches = compact_summary_json_actual == compact_summary_json_expected
                        if not compact_summary_json_matches:
                            compact_summary_mismatch_details.append(
                                "compact_summary_json_file content does not match expected inspector JSON summary"
                            )

    schema_supported = schema_version in supported_schema_versions
    verified = (
        (len(missing_artifacts) == 0)
        and evaluation_matches_memo
        and compact_summary_text_matches
        and compact_summary_json_matches
        and schema_supported
    )

    result = {
        "manifest_file": str(manifest_path.resolve()).replace("\\", "/"),
        "manifest_schema_version": schema_version,
        "schema_supported": schema_supported,
        "verified": verified,
        "missing_artifacts": missing_artifacts,
        "evaluation_matches_memo": evaluation_matches_memo,
        "compact_summary_artifacts_present": compact_summary_artifacts_present,
        "compact_summary_checks_performed": compact_summary_checks_performed,
        "compact_summary_checks_skipped": not compact_summary_checks_performed,
        "compact_summary_text_matches": compact_summary_text_matches,
        "compact_summary_json_matches": compact_summary_json_matches,
        "compact_summary_mismatch_details": compact_summary_mismatch_details,
        "mismatch_details": mismatch_details,
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")

    print(text)
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
