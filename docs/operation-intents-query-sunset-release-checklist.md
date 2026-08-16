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
- Optional override: use `--manifest-name <filename>.json` to customize the manifest output filename.
- Package outputs also include `intent-transport-decision-package-verification.json` generated by the verifier for handoff integrity evidence.
- Package outputs include `intent-transport-decision-package-summary.txt` for a compact one-line gate status summary.
- Package outputs include `intent-transport-decision-package-summary.json` for machine-readable compact gate status fields.
- Package outputs include `intent-transport-decision-package-inspector-summary.txt` and `intent-transport-decision-package-inspector-summary.json` as refreshed inspector snapshots (`--verify-before-inspect`) for handoff-friendly status reporting.
- Compact summary `.txt` and `.json` artifacts are emitted using the same inspector logic as `tools/inspect_operation_intent_decision_package.py` to keep formatting and fields consistent.
- Decision package builder performs a final summary refresh and verification pass after summary artifacts are registered, ensuring summary files and verifier state are fully consistent at handoff time.
- The manifest `artifacts` section now includes `verification_file` alongside bundle/evaluation/memo paths.
- Manifest schema is versioned (`manifest_schema_version`) and verifier output includes `schema_supported` for compatibility checks.
- Decision-package command output now includes `verification_verified` and `verification_schema_supported` for quick pass/fail parsing in CI logs.
- Decision-package command output also includes `verification_compact_summary_checks_performed` and `verification_compact_summary_checks_skipped` to make compatibility-path verification behavior explicit.
- Decision-package command output includes `verification_compact_summary_mismatch_count` and `verification_compact_summary_mismatch_details` for machine-readable compact-summary mismatch diagnostics.
- Decision-package command output includes `verification_compact_summary_artifacts_present` to distinguish legacy manifests from manifests that include compact summary artifacts.
- Decision-package command output includes refreshed inspector fields: `inspector_verified`, `inspector_mismatch_count`, and `inspector_mismatch_details`.
- Decision-package verifier now validates optional inspector summary artifacts (`inspector_summary_file`, `inspector_summary_json_file`) and emits parity fields (`inspector_summary_artifacts_present`, `inspector_summary_checks_performed`, `inspector_summary_checks_skipped`, `inspector_summary_mismatch_details`).
- Decision-package and dry-run command outputs now propagate verifier inspector-summary diagnostics (`verification_inspector_summary_*` and `decision_package_inspector_summary_*`).
- Dry-run regression now asserts expected boolean/count/list values for compact-summary and inspector-summary parity fields, not only field existence.
- Verifier output now includes explicit mismatch counters: `compact_summary_mismatch_count` and `inspector_summary_mismatch_count`.
- Dry-run now prefers builder-emitted inspector status fields (`inspector_verified`, `inspector_mismatch_count`, `inspector_mismatch_details`) with inspector-summary JSON as fallback.
- Builder and dry-run outputs now also propagate verifier inspector parity booleans: `verification_inspector_summary_text_matches`, `verification_inspector_summary_json_matches`, `decision_package_inspector_summary_text_matches`, and `decision_package_inspector_summary_json_matches`.
- Verifier regression suite now explicitly covers malformed `inspector_summary_json_file` handling (non-JSON payload becomes structured mismatch diagnostics).
- Builder and dry-run outputs now surface verifier `evaluation_matches_memo` status (`verification_evaluation_matches_memo` / `decision_package_evaluation_matches_memo`) for direct contract-gate checks.
- Dry-run now prefers builder verification fields for `decision_package_verified` and `decision_package_schema_supported`, falling back to compact-summary JSON only when needed.
- Inspector summary rendering now prefers verifier `compact_summary_mismatch_count` when present (with details-length fallback), and regression coverage validates this stale/tampered verification behavior.
- Verifier backward-compatibility regression now also covers manifests that omit only `inspector_summary_*` artifact keys (compact-summary checks still enforced).
- Builder and dry-run outputs now include verifier failure-context fields `verification_missing_artifacts`/`verification_mismatch_details` and `decision_package_verification_missing_artifacts`/`decision_package_verification_mismatch_details` for machine-readable debugging.
- Dry-run output now includes `decision_package_failed_checks`, sourced from compact summary JSON, so blocked-gate reasons are immediately available in one payload.
- Dry-run output now includes `decision_package_passed_checks` and `decision_package_total_checks` for compact gate-score reporting in the same payload.
- Builder and dry-run outputs now also expose verifier compact-summary match booleans: `verification_compact_summary_text_matches`, `verification_compact_summary_json_matches`, `decision_package_compact_summary_text_matches`, and `decision_package_compact_summary_json_matches`.
- Builder and dry-run outputs now also expose direct evaluation gate fields: `verification_decision`, `verification_promotion_ready`, `verification_passed_checks`, `verification_total_checks`, `verification_failed_checks`, and the matching `decision_package_*` fields.
- Builder and dry-run outputs now also expose per-check evaluation details via `verification_checks` and `decision_package_checks` for deeper CI diagnostics.
- Inspector JSON now also exposes the evaluation `checks` list for parity with builder/dry-run per-check diagnostics.
- Regression coverage now compares emitted `checks` arrays verbatim against the evaluation artifact so content drift is caught, not just array length.
- Verification JSON now carries the `checks` vector itself so downstream summaries can prefer the file-backed contract instead of rehydrating from the evaluation artifact.
- Inspector output now prefers the persisted verification `checks` vector when present so the rendered summary stays aligned with the file-backed contract.
- Dry-run output now also prefers the persisted verification `checks` vector, removing the remaining compact-summary fallback for per-check reporting.
- Builder inspector status fields now prefer the verification payload over the raw inspector JSON, keeping the package summary aligned with the persisted contract.
- Dry-run inspector status fields now prefer the builder's verification-backed inspector fields, removing the last raw inspector JSON fallback in the package summary.
- Dry-run no longer loads the raw inspector JSON for status derivation, making the builder-backed contract explicit.
- Builder no longer uses raw inspector JSON to backfill inspector status fields; the verification payload is now the sole source for those values.

