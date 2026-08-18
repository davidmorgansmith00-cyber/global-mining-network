# Global Mining Network Client UI Roadmap v1

**Status:** Phase 1 in progress
**Version:** 1.0
**Date:** 2026-08-18
**Owner:** Gameplay and UX
**Client:** Godot 4.x / GDScript

## 1. Purpose

This roadmap turns the existing Godot gameplay shell into a usable, expandable client for Global Mining Network. It is ordered around the current backend capabilities and the product's core fantasy:

- One fictional global chain.
- One shared network visible from the first session.
- Meaningful engineering tradeoffs instead of repetitive clicking.
- A player operation that grows from a weak home computer to civilization-scale infrastructure.

The roadmap is intentionally incremental. It extends the existing client network and gameplay-shell code instead of introducing a second client architecture.

## 2. Non-Negotiable Client Rules

The Godot client is presentation, input, and local interaction only.

The server owns:

- Player identity, sessions, balances, inventory, rewards, and progression.
- Hardware, power, cooling, effective hashrate, and offline progression.
- Operation acceptance, contribution, block progress, finalization, and rewards.
- Market stock, prices, purchases, upgrades, pools, events, and notifications.
- The canonical chain and all historical outcomes.

The client may:

- Render server payloads.
- Format values for display without changing their meaning.
- Sort, filter, paginate, and search received read models.
- Interpolate visual motion for presentation only.
- Send explicit user intents and show pending, success, and failure states.

The client must not:

- Calculate authoritative rewards, balances, effective hashrate, power penalties, cooling penalties, or block completion.
- Send per-second mining or progression requests.
- Invent a local chain, local balance, or local reward result.
- Treat a stale client estimate as authoritative after reconnect.
- Hide server rejection, maintenance, or stale-data conditions.

Every screen in this roadmap must name its authoritative endpoint or stream and its recovery behavior.

## 3. Existing Client Baseline

The repository already contains a useful M1 foundation:

- `GmnApiClient` and `GmnSession` for auth and runtime session state.
- `GameplayShellController`, `GameplayShellViewModel`, `GameplayShellPanel`, and `GameplayShellSceneRoot` for the newer shell path.
- A second `gmn_*` gameplay shell path with status polling and HUD services.
- Snapshot, websocket, reconnect cursor, and checkpoint helpers.
- Reward timeline and operation-intent services.
- Contract, reconnect, scene, and integration smoke coverage.

### Foundation Decision

Phase 1 must select one supported scene composition and one controller/view-model path. New screens must use that path. The legacy path may remain temporarily for regression coverage, but it must not receive new features after the consolidation decision.

The Phase 1 contract audit must also resolve any mismatch between operation-intent URL construction, session binding, and the current server contract before the operation screen is treated as production-ready.

### Phase 1 Slice Started - 2026-08-18

- Selected `scenes/gameplay_shell.tscn` and `scripts/ui/*` as the supported shell composition.
- Added `GameplayShellUiState` for explicit loading, ready, stale, error, unauthorized, and maintenance states.
- Added a visible state line to the shell without introducing client-owned gameplay calculations.
- Preserved `session_id` through auth responses and corrected operation-intent URLs to bind to the active session.
- Added UI-state smoke coverage to the existing client smoke runner.

Remaining Phase 1 work is shared route/error primitives, scene migration tests for the legacy path, and the first-run route foundation from Phase 2.

### Phase 2 Slice Started - 2026-08-18

- Added `scenes/onboarding.tscn` as the project main scene.
- Added login and registration controls using the existing `GmnApiClient` auth methods.
- Added server bootstrap gating through `GET /api/v1/player/bootstrap` before gameplay entry.
- Added runtime session handoff into `gameplay_shell.tscn`; tokens are not persisted by the client.
- Added recoverable validation, loading, authentication failure, and bootstrap failure states.
- Added onboarding URL/session contract smoke coverage.

Remaining Phase 2 work is launcher handoff metadata, explicit session restore UX, and full UI integration coverage against the local API.

### Phase 3 Slice Started - 2026-08-18

