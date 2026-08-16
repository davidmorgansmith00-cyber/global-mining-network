# Global Mining Network Operations Runbook

## Scope
This runbook defines operational controls for blockchain realtime retention and websocket connection lifecycle maintenance.

## Cleanup Scheduler Controls
Worker cleanup is executed by the periodic scheduler in [workers/app/worker.py](workers/app/worker.py).

Environment variables:
- `BLOCKCHAIN_CLEANUP_ENABLED` (default `true`)
- `BLOCKCHAIN_CLEANUP_INTERVAL_SECONDS` (default `300`, minimum `30`)
- `BLOCKCHAIN_CLEANUP_STARTUP_JITTER_SECONDS` (default `0`, minimum `0`)
- `BLOCKCHAIN_CLEANUP_BACKOFF_MAX_SECONDS` (default `1800`, minimum `30`)
- `BLOCKCHAIN_CLEANUP_TIMEOUT_SECONDS` (default `10`, minimum `1`)
- `BLOCKCHAIN_EVENT_RETENTION_SECONDS` (default `86400`, minimum `60`)
- `BLOCKCHAIN_CHECKPOINT_RETENTION_SECONDS` (default `604800`, minimum `60`)
- `BLOCKCHAIN_MAX_NETWORK_EVENTS` (default `100000`, minimum `1`)

Maintenance authorization variables shared by API and worker:
- `MAINTENANCE_AUTH_HEADER` (default `X-Maintenance-Token`)
- `MAINTENANCE_AUTH_TOKEN` (default `local-maintenance-token`)
- `MAINTENANCE_AUTH_PREVIOUS_TOKEN` (default empty, optional overlap token for rotation windows)

Maintenance auth scope observability label variables (API):
- `MAINTENANCE_AUTH_CURRENT_TOKEN_SCOPE_LABEL` (default `current`)
- `MAINTENANCE_AUTH_PREVIOUS_TOKEN_SCOPE_LABEL` (default `previous`)
- `MAINTENANCE_AUTH_UNKNOWN_TOKEN_SCOPE_LABEL` (default `unknown`)

Worker maintenance token secret source variables:
- `MAINTENANCE_AUTH_TOKEN_FILE` (default empty; when set, worker reads token from this file path and falls back to `MAINTENANCE_AUTH_TOKEN` if missing/unreadable/empty)

Cleanup endpoint rate limiting variables:
- `MAINTENANCE_CLEANUP_RATE_LIMIT_WINDOW_SECONDS` (default `60`)
- `MAINTENANCE_CLEANUP_RATE_LIMIT_MAX_REQUESTS` (default `6`)
- `MAINTENANCE_CLEANUP_RATE_LIMIT_PERSISTENCE_ENABLED` (default `true`)

Maintenance metrics export endpoint:
- `GET /api/v1/blockchain/maintenance/metrics` with maintenance auth header/token.
- Contract schema: `maintenance.metrics.v1`.
- `GET /api/v1/blockchain/maintenance/metrics/plaintext` with maintenance auth header/token.
- Plaintext endpoint emits Prometheus-style metric lines aligned to the metrics contract.

## Maintenance Token Rotation Procedure
Perform token rotation in all non-local environments at least quarterly.

1. Generate a new maintenance token in the secret manager for the target environment.
2. Update both API and worker secret references for `MAINTENANCE_AUTH_TOKEN`.
2a. During overlap windows, set previous value in `MAINTENANCE_AUTH_PREVIOUS_TOKEN`.
3. Roll API first and confirm cleanup endpoint accepts the new token.
4. Roll worker and confirm scheduled cleanup jobs continue succeeding.
4a. Confirm maintenance endpoints continue accepting both current and previous token during overlap window.
5. Verify there are no `cleanup_unauthorized_attempt` warnings after rollout.
6. Clear `MAINTENANCE_AUTH_PREVIOUS_TOKEN`, revoke the old token, and record rotation completion in the operations log.

Quarterly checklist entry:
- Confirm maintenance token rotation completed for local-dev shared defaults (if used), staging, and production.
- Attach evidence: deploy IDs, secret version IDs, and cleanup success logs.

### Post-Rotation Audit Evidence Capture
Capture the following evidence for every non-local token rotation and store it with incident/change records:

1. Metric query screenshots or exported panels showing:
	- `increase(gmn_maintenance_auth_requests_total{token_scope="previous"}[1h])`
	- `increase(gmn_maintenance_auth_requests_total{token_scope="unknown"}[5m])`
	- `increase(gmn_maintenance_auth_requests_total{token_scope="current"}[1h])`
2. API and worker deployment IDs used during rollout.
3. Secret version IDs for both current and previous token values.
4. Timestamp when overlap window started and timestamp when previous token was revoked.

Retention policy guidance:
- Staging evidence retention: minimum 30 days.
- Production evidence retention: minimum 180 days.
- If a security incident occurred during rotation, retain evidence per incident policy (minimum 1 year).