Verify generated package integrity:
- PowerShell: `python tools/verify_operation_intent_decision_package.py --manifest artifacts/operation-intent-decision-package/intent-transport-decision-package-manifest.json`
- The verifier checks artifact path existence and validates that `rollout_gate_evaluation` embedded in memo draft matches the standalone evaluation artifact.
- When compact summary artifacts are present in the manifest, the verifier also checks that `.txt` and `.json` summary contents match expected values derived from evaluation + verification artifacts.
- If the compact summary JSON artifact is malformed, verifier marks package as unverified and reports a compact-summary parse mismatch detail.
- Backward compatibility: for older manifest files that do not include compact summary artifact keys, verifier still supports schema `1.0` and skips compact-summary consistency checks.
- Verifier output includes `compact_summary_checks_performed` and `compact_summary_checks_skipped` to make compatibility-path behavior explicit in CI logs.
- Verifier output also includes `compact_summary_artifacts_present` so CI can distinguish whether compact summary artifacts were provided by the manifest.

Print compact package gate summary:
- PowerShell: `python tools/inspect_operation_intent_decision_package.py --manifest artifacts/operation-intent-decision-package/intent-transport-decision-package-manifest.json`
- JSON mode: append `--format json`.
- CI mode: append `--fail-on-unverified` to return non-zero when verification status is false.
- Fresh-check mode: append `--verify-before-inspect` to recompute verification from current artifacts before printing summary.
- File output mode: append `--output <path>` to write the rendered inspector output payload to disk.
- `--output` can be combined with `--fail-on-unverified` to persist diagnostics even when the command exits non-zero.
- Inspector JSON output includes compact summary verification path flags: `compact_summary_checks_performed` and `compact_summary_checks_skipped`.
- Inspector JSON output includes compact summary mismatch diagnostics: `compact_summary_mismatch_count` and `compact_summary_mismatch_details`.
- Inspector text output now includes compatibility-path fields: `summary_artifacts_present`, `summary_checks_performed`, and `summary_checks_skipped`.
- Inspector text output also includes `summary_mismatch_count` for compact one-line mismatch signal visibility.

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
- `artifacts/operation-intent-dry-run/decision-package/intent-transport-decision-package-manifest.json`
- `artifacts/operation-intent-dry-run/decision-package/intent-transport-decision-package-verification.json`
- `artifacts/operation-intent-dry-run/decision-package/intent-transport-decision-package-summary.txt`
- `artifacts/operation-intent-dry-run/decision-package/intent-transport-decision-package-summary.json`
- `artifacts/operation-intent-dry-run/decision-package/intent-transport-decision-package-inspector-summary.txt`
- `artifacts/operation-intent-dry-run/decision-package/intent-transport-decision-package-inspector-summary.json`
- Dry-run now reuses inspector summary artifacts emitted by `build_operation_intent_decision_package.py` rather than invoking inspector separately.

Dry-run quick gate fields in command JSON output:
- `decision_package_decision`
- `decision_package_promotion_ready`
- `decision_package_verified`
- `decision_package_schema_supported`
- `decision_package_compact_summary_checks_performed`
- `decision_package_compact_summary_checks_skipped`
- `decision_package_compact_summary_artifacts_present`
- `decision_package_compact_summary_mismatch_count`
- `decision_package_compact_summary_mismatch_details`
- `decision_package_inspector_verified`
- `decision_package_inspector_mismatch_count`
- `decision_package_inspector_mismatch_details`

## Owner Checklist
1. Backend owner approves strict-mode metrics health.
2. Client owner confirms header transport rollout completion.
3. QA owner confirms sunset-gated test pass evidence.
4. Operations owner confirms rollback playbook readiness.
5. Final approver signs completed production decision memo template.
