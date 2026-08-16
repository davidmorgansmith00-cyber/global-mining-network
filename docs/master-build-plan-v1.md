# Master Build Plan v1
Source constraints synthesized from [docs/global-mining-network-official-specification.md](docs/global-mining-network-official-specification.md) and [docs/game-design-brief-v1.md](docs/game-design-brief-v1.md)

## 1) Program Charter and Non-Negotiables
### Charter
Build and operate a persistent multiplayer simulation game where all players contribute to one fictional global chain, with server-authoritative progression and scalable time-based simulation from first login through long-horizon LiveOps.

### Product Outcomes
- Deliver a stable Windows-first playable product with launcher, patching, account UX, onboarding, social surfaces, and support operations.
- Preserve fairness, anti-cheat posture, and economy integrity from day one.
- Ship an MVP vertical slice that already matches final architecture direction, avoiding rewrite traps.

### Non-Negotiables
- One logical global chain only.
- Server owns all meaningful state: balances, rewards, progression, block state, outcomes.
- Time-based reconstruction over per-player per-second loops.
- Fictional blockchain simulation only, never real cryptocurrency behavior.
- Ledger-style immutable transaction history for economy actions.
- Modular monolith first; extract services only with measured scaling pressure.

### Scope Boundaries
- In scope: game client, backend simulation, operations tooling, launcher/updater, analytics, support workflows.
- Out of scope at launch: real-money competitive advantage, real tokenization, unnecessary microservice fragmentation.

## 2) Delivery Model and Team Roles
### Delivery Model
- Sprint cadence: 2-week engineering sprints.
- Tracks: Platform track (engine/backend/infra) and Product track (UX/content/live features).
- Stage gates: Architecture gate, Vertical slice gate, Closed alpha gate, Open beta gate, Launch gate.
- Quality gates: automated tests, economy safety checks, load thresholds, security review, playability review.
- Release rhythm after launch: monthly feature drops, weekly balance/data updates, emergency hotfix path.

### Small-Team Role Map (scalable)
- Technical Lead/Architect: domain boundaries, concurrency safety, scaling path.
- Backend Engineer A: mining/blockchain/difficulty/ledger cores.
- Backend Engineer B: auth/social/marketplace/admin/tools.
- Client Engineer (Godot): gameplay UI, onboarding, settings, network presentation.
- Platform Engineer (part-time early, full-time by beta): CI/CD, environments, observability, release/patch tooling.
- Game Designer/System Designer: progression, economy knobs, event design.
- Product/UX Designer: launcher/install/account/onboarding/settings/accessibility/support UX.
- QA/Simulation Engineer: automation, load simulator, economy simulator, regression.
- LiveOps/Community Support (from beta): moderation runbooks, incident comms, player support loop.

### Scale-Up Trigger
Add dedicated specialists when any two are true for 2 consecutive sprints:
- Release blockers exceed 20% sprint capacity.
- Test cycle exceeds 24 hours.
- On-call burden exceeds agreed budget.
- Feature throughput falls below roadmap baseline.

## 3) Repository and Code Structure Blueprint (monorepo folders, domain modules, naming conventions, dependency boundaries)
### Monorepo Layout
- /client-godot
- /server
- /workers
- /simulator
- /database
- /infra
- /launcher-windows
- /patcher
- /admin-web
- /docs
- /tests
- /tools
- /content

### Backend Domain Module Blueprint
- /server/api
- /server/domain/auth
- /server/domain/players
- /server/domain/mining
- /server/domain/blockchain
- /server/domain/difficulty
- /server/domain/hardware
- /server/domain/facilities
- /server/domain/power
- /server/domain/cooling
- /server/domain/economy
- /server/domain/marketplace
- /server/domain/research
- /server/domain/manufacturing
- /server/domain/automation
- /server/domain/pools
- /server/domain/events
- /server/domain/achievements
- /server/domain/notifications
- /server/domain/social
- /server/domain/anti_cheat
- /server/domain/admin
- /server/domain/analytics
- /server/shared

### Naming Conventions
- Domain-first naming: block_finalization_service, reward_settlement_worker, pool_membership_policy.
- Table names plural snake_case; event types dot-delimited with version suffix.
- API endpoints versioned under /api/v1.
- Message contracts versioned by schema_version field.

