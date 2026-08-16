# Copilot Instructions for Global Mining Network

Treat this repository as a persistent multiplayer simulation game project with strict architecture constraints.

## Always-On Rules
- Server is authoritative for all meaningful game state.
- The client is presentation and input only.
- The game uses a fictional blockchain simulation only.
- Do not propose or implement real cryptocurrency, real wallets, or real proof-of-work.
- Prefer time-based simulation using state changes, timestamps, and aggregation.
- Avoid per-player per-second simulation patterns.
- Keep designs data-driven and scalable.

## Required Context Documents
Before substantial design or implementation work, consult:
- docs/global-mining-network-official-specification.md
- docs/game-design-brief-v1.md
- docs/master-build-plan-v1.md
- docs/implementation-plan-v1.md

If a request conflicts with those documents, call out the conflict and propose an architecture-compliant alternative.

## Repository Direction
- Preserve modular backend domain boundaries.
- Keep API and websocket responsibilities explicit.
- Preserve economy integrity with ledger-style transaction thinking.
- Protect fairness and anti-cheat assumptions in all game logic.
