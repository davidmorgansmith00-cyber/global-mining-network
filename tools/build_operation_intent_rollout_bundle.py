from __future__ import annotations

import argparse
import glob
import json
from datetime import UTC, datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a single rollout-decision JSON bundle from one or more "
            "capture_operation_intent_transport_metrics.py output files."
        )
    )
    parser.add_argument(
        "--inputs",
        nargs="*",
        default=[],
        help="Explicit helper output JSON files to include",
    )
    parser.add_argument(
        "--input-glob",
        default="",
        help="Optional glob for helper output JSON files (example: artifacts/intent-transport-*.json)",
    )
    parser.add_argument(
        "--query-threshold-percent",
        type=float,
        default=1.0,
        help="Query-share threshold for pass/fail summaries (default: 1.0)",
    )
    parser.add_argument(
        "--strict-rejection-max-delta",
        type=int,
        default=0,
        help="Maximum allowed total query_rejected_strict delta across inputs (default: 0)",
    )
    parser.add_argument(
        "--mismatch-rate-max-per-minute",
        type=float,
        default=0.1,
        help="Maximum allowed mismatch rate_per_minute observed across inputs (default: 0.1)",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output file path for bundle JSON",
    )
    return parser.parse_args()


def _collect_input_files(explicit_inputs: list[str], input_glob: str) -> list[Path]:
    paths: set[Path] = set()
    for item in explicit_inputs:
        paths.add(Path(item))

    if input_glob:
        for matched in glob.glob(input_glob):
            paths.add(Path(matched))

    resolved = sorted(path for path in paths if path.exists())
    if not resolved:
        raise RuntimeError("No input files found; provide --inputs or --input-glob with existing files")
    return resolved


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _extract_entry(path: Path, payload: dict[str, object]) -> dict[str, object]:
    query_share = payload.get("query_share_from_deltas", {})
    summary = payload.get("summary", {})

    query_share_percent = _safe_float(
        query_share.get("query_share_percent") if isinstance(query_share, dict) else 0
    )
    query_delta = _safe_int(query_share.get("query_delta") if isinstance(query_share, dict) else 0)
    total_delta = _safe_int(query_share.get("total_transport_delta") if isinstance(query_share, dict) else 0)

    mismatch_rate = 0.0
    strict_rejected_delta = 0
    if isinstance(summary, dict):
        mismatch_rate = _safe_float(summary.get("mismatch", {}).get("rate_per_minute"))
        strict_rejected_delta = _safe_int(summary.get("query_rejected_strict", {}).get("delta"))

    return {
        "file": str(path).replace("\\", "/"),
        "finished_at": str(payload.get("finished_at", "")),
        "elapsed_seconds": _safe_float(payload.get("elapsed_seconds", 0)),
        "query_share_percent": query_share_percent,
        "query_delta": query_delta,
        "total_transport_delta": total_delta,
        "mismatch_rate_per_minute": mismatch_rate,
        "query_rejected_strict_delta": strict_rejected_delta,
    }


def _load_entries(files: list[Path]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in files:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        entries.append(_extract_entry(path, payload))

    entries.sort(key=lambda item: str(item.get("finished_at", "")))
    if not entries:
        raise RuntimeError("No valid helper payloads were parsed from inputs")
    return entries


def _build_bundle(
    entries: list[dict[str, object]],
    query_threshold_percent: float,
    strict_rejection_max_delta: int,
    mismatch_rate_max_per_minute: float,
) -> dict[str, object]:
    total_query_delta = sum(_safe_int(item.get("query_delta", 0)) for item in entries)
    total_transport_delta = sum(_safe_int(item.get("total_transport_delta", 0)) for item in entries)
    overall_query_share_percent = (
        (total_query_delta / total_transport_delta) * 100.0 if total_transport_delta > 0 else 0.0
    )

    days_below_threshold = sum(
        1 for item in entries if _safe_float(item.get("query_share_percent", 0.0)) < query_threshold_percent
    )
    all_days_below_threshold = days_below_threshold == len(entries)

    max_query_share_percent = max(_safe_float(item.get("query_share_percent", 0.0)) for item in entries)
    max_mismatch_rate_per_minute = max(_safe_float(item.get("mismatch_rate_per_minute", 0.0)) for item in entries)
    total_query_rejected_strict_delta = sum(
        _safe_int(item.get("query_rejected_strict_delta", 0)) for item in entries
    )

    strict_rejection_window_pass = total_query_rejected_strict_delta <= strict_rejection_max_delta
    mismatch_rate_window_pass = max_mismatch_rate_per_minute <= mismatch_rate_max_per_minute

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "inputs_count": len(entries),
        "query_threshold_percent": query_threshold_percent,
        "strict_rejection_max_delta": strict_rejection_max_delta,
        "mismatch_rate_max_per_minute": mismatch_rate_max_per_minute,
        "daily_entries": entries,
        "aggregate": {
            "total_query_delta": total_query_delta,
            "total_transport_delta": total_transport_delta,
            "overall_query_share_percent": round(overall_query_share_percent, 4),
            "days_below_threshold": days_below_threshold,
            "all_days_below_threshold": all_days_below_threshold,
            "max_query_share_percent": round(max_query_share_percent, 4),
            "max_mismatch_rate_per_minute": round(max_mismatch_rate_per_minute, 4),
            "total_query_rejected_strict_delta": total_query_rejected_strict_delta,
        },
        "threshold_checks": {
            "query_share_window_pass": all_days_below_threshold,
            "query_share_window_rule": (
                "All included entries must have query_share_percent below query_threshold_percent"
            ),
            "strict_rejection_window_pass": strict_rejection_window_pass,
            "strict_rejection_window_rule": (
                "Total query_rejected_strict delta across inputs must be <= strict_rejection_max_delta"
            ),
            "mismatch_rate_window_pass": mismatch_rate_window_pass,
            "mismatch_rate_window_rule": (
                "Maximum mismatch_rate_per_minute across inputs must be <= mismatch_rate_max_per_minute"
            ),
        },
    }


def main() -> int:
    args = _parse_args()
    files = _collect_input_files(args.inputs, args.input_glob)
    entries = _load_entries(files)
    bundle = _build_bundle(
        entries,
        query_threshold_percent=args.query_threshold_percent,
        strict_rejection_max_delta=args.strict_rejection_max_delta,
        mismatch_rate_max_per_minute=args.mismatch_rate_max_per_minute,
    )

    text = json.dumps(bundle, indent=2, sort_keys=True)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())