### Dependency Boundaries
- API layer depends on application services, never direct persistence logic.
- Domain modules communicate through explicit service interfaces/events, not internal imports across aggregates.
- Shared module limited to primitives, utility types, and cross-cutting concerns.
- Workers consume domain application services via command/event contracts.
- Client cannot import or replicate authoritative formulas.

### Modular Monolith to Service Extraction Path
- Phase 1: modular monolith with strict package boundaries and queue-backed asynchronous workloads.
- Phase 2: isolate hotspots behind internal interfaces and asynchronous boundaries.
- Phase 3: extract only proven bottlenecks (example: websocket fanout, analytics pipeline, matchmaking-like heavy subsystem if introduced).
- Extraction criteria: sustained CPU/latency bottlenecks, independent scale profile, clear bounded context, no circular data ownership.

## 4) Environment Strategy (local dev, test env, staging, production)
### Local Development
- Docker Compose baseline: API, worker, PostgreSQL, Redis, object storage emulator, telemetry collector.
- One-command bootstrap with seed data profiles: minimal, gameplay, scale-smoke.
- Local launcher can target localhost build channel.

### Shared Test Environment
- Ephemeral per-branch integration environment for backend plus contract tests.
- Persistent test realm with deterministic data reset schedule.
- Automated data snapshots for replayable bug reproduction.

### Staging
- Production-like topology with reduced scale.
- Mandatory for release candidates, migration rehearsals, patch rehearsals.
- Synthetic player load always active to catch idle-time regressions.

### Production
- Blue/green or canary rollout support.
- Region strategy initially single region with multi-zone redundancy.
- Feature flags and content flags for controlled exposure.
- Operational principle: config/content changes no code deploy for routine balancing.
- Canonical chain continuity invariant across all zones and future regions (single logical chain timeline).
- Monotonic server-time authority for all authoritative timestamps and settlement windows.

## 5) End-to-End System Architecture Plan (client, api, workers, db, redis, websockets, auth, anti-cheat, analytics, admin)
### Client (Godot)
- Responsibilities: input, visualization, UX flows, local interpolation, settings, accessibility controls.
- Never authoritative for progression math, balances, rewards, block completion.

### API Layer (FastAPI)
- Handles authenticated commands, queries, and idempotent action intake.
- Validates request constraints, rates, and entitlement checks.
- Publishes domain events for asynchronous work.

### Worker Layer
- Block finalization orchestration.
- Reward settlement batching.
- Marketplace matching/settlement.
- Notification fanout.
- Analytics event materialization.
- Scheduled systems: event lifecycle, leaderboard refresh, maintenance routines.

### Data Stores
- PostgreSQL: canonical state, immutable ledgers/events, transactional integrity.
- Redis: hot aggregate caches, distributed locks, session/rate-limits, websocket fanout support.

### WebSocket Gateway
- Delivers aggregated stream updates: network state, block progress, event states, notifications.
- Contract includes event type taxonomy and payload versions.
- Backpressure and slow-consumer management required.

### Auth
- Email/password + OAuth provider support.
- Access/refresh token model with revocation and device/session tracking.
- Account recovery, verification, deletion, and security logs.

### Anti-Cheat
- Server-side validation on all value-changing actions.
- Behavior anomaly detectors and impossible-state checks.
- Action-frequency/rate heuristics with progressive enforcement.
- Full auditability for support and moderation decisions.

### Analytics and Admin
- Analytics pipeline from domain events to curated dashboards.
- Admin web for configurable game parameters and operational tools.
- Privilege-segmented admin roles with immutable admin action audit log.

## 6) Data and Domain Modeling Plan (entities, ownership, event logs, ledger design, idempotency strategy)
### Core Aggregates and Ownership
- Player aggregate owns progression profile, entitlement state, operation states.
- Blockchain aggregate owns active block, block history, finalization state.
- Economy aggregate owns ledger entries and balance projections.
- Marketplace aggregate owns listings/orders/trades lifecycle.
- Pool aggregate owns membership, contribution accounting, reward policy snapshots.
- Content aggregate owns versioned definitions for hardware, research, recipes, events.

