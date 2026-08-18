# Global Mining Network Progress Tracker

**Status:** Active Tracking  
**Version:** 1.1  
**Date Initialized:** 2026-08-15
**Last Updated:** 2026-08-17

---

## 1. Purpose
This document tracks actual delivery progress against:
- docs/master-build-plan-v1.md
- docs/implementation-plan-v1.md

It is the working execution board for milestones, workstreams, blockers, risks, and next actions.

---

## 2. Status Vocabulary
- Not Started
- Planned
- In Progress
- Blocked
- Done

---

## 3. Overall Program Status
- Current Phase: M1 Simulation Core Vertical Slice
- Current Slice: M1 Slice 2 - Client Gameplay Shell Integration
- Overall Status: In Progress
- Architecture Status: Ready
- Implementation Status: M0 closed, M1 Slice 1 closed, M1 Slice 2 execution started

---

## 4. Milestone Status Board
| Milestone | Status | Notes |
|---|---|---|
| M0 Foundations | Done | Closed after persistence test baseline passed and exit review completed |
| M1 Simulation Core Vertical Slice | In Progress | Slice 1 closed; Slice 2 (Client Gameplay) now executing |
| M2 Constraint Systems and Economy Foundations | Not Started | Locked behind M1 proof |
| M3 Social-Competitive Core | Not Started | Locked behind M2 baseline systems |
| M4 Productization and Launcher Beta | Not Started | Launcher/update work begins after artifact pipeline exists |
| M5 Content, Events, and Admin Operations | Not Started | Depends on content and admin platform baselines |
| M6 Closed Beta Hardening | Not Started | Depends on product stability and ops tooling |
| M7 Open Beta and Launch Readiness | Not Started | Depends on beta hardening |
| Launch | Not Started | Depends on launch readiness gate |

---

## 5. Current Workstream Board
| Workstream | Status | Owner | Notes |
|---|---|---|---|
| Architecture and Program Control | In Progress | Program Lead | Baseline docs are active and now guiding M1 execution; copilot-instructions.md tracks current slice |
| Platform and Developer Experience | In Progress | Platform Lead | Root scaffold, compose stack, service skeleton, and CI baseline created |
| Identity and Account Systems | In Progress | Backend Lead | Auth session lifecycle complete (register/login/refresh/logout); client session bootstrap wired |
| Player State and Progression Core | In Progress | Backend Lead | Player bootstrap contract skeleton created |
| Simulation Kernel | In Progress | Simulation Lead | Mining service processing intervals with per-operation timestamps and explicit boundary-event timestamps |
| Blockchain and Difficulty | In Progress | Simulation Lead | Persistent active/finalized block state store with DB-backed integration and cross-process race coverage |
| Economy and Ledger | In Progress | Economy Lead | Block finalization ledger posting contract added with DB-backed entry test coverage |
| Hardware, Power, Cooling, Facilities | Not Started | Economy Lead | Starts in M2 |
| Marketplace and Trading | Not Started | Economy Lead | Starts after ledger/inventory baseline |
| Research, Manufacturing, Automation | Not Started | Economy Lead | Starts after content and economy baseline |
| Pools, Social, Notifications | Not Started | Gameplay Lead | Starts in M3 |
| Client Gameplay and UX | In Progress | Gameplay Lead | M1 Slice 2: Session bootstrap wired; HUD/events/timeline next |
| WebSocket and Realtime Delivery | Not Started | Backend Lead | Starts after event contract baseline |
| Content Pipeline and Data Ops | In Progress | Content Lead | Initial content schema scaffold and validator created |
| Launcher, Installer, Patcher | Not Started | Platform Lead | Starts in M3-M4 |
| Admin, Analytics, Operations | In Progress | Operations Lead | Basic logging baseline started in M0 |
| Security, Moderation, Support | In Progress | Security Lead | Request correlation baseline started; broader security work still pending |
| QA, Simulation, Load Validation | In Progress | QA Lead | Automated persistence integration tests added and passing |

---

## 6. Current Slice Checklist

### M1 Slice 2 - Client Gameplay Shell Integration
| Item | Status | Notes |
|---|---|---|
| GMN-CL-01: Session Bootstrap Wiring | Done | Client session bootstrap flow wired; register/login/refresh/logout working; tests passing |
| GMN-CL-02: Global Chain Status HUD | Planned | Next: Consume /api/v1/blockchain/status and render block status |
| GMN-CL-03: Snapshot + Reconnect Event Stream | Planned | Load snapshot and subscribe to websocket with cursor handling |
| GMN-CL-04: Player Reward Timeline Panel | Planned | Render reward history from /api/v1/blockchain/players/{player_id}/rewards |
| GMN-CL-05: Gameplay Shell Scene Scaffold | Planned | Orchestrate session/status/snapshot/events in unified controller |
| GMN-CL-06: Operation Intent Session-Bound Contract | Planned | Wire start/stop intents with session binding |

