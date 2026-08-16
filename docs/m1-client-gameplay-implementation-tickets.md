# M1 Client Gameplay Implementation Tickets

Status: Active
Version: 1.0
Date: 2026-08-15

Source alignment:
- docs/m1-client-gameplay-minimal-slice-plan.md
- docs/m1-slice-1-simulation-kernel-tick-contract.md

## Ticket GMN-CL-01: Session Bootstrap Wiring
Owner: Gameplay Lead
Priority: P0

Scope:
- Implement client session bootstrap flow for register/login based on `/api/v1/auth/register` and `/api/v1/auth/login`.
- Persist `player_id`, `access_token`, and `refresh_token` in client runtime state only.

Acceptance criteria:
1. Client can bootstrap a session against local API.
2. Session values are available to authorized HTTP and websocket requests.
3. No client-owned progression or reward state is introduced.

## Ticket GMN-CL-02: Global Chain Status HUD
Owner: Gameplay Lead
Priority: P0

Scope:
- Consume `GET /api/v1/blockchain/status`.
- Render active block number, required work, accumulated work, and progress ratio.

Acceptance criteria:
1. HUD displays authoritative values from the server contract.
2. Fallback polling interval is configurable.
3. Client does not derive authoritative progression values locally.

## Ticket GMN-CL-03: Snapshot + Reconnect Event Stream
Owner: Gameplay Lead
Priority: P0

Scope:
- Load `GET /api/v1/blockchain/network-snapshot` on scene start.
- Subscribe to `/api/v1/blockchain/network-events/ws` using `after_sequence` cursor.
- Reconnect by replaying from last acknowledged cursor.

Acceptance criteria:
1. Reconnect resumes from the saved cursor.
2. Duplicate event application is avoided by sequence checks.
3. Cursor persistence path is present for channel-scoped checkpoints.

## Ticket GMN-CL-04: Player Reward Timeline Panel
Owner: Gameplay Lead
Priority: P1

Scope:
- Consume `GET /api/v1/blockchain/players/{player_id}/rewards`.
- Render read-only reward entries with block, reward amount, and contribution hashes.

Acceptance criteria:
1. Timeline renders server-returned entries without client mutation.
2. Empty states are handled when no rewards exist.
3. Rendering uses contract fields without inferred reward math.

## Ticket GMN-CL-05: Gameplay Shell Scene Scaffold
Owner: Gameplay Lead
Priority: P0

Scope:
- Add initial gameplay shell controller that orchestrates:
  - session bootstrap,
  - status refresh,
  - snapshot bootstrap,
  - network event stream cursor updates.

Acceptance criteria:
1. Scene controller coordinates API/websocket interactions via dedicated network service classes.
2. Contract field names are centralized in one location.
3. Errors are surfaced through non-authoritative client diagnostics only.