- Added authoritative player-profile loading to the gameplay shell.
- Added starter machine, tier, base/effective hashrate, power, throttle, heat, and cooling readouts.
- Made the displayed base hashrate read-only and sourced operation start from the server profile.
- Kept the global block HUD and operation controls in the same persistent shell.
- Added starter-machine profile mapping smoke coverage.

Remaining Phase 3 work is live websocket-first refresh behavior, explicit operation status display, and end-to-end testing against the running local API.

### Phase 4 Slice Started - 2026-08-18

- Added server-backed NPC market catalog rendering to the gameplay shell.
- Added item ID and quantity purchase controls with session-bound purchase requests.
- Added accepted-purchase refresh behavior for authoritative profile and market state.
- Added market request-shape and catalog mapping smoke coverage.
- Kept upgrade controls pending because the current server contract does not expose a player upgrade command endpoint.

Remaining Phase 4 work is the contract-backed upgrade flow, richer inventory/receipt presentation, and live local API purchase validation.

### Upgrade Command Contract Implemented - 2026-08-18

The server now exposes a dedicated player upgrade runtime. The client must not turn a recommendation into a local upgrade or reuse the market purchase route as an upgrade shortcut.

The implemented server contract is:

**Start upgrade intent**

- Endpoint: `POST /api/v1/hardware/upgrades/start?session_id=<active_session_id>`
- Request body:

```json
{
	"hardware_id": "improved_workstation",
	"idempotency_key": "upgrade-<client-generated-unique-key>"
}
```

- Server derives `player_id` from the validated session.
- Server validates unlock state, current hardware, balance, inventory, conflicting upgrades, and content version.
- Server owns the actual start timestamp, cost, duration, and resulting upgrade record.
- The client must not send price, duration, hashrate, power, cooling, or completion values.

**Read upgrade status**

- Endpoint: `GET /api/v1/hardware/upgrades/current?player_id=<player_id>`
- Response must include a versioned contract such as:

```json
{
	"schema_version": "hardware.upgrade.v1",
	"status": "running",
	"upgrade_id": "<server-id>",
	"hardware_id": "improved_workstation",
	"started_at": "2026-08-18T16:00:00Z",
	"completes_at": "2026-08-20T16:00:00Z",
	"server_now": "2026-08-18T18:00:00Z",
	"completion_confirmed": false
}
```

The client may display time remaining using server timestamps, but the server decides completion. On reconnect, the client reloads this status and the player profile; it never advances progress locally.

**Completion and failure states**

The response must distinguish at least `idle`, `running`, `completed`, `rejected`, and `cancelled`. Rejections should identify stable reasons such as `insufficient_balance`, `tier_locked`, `upgrade_in_progress`, `hardware_not_owned`, or `content_version_mismatch`.

**Contract acceptance gate**

Upgrade UI can now begin against the implemented contract, subject to the following verified backend guarantees:

1. Atomic ledger-backed cost deduction and upgrade record creation.
2. Idempotent start behavior for repeated `idempotency_key` submissions.
3. Server-time-based progress and reconnect-safe status reads.
4. Authoritative profile recalculation after confirmed completion.
5. Unit, integration, race, replay, and permission tests.

The client may render the server's `next_recommended_upgrade` and `upgrade_progression` as read-only information until the upgrade UI slice is implemented. The backend migration is `0026_hardware_upgrade_runtime.sql`; routes are `/api/v1/hardware/upgrades/start` and `/api/v1/hardware/upgrades/current`.

### Phase 5 Slice Started - 2026-08-18

- Added read-only block explorer summary loading from `/api/v1/explorer/blocks`.
- Added player history summary loading from `/api/v1/explorer/players/{player_id}/history`.
- Added active event summary loading from `/api/v1/events/active`.
- Added history/event read-model smoke coverage.
- Kept canonical chain history and event results server-owned; no client mutation or reward inference was added.

Remaining Phase 5 work is detailed block/history panels, pagination, event cards, and snapshot-to-live history continuity.

