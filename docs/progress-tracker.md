# Global Mining Network Progress Tracker

**Status:** Active Tracking  
**Version:** 1.0  
**Date Initialized:** 2026-08-15

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
- Current Slice: M1 Slice 1 - Simulation Kernel Implementation Kickoff
- Overall Status: In Progress
- Architecture Status: Ready
- Implementation Status: M0 closed, M1 execution started

---

## 4. Milestone Status Board
| Milestone | Status | Notes |
|---|---|---|
| M0 Foundations | Done | Closed after persistence test baseline passed and exit review completed |
| M1 Simulation Core Vertical Slice | In Progress | Opened with Slice 1 planning for simulation kernel contracts |
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
| Architecture and Program Control | In Progress | Program Lead | Baseline docs are active and now guiding M1 execution |
| Platform and Developer Experience | In Progress | Platform Lead | Root scaffold, compose stack, service skeleton, and CI baseline created |
| Identity and Account Systems | In Progress | Backend Lead | Versioned auth route now includes register/login/refresh/logout and session contract coverage |
| Player State and Progression Core | In Progress | Backend Lead | Player bootstrap contract skeleton created |
| Simulation Kernel | In Progress | Simulation Lead | Mining service now processes intervals with per-operation timestamps and explicit boundary-event timestamps |
| Blockchain and Difficulty | In Progress | Simulation Lead | Persistent active/finalized block state store added with DB-backed integration and cross-process race coverage |
| Economy and Ledger | In Progress | Economy Lead | Block finalization ledger posting contract added and DB-backed entry test coverage added |
| Hardware, Power, Cooling, Facilities | Not Started | Economy Lead | Starts in M2 |
| Marketplace and Trading | Not Started | Economy Lead | Starts after ledger/inventory baseline |
| Research, Manufacturing, Automation | Not Started | Economy Lead | Starts after content and economy baseline |
| Pools, Social, Notifications | Not Started | Gameplay Lead | Starts in M3 |
| Client Gameplay and UX | Planned | Gameplay Lead | Minimal slice starts in M1 |
| WebSocket and Realtime Delivery | Not Started | Backend Lead | Starts after event contract baseline |
| Content Pipeline and Data Ops | In Progress | Content Lead | Initial content schema scaffold and validator created |
| Launcher, Installer, Patcher | Not Started | Platform Lead | Starts in M3-M4 |
| Admin, Analytics, Operations | In Progress | Operations Lead | Basic logging baseline started in M0 |
| Security, Moderation, Support | In Progress | Security Lead | Request correlation baseline started; broader security work still pending |
| QA, Simulation, Load Validation | In Progress | QA Lead | Automated persistence integration tests added and passing |

---

## 6. Current Slice Checklist
### M0 Slice 1 - Execution Baseline and Authoritative Skeleton
| Item | Status | Notes |
|---|---|---|
| Monorepo folder scaffold | Done | Root monorepo folders and placeholder docs created |
| Docker Compose local stack | Done | Postgres, Redis, API, and worker services scaffolded |
| CI pipeline baseline | Done | GitHub Actions baseline validates API import and content schemas |
| Migration framework | Done | SQL migration runner scaffold created |
| Initial core tables | Done | Initial players, auth_sessions, and domain_events tables defined |
| Auth/session contract skeleton | Done | Versioned auth endpoints and request/response models created |
| Player bootstrap contract skeleton | Done | Versioned player bootstrap contract created |
| Domain event envelope standard | Done | Shared envelope model created in server shared layer |
| Content schema scaffold | Done | Initial content schemas and validator created |
| Structured logging baseline | Done | Server and worker logging baseline created |
| Correlation ID baseline | Done | Middleware adds and returns request correlation IDs |

### M0 Slice 2 - Service and Contract Baseline
| Item | Status | Notes |
|---|---|---|
| Auth service implementation stub | Done | DB-backed registration/login validated successfully against local Postgres |
| Player bootstrap service stub | Done | DB-backed player bootstrap validated successfully against local Postgres |
| Database connection baseline | Done | Shared DB helper validated successfully against local Postgres |
| Migration execution workflow | Done | Migrations executed successfully with the documented local workflow |
| Request-scoped logging enrichment | Done | Correlation ID logging context is now wired into server log records |

### M0 Slice 3 - Persistence Test Baseline
| Item | Status | Notes |
|---|---|---|
| Migration automation test | Done | Verifies required tables exist after migration run |
| DB-backed auth register/login test | Done | Verifies persisted register/login flow against local Postgres |
| DB-backed player bootstrap test | Done | Verifies persisted starter profile retrieval |
| Local persistence test command | Done | `python -m unittest tests/integration/test_persistence.py -v` |

### M0 Exit Criteria Review
| Criterion | Status | Notes |
|---|---|---|
| Monorepo structure and ownership map baseline | Done | Structure and role-based workstream ownership map are now defined in the tracker |
| Local compose baseline and bootstrap | Done | Local stack scaffolding validated |
| CI baseline and basic checks | Done | CI workflow validates API import and content schema syntax |
| Migration framework and initial schema | Done | Migration runner plus core tables verified |
| Auth and player bootstrap skeleton | Done | Versioned routes with DB-backed baseline are in place |
| Domain event envelope and correlation ID baseline | Done | Envelope model and request-scoped logging are wired |
| Initial automated persistence tests | Done | Migration + DB-backed auth/bootstrap tests passing |
| M0 readiness for M1 handoff | Done | Approved to proceed to M1 with owner assignment tracked as a non-blocking governance follow-up |

### M1 Slice 1 - Simulation Kernel and Tick Contract Planning
| Item | Status | Notes |
|---|---|---|
| Define authoritative simulation tick contract | Done | Published in docs/m1-slice-1-simulation-kernel-tick-contract.md |
| Define event-to-state reconstruction boundaries | Done | Boundary events and replay persistence rules documented in the contract |
| Define tick processing sequence | Done | Ordered authoritative tick pipeline documented in the contract |
| Define anti-cheat and authority invariants | Done | Server authority and one-chain invariants documented in the contract |
| Define M1 Slice 1 acceptance criteria | Done | Pass/fail criteria published in the contract |
| Break M1 Slice 1 into implementation tasks | Done | Task breakdown for kernel, event contracts, and validation added to the contract |