### Data Model Principles
- Immutable append-only logs for financial/economy and critical history.
- Mutable projections for low-latency reads.
- Every value-changing command persists a causality trail.

### Numeric Strategy Contract
- Canonical backend accounting types:
	- Integer smallest units for discrete currencies/resources where exact arithmetic is required.
	- Fixed-precision decimal for ratios and configured coefficients that must round deterministically.
	- No floating-point as authoritative source for ledger or reward settlement outputs.
- Rounding ownership:
	- Ledger and reward settlement own authoritative rounding decisions.
	- Client formatting never changes authoritative stored values.
- Magnitude policy:
	- Define tested magnitude envelopes for hashrate, cumulative work, and long-horizon resource totals.
	- Add overflow/underflow guards and fail-closed behavior for out-of-range values.
- Serialization policy:
	- API/WebSocket contracts define numeric encoding rules for large values (string-encoded large integers where needed).
	- Client formatting layer supports engineering units and scientific notation without precision loss in display.

### Ledger Design
- Double-entry style transaction records where applicable.
- Required fields: transaction id, actor, resource, amount, reason, related entity id, post-balance snapshot, timestamp.
- No direct balance mutation without ledger write.

### Event Log Plan
- Domain event store tables by bounded context.
- Event schema includes event_id, event_type, schema_version, aggregate_id, occurred_at, correlation_id, causation_id.
- Replay-safe processing with checkpointed consumer offsets.

### Idempotency Strategy
- Idempotency key required for all mutating client commands.
- Dedup tables keyed by actor + command type + idempotency key.
- Workers use exactly-once effect simulation through transaction guards, unique constraints, and retry-safe command handlers.

### Concurrency Safeguards
- Block finalization lock strategy: Redis lock plus DB transaction checks.
- Unique constraints preventing duplicate active block and duplicate reward grants.
- Compare-and-set style version fields on contention-prone entities.

### Block Record Contract
Mandatory canonical block fields:
- block_number
- block_id
- previous_block_id
- difficulty
- required_work
- accumulated_work
- network_hashrate_snapshot
- participating_miners_count
- start_timestamp
- completion_timestamp
- reward_pool_snapshot
- special_modifiers_snapshot
- event_context
- historical_stats

Ownership and write path:
- Blockchain aggregate owns canonical block record creation and mutation during active lifecycle.
- Block finalization worker performs atomic transition from active to finalized record.
- Post-finalization block records are immutable except for additive analytics projections stored separately.

### Reward Settlement Determinism Contract
- Deterministic ordering key for settlement inputs: block_id, then pool_id (if applicable), then player_id.
- Fixed rounding mode for fractional reward splits: floor at the smallest currency unit.
- Residual distribution rule: assign remainder by deterministic ordering key.
- Tie handling rule: stable ordering by immutable identifiers only.
- Replay guarantee: same canonical inputs must always produce identical outputs.
- Pool policy snapshot rule: once a block closes, reward policy used for that block is immutable.

### Piecewise Time Reconstruction Contract
- Reconstruct progression as piecewise intervals bounded by authoritative state-change timestamps.
- State changes that must split intervals include: upgrades, equipment install/remove, pool join/leave, event modifier start/end, maintenance state changes.
- Each interval uses the exact modifier set active during that interval; no blended averaging across boundary changes.
- Offline catch-up applies the same piecewise contract with configured cap windows.
- Authoritative timestamp source is server time only.

## 7) Networking Plan (REST/WebSocket boundaries, contracts, message taxonomy)
### REST Boundaries
- REST for command/query actions: account, inventory, purchase, install, research start, market order actions, settings changes.
- Responses include authoritative state deltas and canonical timestamps.
- Contract-first OpenAPI with generated client stubs.

### WebSocket Boundaries
- WebSocket for aggregated live telemetry and event updates.
- No per-hash or per-second player command traffic.
- Reconnect protocol with last-seen sequence for gap recovery.