### Phase 5 Visual Repair - 2026-08-18

- Fixed authenticated session handoff so gameplay receives the registered player ID after onboarding scene replacement.
- Prevented unauthenticated shell polling from requesting profile/history with an empty player ID.
- Added plain-text response handling so server error bodies render as recoverable UI errors without JSON parse noise.
- Added a minimum client window size and separated market/history rows to prevent panel overlap.

### Phase 6 Slice Started - 2026-08-18

- Added pool browse summary loading from `/api/v1/pools/browse`.
- Added hashrate leaderboard summary loading from `/api/v1/leaderboards/hashrate`.
- Added current-player leaderboard position loading from `/api/v1/players/{player_id}/leaderboard-position`.
- Added social read-model smoke coverage.
- Kept pool membership and notification commands out of this slice until their session-bound contracts are standardized.

Remaining Phase 6 work is pool membership UX, notification inbox/reconnect handling, and social permission/error states.

### Phase 7 Slice Started - 2026-08-18

- Added a runtime-only accessibility settings model aligned with the launcher guide.
- Added clamped UI scale and text scale values.
- Added high-contrast and color-mode settings fields for the next visual pass.
- Added a visible reduce-motion toggle and status readout in the gameplay shell.
- Added accessibility settings smoke coverage.

Remaining Phase 7 work is applying the palette and scale values across all controls, keyboard focus review, maintenance/recovery banners, and settings persistence policy.

### Phase 8 Slice Started - 2026-08-18

- Added an allowlisted runtime client telemetry collector for funnel and recovery events.
- Scrubbed email, passwords, tokens, session IDs, and player IDs before retention.
- Added telemetry smoke coverage and registered it in the aggregate client runner.
- Kept events local-only because the current server exposes analytics queries but no client telemetry-ingest contract.

Remaining Phase 8 work is a versioned server ingest endpoint, compatibility/version checks, release-build validation, and end-to-end telemetry delivery tests.

## 4. Roadmap Summary

| Phase | Outcome | Priority | Gate |
|---|---|---:|---|
| 1 | Consolidated app shell and UI state foundation | P0 | One supported composition path |
| 2 | Login, registration, session restore, and first-run entry | P0 | Recoverable authenticated entry |
| 3 | Starter machine screen and persistent global HUD | P0 | First playable shared-world loop |
| 4 | Hardware, power, cooling, upgrade, and market UX | P0 | First meaningful optimization decisions |
| 5 | Chain explorer, player history, and event surfaces | P1 | Persistent world history is legible |
| 6 | Pools, social, leaderboards, and notifications | P1 | Shared coordination loop is usable |
| 7 | Accessibility, settings, support, and recovery polish | P0 | Beta usability gate |
| 8 | Telemetry, contract hardening, and release readiness | P0 | Client release candidate |

Accessibility and error-state work starts in Phase 1 as shared infrastructure and closes in Phase 7. Telemetry hooks start with Phase 2 even though the final release gate is Phase 8.

## 5. Phase 1 - Foundation Consolidation and Information Architecture

**Goal:** Make one dependable application shell before adding more screens.

### Screens and Components

- Root scene and route coordinator.
- Shared top bar with player/session state, network connection state, and navigation.
- Shared loading, empty, stale-data, unauthorized, maintenance, and retry states.
- Shared modal/dialog, toast, confirmation, and destructive-action patterns.
- Shared numeric formatting for credits, work, rates, percentages, heat, and time.
- Shared responsive layout rules for desktop window sizes.
- Screen-level view models that consume authoritative payloads without domain calculations.

### Contracts

Reuse and normalize:

- Auth register, login, refresh, and logout.
- Player bootstrap and profile.
- Blockchain status and network snapshot.
- Network event stream and reconnect checkpoints.
- Player rewards.
- Operation start and stop intents.

Add a contract adapter boundary so raw API dictionaries do not spread across scene scripts. Each adapter records the payload schema version and last successful refresh time.

### Acceptance Criteria

