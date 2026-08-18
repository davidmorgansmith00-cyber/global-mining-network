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
- `scenes/onboarding.tscn`: Phase 2 login/registration entry scene and gameplay handoff.
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

Phase 2 onboarding:
- `onboarding.tscn` is the project main scene.
- Login and registration use the server auth endpoints, then load `/api/v1/player/bootstrap` before entering gameplay.
- Session tokens remain runtime-only; gameplay receives the authenticated session through an explicit scene handoff.

Phase 3 starter operation screen:
- The gameplay shell fetches `/api/v1/players/profile` and renders machine, tier, hashrate, power, throttle, heat, and cooling values from the server.
- The operation start intent uses the server-returned `base_hashrate`; the client no longer accepts an authoritative hashrate typed by the player.
- Global block status remains visible alongside the machine constraints.

Phase 4 economy UX:
- The gameplay shell renders the server-provided NPC market catalog from blockchain status.
- Purchases use `/api/v1/market/purchase?session_id=<active_session_id>` with `item_id` and `quantity` only.
- Accepted purchases trigger a fresh authoritative profile/status read; the client does not calculate prices, balances, or stock.

Phase 5 history surfaces:
- The gameplay shell reads canonical block history, player history, and active events from the explorer/events endpoints.
- These summaries are read-only and do not create alternate chain state or client-side rewards.

Phase 6 social surfaces:
- The gameplay shell reads pool browse data, the hashrate leaderboard, and the current player's leaderboard position.
- These are read-only summaries; pool membership commands and notifications remain separate server-authoritative flows.

Phase 7 accessibility foundation:
- The gameplay shell includes launcher-aligned runtime settings semantics for UI scale, text scale, high contrast, color mode, and reduce motion.
- The first visible control toggles reduce motion without changing server-owned gameplay state.

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