### Message Taxonomy
- network.block_progress.v1
- network.hashrate_snapshot.v1
- event.lifecycle.v1
- market.ticker.v1
- pool.update.v1
- player.notification.v1
- moderation.notice.v1
- system.maintenance.v1

### Contract Governance
- Backward compatibility window for one major client version lag.
- Deprecation policy: announce in launcher and patch notes two releases before removal.
- Schema validation in CI for REST and WebSocket payloads.

## 8) Gameplay System Build Order (all major game systems, exact sequencing and dependencies)
### Sequenced Build Order
1. Identity and Session Core
- Dependencies: none.
- Delivers account creation/login/session lifecycle.

2. Player Profile + Starter State
- Dependencies: identity.
- Delivers first-login initialization and starter machine.

3. Time-Based Simulation Kernel
- Dependencies: player state.
- Delivers authoritative elapsed-time reconstruction primitives.

4. Global Blockchain Core
- Dependencies: simulation kernel.
- Delivers active block, accumulation logic, finalization path, history tables.
- Enforces invariant: block finalizes only when accumulated_work >= required_work, atomically under contention controls.

5. Difficulty Engine
- Dependencies: blockchain history.
- Delivers moving-window dynamic difficulty with config-driven parameters: target block time, window length, max upward adjustment, max downward adjustment.

6. Economy Ledger + Balance Projections
- Dependencies: blockchain core.
- Delivers reward posting and all value changes via ledger.

7. Hardware/Power/Cooling Foundations
- Dependencies: economy + simulation kernel.
- Delivers effective hashrate from constraint systems.

8. Offline Progression Rules
- Dependencies: simulation kernel + core systems.
- Delivers capped offline reconstruction.

9. Marketplace v1 (NPC + Player Listings)
- Dependencies: ledger + inventory.
- Delivers race-safe buy/sell settlement.

10. Research and Manufacturing v1
- Dependencies: ledger + content definitions.
- Delivers time-based unlock/production loops.

11. Pools + Reward Distribution Policies
- Dependencies: blockchain + ledger + player history.
- Delivers cooperative competition layer.

12. Events/Special Blocks/Fork Event Framework
- Dependencies: blockchain + content + pools.
- Delivers LiveOps event engine, including late-game fork events with branch contribution windows.
- Fork-event rule: branches may compete during a bounded event window, then resolve deterministically to one canonical continuation.
- Losing branch data is retained as immutable historical event records only and never becomes an active competing canonical head after resolution.

13. Social + Notifications + Basic Moderation
- Dependencies: auth + profiles.
- Delivers friend basics, pool communication, notification center.

14. Chain Explorer + Player History
- Dependencies: block history + analytics materialization.
- Delivers persistent world memory surfaces.

15. Automation Systems
- Dependencies: manufacturing/research/power/cooling.
- Delivers late-game strategy over repetitive actions.

16. Endgame Environment Framework
- Dependencies: all core simulation systems.
- Delivers extensible constraints for off-world progression.

## 9) UX and Product Surface Plan (launcher, patcher/updater, install/update UX, account UX, onboarding tutorial, settings, notifications, chain explorer, marketplace UX, social UX)
### Launcher and Installer (Windows-first)
- Deliver signed installer and signed launcher executable.
- Launcher features: install path selection, disk space check, repair install, channel selection, patch notes, maintenance alerts.
- Update downloader: segmented downloads with resume, checksum validation, delta patch support, fallback full package.
- UX states: install, verifying, downloading, applying patch, rollback on failure, launch readiness.
- Background updates optional with user-controlled bandwidth cap.

### Account UX
- First-run account creation/login with clear privacy and telemetry choices.
- Email verification and recovery flows with minimal friction.
- Session visibility: current device list and revoke controls.

### Onboarding Tutorial
- First 20 minutes teach: hashrate, power, heat, global contribution, first upgrade, first meaningful decision.
- Contextual progressive disclosure, not modal overload.
- Early global HUD always visible to reinforce one shared world.

### Settings and Accessibility
- Graphics presets and performance mode.
- Input remapping and sensitivity controls.
- UI scaling, text size, color-blind safe palettes, contrast presets.
- Motion reduction and animation intensity controls.
- Notification preference center with granular categories.
- Telemetry opt-in toggle with transparent impact statement.