- One supported gameplay shell path is documented and instantiated by the main scene.
- Existing session, HUD, snapshot, reconnect, reward, and operation tests remain green.
- A failed request produces a recoverable UI state rather than a blank panel.
- Stale data is visibly marked and cannot be mistaken for a fresh authoritative result.
- No new screen owns balances, rewards, progression, or simulation state.

### Tests

- Scene wiring and route selection tests.
- Contract-key smoke tests for status, snapshot, events, rewards, profile, and auth.
- View-model mapping tests using server-shaped fixtures.
- Polling fallback and websocket reconnect regression tests.
- Static review check that new UI code does not contain authoritative formulas.

### Dependencies

Existing `client-godot/scripts/network`, `client-godot/scripts/ui`, current gameplay shell scenes, and existing M1 test harness.

## 6. Phase 2 - First-Run Onboarding and Launcher Handoff

**Goal:** Move a new player from launch to an authenticated gameplay shell without manual API work.

### Screens

1. Launcher handoff/loading screen.
2. Login screen.
3. Registration screen.
4. Session restore screen.
5. First-run welcome and global-chain introduction.
6. Account/session error recovery screen.
7. Transition into the starter operation screen.

### Contracts

- `POST /api/v1/auth/register`.
- `POST /api/v1/auth/login`.
- `POST /api/v1/auth/refresh`.
- `POST /api/v1/auth/logout`.
- `GET /api/v1/player/bootstrap`.
- Launcher-provided client version/channel/start context.

### UX Requirements

- Explain that the player joins one shared fictional network.
- Explain that the server calculates progression and outcomes.
- Never expose access or refresh tokens in visible UI or logs.
- Make invalid credentials, expired sessions, offline API, and maintenance states actionable.
- Preserve the intended destination after a successful session restore.

### Acceptance Criteria

- A new local player can register and reach the starter screen.
- An existing player can log in and restore the correct player profile.
- Refresh and logout clear or replace runtime session state correctly.
- Missing or invalid launcher context produces a useful recovery path.
- The player never needs to paste API URLs or manually copy identifiers.

### Tests

- Register, login, refresh, logout integration coverage.
- Session expiry and retry behavior.
- First-run routing tests.
- Invalid credentials and API-unavailable UI tests.
- Launcher handoff compatibility tests.

## 7. Phase 3 - Starter Machine Screen and Persistent Global HUD

**Goal:** Make the central fantasy playable and visible in the first session.

### Screen Layout

**Primary operation screen**

- Machine visualization: name, tier, status, and a non-authoritative visual state.
- Effective hashrate and base hashrate from the server profile.
- Power consumed versus capacity.
- Heat generated, cooling capacity, and cooling efficiency.
- Current operation state: stopped, starting, running, stopping, rejected, or stale.
- Start and stop intent controls.
- Recent reward summary and empty state.

**Persistent global HUD**

- Active block number.
- Required work.
- Accumulated work.
- Server-provided progress ratio.
- Recent finalizations.
- Network connection and reconnect state.

### Contracts

- `GET /api/v1/players/profile?player_id=<id>`.
- `GET /api/v1/blockchain/status`.
- `GET /api/v1/blockchain/network-snapshot`.
- `/api/v1/blockchain/network-events/ws`.
- `GET/PUT /api/v1/blockchain/checkpoints/<channel>`.
- `GET /api/v1/blockchain/players/<player_id>/rewards`.
- `POST /api/v1/blockchain/operations/intents/start`.
- `POST /api/v1/blockchain/operations/intents/stop`.

Transport rule: snapshot first, websocket as the primary live path, polling as fallback, and authoritative refresh after every accepted write.

### Acceptance Criteria

- The player sees the machine and global block state without opening the API docs.
- Machine values are rendered directly from the server profile.
- Operation controls send intents only; they do not mutate local progression.
- Reconnect resumes from the latest acknowledged cursor.
- The global HUD remains visible while moving between starter-screen panels.
- Empty rewards and pre-finalization states are clear rather than errors.

### Tests

