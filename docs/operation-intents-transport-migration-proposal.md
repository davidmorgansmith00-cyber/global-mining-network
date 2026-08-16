# Operation Intent Transport Migration Proposal

Status: Proposed
Version: 1.0
Date: 2026-08-16

Objective:
- Migrate operation-intent session binding from query-only transport to a standardized header transport while preserving server-authoritative identity derivation.

## 1. Target Contract
Header name:
- X-Session-Id

Endpoint compatibility target:
- POST /api/v1/blockchain/operations/intents/start
- POST /api/v1/blockchain/operations/intents/stop

Accepted during migration window:
- Header-only session binding (`X-Session-Id`).
- Query-only session binding (`session_id`) for backward compatibility.
- Query + header when both values are identical.

Rejected during migration window:
- Query + header with mismatched values (400 Bad Request).

## 2. Rollout Milestones
1. Milestone A: Dual-mode acceptance
- Enable both query and header session transports.
- Add integration coverage for header-only success and mismatch rejection.

2. Milestone B: Client default swap
- Update first-party clients to send header transport by default.
- Keep query support enabled for compatibility clients.

3. Milestone C: Query deprecation notice
- Announce sunset timeline for query mode in release notes and API docs.
- Begin telemetry review of query-mode usage share.

4. Milestone D: Strict-mode canary
- Enable `OPERATION_INTENT_REQUIRE_HEADER_BINDING=true` in pre-prod canary environments.
- Keep production dual-mode until canary transport/error metrics remain within rollback thresholds.

5. Milestone E: Query sunset
- Remove query-mode acceptance after deprecation window closes and rollback criteria remain green.

Execution checklist:
- See `docs/operation-intents-query-sunset-release-checklist.md` for dated release timeline, evidence requirements, and stage-gate owner checklist.
- Use `tools/capture_operation_intent_transport_metrics.py` to collect reproducible transport-mode evidence snapshots for canary and promotion reviews.
- Record final go/no-go using `docs/operation-intents-production-rollout-decision-memo-template.md`.

## 3. Compatibility Window
Recommended minimum window:
- 2 release cycles after Milestone B.

Exit criteria for window closure:
- Query-mode requests stay below 1% of operation-intent traffic for 14 consecutive days.
- No increase in 401/400 rates attributable to transport migration.
- No unresolved client regressions in compatibility cohort.

## 4. Rollback Criteria
Trigger rollback to full dual-mode behavior when any of the following occurs:
- Header-mode 401 rate exceeds baseline by >2x for 30+ minutes.
- 400 mismatch errors exceed a sustained threshold indicating integration breakage.
- Critical client cohort reports inability to submit start/stop intents.

Canary promotion criteria:
- `query` mode share remains <1% for 14 consecutive days.
- `query_rejected_strict` remains near zero outside scheduled strict-mode windows.
- `mismatch` mode does not exhibit sustained growth versus pre-canary baseline.
- No unresolved P1/P2 client regressions in start/stop intent flows.

Rollback action:
- Continue accepting query mode as primary fallback while remediation is deployed.
- Preserve response payload contract fields unchanged.

## 5. Invariants (Must Not Change)
- Server derives player identity from validated session only.
- Client payloads must not include `player_id`.
- Operation intent response fields remain stable:
  - operation_id
  - player_id
  - accepted
  - status
  - detail
