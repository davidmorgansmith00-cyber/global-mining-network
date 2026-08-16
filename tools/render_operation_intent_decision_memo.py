from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a markdown decision memo draft from prefill_operation_intent_decision_memo.py JSON output."
    )
    parser.add_argument("--input", required=True, help="Path to memo draft JSON")
    parser.add_argument(
        "--evaluation",
        default="",
        help="Optional rollout evaluation JSON path from evaluate_operation_intent_rollout_gate.py",
    )
    parser.add_argument("--output", default="", help="Optional path to write markdown output")
    return parser.parse_args()


def _get(data: dict[str, object], *keys: str) -> object:
    current: object = data
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key, "")
    return current


def _markdown_from_draft(payload: dict[str, object], evaluation: dict[str, object] | None) -> str:
    resolved_evaluation = evaluation
    if resolved_evaluation is None:
        embedded_evaluation = payload.get("rollout_gate_evaluation", {})
        if isinstance(embedded_evaluation, dict):
            resolved_evaluation = embedded_evaluation

    lines = [
        "# Operation Intent Production Rollout Decision Memo",
        "",
        f"Generated at: {datetime.now(UTC).isoformat()}",
        "",
        "## Decision Summary",
        f"- Decision date: {_get(payload, 'decision_summary', 'decision_date')}",
        f"- Environment scope: {_get(payload, 'decision_summary', 'environment_scope')}",
        f"- Proposed action: {_get(payload, 'decision_summary', 'proposed_action')}",
        f"- Decision owner: {_get(payload, 'decision_summary', 'decision_owner')}",
        "",
        "## Evidence Inputs",
        f"- Rollout bundle: {_get(payload, 'evidence_inputs', 'rollout_bundle_file')}",
        f"- Strict-mode sunset test log: {_get(payload, 'evidence_inputs', 'strict_mode_sunset_test_log')}",
        f"- Error-rate comparison report: {_get(payload, 'evidence_inputs', 'error_rate_comparison_report')}",
        f"- Client compatibility sign-off: {_get(payload, 'evidence_inputs', 'client_compatibility_signoff_record')}",
        "",
        "## Threshold Evaluation",
        "### Query Share",
        f"- overall_query_share_percent: {_get(payload, 'threshold_evaluation', 'query_share_threshold', 'overall_query_share_percent')}",
        f"- days_below_threshold: {_get(payload, 'threshold_evaluation', 'query_share_threshold', 'days_below_threshold')}",
        f"- query_share_window_pass: {_get(payload, 'threshold_evaluation', 'query_share_threshold', 'query_share_window_pass')}",
        f"- auto_result: {_get(payload, 'threshold_evaluation', 'query_share_threshold', 'auto_result')}",
        "",
        "### Strict Rejection Stability",
        f"- total_query_rejected_strict_delta: {_get(payload, 'threshold_evaluation', 'strict_rejection_stability', 'total_query_rejected_strict_delta')}",
        f"- strict_mode_window_periods_reviewed: {_get(payload, 'threshold_evaluation', 'strict_rejection_stability', 'strict_mode_window_periods_reviewed')}",
        f"- auto_result: {_get(payload, 'threshold_evaluation', 'strict_rejection_stability', 'auto_result')}",
        "",
        "### Mismatch Stability",
        f"- max_mismatch_rate_per_minute: {_get(payload, 'threshold_evaluation', 'mismatch_stability', 'max_mismatch_rate_per_minute')}",
        f"- baseline_mismatch_rate_per_minute: {_get(payload, 'threshold_evaluation', 'mismatch_stability', 'baseline_mismatch_rate_per_minute')}",
        f"- sustained_duration_observed: {_get(payload, 'threshold_evaluation', 'mismatch_stability', 'sustained_duration_observed')}",
        f"- auto_result: {_get(payload, 'threshold_evaluation', 'mismatch_stability', 'auto_result')}",
        "",
        "### Error-Rate Safety",
        f"- baseline_400_401_rates: {_get(payload, 'threshold_evaluation', 'error_rate_safety', 'baseline_400_401_rates')}",
        f"- canary_400_401_rates: {_get(payload, 'threshold_evaluation', 'error_rate_safety', 'canary_400_401_rates')}",
        f"- auto_result: {_get(payload, 'threshold_evaluation', 'error_rate_safety', 'auto_result')}",
        "",
        "### Client Regression Gate",
        f"- open_p1_count: {_get(payload, 'threshold_evaluation', 'client_regression_gate', 'open_p1_count')}",
        f"- open_p2_count: {_get(payload, 'threshold_evaluation', 'client_regression_gate', 'open_p2_count')}",
        f"- auto_result: {_get(payload, 'threshold_evaluation', 'client_regression_gate', 'auto_result')}",
        "",
        "## Rollback Trigger Review",
        f"- header_401_rate_exceeded_2x_for_30m: {_get(payload, 'rollback_trigger_review', 'header_401_rate_exceeded_2x_for_30m')}",
        f"- mismatch_threshold_exceeded_for_30m: {_get(payload, 'rollback_trigger_review', 'mismatch_threshold_exceeded_for_30m')}",
        f"- critical_compatibility_cohort_blocked: {_get(payload, 'rollback_trigger_review', 'critical_compatibility_cohort_blocked')}",
        f"- incident_ids_and_remediation: {_get(payload, 'rollback_trigger_review', 'incident_ids_and_remediation')}",
        "",
        "## Final Recommendation",
        f"- recommended_action: {_get(payload, 'final_recommendation', 'recommended_action')}",
        f"- rationale_summary: {_get(payload, 'final_recommendation', 'rationale_summary')}",
        f"- required_followups_before_production: {_get(payload, 'final_recommendation', 'required_followups_before_production')}",
        "",
        "## Approvals",
        f"- backend_owner: {_get(payload, 'approvals', 'backend_owner')}",
        f"- client_owner: {_get(payload, 'approvals', 'client_owner')}",
        f"- qa_owner: {_get(payload, 'approvals', 'qa_owner')}",
        f"- operations_owner: {_get(payload, 'approvals', 'operations_owner')}",
        f"- final_approver: {_get(payload, 'approvals', 'final_approver')}",
        "",
    ]

    if isinstance(resolved_evaluation, dict) and resolved_evaluation:
        failed_checks = resolved_evaluation.get("failed_checks", [])
        lines.extend(
            [
                "## Rollout Gate Evaluation",
                f"- promotion_ready: {resolved_evaluation.get('promotion_ready', '')}",
                f"- decision: {resolved_evaluation.get('decision', '')}",
                f"- failed_checks: {failed_checks}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> int:
    args = _parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise RuntimeError(f"Input file does not exist: {input_path}")

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Memo draft input must be a JSON object")

    evaluation: dict[str, object] | None = None
    if args.evaluation:
        evaluation_path = Path(args.evaluation)
        if not evaluation_path.exists():
            raise RuntimeError(f"Evaluation file does not exist: {evaluation_path}")
        loaded_evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        if not isinstance(loaded_evaluation, dict):
            raise RuntimeError("Evaluation input must be a JSON object")
        evaluation = loaded_evaluation

    markdown = _markdown_from_draft(payload, evaluation)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")

    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