- Profile and status contract fixtures.
- Scene rendering for machine, power, cooling, and block values.
- Start/stop intent request-shape tests.
- Snapshot-to-stream continuity and duplicate-event tests.
- Connection-loss, stale-data, and retry tests.
- End-to-end local flow: register, bootstrap, start, refresh, stop.

## 8. Phase 4 - Early Economy UX

**Goal:** Turn the starter machine into a small optimization game without moving calculations into the client.

### Screens

1. Hardware and facility overview.
2. Hardware detail and comparison view.
3. Power constraint panel.
4. Cooling and heat panel.
5. Upgrade tree and progress detail.
6. NPC market catalog.
7. Purchase confirmation and receipt state.
8. Offline catch-up summary.

### Server-Owned Fields to Render

- Hardware ID, name, tier, and base hashrate.
- Effective hashrate.
- Power available, consumed, and capacity.
- Power throttle multiplier.
- Heat generated, cooling capacity, and cooling efficiency.
- Player tier, inventory, upgrade availability, prices, stock, and unlock conditions.
- Offline work earned, cap, cap-applied flag, and server message.

The client may compare two server-returned values for presentation, such as showing that one machine has a higher displayed hashrate. It must not reproduce the formula that produced those values.

### Commands and Queries

- Player profile and progression read models.
- Versioned hardware and facility content definitions.
- Upgrade start/status/completion commands.
- NPC market catalog query.
- Idempotent purchase command.
- Authoritative post-command profile, balance, and inventory refresh.

Exact endpoint names must be confirmed against the current server OpenAPI contract before implementation tickets are cut.

### Acceptance Criteria

- Power and cooling appear as meaningful constraints, not decorative numbers.
- Upgrade and purchase buttons show pending, accepted, rejected, and stale states.
- Insufficient balance, unavailable stock, locked tier, and conflict errors are understandable.
- Offline progression is described using the server's result and cap message.
- Reconnect or refresh never loses an accepted upgrade or purchase.
- No balance or effective-hashrate formula exists in client code.

### Tests

- Profile field and content-pack contract tests.
- Purchase success, insufficient balance, out-of-stock, duplicate submission, and stale-price tests.
- Upgrade progress, reconnect, and completion-refresh tests.
- Offline-cap message and empty-inventory tests.
- Authority-boundary tests for power, cooling, and effective hashrate.

## 9. Phase 5 - Chain Explorer, Player History, and Events

**Goal:** Make the permanent shared-world history understandable and inspectable.

### Screens

- Chain explorer list with pagination and filters.
- Finalized block detail.
- Player contribution history.
- Expanded reward timeline.
- Network event feed.
- Milestone and special-event banners.
- Empty, unavailable, and historical-data states.

### Contracts

- Finalized block history and block detail read models.
- Player contribution and reward history.
- Network event snapshots and live event stream.
- Cursor-based pagination and reconnect state.

### Acceptance Criteria

- The explorer shows one canonical chain, never competing active heads.
- Historical views are read-only and cannot mutate ledger or block state.
- Refresh and reconnect do not duplicate history entries.
- Live events and permanent history are visually distinct.
- Large values remain precise in display formatting.

### Tests

- Pagination and cursor tests.
- Snapshot-to-live continuity tests.
- Empty and partial-history rendering tests.
- Duplicate and out-of-order event tests.
- Large numeric formatting tests.

## 10. Phase 6 - Pools, Social, Leaderboards, and Notifications

**Goal:** Make the player feel part of a global machine while preserving the one-chain model.

### Screens

- Pool discovery and browse.
- Pool creation and join/leave flows.
- Pool detail and contribution summary.
- Leaderboard entry points and player rank.
- Player profile and history summary.
- Notifications center.
- Social activity and network announcements.

### Contracts

- Pool list, detail, membership, and contribution read models.
- Pool create/join/leave commands with server validation.
- Leaderboard read models.
- Notification inbox, read state, and reconnect stream.
- Moderation-safe profile and announcement payloads.

### Acceptance Criteria

