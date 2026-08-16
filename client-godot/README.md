# Client Godot

This folder contains the M1 client gameplay shell scaffolding for the Godot 4 client.

Current scaffold:
- `scripts/network/gmn_contracts.gd`: central contract key definitions.
- `scripts/network/gmn_api_client.gd`: URL and session helpers for authoritative API endpoints.
- `scripts/network/gmn_stream_client.gd`: websocket reconnect cursor helper for network event streaming.
- `scripts/ui/gameplay_shell_controller.gd`: initial gameplay shell controller wiring.
- `scripts/ui/gameplay_shell_view_model.gd`: maps authoritative payloads to render-ready UI fields.
- `scripts/ui/gameplay_shell_panel.gd`: simple panel binder for label-based status/snapshot/reward rendering.
- `scripts/tests/gmn_contract_validation_smoke.gd`: client-side contract key validation smoke suite.
- `scripts/tests/gmn_reconnect_smoke.gd`: reconnect cursor monotonicity smoke suite.
- `scripts/tests/gmn_gameplay_shell_smoke_runner.gd`: aggregate smoke runner for client shell checks.

Smoke validation usage:
- Instantiate `GmnGameplayShellSmokeRunner` in a temporary scene or script and call `run_all()`.
- Treat any non-empty `failures` list as a failing validation gate before widening client feature scope.

M1 scope rules:
- Client is presentation and input only.
- Server remains authoritative for progression, rewards, balances, and block outcomes.
- Client-side calculations may support UX estimates only and must never become authoritative state.