# M1 Client Gameplay Minimal Slice Plan

Status: Planned
Version: 1.0
Date: 2026-08-15

Source alignment:
- docs/global-mining-network-official-specification.md
- docs/game-design-brief-v1.md
- docs/m1-slice-1-simulation-kernel-tick-contract.md
- docs/implementation-plan-v1.md

## 1. Objective
Define a minimal client gameplay slice for M1 that presents authoritative server state without introducing client-owned progression, reward, or block logic.

## 2. Scope
In scope:
- Login-to-gameplay shell flow in the Godot client.
- Read-only global block HUD fed by authoritative API/WebSocket contracts.
- Basic player reward history and operation status presentation.
- Reconnect-aware network event stream consumption.

Out of scope:
- Client-authoritative mining calculations.
- Local reward settlement math.
- Marketplace, pools, and advanced social UX.

## 3. Authority Boundaries
The client may:
- Send user intents and display returned server state.
- Render estimates for UX only when explicitly marked non-authoritative.

The client may not:
- Set progression, rewards, balances, block completion, or difficulty values.
- Compute authoritative contribution outcomes.
- Mutate ledger-like values locally and treat them as truth.

## 4. Minimal Surface Backlog
1. Session bootstrap flow
- Connect client session to existing auth/session contract.
- Store session context for authorized API and websocket usage.

2. Global chain status HUD
- Consume `/api/v1/blockchain/status` and show block number, required work, accumulated work, and progress ratio.
- Polling fallback permitted; websocket-first when available.

3. Network snapshot and reconnect stream
- Load `/api/v1/blockchain/network-snapshot` at scene entry.
- Subscribe to `/api/v1/blockchain/network-events/ws` with reconnect cursor handling.
- Recover from disconnect by resuming with last acknowledged cursor.

4. Player reward timeline panel
- Consume `/api/v1/blockchain/players/{player_id}/rewards`.
- Display reward amounts and contribution hashes as read-only history.

5. Operation command shell
- Provide minimal command UI for operation start/stop intents.
- Call `POST /api/v1/blockchain/operations/intents/start?session_id=<active_session_id>` with payload `{ "operation_id", "base_hashrate_hps" }`.
- Call `POST /api/v1/blockchain/operations/intents/stop?session_id=<active_session_id>` with payload `{ "operation_id" }`.
- Do not send `player_id` in operation-intent payloads; server derives player identity from the active session.
- Do not show speculative balances as authoritative state.

## 5. Acceptance Criteria
- Client displays server-authoritative state consistently after reconnect.
- No client path can override authoritative blockchain or ledger outcomes.
- UI state restoration works from server snapshot plus cursor replay.
- Slice can be demoed end-to-end with existing M1 APIs and contracts.

## 6. Delivery Sequence
1. Bootstrap and session binding wiring.
2. Status HUD with authoritative chain read model.
3. Snapshot-plus-websocket reconnect pipeline.
4. Reward history panel and read-only contribution visibility.
5. Operation command shell and UX hardening.

## 7. Test and Validation Expectations
- Contract tests for client deserialization of versioned API/websocket payloads.
- Reconnect scenario test for cursor resume behavior.
- Negative checks proving client-supplied progression fields are ignored by server.
- Smoke run against local compose stack with one active global chain.
