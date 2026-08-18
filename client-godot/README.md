# Client Godot

This folder contains the supported M1 gameplay shell and the Phase 1 UI foundation for the Godot 4 client.

Current scaffold:
- `scripts/network/gmn_contracts.gd`: central contract key definitions.
- `scripts/network/gmn_api_client.gd`: URL and session helpers for authoritative API endpoints.
- `scripts/network/gmn_stream_client.gd`: websocket reconnect cursor helper for network event streaming.
- `scripts/ui/gameplay_shell_controller.gd`: initial gameplay shell controller wiring.
- `scripts/ui/gameplay_shell_view_model.gd`: maps authoritative payloads to render-ready UI fields.
- `scripts/ui/gameplay_shell_panel.gd`: simple panel binder for label-based status/snapshot/reward rendering.
- `scripts/ui/gameplay_shell_scene_root.gd`: scene-level coordinator that binds controller + panel and drives periodic refresh/render.
- `scripts/ui/gameplay_shell_ui_state.gd`: shared loading, ready, stale, error, unauthorized, and maintenance state model.
- `scenes/gameplay_shell.tscn`: concrete gameplay shell scene with controller/panel nodes and label bindings.
- `scripts/tests/gmn_contract_validation_smoke.gd`: client-side contract key validation smoke suite.
- `scripts/tests/gmn_operation_intent_contract_smoke.gd`: validates operation-intent request shape (`session_id` query requirement and no `player_id` payload field).
- `scripts/tests/gmn_reconnect_smoke.gd`: reconnect cursor monotonicity smoke suite.
- `scripts/tests/gmn_gameplay_shell_smoke_runner.gd`: aggregate smoke runner for client shell checks.

Supported shell path:
- `scenes/gameplay_shell.tscn` uses `scripts/ui/*` as the supported controller, panel, view-model, and scene-root composition.
- The parallel `scripts/gameplay/*` path is legacy compatibility surface only; new UI work must use `scripts/ui/*` until an explicit migration slice removes it.

Phase 1 foundation:
- UI state is explicit and presentational only: `loading`, `ready`, `stale`, `error`, `unauthorized`, and `maintenance`.
- Session responses retain `session_id`; operation intents bind to that session ID and never include `player_id` in the payload.
- The shell renders a visible authoritative-state status line and preserves the existing reconnect/polling behavior.

Operation intent plumbing:
- `GmnApiClient` now includes non-authoritative start/stop intent pass-through calls:
	- `POST /api/v1/blockchain/operations/intents/start?session_id=<active_session_id>` with payload `{ "operation_id", "base_hashrate_hps" }`
	- `POST /api/v1/blockchain/operations/intents/stop?session_id=<active_session_id>` with payload `{ "operation_id" }`
- Client request payloads must not include `player_id`; server derives player identity from active session binding.
- `GameplayShellController` exposes `send_start_operation_intent(...)` and `send_stop_operation_intent(...)` and does not mutate authoritative progression state locally.
- `GameplayShellSceneRoot` wires scene-level inputs/buttons and renders request/response status for start/stop intents in `ActionStatusLabel`.

Smoke validation usage:
- Instantiate `GmnGameplayShellSmokeRunner` in a temporary scene or script and call `run_all()`.
- Treat any non-empty `failures` list as a failing validation gate before widening client feature scope.

M1 scope rules:
- Client is presentation and input only.
- Server remains authoritative for progression, rewards, balances, and block outcomes.
- Client-side calculations may support UX estimates only and must never become authoritative state.