- Pool actions are explicit server commands with clear permission errors.
- Pool rewards and contribution summaries are rendered from server projections.
- Leaderboards identify the global chain context and do not imply separate chains.
- Notifications resume safely after reconnect and do not duplicate.
- Social surfaces expose only fields allowed by privacy and moderation policy.

### Tests

- Pool membership and permission tests.
- Leaderboard consistency and empty-state tests.
- Notification reconnect, deduplication, and read-state tests.
- Moderation and blocked-content rendering tests.
- Server-authority tests for pool contribution and reward fields.

## 11. Phase 7 - Accessibility, Settings, Support, and Recovery

**Goal:** Make every shipped screen usable, recoverable, and supportable before beta hardening.

### Screens and Shared Features

- Settings screen.
- UI scale and text-size controls.
- High-contrast and color-vision-safe palettes aligned with launcher semantics.
- Reduce-motion setting.
- Keyboard navigation and focus states.
- Audio and notification preferences.
- Connection diagnostics.
- Maintenance and degraded-mode banners.
- Help, FAQ, and support entry points.

### Contracts

- Local-only settings policy or a versioned player-settings endpoint.
- Maintenance/status endpoint.
- Launcher-to-client shared accessibility settings contract.
- Support and documentation links.

### Acceptance Criteria

- All primary flows work with keyboard navigation.
- Text and controls remain legible at supported UI scales.
- Reduced motion disables non-essential animation.
- Error, loading, empty, stale, unauthorized, and maintenance states are consistent.
- A player can recover from API failure, websocket failure, expired session, and interrupted command.
- Client settings do not override server-authoritative gameplay values.

### Tests

- Focus order and keyboard navigation checks.
- Palette, text scale, and reduced-motion tests.
- Connection-loss and retry tests for every primary screen.
- Maintenance-mode and version-mismatch tests.
- Contrast and readable-layout review at supported window sizes.

## 12. Phase 8 - Telemetry, Hardening, and Release Readiness

**Goal:** Close cross-screen gaps and make the client measurable and releasable.

### Instrumentation

Instrument transitions and failures, not private content or secrets:

- Launcher handoff completed.
- Registration/login success and failure category.
- First machine viewed.
- First operation intent accepted/rejected.
- First upgrade or market action accepted/rejected.
- First history/explorer view.
- Pool join/create attempt.
- Reconnect success/failure and stale-data duration.
- Accessibility settings used.

### Release Criteria

- All screen contracts have schema/version expectations.
- All writes have pending, success, rejection, and retry behavior.
- All realtime screens define snapshot, websocket, and polling behavior.
- End-to-end happy path passes from launcher handoff through first operation.
- No client-authoritative formulas or balance mutations are present.
- Godot smoke tests, integration tests, contract tests, and release build checks pass.
- Supported API/client compatibility is documented.

## 13. Cross-Cutting Contract Matrix

| Surface | Read contract | Write contract | Live/update path | Fallback | Authoritative values |
|---|---|---|---|---|---|
| Auth and session | Register/login/refresh responses | Register, login, refresh, logout | None | Retry or session recovery | Identity and session validity |
| Starter machine | Player profile/bootstrap | None | Profile refresh after accepted commands | Poll/profile reload | Hardware, power, heat, cooling, effective hashrate |
| Global HUD | Blockchain status and snapshot | None | Aggregated websocket events | Status polling | Active block, work, progress, finalizations |
| Operation controls | Operation state where available | Start/stop intents | Operation response and refresh | Retry with idempotency policy | Accepted operation and player binding |
| Rewards | Player reward history/balances | Claim or settlement commands when added | Reward events | Refresh history | Reward amounts and contribution hashes |
| Market | Catalog and inventory | Purchase command | Economy event or refresh | Reload catalog/profile | Prices, stock, balance, receipt |
| Upgrades | Profile/progression | Upgrade command | Progress event or refresh | Reload profile | Unlock, cost, duration, completion |
| Explorer | Block/history read models | None | Event stream for new history | Cursor pagination | Canonical chain history |
| Pools/social | Pool, profile, leaderboard read models | Membership/social commands | Notifications/events | Refresh and reconnect | Membership, rank, contribution, permissions |
| Settings | Local settings or settings read model | Settings update if server-backed | Optional settings event | Local defaults | Only settings, never gameplay outcomes |

