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

    evaluation_matches_memo = False
    mismatch_details = ""
    if not missing_artifacts:
        evaluation = _load_json(artifact_paths["evaluation_file"], "Evaluation")
        memo_draft = _load_json(artifact_paths["memo_draft_file"], "Memo draft")
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

    verified = (len(missing_artifacts) == 0) and evaluation_matches_memo

    result = {
        "manifest_file": str(manifest_path.resolve()).replace("\\", "/"),
        "verified": verified,
        "missing_artifacts": missing_artifacts,
        "evaluation_matches_memo": evaluation_matches_memo,
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