---

## 7. M1 Slice 1 - Simulation Kernel Implementation Kickoff (CLOSED)
| Item | Status | Notes |
|---|---|---|
| Server time abstraction baseline | Done | Added `server/shared/time.py` with system and fixed UTC clock models |
| Piecewise interval slicer baseline | Done | Added deterministic interval slicing in `server/domain/mining/interval_slicer.py` |
| Simulation boundary event contracts baseline | Done | Added boundary event type constants and schema model in `server/domain/mining/contracts.py` |
| Mining package export surface updated | Done | Exposed contract and slicer primitives via `server/domain/mining/__init__.py` |
| Deterministic interval unit tests | Done | Added and passed `tests/unit/test_mining_interval_slicer.py` |
| Mining simulation service baseline | Done | Added `server/domain/mining/service.py` with per-operation last-processed timestamps and authoritative contribution processing |
| Boundary-event timestamp contract hardening | Done | Removed the hidden default timestamp from mining boundary events so callers must provide authoritative times explicitly |
| Auth session lifecycle baseline | Done | Added register/login/refresh/logout lifecycle support with session IDs and revocation handling |
| Auth session lifecycle integration coverage | Done | Added persistence coverage for refresh rotation and logout revocation |
| Auth HTTP lifecycle integration coverage | Done | Added API integration tests validating register/refresh/logout lifecycle and post-logout refresh rejection |
| Auth refresh invalid-token rejection coverage | Done | Added API integration test ensuring refresh returns 401 for invalid refresh tokens |
| Auth logout idempotency baseline | Done | Logout now returns success for repeated valid session/token revocation requests to support safe client retries |
| Auth logout idempotency integration coverage | Done | Added API integration test confirming repeated valid logout requests return successful revoked responses |
| Auth duplicate-register contract hardening | Done | Registration now rejects already-registered emails with a deterministic 400 response contract |
| Auth duplicate-register and invalid-login API coverage | Done | Added API integration tests for duplicate email registration rejection and login rejection for wrong password/unknown player |
| Auth login session-rotation API coverage | Done | Added API integration test asserting repeated successful logins mint distinct session IDs and refresh tokens for the same player |
| Auth expired-session refresh rejection coverage | Done | Added API integration test asserting refresh returns unauthorized after server-side session expiry |
| Shared-block aggregation integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_multiple_operations_contribute_to_same_active_block` |
| Timestamp progression and boundary application test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_operation_last_processed_timestamp_advances_and_boundary` |
| Upgrade-boundary multiplier integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_hardware_upgrade_boundary_updates_effective_hashrate_multiplier` |
| Throttle and maintenance boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_throttle_and_maintenance_boundaries_update_multiplier` |
| Power-state boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_power_state_boundary_updates_effective_hashrate_multiplier` |
| Modifier start/end boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_modifier_start_and_end_boundaries_update_multiplier_state` |
| Cooling-state boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_cooling_state_boundary_updates_effective_hashrate_multiplier` |
| Pool-membership boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_pool_membership_boundary_updates_effective_hashrate_multiplier` |
| Block-finalized boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_block_finalized_boundary_event_is_safe_noop_for_multiplier_state` |
| Same-timestamp boundary determinism hardening | Done | Mining service now applies deterministic tie-break ordering for same-timestamp boundary states |
| Atomic finalization concurrency test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_atomic_finalization_under_concurrency` |
| DB-backed active/finalized block persistence | Done | Added `server/domain/blockchain/store.py` and migration table coverage |
| DB-backed ledger posting contract wiring | Done | Added `server/domain/economy/ledger.py` and finalization-to-ledger integration in mining service |
| Blockchain persistence and ledger integration tests | Done | Added and passed `tests/integration/test_blockchain_persistence_and_ledger.py` |
| Cross-process blockchain finalization race coverage | Done | Added Postgres-backed race regression ensuring one finalized block and one block-ledger entry under concurrent service instances |
| Difficulty adjustment baseline service | Done | Added `server/domain/difficulty/service.py` with bounded adjustment by finalized block timing window |
| Difficulty config DB baseline | Done | Added `database/migrations/0004_difficulty_config.sql` default singleton settings row |
| Reward settlement calculation baseline | Done | Added `server/domain/economy/reward_settlement.py` and wired mining finalization reward amount computation |
| Difficulty and reward unit tests | Done | Added and passed `tests/unit/test_difficulty_and_reward_settlement.py` |
| Deterministic replay settlement integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_deterministic_replay_produces_identical_settlement_outcomes` |
| Difficulty-linked integration coverage | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_difficulty_adjusts_next_required_work_from_finalized_history` |
| Immutable per-player reward ledger entries | Done | Added `database/migrations/0005_player_reward_ledger.sql` and posting integration in `server/domain/economy/ledger.py` |
| Player-level reward allocation flow | Done | Mining service now allocates finalized reward by player contribution share and posts immutable entries |
| Player reward ledger replay projection baseline | Done | Added economy read-model projection that reconstructs per-player reward balances from immutable ledger entries |
| Player reward replay determinism integration coverage | Done | Added DB-backed test asserting repeated replay projections return identical per-player balances and totals |
| Player reward cumulative replay integration coverage | Done | Added DB-backed replay test asserting multi-block finalized rewards accumulate to deterministic per-player balances |
| Player reward replay API read surface | Done | Added `GET /api/v1/blockchain/reward-balances` exposing replay-projected per-player reward balances and total |
| Player reward replay API integration coverage | Done | Added API integration test asserting replay-projected balances match immutable ledger outcomes for multi-player finalization |
| Player reward replay empty-ledger API coverage | Done | Added API integration test asserting replay endpoint returns zero total and no entries when ledger has no reward records |
| Reward-balance and player-history API consistency coverage | Done | Added API integration test asserting replayed reward balances align with per-player reward history totals and aggregate total |
| Finalized reward parity coverage across status/events/ledger | Done | Added integration test asserting finalized reward pool amount and block number remain consistent across status API, network events, and ledger |
| Blockchain status read-model and API exposure | Done | Added `server/domain/blockchain/read_models.py` and `GET /api/v1/blockchain/status` endpoint |
| Blockchain status API integration coverage | Done | Added and passed `tests/integration/test_blockchain_status_api.py` |
| Per-player contribution transparency API | Done | Added `GET /api/v1/blockchain/players/{player_id}/rewards` backed by player reward history read-model |
| WebSocket-ready network snapshot contract baseline | Done | Added `GET /api/v1/blockchain/network-snapshot` and `network.snapshot.v1` schema contract model |
| Contribution-hash persistence on player ledger entries | Done | Added migration `0006_player_reward_contributions.sql` and persisted per-player finalized contribution hashes |
| Network event stream scaffolding | Done | Added `server/domain/blockchain/network_stream.py` with sequence IDs and cursor-based retrieval |
| Reconnect cursor semantics | Done | Added `snapshot_sequence` and `reconnect_cursor` in network snapshot and `GET /api/v1/blockchain/network-events` cursor endpoint |
| Progress/finalization event publishing | Done | Mining service now emits `network.block_progress.v1` and `network.block_finalized.v1` events |
| Persisted event stream storage | Done | Added `database/migrations/0007_network_events.sql` and Postgres-backed event stream implementation |
| WebSocket transport baseline | Done | Added `/api/v1/blockchain/network-events/ws` live cursor stream endpoint scaffold |
| WebSocket reconnect integration coverage | Done | Added websocket and cursor endpoint tests in `tests/integration/test_blockchain_status_api.py` |
| Client replay checkpoint persistence | Done | Added `database/migrations/0008_client_event_checkpoints.sql` and checkpoint read/write APIs |
| Checkpoint revoked-session auth coverage | Done | Added integration test asserting checkpoint GET/PUT return unauthorized when session binding has been revoked |
| Checkpoint mismatched-binding auth coverage | Done | Added integration test asserting checkpoint GET/PUT return unauthorized when `player_id` and `session_id` do not belong to the same binding |
| Checkpoint negative-cursor contract hardening | Done | Enforced non-negative reconnect cursor schema validation and added integration test asserting negative checkpoint cursor updates are rejected |
| Checkpoint unsupported-channel contract coverage | Done | Added integration test asserting checkpoint GET/PUT reject unsupported channels with deterministic 400 responses |
| Checkpoint bootstrap cursor contract coverage | Done | Added integration test asserting checkpoint GET with no stored checkpoint returns reconnect cursor derived from authoritative global event stream |
| Checkpoint player_rewards channel contract coverage | Done | Added integration test asserting checkpoint GET/PUT for `player_rewards` persist and return the channel-scoped reconnect cursor context |
| Operation intent non-positive hashrate contract coverage | Done | Added integration test asserting operation start intent rejects zero/negative `base_hashrate_hps` with deterministic 400 validation |
| Network events negative-cursor contract coverage | Done | Added integration test asserting `after_sequence=-1` is rejected by endpoint validation with HTTP 422 |

---

## 10. Next Actions

1. **Execute M1 Slice 2 using the 8-step cycle** in `.github/agents/slice-executor.agent.md`
2. **Current ticket:** GMN-CL-02: Global Chain Status HUD (P0)
   - Consume `/api/v1/blockchain/status` endpoint
   - Render authoritative block state in HUD
   - No client-side progression calculations
3. **Delivery order:** GMN-CL-02 → GMN-CL-03 → GMN-CL-05 → GMN-CL-06 → GMN-CL-04
4. **After M1 Slice 2 closes:** Move to M2 Constraint Systems (economy, difficulty, rewards UI)