Every new surface must add a row to this matrix before implementation begins.

## 14. Realtime and Recovery Policy

Each live surface follows this order:

1. Load an authoritative snapshot or read model.
2. Restore the last valid cursor/checkpoint.
3. Connect to the websocket stream when available.
4. Apply only newer, schema-valid server events.
5. Acknowledge the cursor after successful rendering/application.
6. Fall back to polling when the stream is unavailable.
7. Refresh authoritative read models after accepted writes.
8. Mark data stale when freshness cannot be established.

The client must not estimate missing rewards, block completion, or progression while disconnected. It may show a visual connection animation, but the data state must remain clearly stale or unknown.

## 15. Test Strategy and Quality Gates

### View-Model Tests

- Server payload maps to expected display fields.
- Missing optional fields produce safe empty states.
- Large numeric values remain displayable without precision-changing conversions.
- No mapping function writes authoritative state.

### Scene and Integration Tests

- Every phase adds scene wiring tests.
- Happy-path commands test pending, success, rejection, and retry states.
- Reconnect tests cover snapshot, cursor, duplicate, and out-of-order events.
- Auth tests cover session restore, expiration, logout, and unauthorized responses.

### Contract and Authority Tests

- Required payload keys and schema versions are validated.
- Operation payloads contain no client-supplied player identity.
- Client code does not calculate server-owned economy or chain outcomes.
- API rejection is visible and does not silently update the UI as success.

### Release Gate

A UI phase is complete only when its screen list, contract matrix rows, acceptance criteria, tests, accessibility states, and recovery behavior are all documented and passing.

## 16. Ticket Breakdown Order

The first implementation tickets should be:

1. `GMN-UI-01`: Select and consolidate the supported gameplay shell path.
2. `GMN-UI-02`: Add shared route, loading, empty, stale, error, and modal primitives.
3. `GMN-UI-03`: Build login, registration, session restore, and first-run routing.
4. `GMN-UI-04`: Build the starter machine view from the player profile contract.
5. `GMN-UI-05`: Integrate the persistent global HUD with snapshot and stream fallback.
6. `GMN-UI-06`: Wire server-authoritative start/stop controls and operation states.
7. `GMN-UI-07`: Add hardware, power, and cooling read-only panels.
8. `GMN-UI-08`: Add upgrade and NPC market flows with post-action refresh.
9. `GMN-UI-09`: Add explorer, history, rewards, and event surfaces.
10. `GMN-UI-10`: Add pools, leaderboards, notifications, and social surfaces.
11. `GMN-UI-11`: Close accessibility, settings, support, and recovery behavior.
12. `GMN-UI-12`: Add telemetry, contract drift checks, and release gate coverage.

## 17. Immediate Next Slice

Start with `GMN-UI-01` through `GMN-UI-03`.

### First Slice Deliverables

- Select one gameplay shell path and document the migration boundary.
- Create the root route and shared state/error primitives.
- Add a real login/register/session-restore screen.
- Route a successful session into the existing gameplay shell.
- Add contract fixtures for auth, bootstrap, profile, status, snapshot, rewards, and operation intents.
- Keep the current shell available behind the new route until integration tests pass.

### First Slice Exit Criteria

- A local player can launch the client, register or log in, restore a session, and reach the gameplay shell.
- The client displays server-provided player and network state.
- Reconnect and API failure states are visible and recoverable.
- Existing client smoke and integration tests remain green.
- No new authoritative gameplay logic is introduced into Godot.

## 18. References

- `docs/global-mining-network-official-specification.md`
- `docs/game-design-brief-v1.md`
- `docs/master-build-plan-v1.md`
- `docs/implementation-plan-v1.md`
- `docs/m1-client-gameplay-implementation-tickets.md`
- `docs/m1-client-gameplay-minimal-slice-plan.md`
- `client-godot/README.md`