### Core Product Surfaces
- Notifications hub with action links.
- Chain explorer with milestones and records.
- Marketplace UX focused on trust signals and clear fees.
- Social UX: pool browse/join, profile cards, moderation reporting entry points.

### Support Workflows in Product
- In-app report issue flow with log attachment consent.
- Self-service troubleshooting panel: connectivity test, patch integrity check, FAQ shortcuts.
- Status page integration and incident banners.

## 10) Content Pipeline Plan (data-driven content authoring, validation, rollout)
### Authoring Model
- Content lives in structured data definitions under /content with strict schemas.
- Categories: hardware, buildings, research, recipes, events, special blocks, achievements, localization text.

### Validation Pipeline
- Schema validation on commit.
- Balance sanity checks: impossible recipes, invalid unlock chains, negative outputs.
- Dependency graph validation: no orphan unlocks, no cycle deadlocks unless explicitly allowed.

### Rollout Strategy
- Content packs versioned and signed.
- Staged rollout: internal, staging, canary cohort, global.
- Hotfix path for data-only corrections without client patch when possible.

### Governance
- Content review board: design + backend + LiveOps.
- Every content change requires expected economy impact note.

## 11) Build/Release/Distribution Plan (build artifacts, patch channels, delta updates, rollback, client version compatibility)
### Build Artifacts
- Client package, launcher package, patch manifests, server container images, worker images, admin web bundle.
- Artifact provenance: commit hash, build id, timestamp, signer.

### Release Channels
- Internal, Experimental, Beta, Stable.
- Launcher selects channel per user entitlement.

### Delta Update Strategy
- Binary diff patches between adjacent versions.
- Fallback to full download when base mismatch detected.
- Chunked transfer with resume and post-apply verification.

### Rollback Plan
- Client rollback via launcher manifest pin.
- Server rollback with reversible migrations policy and guarded feature flags.
- Emergency kill-switches for problematic events/content.

### Compatibility Policy
- Support N and N-1 client versions for online access window.
- Hard minimum version enforcement for protocol-breaking changes.
- User-facing deprecation schedule in launcher messaging.

## 12) Security and Compliance Plan (auth hardening, secrets, abuse handling, moderation)
### Auth and Account Security
- Argon2id or equivalent modern password hashing.
- MFA-ready architecture even if not launch-critical.
- Rate limits and lockout strategy with anti-enumeration responses.
- Signed, rotating tokens with revocation and anomaly checks.

### Secrets and Infrastructure Security
- Secrets in managed vault, never in repo.
- Short-lived credentials for automation where possible.
- Environment-level secret scopes and rotation cadence.

### Abuse and Moderation
- Report intake pipeline with evidence snapshots.
- Moderation roles and action taxonomy: warning, mute, suspension, ban.
- Appeal workflow with audit trail and SLA targets.

### Compliance Baseline
- Privacy policy alignment for telemetry and account data.
- Data retention schedules by data class.
- Account deletion/export workflows and operational playbook.

## 13) Observability and Operations Plan (logs, metrics, tracing, alerts, SLOs, runbooks, on-call)
### Telemetry Stack
- Structured JSON logs with correlation ids.
- Metrics: API latency/error, worker lag, block finalize latency, reward settlement lag, economy deltas, websocket connection health.
- Tracing across API to DB/Redis/worker boundaries.

### SLO Framework
- API availability SLO.
- Action success SLO for key commands.
- Block finalization correctness/latency SLO.
- Update delivery success SLO for launcher patching.

### Alerting
- Severity tiers with paging thresholds.
- Alert dedup and suppression windows during planned maintenance.
- Synthetic checks for login, market action, websocket updates.

### Runbooks and On-Call
- Incident runbooks for auth outage, block finalization contention, ledger mismatch alarm, patch failure spike.
- Follow-the-sun not required initially; define local primary/secondary rotation.
- Post-incident review template with prevention tasks.

## 14) Testing and Simulation Plan (unit/integration/load/economy simulation/mass player simulation)
### Test Pyramid
- Unit tests for domain rules and formulas.
- Integration tests for API + DB + Redis + workers.
- Contract tests for REST/WebSocket schemas.
- End-to-end tests for critical user journeys including launcher update flow.