## Expected Log Signals
API cleanup endpoint logs:
- `cleanup_executed ... cleanup_runs_total=... cleanup_deleted_network_events_total=... cleanup_deleted_client_checkpoints_total=... source_ip=... user_agent=... token_scope=...`
- `cleanup_unauthorized_attempt source_ip=... user_agent=... token_scope=...`
- `cleanup_rate_limited ... cleanup_rate_limit_rejections_total=... source_ip=... user_agent=... token_scope=...`

Maintenance metrics endpoint fields:
- `cleanup_runs_total`
- `cleanup_deleted_network_events_total`
- `cleanup_deleted_client_checkpoints_total`
- `cleanup_rate_limit_rejections_total`
- `websocket_stale_evictions_total`
- `cleanup_rate_limit_mode` (`persisted` or `in_memory`)
- `cleanup_rate_limit_requests_in_window`
- `maintenance_auth_current_token_scope_label`
- `maintenance_auth_previous_token_scope_label`
- `maintenance_auth_unknown_token_scope_label`
- `maintenance_auth_scope_requests_total` (map keyed by token scope label)

Worker scheduler logs:
- `cleanup_job_completed ... runs_total=... failures_total=... deleted_network_events_total=... deleted_client_checkpoints_total=...`
- `cleanup_job_failed ... failures_total=... consecutive_failures=... backoff_seconds=... error_type=...`
- `cleanup_scheduler_startup_jitter_sleep seconds=...`
- `cleanup_scheduler_auth_token_source mode=env|file`

Websocket lifecycle logs:
- `websocket_stale_evicted ... websocket_stale_evictions_total=...`

## Alert Threshold Guidance
Use these starting thresholds and tune after baseline measurement.

Cleanup scheduler alerts:
- Trigger warning if `cleanup_job_failed` appears for 3 consecutive runs.
- Trigger critical if `cleanup_job_failed` appears for 10 minutes continuously.

Cleanup effectiveness alerts:
- Trigger warning if `cleanup_deleted_network_events_total` and `cleanup_deleted_client_checkpoints_total` remain unchanged for 24 hours while event ingestion is active.
- Trigger warning if each `cleanup_executed` run deletes more than 25% of `BLOCKCHAIN_MAX_NETWORK_EVENTS` for 3 consecutive runs.

Security alerts:
- Trigger warning on any `cleanup_unauthorized_attempt` in non-local environments.
- Trigger critical if unauthorized attempts exceed 10 per 5 minutes.
- Trigger warning if `cleanup_rate_limited` appears more than 5 times in 10 minutes.

Token-scope metrics alerts (`gmn_maintenance_auth_requests_total{token_scope=...}`):
- Trigger warning if `token_scope="unknown"` increases by more than 5 over 5 minutes in staging or production.
- Trigger critical if `token_scope="unknown"` increases by more than 20 over 5 minutes in production.
- Trigger warning if `token_scope="previous"` remains non-zero for more than 24 hours after a planned rotation window closes.

Staged token rotation rollback criteria:
- Stage 1 (API-only rollout): rollback immediately if `increase(gmn_maintenance_auth_requests_total{token_scope="unknown"}[5m]) > 5` persists for 10 minutes.
- Stage 2 (worker canary rollout): rollback canary if `increase(gmn_maintenance_auth_requests_total{token_scope="unknown"}[5m]) > 5` or cleanup jobs produce repeated unauthorized attempts during the canary window.
- Stage 3 (broad worker rollout): pause rollout and rollback to previous secret version if `increase(gmn_maintenance_auth_requests_total{token_scope="unknown"}[5m]) > 20` at any point.
- Rotation completion gate: do not finalize rotation while `increase(gmn_maintenance_auth_requests_total{token_scope="previous"}[1h])` remains above 0 for more than 24 hours after the announced overlap cutoff.

Dashboard panel examples:
- `Maintenance Auth Requests by Scope (rate 5m)`: plot `rate(gmn_maintenance_auth_requests_total[5m])` grouped by `token_scope`.
- `Unknown Scope Burst`: plot `increase(gmn_maintenance_auth_requests_total{token_scope="unknown"}[5m])` as a single-stat and alert source.
- `Previous Token Decay`: plot `increase(gmn_maintenance_auth_requests_total{token_scope="previous"}[1h])` to confirm overlap traffic trends toward zero post-rotation.

Overlap-window sunset verification guidance:
- Recommended post-cutoff observation window: 24 hours minimum, 48 hours preferred for production.
- Query 1 (previous-scope decay): `increase(gmn_maintenance_auth_requests_total{token_scope="previous"}[1h])`
	- Expectation after cutoff: trends to `0` and remains `0` for the full observation window.
- Query 2 (unknown-scope safety check): `increase(gmn_maintenance_auth_requests_total{token_scope="unknown"}[5m])`
	- Expectation after cutoff: remains below warning threshold and does not show sustained growth.
- Query 3 (current-scope continuity): `increase(gmn_maintenance_auth_requests_total{token_scope="current"}[1h])`
	- Expectation after cutoff: remains non-zero during normal maintenance activity, confirming active clients use current token.
