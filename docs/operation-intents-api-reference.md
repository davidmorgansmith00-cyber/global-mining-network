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

Concrete rollout plan:
- See `docs/operation-intents-transport-migration-proposal.md` for header shape, compatibility window, deprecation milestones, and rollback criteria.