### Concurrency and Integrity Tests
- Simultaneous block completion contention.
- Duplicate purchase/order race attempts.
- Idempotency replay attempts.
- Offline progression tampering scenarios.
- Piecewise reconstruction tests: upgrade-at-timestamp boundary.
- Piecewise reconstruction tests: pool join/leave mid-interval boundary.
- Piecewise reconstruction tests: event modifier start/end boundary.
- Deterministic settlement tests: rounding, remainder distribution, and replay consistency.
- Numeric stress tests: extreme hashrate, cumulative work, and resource magnitudes across long-horizon simulations.
- Block invariant tests: finalize only when accumulated_work >= required_work under concurrent finalize attempts.

### Simulation Harnesses
- Mass player simulator with aggregated cohorts, not one process per player.
- Economy simulator for accelerated multi-month balancing.
- Scenario packs: new player growth, whale-equivalent efficiency build, event shock, market scarcity.

### Performance Gates
- Baseline load targets per milestone.
- Regression budget: no release if key latencies degrade beyond agreed threshold.
- Soak tests before beta and launch.

## 15) Milestone Roadmap from M0 to Launch + 6 months LiveOps (exit criteria per milestone)
### M0: Foundations (Weeks 1-4)
- Exit: monorepo scaffold, CI, local compose, auth skeleton, seed pipeline, architecture docs approved.

### M1: Simulation Core Vertical Slice (Weeks 5-10)
- Exit: single global active block, time-based contribution, reward ledger posting, starter progression, minimal client loop.

### M2: Core Economy and Constraints (Weeks 11-16)
- Exit: hardware/power/cooling constraints, offline progression caps, NPC market, basic telemetry.

### M3: Social-Competitive Core (Weeks 17-22)
- Exit: pools v1, player marketplace v1, leaderboards, notifications center, anti-cheat v1.

### M4: Productization and Launcher Beta (Weeks 23-28)
- Exit: Windows installer/launcher, patching + rollback, onboarding tutorial v1, settings/accessibility baseline.

### M5: Content and Event Framework (Weeks 29-34)
- Exit: data-driven content pipeline, special blocks/events v1, chain explorer v1, admin tuning panels.

### M6: Closed Beta (Weeks 35-40)
- Exit: stability targets met, support workflows live, moderation workflows active, load tests at beta concurrency target.

### M7: Open Beta (Weeks 41-46)
- Exit: patch success rate target met, incident response proven, economy health within guardrails, onboarding conversion targets met.

### Launch (Weeks 47-52)
- Exit: launch readiness checklist complete, launch runbook rehearsed, Genesis process approved and immutable handling verified.

### LiveOps +6 Months
- Month 1: stability and economy tuning.
- Month 2: first major event cadence.
- Month 3: marketplace improvements and social polish.
- Month 4: automation depth expansion.
- Month 5: midgame content pack.
- Month 6: first endgame framework expansion gate.
- Exit for month 6: sustained SLO attainment, content cadence stable, support SLA maintained.

## 16) Risk Register and Mitigations
1. Risk: block finalization race conditions.
- Mitigation: dual lock strategy, unique constraints, chaos concurrency tests.

2. Risk: economy inflation or sink failure.
- Mitigation: simulator-driven balancing, guardrail alerts, rapid data-only tuning.

3. Risk: launcher patch failures at scale.
- Mitigation: chunk resume, checksum verification, staged channel rollout, rollback manifest.

4. Risk: anti-cheat false positives harming trust.
- Mitigation: graduated enforcement, human review queue, appeal tooling.

5. Risk: modular monolith entropy into tight coupling.
- Mitigation: dependency checks, architecture reviews each sprint, interface contracts.

6. Risk: small team overload near launch.
- Mitigation: milestone scope discipline, explicit cut lines, automation-first QA investment.

7. Risk: websocket fanout bottlenecks.
- Mitigation: aggregated payloads, redis pub/sub optimization, horizontal gateway scale path.

8. Risk: content errors break progression.
- Mitigation: schema + dependency validation, staging playtest gates, feature-flagged rollout.