### M1 Slice 1 - Simulation Kernel Implementation Kickoff
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
| Timestamp progression and boundary application test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_operation_last_processed_timestamp_advances_and_boundaries_apply` |
| Upgrade-boundary multiplier integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_hardware_upgrade_boundary_updates_effective_hashrate_multiplier` |
| Throttle and maintenance boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_throttle_and_maintenance_boundaries_update_multiplier_and_pause_state` |
| Power-state boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_power_state_boundary_updates_effective_hashrate_multiplier` |
| Modifier start/end boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_modifier_start_and_end_boundaries_update_multiplier_state` |
| Cooling-state boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_cooling_state_boundary_updates_effective_hashrate_multiplier` |
| Pool-membership boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_pool_membership_boundary_updates_effective_hashrate_multiplier` |
| Block-finalized boundary integration test | Done | Added and passed `tests/integration/test_mining_simulation_service.py::test_block_finalized_boundary_event_is_safe_noop_for_multiplier_state` |
| Same-timestamp boundary determinism hardening | Done | Mining service now applies deterministic tie-break ordering for same-timestamp boundary states, with integration coverage asserting identical outcomes regardless of insertion order |
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
| Finalized reward parity coverage across status/events/ledger | Done | Added integration test asserting finalized reward pool amount and block number remain consistent across status API, network finalized events, and persisted ledger entries |
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
| Checkpoint player_rewards channel contract coverage | Done | Added integration test asserting checkpoint GET/PUT for `player_rewards` persist and return the channel-scoped reconnect cursor contract |
| Operation intent non-positive hashrate contract coverage | Done | Added integration test asserting operation start intent rejects zero/negative `base_hashrate_hps` with deterministic 400 validation detail |
| Network events negative-cursor contract coverage | Done | Added integration test asserting `after_sequence=-1` is rejected by endpoint validation with HTTP 422 |
| Network events negative-limit contract coverage | Done | Added integration test asserting `limit=-1` is rejected by endpoint validation with HTTP 422 |
| Network snapshot recent-limit bounds coverage | Done | Added integration test asserting `recent_limit` values outside [1, 100] are rejected with HTTP 422 |
| Network events limit bounds coverage | Done | Added integration test asserting `limit` values outside [1, 500] are rejected with HTTP 422 |
| Blockchain status recent-limit bounds coverage | Done | Added integration test asserting status `recent_limit` values outside [1, 100] are rejected with HTTP 422 |
| Player reward history recent-limit bounds coverage | Done | Added integration test asserting reward history `recent_limit` values outside [1, 200] are rejected with HTTP 422 |
| Cleanup query-parameter bounds coverage | Done | Added integration test asserting cleanup rejects `event_retention_seconds<60`, `checkpoint_retention_seconds<60`, and `max_network_events<1` with HTTP 422 |
| Operation start required-field schema coverage | Done | Added integration test asserting operation start rejects payloads missing `operation_id` or `base_hashrate_hps` with HTTP 422 |
| Checkpoint required-query schema coverage | Done | Added integration test asserting checkpoint GET/PUT reject requests missing required `player_id` or `session_id` query parameters with HTTP 422 |
| Operation stop required-field schema coverage | Done | Added integration test asserting operation stop rejects payloads missing required `operation_id` with HTTP 422 |
| Checkpoint upsert required-field schema coverage | Done | Added integration test asserting checkpoint upsert rejects payloads missing required `reconnect_cursor` with HTTP 422 |
| Checkpoint player_rewards bootstrap cursor coverage | Done | Added integration test asserting checkpoint GET for `player_rewards` with no stored checkpoint returns reconnect cursor consistent with authoritative player_rewards stream |
| Checkpoint player_rewards negative-cursor coverage | Done | Added integration test asserting player_rewards checkpoint upsert rejects negative `reconnect_cursor` with HTTP 422 |
| Checkpoint player_rewards required-field schema coverage | Done | Added integration test asserting player_rewards checkpoint upsert rejects payloads missing required `reconnect_cursor` with HTTP 422 |
| Checkpoint player_rewards required-query schema coverage | Done | Added integration test asserting player_rewards checkpoint GET/PUT reject requests missing required `player_id` or `session_id` query parameters with HTTP 422 |
| Checkpoint global empty-value auth coverage | Done | Added integration test asserting global checkpoint GET/PUT reject empty `player_id` or `session_id` values with deterministic invalid-session responses |
| Checkpoint player_rewards empty-value auth coverage | Done | Added integration test asserting player_rewards checkpoint GET/PUT reject empty `player_id` or `session_id` values with deterministic invalid-session responses |
| Operation stop missing-session transport coverage | Done | Added integration test asserting operation stop without query/header session transport is rejected with deterministic invalid-session response |
| Network events non-integer cursor coverage | Done | Added integration test asserting `after_sequence` rejects non-integer values with HTTP 422 |
| Network events non-integer limit coverage | Done | Added integration test asserting `limit` rejects non-integer values with HTTP 422 |
| Blockchain status non-integer recent-limit coverage | Done | Added integration test asserting status `recent_limit` rejects non-integer values with HTTP 422 |
| Network snapshot non-integer recent-limit coverage | Done | Added integration test asserting network snapshot `recent_limit` rejects non-integer values with HTTP 422 |
| Player reward history non-integer recent-limit coverage | Done | Added integration test asserting reward history `recent_limit` rejects non-integer values with HTTP 422 |
| Cleanup non-integer query-parameter coverage | Done | Added integration test asserting cleanup query parameters reject non-integer values with HTTP 422 |
| Operation start non-numeric hashrate coverage | Done | Added integration test asserting operation start rejects non-numeric `base_hashrate_hps` values with HTTP 422 |
| Operation stop malformed-body coverage | Done | Added integration test asserting operation stop rejects non-object JSON payloads with HTTP 422 |
| Operation start malformed-body coverage | Done | Added integration test asserting operation start rejects non-object JSON payloads with HTTP 422 |
| Operation intent empty-session transport coverage | Done | Added integration test asserting operation start/stop reject empty `session_id` query transport with deterministic invalid-session responses |
| Checkpoint upsert non-integer cursor coverage | Done | Added integration test asserting checkpoint upserts for `global` and `player_rewards` reject non-integer `reconnect_cursor` values with HTTP 422 |
| Operation intent empty-session header coverage | Done | Added integration test asserting operation start/stop reject empty session header transport with deterministic invalid-session responses |
| Checkpoint upsert malformed-body coverage | Done | Added integration test asserting checkpoint upserts for `global` and `player_rewards` reject non-object JSON payloads with HTTP 422 |
| Operation intent invalid-session header coverage | Done | Added integration test asserting operation start/stop reject invalid session header transport with deterministic invalid-session responses |
| Checkpoint invalid-binding auth coverage | Done | Added integration test asserting checkpoint GET/PUT for `global` and `player_rewards` reject invalid non-empty `player_id`/`session_id` values with deterministic invalid-session responses |
| Operation intent invalid-session query coverage | Done | Added integration test asserting operation start/stop reject invalid query `session_id` transport with deterministic invalid-session responses |
| Operation intent mismatch-detail header-name coverage | Done | Added integration test asserting query/header session mismatch errors for start/stop return the exact configured header-name detail string |
| Operation intent strict-mode detail coverage | Done | Added integration test asserting strict header mode query-only rejections for start/stop return the exact configured header-name detail string |
| Operation intent strict-mode counter exactness coverage | Done | Added integration test asserting strict header mode query-only rejections increment `query_rejected_strict` exactly twice for start and stop |
| Empty recent-limit query coverage | Done | Added integration test asserting status, network snapshot, and reward history endpoints reject empty `recent_limit` query values with HTTP 422 |
| Fractional recent-limit query coverage | Done | Added integration test asserting status, network snapshot, and reward history endpoints reject fractional `recent_limit` query values with HTTP 422 |
| Negative recent-limit query coverage | Done | Added integration test asserting status, network snapshot, and reward history endpoints reject negative `recent_limit` query values with HTTP 422 |
| Empty network-events query coverage | Done | Added integration test asserting network-events rejects empty `after_sequence` and empty `limit` query values with HTTP 422 |
| Fractional network-events query coverage | Done | Added integration test asserting network-events rejects fractional `after_sequence` and `limit` query values with HTTP 422 |
| Empty cleanup query coverage | Done | Added integration test asserting cleanup rejects empty `event_retention_seconds`, `checkpoint_retention_seconds`, and `max_network_events` query values with HTTP 422 |
| Empty checkpoint cursor payload coverage | Done | Added integration test asserting checkpoint upserts for `global` and `player_rewards` reject empty `reconnect_cursor` payload values with HTTP 422 |
| Operation intent whitespace query-session coverage | Done | Added integration test asserting operation start/stop reject whitespace-only query `session_id` transport with deterministic invalid-session responses |
| Operation intent whitespace header-session coverage | Done | Added integration test asserting operation start/stop reject whitespace-only session header transport with deterministic invalid-session responses |
| Operation intent tab-whitespace session transport coverage | Done | Added integration test asserting operation start/stop reject tab-whitespace query/header `session_id` transports with deterministic invalid-session responses |
| Operation intent newline-whitespace query-session coverage | Done | Added integration test asserting operation start/stop reject newline-whitespace query `session_id` transport with deterministic invalid-session responses |
| Operation intent carriage-return query-session coverage | Done | Added integration test asserting operation start/stop reject carriage-return query `session_id` transport with deterministic invalid-session responses |
| Operation intent CRLF query-session coverage | Done | Added integration test asserting operation start/stop reject CRLF query `session_id` transport with deterministic invalid-session responses |
| Operation intent operation_id empty/whitespace payload coverage | Done | Hardened operation intent request schema to trim/require non-empty `operation_id` and added integration tests asserting start/stop reject empty or whitespace-only values with HTTP 422 |
| Whitespace recent-limit query coverage | Done | Added integration test asserting status, network snapshot, and reward history endpoints reject whitespace-only `recent_limit` query values with HTTP 422 |
| Tab-whitespace recent-limit query coverage | Done | Added integration test asserting status, network snapshot, and reward history endpoints reject tab-whitespace `recent_limit` query values with HTTP 422 |
| Newline-whitespace recent-limit query coverage | Done | Added integration test asserting status, network snapshot, and reward history endpoints reject newline-whitespace `recent_limit` query values with HTTP 422 |
| Whitespace network-events query coverage | Done | Added integration test asserting network-events rejects whitespace-only `after_sequence` and `limit` query values with HTTP 422 |
| Tab-whitespace network-events query coverage | Done | Added integration test asserting network-events rejects tab-whitespace `after_sequence` and `limit` query values with HTTP 422 |
| Whitespace cleanup query coverage | Done | Added integration test asserting cleanup rejects whitespace-only `event_retention_seconds`, `checkpoint_retention_seconds`, and `max_network_events` query values with HTTP 422 |
| Tab-whitespace cleanup query coverage | Done | Added integration test asserting cleanup rejects tab-whitespace `event_retention_seconds`, `checkpoint_retention_seconds`, and `max_network_events` query values with HTTP 422 |
| Fractional cleanup query coverage | Done | Added integration test asserting cleanup rejects fractional `event_retention_seconds`, `checkpoint_retention_seconds`, and `max_network_events` query values with HTTP 422 |
| Negative cleanup query coverage | Done | Added integration test asserting cleanup rejects negative `event_retention_seconds`, `checkpoint_retention_seconds`, and `max_network_events` query values with HTTP 422 |
| Whitespace checkpoint binding coverage | Done | Added integration test asserting checkpoint GET/PUT for `global` and `player_rewards` reject whitespace-only `player_id`/`session_id` query values with deterministic invalid-session responses |
| Whitespace checkpoint cursor payload coverage | Done | Added integration test asserting checkpoint upserts for `global` and `player_rewards` reject whitespace-only `reconnect_cursor` payload values with HTTP 422 |
| Whitespace hashrate payload coverage | Done | Added integration test asserting operation start rejects whitespace-only `base_hashrate_hps` payload values with HTTP 422 |
| Empty hashrate payload coverage | Done | Added integration test asserting operation start rejects empty-string `base_hashrate_hps` payload values with HTTP 422 |
| Whitespace maintenance auth coverage | Done | Added integration test asserting cleanup rejects whitespace-only maintenance auth header values with HTTP 401 |
| Fractional checkpoint cursor payload coverage | Done | Added integration test asserting checkpoint upserts for `global` and `player_rewards` reject fractional `reconnect_cursor` payload values with HTTP 422 |
| Whitespace maintenance metrics auth coverage | Done | Added integration test asserting maintenance metrics JSON/plaintext endpoints reject whitespace-only maintenance auth header values with HTTP 401 |
| Empty maintenance auth coverage | Done | Added integration test asserting cleanup and maintenance metrics JSON/plaintext endpoints reject empty-string maintenance auth header values with HTTP 401 |
| Maintenance metrics unauthorized counter exactness coverage | Done | Added integration test asserting unauthorized maintenance metrics JSON/plaintext requests increment unknown auth-scope counter exactly twice while one authorized metrics read increments current scope once |
| Checkpoint case-variant channel coverage | Done | Added integration test asserting checkpoint GET/PUT reject case-variant channel names (for example `GLOBAL`) with deterministic unsupported-channel responses |
| WebSocket auth/session binding | Done | WebSocket now validates `player_id` + `session_id` against active auth sessions |
| Per-client channel filtering | Done | Added `global` and `player_rewards` channel filters with player-scoped event routing |
| Event/checkpoint retention cleanup endpoint | Done | Added `POST /api/v1/blockchain/maintenance/cleanup` with age/cap cleanup for network events and checkpoints |
| WebSocket heartbeat and stale-connection eviction | Done | Added server `ping` heartbeat plus stale timeout disconnect handling with configurable intervals |
| Realtime lifecycle integration coverage | Done | Added cleanup retention and stale websocket eviction tests in `tests/integration/test_blockchain_status_api.py` |
| Scheduled retention cleanup worker invocation | Done | Worker now performs periodic cleanup calls with environment-driven schedule and retention configuration |
| Realtime cleanup and eviction observability counters | Done | Added structured logs with cumulative cleanup run/deletion totals and websocket stale-eviction totals |
| Maintenance endpoint auth guardrails | Done | Added maintenance token header validation for blockchain cleanup endpoint with unauthorized-attempt logging |
| Realtime operations runbook baseline | Done | Added docs/operations-runbook.md with scheduler controls, alert thresholds, and incident response steps |
| Maintenance token rotation procedure | Done | Added runbook rotation steps and quarterly checklist requirements for shared API/worker maintenance token updates |
| Cleanup endpoint rate limiting guard | Done | Added lightweight in-memory request window cap and 429 response with Retry-After for excess cleanup calls |
| Maintenance access audit logging enrichment | Done | Cleanup endpoint logs now include source IP and user-agent on success, unauthorized, and rate-limited events |
| Worker cleanup failure exponential backoff | Done | Added consecutive-failure backoff with configurable cap to reduce retry pressure during API outages |
| Optional persisted cleanup rate-limit state | Done | Added DB-backed `maintenance_cleanup_rate_limit_state` limiter option to preserve windows across API restarts |
| Maintenance metrics export contract | Done | Added authenticated `GET /api/v1/blockchain/maintenance/metrics` with `maintenance.metrics.v1` counters contract |
| Worker cleanup startup jitter option | Done | Added configurable startup jitter delay for cleanup schedule staggering in multi-worker deployments |
| Persisted limiter retry-after boundary coverage | Done | Added integration test coverage validating persisted limiter `Retry-After` behavior near window expiry |
| Maintenance dual-token auth overlap support | Done | Maintenance endpoints now accept current and optional previous token during credential rotation windows |
| Plaintext maintenance metrics endpoint | Done | Added authenticated Prometheus-style plaintext metrics endpoint aligned to maintenance metrics contract |
| Maintenance token-scope observability labels | Done | Added configurable scope labels plus scope-attributed maintenance auth counters in logs and metrics exports |
| Worker maintenance token file-secret support | Done | Worker now supports `MAINTENANCE_AUTH_TOKEN_FILE` with safe fallback to env token and startup source-mode logging |
| Token-scope metrics dashboard and alert examples | Done | Added runbook guidance for unknown-scope spike detection and previous-token overlap decay monitoring |
| Worker token file-mounted path integration coverage | Done | Added worker cleanup integration test that validates file-path token header usage against a local HTTP endpoint |
| Worker startup missing-token validation warning | Done | Worker now emits explicit warning in non-local environments when both file and env maintenance token sources are unset |
| Unknown token-scope metrics assertion coverage | Done | Maintenance metrics integration test now verifies unauthorized metrics calls increment the `unknown` token scope counter |
| Missing-token incident troubleshooting guidance | Done | Added runbook section for `cleanup_scheduler_missing_maintenance_token` incident handling, rollback, and canary verification |
| Unauthorized plaintext metrics unknown-scope coverage | Done | Integration test now verifies unauthorized plaintext metrics calls are reflected in unknown token-scope counters via authorized metrics fetch |
| Staged token rotation rollback criteria guidance | Done | Added explicit stage-based rollback thresholds in runbook using `token_scope=previous` and `token_scope=unknown` metric signals |
| Worker token-file fallback integration coverage | Done | Added integration tests validating fallback to env token when `MAINTENANCE_AUTH_TOKEN_FILE` is unreadable or empty |
| Maintenance alert routing and escalation ownership guidance | Done | Added explicit owner/escalation mapping and handoff checklist for unknown scope, unauthorized attempts, and rate-limit spikes |
| Previous token-scope overlap metrics integration coverage | Done | Added integration coverage validating `token_scope=previous` behavior for both JSON and plaintext metrics endpoints during overlap windows |
| Overlap-window sunset verification guidance | Done | Added concrete metric query examples and 24h/48h recommended observation windows for rotation closure verification |
| Unauthorized cleanup unknown-scope metrics coverage | Done | Added integration coverage verifying unauthorized cleanup calls increment `token_scope=unknown` when validated via authorized metrics retrieval |
| Post-rotation audit evidence capture guidance | Done | Added runbook guidance for capturing query screenshots, deploy IDs, secret version IDs, and overlap timestamps with retention policy windows |
| Mixed-request deterministic scope-counter integration coverage | Done | Added integration test validating deterministic per-scope counter totals across consecutive authorized and unauthorized maintenance requests |
| Weekly maintenance security review checklist guidance | Done | Added concise runbook checklist for weekly review of unknown/previous/current scope trends and unauthorized-attempt follow-up |
| Plaintext mixed-scope label integration coverage | Done | Added integration assertions that plaintext metrics include all observed scope labels after mixed authorized/unauthorized request sequences |
| Monthly maintenance control self-audit guidance | Done | Added runbook checklist to baseline monthly unknown/previous/current/rate-limit metrics and tune alert thresholds with explicit action triggers |
| Persisted vs in-memory mixed-scope parity integration coverage | Done | Added integration test validating identical unknown/current/previous scope counters under mixed maintenance traffic in both rate-limit modes |
| Workstream ownership governance closure | Done | Assigned role-based owners across active and upcoming workstreams to close the M0 governance gap |
| CI DB integration automation decision | Done | Decided to run optional CI-level DB integration automation as M1 hardening support work |
| M1 contract sign-off sequencing decision | Done | Confirmed sign-off order: simulation kernel -> blockchain/difficulty -> economy/ledger |
| Optional CI DB integration automation implementation | Done | Added optional `db-integration` GitHub Actions job with Postgres service and explicit DB-backed test suite trigger |
| M1 ordered sign-off checklist documentation | Done | Added `docs/m1-slice-1-signoff-checklist.md` with required gate sequence and evidence expectations |
| M1 client gameplay minimal slice planning baseline | Done | Added `docs/m1-client-gameplay-minimal-slice-plan.md` aligned with server-authoritative API/websocket contracts |
| M1 client gameplay implementation ticketization | Done | Added `docs/m1-client-gameplay-implementation-tickets.md` covering session bootstrap, status HUD, reconnect stream, reward timeline, and shell orchestration |
| M1 client gameplay shell scaffold baseline | Done | Added initial Godot network/shell scripts in `client-godot/scripts/network` and `client-godot/scripts/ui` plus README updates |
| Optional CI workflow-dispatch DB baseline run | Done | Workspace is now git-backed and dispatch works; run `31954573823` executed and surfaced missing `httpx` in CI dependency install path |
| Client gameplay shell HTTP execution wiring | Done | Added async request execution for register/login/status/snapshot/rewards/checkpoints in `client-godot/scripts/network/gmn_api_client.gd` |
| Client gameplay websocket reconnect checkpoint wiring | Done | Added stream connect/poll/ping-pong/cursor ack plus checkpoint restore/persist orchestration in shell controller and stream client |
| Client gameplay shell UI render adapter wiring | Done | Added `gameplay_shell_view_model.gd` and `gameplay_shell_panel.gd` to map authoritative payloads and bind label-based UI rendering |
| Client-side contract and reconnect smoke validation baseline | Done | Added `gmn_contract_validation_smoke.gd`, `gmn_reconnect_smoke.gd`, and `gmn_gameplay_shell_smoke_runner.gd` |
| Concrete gameplay shell scene wiring | Done | Added `client-godot/scenes/gameplay_shell.tscn` plus `gameplay_shell_scene_root.gd` to instantiate and wire `GameplayShellController` + `GameplayShellPanel` |
| Client operation intent command plumbing | Done | Added non-authoritative start/stop intent pass-through calls in API client and shell controller without local progression mutation |
| Backend operation intent endpoint contracts | Done | Added `/api/v1/blockchain/operations/intents/start` and `/api/v1/blockchain/operations/intents/stop` with server-authoritative player binding rules and validation |
| Operation intent integration coverage | Done | Added integration tests validating start/stop transitions, conflict handling, and rejection of unauthorized authoritative payload fields |
| Operation intent authenticated session binding | Done | Operation start/stop intents now derive `player_id` from active `session_id` on the server and no longer trust client-supplied player identity |
| Scene-level operation action controls | Done | Added operation input fields/buttons and action status label wiring in `gameplay_shell_scene_root.gd` + `client-godot/scenes/gameplay_shell.tscn` |
| Operation runtime tick orchestration loop | Done | Added authoritative runtime tick advancement for active operations on status/snapshot/network-events and websocket loop paths |
| Operation intent reconnect-event coverage | Done | Added integration tests validating operation-intent progression and reconnect-safe network event cursor behavior |
| Operation intent websocket global-channel coverage | Done | Added integration test asserting operation-intent-driven `network.block_progress.v1` events stream over authenticated `channel=global` websocket sessions |
| Operation intent stop-state websocket reconnect coverage | Done | Added integration test asserting no new `network.block_progress.v1` events after stop intent when reconnecting from saved websocket cursor |
| Operation intent client contract documentation alignment | Done | Updated client-facing docs with session-bound intent contracts (`session_id` query + no client `player_id` payload field) across gameplay plan, ticket map, and client README |
| Operation intent client request-shape smoke coverage | Done | Added `gmn_operation_intent_contract_smoke.gd` and wired it into `gmn_gameplay_shell_smoke_runner.gd` to assert `session_id` query usage and payload exclusion of `player_id` |
| Operation intent API reference note | Done | Added `docs/operation-intents-api-reference.md` with start/stop request/response examples plus standard error cases |
| Operation intent response contract assertion hardening | Done | Expanded blockchain integration tests to assert response fields (`operation_id`, `player_id`, `accepted`, `status`, `detail`) across start/stop intent flows |
| Operation intent transport transition guidance note | Done | Added migration note documenting query-to-header transport planning while preserving server-derived identity and stable response contract fields |
| Operation intent expired-session unauthorized coverage | Done | Added integration test asserting both start and stop intents return 401 with `Invalid session binding` when session binding is expired |
| Operation intent transport migration proposal baseline | Done | Added `docs/operation-intents-transport-migration-proposal.md` covering header shape, compatibility window, deprecation milestones, and rollback criteria |
| Operation intent dual-mode transport integration scaffolding | Done | Added server support for query-plus-header session transport (`X-Session-Id`), plus integration coverage for header-only success and query/header mismatch rejection |
| Operation intent transport-mode observability instrumentation | Done | Added maintenance metrics counters for `query`/`header`/`dual_match`/`mismatch`/`missing` request modes, plus plaintext Prometheus export and integration assertions |
| Operation intent strict transport guardrail option | Done | Added `OPERATION_INTENT_REQUIRE_HEADER_BINDING` to reject query-only transport in canary environments, with integration coverage and `query_rejected_strict` metrics mode |
| Operation intent query-sunset release checklist | Done | Added `docs/operation-intents-query-sunset-release-checklist.md` with dated release-note timeline, evidence bundle, rollback triggers, and owner stage gates |
| Operation intent env-gated query-sunset test staging | Done | Added integration sunset test path gated by `GMN_ENABLE_QUERY_SUNSET_TESTS=1` to validate header-only behavior during strict-mode windows |
| Operation intent transport evidence capture helper | Done | Added `tools/capture_operation_intent_transport_metrics.py` to capture maintenance metrics snapshots and short trend deltas/rates for promotion evidence bundles |
| Operation intent production decision memo template | Done | Added `docs/operation-intents-production-rollout-decision-memo-template.md` mapping helper JSON fields and threshold checks into a standardized go/no-go artifact |
| Operation intent query-share helper output mapping | Done | Extended metrics helper to emit `query_share_from_deltas` and updated checklist/memo docs to use canonical query-share fields for promotion gates |
| Operation intent 14-day rollout bundle builder | Done | Added `tools/build_operation_intent_rollout_bundle.py` to combine daily captures into one threshold-oriented bundle (`aggregate` + `threshold_checks`) for decision memo completion |
| Operation intent decision memo prefill helper | Done | Added `tools/prefill_operation_intent_decision_memo.py` to pre-populate decision draft JSON from rollout bundle values while leaving manual-judgment sections explicit |
| Operation intent end-to-end dry-run workflow helper | Done | Added `tools/run_operation_intent_rollout_dry_run.py` to generate synthetic day files and verify bundle + prefill pipeline outputs in one command |
| Operation intent rollout tooling unit coverage | Done | Added `tests/unit/test_operation_intent_rollout_tooling.py` to validate bundle builder, memo prefill helper, and dry-run generator pipeline behavior |
| Operation intent threshold-check automation expansion | Done | Extended bundle `threshold_checks` with strict-rejection and mismatch-rate pass/fail flags and wired memo prefill auto-results to those checks |
| Operation intent memo markdown renderer | Done | Added `tools/render_operation_intent_decision_memo.py` plus unit coverage to generate a readable markdown decision memo from prefilled JSON draft artifacts |
| Operation intent dry-run markdown artifact wiring | Done | Updated `tools/run_operation_intent_rollout_dry_run.py` to pass strict/mismatch thresholds into bundle generation and emit `intent-transport-decision-memo.md` automatically |
| Operation intent dry-run summary contract test | Done | Expanded tooling unit test to assert dry-run JSON output reports daily file count plus bundle/draft/markdown artifact paths |
| Operation intent checklist auto-result wording sync | Done | Updated query-sunset checklist to reflect that mismatch auto-result is now computed by tooling threshold checks rather than always manual-review-only |
| Operation intent dry-run context parameterization | Done | Added `--environment-scope` and `--decision-owner` options to dry-run helper and verified prefilled memo fields honor supplied rollout context |
| Operation intent threshold-failure prefill coverage | Done | Added tooling unit test that forces query-share, strict-rejection, and mismatch threshold failures and verifies prefill helper emits `fail_candidate` auto-results |
| Operation intent rollout gate evaluator helper | Done | Added `tools/evaluate_operation_intent_rollout_gate.py` to convert bundle threshold checks into a promotion-ready/hold decision summary with optional non-zero exit for CI gating |
| Operation intent dry-run rollout evaluation wiring | Done | Updated dry-run helper to generate `intent-transport-rollout-evaluation.json` and added test coverage for emitted decision summary artifacts |
| Operation intent memo evaluation snapshot rendering | Done | Extended memo markdown renderer with optional evaluation JSON input and included rollout gate decision section in dry-run generated memo artifacts |
| Operation intent evaluator readiness count summary | Done | Added `passed_checks` and `total_checks` to rollout evaluation output and validated these fields in tooling unit tests and checklist guidance |
| Operation intent embedded gate-evaluation memo prefill | Done | Updated prefill helper to ingest rollout evaluation JSON and embed `rollout_gate_evaluation` in memo draft so markdown rendering can use draft-contained decision context by default |
| Operation intent decision package orchestrator helper | Done | Added `tools/build_operation_intent_decision_package.py` to generate bundle, evaluation, memo draft, and markdown memo in one command from capture inputs |
| Operation intent decision package fail-on-blocked mode | Done | Added `--fail-on-blocked` pass-through in decision package builder so CI can enforce non-zero exit when rollout gate evaluation is not promotion-ready |
| Operation intent decision package manifest index | Done | Decision package builder now emits `intent-transport-decision-package-manifest.json` recording thresholds/inputs and canonical artifact paths for review handoff |
| Operation intent custom manifest filename coverage | Done | Added tooling test and checklist guidance for `--manifest-name` to support custom decision-package manifest naming conventions |
| Operation intent decision package verifier helper | Done | Added `tools/verify_operation_intent_decision_package.py` with unit coverage to validate manifest artifact existence and memo/evaluation decision consistency |
| Operation intent auto verification artifact emission | Done | Decision package builder now runs verifier automatically after manifest generation and writes `intent-transport-decision-package-verification.json` |
| Operation intent dry-run decision-package parity | Done | Dry-run helper now also produces a nested decision package with manifest and verification artifacts for full rehearsal parity with production handoff flow |
| Operation intent manifest verification-path enrichment | Done | Decision package manifest now records `artifacts.verification_file` so verification output is included in manifest-indexed artifact inventory |
| Operation intent manifest schema version enforcement | Done | Added `manifest_schema_version` in package manifests and verifier `schema_supported` checks with test coverage for unsupported schema rejection |
| Operation intent package summary verification flags | Done | Decision package summary JSON now exposes `verification_verified` and `verification_schema_supported` for quick machine-readable gate status parsing |
| Operation intent verifier missing-artifact coverage | Done | Added unit coverage asserting verifier fails and reports `missing_artifacts` when manifest-referenced artifacts are deleted or absent |
| Operation intent compact package inspector helper | Done | Added `tools/inspect_operation_intent_decision_package.py` with text/json output and optional fail-on-unverified mode for concise release and CI status reporting |
| Operation intent package compact-summary artifact | Done | Decision package builder now writes `intent-transport-decision-package-summary.txt` and records `compact_summary_file` in both manifest artifacts and command summary output |
| Operation intent package compact-summary JSON artifact | Done | Decision package builder now writes `intent-transport-decision-package-summary.json` and records `compact_summary_json_file` in manifest artifacts and command summary output |
| Operation intent summary/inspector parity hardening | Done | Builder now generates compact summary `.txt`/`.json` artifacts by invoking `inspect_operation_intent_decision_package.py`, with tests asserting emitted files exactly match inspector output |
| Operation intent verifier compact-summary consistency checks | Done | Verifier now validates optional compact summary `.txt`/`.json` artifact contents against expected evaluation+verification-derived values and fails verification on mismatch |
| Operation intent dry-run compact-summary surfacing | Done | Dry-run helper now exposes decision-package compact summary `.txt`/`.json` paths in output JSON and regression coverage asserts both files are emitted |
| Operation intent dry-run top-level gate status fields | Done | Dry-run helper now surfaces `decision_package_decision`, `decision_package_promotion_ready`, `decision_package_verified`, and `decision_package_schema_supported` from compact summary JSON |
| Operation intent malformed summary JSON verification handling | Done | Verifier now converts malformed `compact_summary_json_file` payloads into structured mismatch failures (instead of hard exceptions), with regression coverage |
| Operation intent backward compatibility lock (schema 1.0) | Done | Kept compact summary verification optional for legacy manifests by confirming verifier accepts schema `1.0` manifests without `compact_summary_file`/`compact_summary_json_file` keys |
| Operation intent summary-check observability flags | Done | Verifier output now explicitly surfaces `compact_summary_checks_performed` and `compact_summary_checks_skipped` so CI can distinguish strict vs backward-compatible validation paths |
| Operation intent summary-check flag propagation | Done | Decision package builder and dry-run outputs now propagate compact summary verification path flags (`performed`/`skipped`) for machine-readable pipeline reporting |
| Operation intent inspector JSON compatibility flags | Done | Inspector JSON output now includes `compact_summary_checks_performed` and `compact_summary_checks_skipped` for consistent compatibility-path visibility across tooling outputs |
| Operation intent final summary-verification sequencing | Done | Builder now refreshes compact summary artifacts after final verification-state transition and executes a final verifier pass so summary files and verification output remain in sync |
| Operation intent summary mismatch diagnostic propagation | Done | Builder and dry-run outputs now surface compact-summary mismatch count/details from verifier output for direct CI diagnostics |
| Operation intent summary-artifact presence visibility | Done | Verifier output now includes `compact_summary_artifacts_present` so automation can distinguish absent-legacy vs present-validated summary artifact paths |
| Operation intent summary-artifact presence propagation | Done | Decision package builder and dry-run output now propagate `compact_summary_artifacts_present` for consistent compatibility-path reporting across machine-readable outputs |
| Operation intent inspector text compatibility fields | Done | Inspector text output now includes summary artifact compatibility markers (`summary_artifacts_present`, `summary_checks_performed`, `summary_checks_skipped`) with verifier text-parity enforcement |
| Operation intent inspector refresh mode | Done | Added `--verify-before-inspect` so inspector can recompute verification against current artifacts before output/fail-on-unverified checks, preventing stale-verification false positives |
| Operation intent inspector refresh JSON coverage | Done | Added regression coverage asserting refresh mode updates JSON output (`verified=false`) after post-package artifact tampering |
| Operation intent inspector mismatch diagnostic fields | Done | Inspector JSON now surfaces compact-summary mismatch count/details for parity with verifier and builder diagnostic outputs |
| Operation intent inspector text mismatch visibility | Done | Inspector text output now includes `summary_mismatch_count`, with verifier text-parity enforcement and regression coverage |
| Operation intent inspector output file mode | Done | Added `--output` support to inspector for writing rendered text/JSON payloads to disk, with regression tests validating file content parity |
| Operation intent builder/inspector output unification | Done | Decision package builder now uses inspector `--output` mode to emit compact summary `.txt`/`.json` artifacts, reducing duplicated serialization paths |
| Operation intent inspector failure-output persistence | Done | Added regression coverage that inspector still writes `--output` JSON diagnostics when `--fail-on-unverified` exits non-zero after refreshed verification |
| Operation intent dry-run inspector artifacts | Done | Dry-run helper now emits refreshed inspector summary `.txt`/`.json` files for decision package and returns both paths in its output JSON |
| Operation intent dry-run refreshed-inspector status fields | Done | Dry-run output now includes `decision_package_inspector_verified` and `decision_package_inspector_mismatch_count` sourced from refreshed inspector summary JSON |
| Operation intent dry-run refreshed-inspector mismatch details | Done | Dry-run output now includes `decision_package_inspector_mismatch_details` from refreshed inspector summary JSON for direct diagnostic payload access |
| Operation intent package inspector artifacts | Done | Decision package builder now emits refreshed inspector summary `.txt`/`.json` artifacts and records them in manifest artifacts and command summary output |
| Operation intent dry-run inspector reuse path | Done | Dry-run now consumes inspector summary file paths returned by decision package builder instead of running inspector a second time |
| Operation intent package inspector status fields | Done | Decision package summary output now includes refreshed inspector status fields (`inspector_verified`, `inspector_mismatch_count`, `inspector_mismatch_details`) |
| Operation intent inspector summary parity verification | Done | Verifier now checks optional inspector summary artifacts for content parity and exports `inspector_summary_*` diagnostics; builder and dry-run now surface those machine-readable fields |
| Operation intent dry-run parity assertions hardening | Done | Dry-run regression now validates expected values for compact/inspector parity diagnostics (performed/skipped flags, mismatch counts, mismatch details) instead of key presence only |
| Operation intent verifier mismatch counters | Done | Verifier now emits explicit `compact_summary_mismatch_count` and `inspector_summary_mismatch_count` fields so downstream consumers can use stable counters without recomputing list lengths |
| Operation intent dry-run inspector status source preference | Done | Dry-run now consumes inspector status from builder-emitted summary fields first and uses inspector-summary JSON only as fallback |
| Operation intent inspector parity boolean propagation | Done | Builder/dry-run outputs now expose verifier inspector parity booleans (`*_inspector_summary_text_matches`, `*_inspector_summary_json_matches`) for simpler CI checks |
| Operation intent malformed inspector summary JSON regression | Done | Added verifier test coverage for malformed `inspector_summary_json_file` to ensure failures are surfaced as structured mismatch diagnostics |
| Operation intent evaluation-memo parity field propagation | Done | Builder and dry-run summaries now expose verifier `evaluation_matches_memo` as machine-readable fields for direct promotion gating |
| Operation intent dry-run verified/schema source preference | Done | Dry-run now reads `decision_package_verified` and `decision_package_schema_supported` from builder verification fields first, with compact-summary JSON fallback |
| Operation intent inspector mismatch-count source preference | Done | Inspector now uses verifier `compact_summary_mismatch_count` when available (with fallback), with regression coverage for stale/tampered verification payloads |
| Operation intent inspector-only manifest compatibility regression | Done | Added verifier test ensuring manifests without `inspector_summary_*` keys still verify successfully while compact-summary checks remain active |
| Operation intent verifier failure-context propagation | Done | Builder and dry-run outputs now expose verifier `missing_artifacts` and `mismatch_details` fields for direct CI/debug consumption |
| Operation intent dry-run failed-checks field | Done | Dry-run summary now includes `decision_package_failed_checks` so blocked rollout checks are available without extra artifact reads |
| Operation intent dry-run gate-score fields | Done | Dry-run summary now includes `decision_package_passed_checks` and `decision_package_total_checks` for direct gate-score reporting |
| Operation intent compact-summary match booleans | Done | Builder and dry-run summaries now surface verifier compact-summary text/json match booleans directly for CI checks |
| Operation intent direct evaluation gate fields | Done | Builder and dry-run summaries now surface direct evaluation decision/promotion/check-count fields so consumers can avoid compact-summary JSON reads for core gate status |
| Operation intent per-check evaluation details | Done | Builder and dry-run summaries now expose the evaluation `checks` list directly for per-check CI/debug diagnostics |
| Operation intent inspector checks list parity | Done | Inspector JSON now exposes the evaluation `checks` list so all three tooling surfaces share the same per-check detail model |
| Operation intent exact checks-array parity | Done | Regression coverage now compares builder and dry-run emitted `checks` arrays verbatim against the evaluation artifact, catching content drift beyond shape/length checks |
| Operation intent verification checks vector persistence | Done | Verification JSON now persists the `checks` vector itself and builder summaries prefer that file-backed source over rehydrating from evaluation JSON |
| Operation intent inspector verification-source preference | Done | Inspector output now prefers the persisted verification `checks` vector so rendered summaries stay aligned with the file-backed contract |
| Operation intent dry-run verification-source preference | Done | Dry-run output now prefers the persisted verification `checks` vector, removing the remaining compact-summary fallback for per-check reporting |
| Operation intent builder inspector-source preference | Done | Builder inspector status fields now prefer the verification payload over the raw inspector JSON, keeping the package summary aligned with the persisted contract |
| Operation intent dry-run inspector-source preference | Done | Dry-run inspector status fields now prefer the builder's verification-backed inspector fields, removing the last raw inspector JSON fallback in the package summary |
| Operation intent dry-run raw inspector load cleanup | Done | Dry-run no longer loads the raw inspector JSON for status derivation, making the builder-backed contract explicit |
| Operation intent builder raw inspector fallback removal | Done | Builder no longer uses raw inspector JSON to backfill inspector status fields; the verification payload is now the sole source for those values |
| Operation intent dry-run compact-summary fallback removal | Done | Dry-run core gate fields now prefer verification-backed package summary values only, removing the compact-summary JSON fallback from the final summary surface |
| Operation intent strict verification checks vector | Done | Builder and inspector now carry `checks` strictly from the verification payload, removing the last evaluation fallback for the per-check vector |
| Operation intent builder raw inspector payload removal | Done | Builder no longer reads the raw inspector JSON payload at all; the package summary is now derived entirely from verification-backed fields |
| Operation intent dry-run inspector path cleanup | Done | Dry-run now uses the package-summary inspector artifact strings directly instead of rehydrating them into Path locals |
| Operation intent dry-run summary string inlining | Done | Dry-run now inlines one-use package-summary artifact strings directly in the final result payload, removing redundant locals |
| Operation intent dry-run dead inspector path removal | Done | Dry-run no longer allocates dead inspector-summary path locals during setup; the package-summary strings are used directly |
| Optional CI workflow-dispatch DB baseline rerun | Done | Run `31956249661` succeeded end-to-end (`baseline` and `db-integration` both green); total run window was 67s (`15:38:16Z` to `15:39:23Z`) |
| Local CI-mirrored full suite baseline | Done | Ran the same test selection as optional `db-integration` locally: `65` tests passed in `35.976s` |

---

## 7. Blockers
- None currently recorded.

---

## 8. Active Risks
- Risk: Starting gameplay implementation before repo and authority scaffolding exist.
  - Mitigation: Do not widen scope before M0 Slice 1 is complete.
- Risk: Progress drift between documents and actual work.
  - Mitigation: Update this tracker whenever milestone or slice status changes.

---

## 9. Decisions Pending
- None currently recorded.

---

## 10. Next Actions
1. Implement the remaining M1 simulation kernel timestamp/state-transition work and keep boundary reconstruction deterministic.
2. Tighten the M1 blockchain core slice around active-block invariants, finalization lock strategy, and duplicate-finalization prevention.
3. Continue the M1 ledger and reward-settlement path so block finalization remains immutable and replay-safe.

---

## 11. Update Rule
Whenever meaningful progress changes:
1. Update milestone status.
2. Update current slice checklist.
3. Record blockers or risks.
4. Update next actions.