- Verification gate: close rotation only after Query 1 stays `0` throughout the selected window and Query 2 remains below warning thresholds.

Websocket health alerts:
- Trigger warning if `websocket_stale_evictions_total` increases by more than 100 in 10 minutes.
- Trigger warning if stale evictions are above 20% of active websocket sessions over a 15-minute window.

## Alert Routing and Escalation Ownership
Use the following default ownership and escalation routing for maintenance security signals:

- `token_scope="unknown"` warning threshold breach:
	- Primary owner: on-call backend engineer.
	- Escalate after 10 minutes unresolved to: platform/operations lead.
- `token_scope="unknown"` critical threshold breach:
	- Primary owner: on-call backend engineer.
	- Immediate escalation to: security on-call and platform/operations lead.
- Repeated `cleanup_unauthorized_attempt` warnings:
	- Primary owner: security on-call.
	- Escalate after 5 minutes unresolved to: incident commander.
- `cleanup_rate_limited` spike above warning threshold:
	- Primary owner: backend on-call.
	- Escalate after 15 minutes unresolved to: platform/operations lead.

Escalation handoff checklist:
1. Include the last 15 minutes of relevant metrics (`unknown`, `previous`, rate-limited, unauthorized attempts).
2. Include the latest deploy ID and secret version IDs for API and worker.
3. Include whether overlap token mode is active and the expected overlap cutoff timestamp.

Weekly maintenance security review checklist:
1. Confirm `increase(gmn_maintenance_auth_requests_total{token_scope="unknown"}[1h])` stayed below warning thresholds for the full review window.
2. Confirm `increase(gmn_maintenance_auth_requests_total{token_scope="previous"}[1h])` is expected for any active overlap windows and is zero outside overlap windows.
3. Confirm `increase(gmn_maintenance_auth_requests_total{token_scope="current"}[1h])` is non-zero during expected maintenance activity periods.
4. Review unauthorized maintenance signals (`cleanup_unauthorized_attempt`) and validate escalation/closure status for each alert.
5. Record review timestamp, reviewer name, and links to metric snapshots in the operations log.

Monthly maintenance control self-audit checklist:
1. Calculate 30-day baselines (p50 and p95) for:
	- `increase(gmn_maintenance_auth_requests_total{token_scope="unknown"}[5m])`
	- `increase(gmn_maintenance_auth_requests_total{token_scope="previous"}[1h])`
	- `increase(gmn_maintenance_auth_requests_total{token_scope="current"}[1h])`
	- `increase(gmn_maintenance_cleanup_rate_limit_rejections_total[10m])`
2. Compare active alert thresholds against observed baselines:
	- Unknown-scope warning threshold should remain above normal baseline noise but below documented incident levels.
	- Previous-scope decay threshold should remain aligned with planned overlap-window duration.
	- Rate-limit warning threshold should remain above expected operational bursts.
3. Trigger corrective action when thresholds are misaligned:
	- If threshold is below baseline and causes repeated false positives, propose calibrated threshold updates.
	- If threshold is far above baseline and would miss meaningful spikes, lower threshold and open a follow-up task.
	- If baseline drift is caused by behavior change (for example rollout pattern changes), update runbook rationale and dashboard annotations.
4. Record evidence and approvals:
	- Log reviewer, date, baseline query windows, and approved threshold values.
	- Link dashboard snapshots and alert-history exports used for the decision.
	- Store artifacts using the retention guidance in "Post-Rotation Audit Evidence Capture".

## Incident Response Quick Steps
1. Confirm API and worker share the same `MAINTENANCE_AUTH_HEADER` and `MAINTENANCE_AUTH_TOKEN` values.
2. Check for `cleanup_job_failed` details and validate API reachability from worker network.
3. If cleanup lag is rising, temporarily reduce `BLOCKCHAIN_CLEANUP_INTERVAL_SECONDS` and re-evaluate deletion volumes.
4. If stale evictions spike, verify client pong behavior and inspect network latency before extending stale timeout defaults.
5. If cleanup failures are persistent, verify exponential backoff is active and consider temporarily raising `BLOCKCHAIN_CLEANUP_BACKOFF_MAX_SECONDS` during API instability.

### Missing Maintenance Token Troubleshooting
If worker startup logs `cleanup_scheduler_missing_maintenance_token` in non-local environments:

1. Treat this as a configuration incident and halt further worker rollouts for the affected environment.
2. Verify at least one source is configured before resuming rollout:
	- `MAINTENANCE_AUTH_TOKEN_FILE` points to a readable mounted secret file, or
	- `MAINTENANCE_AUTH_TOKEN` is set from the environment secret source.
3. Validate that `MAINTENANCE_AUTH_HEADER` matches between API and worker.
4. Restart a single worker canary and confirm no repeated `cleanup_scheduler_missing_maintenance_token` warning.
5. Execute one authenticated maintenance call (`/api/v1/blockchain/maintenance/cleanup`) and confirm success.
6. Resume the remaining rollout only after canary validation succeeds; otherwise rollback to last known-good secret configuration.