## 17) Definition of Done Checklists by Domain
### Backend Domain Systems
- Authoritative owner documented.
- Persistence model and migration included.
- Idempotency and concurrency protections tested.
- Metrics and logs emitted.
- Failure and retry behavior verified.

### Client and UX
- UX flow tested for first-time and returning users.
- Accessibility baseline validated.
- Error states and recovery paths implemented.
- Telemetry and privacy choices exposed clearly.

### Launcher/Patcher
- Install, update, resume, repair, rollback verified.
- Signature/checksum verification enforced.
- User messaging clear for each update state.

### Data/Content
- Schema validation passes.
- Balance sanity checks pass.
- Rollback path defined.
- Change notes include expected economy impact.

### Operations
- Dashboards and alerts deployed.
- Runbook entry created/updated.
- On-call ownership assigned.
- SLO impact reviewed.

### Security/Moderation
- Threat review completed.
- Abuse handling path connected to support workflows.
- Audit logging verified for privileged actions.

## 18) First 90 Days Detailed Sprint-by-Sprint Plan
### Sprint 1 (Weeks 1-2)
- Monorepo skeleton and dependency boundaries.
- CI pipeline with lint/test gates.
- Local compose environment + seed scaffolding.
- Auth/account architecture design review.

### Sprint 2 (Weeks 3-4)
- Auth v1 endpoints and session model.
- Player profile/starter bootstrap.
- Domain event envelope standardization.
- Initial observability stack integration.

### Sprint 3 (Weeks 5-6)
- Time-based simulation kernel.
- Global active block state model.
- Block accumulation read model.
- Concurrency guard design tests.

### Sprint 4 (Weeks 7-8)
- Block finalization worker path.
- Difficulty adjustment engine v1.
- Ledger v1 with immutable transaction records.
- Critical integrity tests.

### Sprint 5 (Weeks 9-10)
- Hardware/power/cooling formulas v1.
- Starter upgrade loop in client.
- Offline progression caps v1.
- Telemetry events for progression funnel.

### Sprint 6 (Weeks 11-12)
- NPC market v1 and inventory integration.
- WebSocket aggregated network updates.
- Basic notification center.
- First internal playable vertical slice review.

### Sprint 7 (Weeks 13-14)
- Player marketplace listing/settlement v1.
- Pool creation/join flow v1.
- Leaderboard pipeline baseline.
- Anti-cheat rate and validation controls v1.

### Sprint 8 (Weeks 15-16)
- Windows launcher MVP with install/launch flow.
- Patcher manifest generation pipeline.
- Account UX polish + recovery flows.
- Accessibility pass 1 on core screens.

### Sprint 9 (Weeks 17-18)
- Onboarding tutorial v1.
- Settings panel v1 including telemetry opt-in.
- Support issue-report flow in client/launcher.
- Admin web v1 for config read/write with audit logging.

### Sprint 10 (Weeks 19-20)
- Event and special block framework v1.
- Chain explorer v1 and player history v1.
- Content validation pipeline v1.
- Staging environment rehearsal and load smoke tests.

### Sprint 11 (Weeks 21-22)
- Reliability hardening and defect burn-down.
- Patch resume/rollback validation at scale.
- Moderation workflow integration.
- Closed alpha readiness assessment.

### Sprint 12 (Weeks 23-24)
- Closed alpha execution and metrics review.
- Economy and onboarding tuning.
- Incident drill and runbook maturity.
- Roadmap recalibration for beta phase.

