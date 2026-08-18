# Operation Intents API Reference

Status: Active
Version: 1.0
Date: 2026-08-16

This reference documents the current server-authoritative operation intent contract.

## Authority Model
- Client submits start and stop intents only.
- Server derives player identity from active session binding.
- Client must not provide authoritative progression, reward, or balance state.

## Start Intent
Endpoint:
- POST /api/v1/blockchain/operations/intents/start?session_id=<active_session_id>

Request body:
```json
{
  "operation_id": "op_runtime_1",
  "base_hashrate_hps": "50"
}
```

Success response (started):
```json
{
  "operation_id": "op_runtime_1",
  "player_id": "<server-derived-player-id>",
  "accepted": true,
  "status": "started",
  "detail": "Operation start intent accepted"
}
```

Success response (already running):
```json
{
  "operation_id": "op_runtime_1",
  "player_id": "<server-derived-player-id>",
  "accepted": true,
  "status": "already_running",
  "detail": "Operation intent accepted; operation is already active"
}
```

Error examples:
- 401 Unauthorized: invalid or expired session_id binding.
- 409 Conflict: operation_id already belongs to a different player.
- 422 Unprocessable Entity: unsupported extra request fields.

## Stop Intent
Endpoint:
- POST /api/v1/blockchain/operations/intents/stop?session_id=<active_session_id>

Request body:
```json
{
  "operation_id": "op_runtime_1"
}
```

Success response:
```json
{
  "operation_id": "op_runtime_1",
  "player_id": "<server-derived-player-id>",
  "accepted": true,
  "status": "stopped",
  "detail": "Operation stop intent accepted"
}
```

Error examples:
- 401 Unauthorized: invalid or expired session_id binding.
- 404 Not Found: operation_id does not exist or is already stopped.
- 409 Conflict: operation_id is bound to a different player.

## Field Contract Summary
Required response fields for successful start and stop intent responses:
- operation_id (string)
- player_id (string, server-derived)
- accepted (boolean)
- status (string)
- detail (string)

## Player Profile (v1.2)
Endpoint:
- GET `/api/v1/players/profile?player_id=<player_id>`

Response:
```json
{
  "schema_version": "player.profile.v1.2",
  "player_id": "<player-id>",
  "hardware_id": "starter_rusty_home_computer",
  "base_hashrate": 12.0,
  "power_available": 120.0,
  "power_consumed": 120.0,
  "power_capacity": 120.0,
  "power_throttle_multiplier": 1.0,
  "cooling_efficiency": 1.0,
  "effective_hashrate": 12.0
}
```

Server formula:
- `power_throttle_multiplier = 1.0` when `power_consumed <= power_capacity`
- Otherwise, `power_throttle_multiplier = max(0.1, 1.0 - (((power_consumed - power_capacity) / power_capacity) ^ 1.5))`
- `effective_hashrate = base_hashrate × power_throttle_multiplier × clamp(cooling_efficiency, 0.0, 1.0)`
- All hardware, power, cooling, and effective hashrate values are calculated server-side only.

## Transport Transition Note (Query -> Header)
Current mode:
- Session binding uses `session_id` query parameter on operation-intent endpoints.

Planned mode:
- Session binding can move to a standardized auth header/token transport.
- Identity remains server-derived from validated session context in either mode.

Migration guidance:
- During rollout planning, validate both transport modes in client integration tests.
- Do not add `player_id` back into client request payloads during transition.
- Keep response contract fields stable (`operation_id`, `player_id`, `accepted`, `status`, `detail`) to avoid client parser churn.

Strict-mode canary option:
- `OPERATION_INTENT_REQUIRE_HEADER_BINDING=true` disables query-only `session_id` transport.
- In strict mode, query-only requests are rejected with `400` and message: `Session binding must be provided via X-Session-Id header`.
- Header-only and query+header (identical values) remain accepted.

Sunset test gate:
- Query-sunset integration tests are staged behind `GMN_ENABLE_QUERY_SUNSET_TESTS=1`.
- These tests validate header-only behavior during strict-mode rollout windows without forcing global CI behavior.

Concrete rollout plan:
- See `docs/operation-intents-transport-migration-proposal.md` for header shape, compatibility window, deprecation milestones, and rollback criteria.
- See `docs/operation-intents-query-sunset-release-checklist.md` for dated release-note steps, evidence bundle requirements, and promotion criteria.

## Migration Observability Metrics
Use maintenance metrics endpoints to monitor operation-intent transport adoption during rollout:
- `GET /api/v1/blockchain/maintenance/metrics`
  - `operation_intent_session_header_name`: configured header used for session binding (default `X-Session-Id`).
  - `operation_intent_transport_requests_total`: cumulative request counters by mode:
    - `query`
    - `header`
    - `dual_match`
    - `mismatch`
    - `missing`
    - `query_rejected_strict`
- `GET /api/v1/blockchain/maintenance/metrics/plaintext`
  - Prometheus-style lines:
    - `gmn_operation_intent_transport_requests_total{mode="query"} ...`
    - `gmn_operation_intent_transport_requests_total{mode="header"} ...`
    - `gmn_operation_intent_transport_requests_total{mode="dual_match"} ...`
    - `gmn_operation_intent_transport_requests_total{mode="mismatch"} ...`
    - `gmn_operation_intent_transport_requests_total{mode="missing"} ...`
    - `gmn_operation_intent_transport_requests_total{mode="query_rejected_strict"} ...`
