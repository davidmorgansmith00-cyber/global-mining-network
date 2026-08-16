# Operation Intent Production Rollout Decision Memo Template

Status: Template
Version: 1.0
Date: 2026-08-16

Use this template for the production go or no-go decision after strict-mode canary evidence collection.

Recommended preparation flow:
1. Build rollout bundle with `tools/build_operation_intent_rollout_bundle.py`.
2. Generate draft memo JSON with `tools/prefill_operation_intent_decision_memo.py`.
3. Copy generated values into this template and complete manual-review sections.

Optional dry run:
- Execute `tools/run_operation_intent_rollout_dry_run.py` to generate a synthetic 14-day artifact set and verify the full workflow before canary week.

## 1. Decision Summary
- Decision date:
- Environment scope:
- Proposed action:
  - Go: proceed with header-only enforcement
  - No-Go: keep dual-mode and continue remediation
- Decision owner:

## 2. Evidence Inputs
Attach files generated from tools/capture_operation_intent_transport_metrics.py:
1. Baseline snapshot file path:
2. Canary trend file path:
3. Final 14-day summary file path:

Attach rollout bundle generated from tools/build_operation_intent_rollout_bundle.py:
1. Rollout bundle file path:

Attach memo draft generated from tools/prefill_operation_intent_decision_memo.py:
1. Memo draft JSON file path:

Attach additional evidence:
1. Strict-mode sunset test run log (GMN_ENABLE_QUERY_SUNSET_TESTS=1)
2. 400 and 401 error-rate comparison report
3. Client compatibility sign-off record

## 3. Helper Output Mapping
The helper output JSON contains:
- snapshots: list of captured counter maps by mode
- summary: per-mode first, last, delta, and rate_per_minute
- query_share_from_deltas: canonical query-share calculation derived from `query`, `header`, and `dual_match` deltas

The rollout bundle JSON contains:
- daily_entries: normalized per-capture summary rows
- aggregate: combined window-level totals and maxima
- threshold_checks: machine-evaluated pass/fail booleans for configured threshold gates

Required mode keys for review:
- query
- header
- dual_match
- mismatch
- query_rejected_strict

## 4. Threshold Evaluation
Complete all checks with explicit pass/fail results.

1. Query share threshold
- Rule: query transport share is below 1% for 14 consecutive days.
- Calculation input:
  - aggregate.overall_query_share_percent:
  - aggregate.days_below_threshold:
  - aggregate.all_days_below_threshold:
  - threshold_checks.query_share_window_pass:
- Result: Pass or Fail

2. Strict rejection stability
- Rule: query_rejected_strict remains near zero outside planned strict-mode windows.
- Calculation input:
  - aggregate.total_query_rejected_strict_delta:
  - threshold_checks.strict_rejection_window_pass:
  - strict-mode window periods reviewed:
- Result: Pass or Fail

3. Mismatch stability
- Rule: mismatch does not show sustained increase versus pre-canary baseline.
- Calculation input:
  - baseline mismatch rate_per_minute:
  - aggregate.max_mismatch_rate_per_minute:
  - threshold_checks.mismatch_rate_window_pass:
  - sustained duration observed:
- Result: Pass or Fail

4. Error-rate safety
- Rule: no material regression in 400 or 401 rates attributable to transport migration.
- Calculation input:
  - baseline 400/401 rates:
  - canary 400/401 rates:
- Result: Pass or Fail

5. Client regression gate
- Rule: no unresolved P1 or P2 client regressions in start or stop intent flow.
- Calculation input:
  - open P1 count:
  - open P2 count:
- Result: Pass or Fail

## 5. Rollback Trigger Review
Check whether any rollback trigger was observed:
1. Header-path 401 rate exceeded 2x baseline for 30+ minutes.
2. Mismatch exceeded agreed threshold for 30+ minutes.
3. Critical compatibility cohort could not start or stop operations.

- Trigger observed: Yes or No
- If yes, provide incident IDs and remediation status:

## 6. Final Recommendation
- Recommended action: Go or No-Go
- Rationale summary:
- Required follow-ups before production action:

## 7. Approvals
- Backend owner:
- Client owner:
- QA owner:
- Operations owner:
- Final approver:
