# Operation Intent Query Sunset Release Checklist

Status: Draft
Version: 1.0
Date: 2026-08-16

Objective:
- Execute a controlled migration from query-compatible operation-intent session binding to header-only transport.

## Timeline (Proposed)
1. 2026-08-19: Publish deprecation notice in release notes and API docs.
2. 2026-08-26: Ensure first-party clients default to `X-Session-Id` header transport.
3. 2026-09-02: Enable strict-mode canary in pre-prod (`OPERATION_INTENT_REQUIRE_HEADER_BINDING=true`).
4. 2026-09-16: Review 14-day canary metrics and decide production promotion readiness.
5. 2026-09-23: Production rollout decision gate for header-only enforcement.

## Release Note Template
Title:
- Deprecation Notice: Operation Intent Query Session Binding

Body:
- Operation intent endpoints currently accept both query (`session_id`) and header (`X-Session-Id`) session binding during migration.
- Query-based binding is deprecated and will be sunset after rollout criteria are met.
- Clients should migrate to header-based transport immediately.

Affected endpoints:
- `POST /api/v1/blockchain/operations/intents/start`
- `POST /api/v1/blockchain/operations/intents/stop`

Required client action:
- Send session binding via `X-Session-Id` header.
- Do not include `player_id` in request payloads.

## Go/No-Go Criteria for Promotion
Promote to next stage only when all are true:
1. `query` transport share is below 1% for 14 consecutive days.
2. `query_rejected_strict` remains near zero outside explicit canary windows.
3. `mismatch` error mode does not show sustained increase versus pre-canary baseline.
4. No unresolved P1/P2 client regressions for start/stop intent flows.

## Required Evidence Bundle
Capture and attach:
1. Metrics export snapshot for `operation_intent_transport_requests_total` across modes (`query`, `header`, `dual_match`, `mismatch`, `query_rejected_strict`).
2. Error-rate comparison for 400/401 on operation-intent endpoints pre- and post-canary.
3. Integration test evidence with strict mode enabled and sunset tests gated by `GMN_ENABLE_QUERY_SUNSET_TESTS=1`.
4. Client compatibility sign-off from all supported first-party versions.
5. Completed production decision package using `docs/operation-intents-production-rollout-decision-memo-template.md`.

## Rollback Triggers
Rollback to dual-mode (query + header accepted) if any trigger occurs:
1. Header-path 401 rate >2x baseline for at least 30 minutes.
2. `mismatch` mode exceeds agreed threshold for at least 30 minutes.
3. Critical compatibility cohort cannot start or stop operations.

## Commands
Run full blockchain integration suite:
- `python -m unittest tests/integration/test_blockchain_status_api.py -v`

Run sunset-gated tests:
- PowerShell: `$env:GMN_ENABLE_QUERY_SUNSET_TESTS='1'; python -m unittest tests/integration/test_blockchain_status_api.py -v`

Capture a single transport metrics snapshot:
- PowerShell: `$env:MAINTENANCE_AUTH_TOKEN='<token>'; python tools/capture_operation_intent_transport_metrics.py --base-url http://127.0.0.1:8000 --output artifacts/intent-transport-snapshot.json`

Capture short trend evidence (example: 15 minutes at 60-second interval):
- PowerShell: `$env:MAINTENANCE_AUTH_TOKEN='<token>'; python tools/capture_operation_intent_transport_metrics.py --base-url http://127.0.0.1:8000 --samples 15 --interval-seconds 60 --output artifacts/intent-transport-trend-15m.json`

Build 14-day rollout bundle from daily captures:
- PowerShell: `python tools/build_operation_intent_rollout_bundle.py --input-glob "artifacts/intent-transport-day*.json" --query-threshold-percent 1.0 --strict-rejection-max-delta 0 --mismatch-rate-max-per-minute 0.1 --output artifacts/intent-transport-rollout-bundle.json`

Pre-fill production decision memo draft from rollout bundle:
- PowerShell: `python tools/prefill_operation_intent_decision_memo.py --bundle artifacts/intent-transport-rollout-bundle.json --evaluation artifacts/intent-transport-rollout-evaluation.json --environment-scope pre-prod-canary --decision-owner backend-oncall --output artifacts/intent-transport-decision-memo-draft.json`

Render a human-readable markdown memo draft from prefilled JSON:
- PowerShell: `python tools/render_operation_intent_decision_memo.py --input artifacts/intent-transport-decision-memo-draft.json --output artifacts/intent-transport-decision-memo.md`
- Optional override: add `--evaluation artifacts/intent-transport-rollout-evaluation.json` to override embedded gate data with a specific evaluation snapshot.

Run a full offline dry run (synthetic 14-day artifacts + bundle + memo draft):
- PowerShell: `python tools/run_operation_intent_rollout_dry_run.py --output-dir artifacts/operation-intent-dry-run --days 14 --query-threshold-percent 1.0 --strict-rejection-max-delta 0 --mismatch-rate-max-per-minute 0.1 --environment-scope pre-prod-canary --decision-owner backend-oncall`

Read computed query share from helper output:
- Use `query_share_from_deltas.query_share_percent` from the output JSON as the canonical query-share value for promotion gates.
- Supporting fields:
	- `query_share_from_deltas.query_delta`
	- `query_share_from_deltas.total_transport_delta`

Read promotion-gate summary from rollout bundle output:
- `aggregate.overall_query_share_percent`
- `aggregate.days_below_threshold`
- `aggregate.all_days_below_threshold`
- `aggregate.total_query_rejected_strict_delta`
- `aggregate.max_mismatch_rate_per_minute`
- `threshold_checks.query_share_window_pass`
- `threshold_checks.strict_rejection_window_pass`
- `threshold_checks.mismatch_rate_window_pass`

Evaluate promotion readiness from bundle thresholds:
- PowerShell: `python tools/evaluate_operation_intent_rollout_gate.py --bundle artifacts/intent-transport-rollout-bundle.json --output artifacts/intent-transport-rollout-evaluation.json`
- Optional CI-gating mode: `python tools/evaluate_operation_intent_rollout_gate.py --bundle artifacts/intent-transport-rollout-bundle.json --fail-on-blocked`
- Read summary fields from evaluation output: `promotion_ready`, `decision`, `passed_checks`, `total_checks`, `failed_checks`.

Build the full decision artifact package in one command:
- PowerShell: `python tools/build_operation_intent_decision_package.py --input-glob "artifacts/intent-transport-day*.json" --output-dir artifacts/operation-intent-decision-package --query-threshold-percent 1.0 --strict-rejection-max-delta 0 --mismatch-rate-max-per-minute 0.1 --environment-scope pre-prod-canary --decision-owner backend-oncall`
- Optional CI-gating mode: append `--fail-on-blocked` to return a non-zero exit if rollout thresholds do not pass.
- Package outputs include `intent-transport-decision-package-manifest.json` as an index of inputs, thresholds, and generated artifact paths.

Read auto-filled draft memo fields:
- `threshold_evaluation.query_share_threshold.auto_result`
- `threshold_evaluation.strict_rejection_stability.auto_result`
- `threshold_evaluation.mismatch_stability.auto_result`
- `rollout_gate_evaluation.decision`
- `rollout_gate_evaluation.promotion_ready`
- `final_recommendation.recommended_action` (manual decision required)

Dry-run expected outputs:
- `artifacts/operation-intent-dry-run/intent-transport-day01.json` ... `intent-transport-day14.json`
- `artifacts/operation-intent-dry-run/intent-transport-rollout-bundle.json`
- `artifacts/operation-intent-dry-run/intent-transport-rollout-evaluation.json`
- `artifacts/operation-intent-dry-run/intent-transport-decision-memo-draft.json`
- `artifacts/operation-intent-dry-run/intent-transport-decision-memo.md`

## Owner Checklist
1. Backend owner approves strict-mode metrics health.
2. Client owner confirms header transport rollout completion.
3. QA owner confirms sunset-gated test pass evidence.
4. Operations owner confirms rollback playbook readiness.
5. Final approver signs completed production decision memo template.
