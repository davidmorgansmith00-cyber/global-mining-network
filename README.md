# Global Mining Network

Persistent multiplayer simulation game built around one fictional global blockchain.

This repository is in M0 foundations. The current goal is to establish the monorepo baseline, local development stack, and authoritative backend skeleton described in the planning documents under `docs/`.

## Current Scope
- Monorepo folder scaffold
- Local Docker Compose stack
- FastAPI API skeleton
- Worker skeleton
- Environment template

## Canonical Planning Docs
- `docs/global-mining-network-official-specification.md`
- `docs/game-design-brief-v1.md`
- `docs/master-build-plan-v1.md`
- `docs/implementation-plan-v1.md`
- `docs/progress-tracker.md`

## Fixed-Step Execution Agent
- Agent file: `.github/agents/slice-executor.agent.md`
- Purpose: execute the next implementation slice in a fixed 8-step cycle.
- Each cycle enforces: scoped implementation, validation, tracker updates, commit, push, and immediate next-slice kickoff.
- Stop only for a real blocker or required product decision.

## M0 Local Stack
- `server` - FastAPI application skeleton
- `workers` - background worker skeleton
- `database` - migration and seed placeholders
- `infra` - environment and deployment support files
- `client-godot` - client placeholder for future Godot project
- `content` - data-driven content placeholder
- `simulator` - replay/load/economy simulation placeholder
- `tests` - automated test root

## Getting Started
1. Copy `.env.example` to `.env`.
2. Start PostgreSQL and Redis with `docker compose up -d db redis`.
3. Run migrations with `python tools/apply_migrations.py` after setting `DATABASE_URL`.
4. Start the local stack with `docker compose up --build`.
5. Open the API health endpoint at `http://localhost:8000/health`.

### Local Migration Workflow
Example PowerShell session:

```powershell
$env:DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/global_mining_network"
python tools/apply_migrations.py
```

This is the current M0 migration baseline until a fuller migration orchestration workflow is introduced.

## M0 Guardrails
- Server authority only for meaningful game state.
- One logical global chain.
- Time-based reconstruction, not per-player per-second simulation.
- No real cryptocurrency or real mining behavior.