## 19) Implementation Instruction Matrix (for each subsystem: owner, prerequisites, files/folders expected, tests required, done criteria)
| Subsystem | Owner | Prerequisites | Expected Folders | Tests Required | Done Criteria |
|---|---|---|---|---|---|
| Auth and Accounts | Backend B | CI, DB baseline | /server/domain/auth, /server/api/auth, /tests/auth | Unit, integration, abuse-rate tests | Login/recovery/revocation stable with audit logs |
| Simulation Kernel | Backend A | Player state model | /server/domain/mining, /server/shared/time, /tests/simulation | Unit formula tests, replay tests | Deterministic elapsed-time reconstruction verified |
| Blockchain Core | Backend A | Simulation kernel | /server/domain/blockchain, /workers/blocks, /database/migrations | Concurrency tests, integration tests | Single active block invariants always hold and finalize condition (accumulated_work >= required_work) is enforced atomically |
| Difficulty Engine | Backend A + Design | Block history | /server/domain/difficulty, /content/difficulty | Unit + simulation tests | Config table exists (target time, window, max up/down bounds) and target block-time control stays within configured adjustment bounds |
| Economy Ledger | Backend A | Blockchain events | /server/domain/economy, /database/ledger, /tests/economy | Integrity, idempotency, race tests | No balance mutation without ledger entry |
| Hardware/Power/Cooling | Backend A + Design | Ledger and content schemas | /server/domain/hardware, /server/domain/power, /server/domain/cooling, /content/hardware | Unit + progression simulation | Effective hashrate constraints match design rules |
| Marketplace | Backend B | Ledger + inventory | /server/domain/marketplace, /workers/marketplace, /tests/marketplace | Race, double-spend, integration | Atomic settlements with clear fee accounting |
| Pools | Backend B | Blockchain + profiles | /server/domain/pools, /server/api/pools, /tests/pools | Unit policy tests, integration | Reward policy snapshots immutable once earned |
| Events/Special Blocks | Backend A + LiveOps | Blockchain + content pipeline | /server/domain/events, /content/events, /workers/events | Schedule, rollback, simulation tests | Timed modifiers apply/revert cleanly |
| WebSocket Gateway | Platform + Backend | Redis + event stream | /server/websocket, /tests/contracts/ws | Contract, reconnect, load tests | Aggregated updates stable at target concurrency |
| Client Gameplay UX | Client Engineer + UX | Core APIs/ws | /client-godot/scenes, /client-godot/scripts, /client-godot/ui | UX regression, onboarding playtests | First-session comprehension and completion goals met |
| Launcher/Patcher Windows | Platform + Client | Build artifacts + manifests | /launcher-windows, /patcher, /tests/patching | Install/update/rollback tests | Signed install and reliable patch recovery |
| Admin Web | Backend B + Platform | Auth RBAC + config APIs | /admin-web, /server/domain/admin, /tests/admin | Permission and audit tests | Safe live tuning with full change traceability |
| Analytics/Observability | Platform + QA | Event schema standards | /server/domain/analytics, /infra/monitoring, /tests/telemetry | Data quality, dashboard checks | Actionable dashboards and alerts in place |
| Moderation/Support | Product + Backend B | Social surfaces + logs | /server/domain/social, /server/domain/moderation, /tools/support | Workflow and audit tests | Report-to-action cycle meets SLA targets |
| Simulators | QA/Simulation Engineer | Domain models | /simulator/mass-player, /simulator/economy, /tests/simulators | Scale and determinism tests | Repeatable balance/scalability evidence for decisions |

## 20) Decision Log Template and Change-Control Process
### Decision Log Template
- Decision ID
- Date
- Owner
- Status: Proposed, Approved, Rejected, Superseded
- Context
- Decision
- Alternatives Considered
- Impacted Systems
- Data Migration Impact
- Operational Impact
- Security/Fairness Impact
- Rollback Plan
- Verification Plan
- Follow-up Tasks

### Change-Control Process
1. Propose change with decision log entry and explicit reason.
2. Classify change type: architecture, gameplay economy, content-only, operational.
3. Run required impact checks:
- one-global-chain integrity
- server-authority integrity
- time-based simulation integrity
- no-real-crypto compliance
- canonical chain continuity invariant
- monotonic server-time authority invariant
4. Require approvers by type:
- architecture: tech lead + backend owner + product owner
- economy: design + backend + LiveOps
- operations/security: platform + security/moderation owner
5. Validate in staging with simulator evidence if systemic.
6. Release behind feature/content flags when feasible.
7. Monitor with predefined success/failure metrics.
8. Close decision with post-release outcome note.

### Emergency Change Path
- Allowed only for active incidents or exploit containment.
- Requires incident ticket, temporary approval pair, and mandatory retroactive decision log completion within 48 hours.
