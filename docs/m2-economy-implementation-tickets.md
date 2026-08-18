# M2 Economy Implementation Tickets

Status: Active  
Version: 1.0  
Date: 2026-08-18  
Phase: M2 Constraint Systems & Economy Foundations  

Source alignment:
- docs/implementation-plan-v1.md (section 6, M2 Phase)
- docs/game-design-brief-v1.md (economy and progression)
- docs/master-build-plan-v1.md (non-negotiables)

---

## Ticket GMN-EC-01: Hardware Effective Hashrate Formula

Owner: Backend Lead (Economy Domain)  
Priority: P0  
Phase: M2 Slice 1  

**Scope:**
- Implement authoritative formula for effective hashrate based on hardware base + power + cooling modifiers
- Expose hardware configuration in player GET profile endpoint
- Return effective_hashrate in operation status responses
- All calculations server-side only; client displays values received from server

**Acceptance criteria:**
1. Effective hashrate is calculated server-side from hardware base, power constraint, and cooling efficiency
2. Client receives and displays effective hashrate from API responses only (no local calculations)
3. Hardware configuration changes (via upgrade or facility modifications) trigger recalculation
4. API contract includes hardware_id, base_hashrate, power_available, cooling_efficiency, effective_hashrate fields
5. Changes to hardware base values require server restart or content pack update (no admin-only mutations)

**Testing requirements:**
- Unit test: Formula correctness with various hardware/power/cooling inputs
- Integration test: Profile endpoint returns correct effective_hashrate after hardware change
- Contract test: Payload structure matches API schema version

---

## Ticket GMN-EC-02: Power Constraints and Facility Limits

Owner: Backend Lead (Economy Domain)  
Priority: P0  
Phase: M2 Slice 1  

**Scope:**
- Implement power budget model: facility provides power capacity, hardware consumes power based on base + overclocking
- Implement throttle curve: when power exceeds capacity, apply efficiency penalty to effective hashrate
- Track power consumption state in player record
- Expose power_available, power_consumed, power_capacity in player status endpoint

**Acceptance criteria:**
1. Facility has power_capacity defined in content
2. Each hardware unit has base_power_consumption
3. Power_consumed = sum of all active hardware power consumption
4. When power_consumed > power_capacity, apply throttle curve reducing effective hashrate
5. Throttle is smooth curve, not binary on/off
6. Client displays power_consumed, power_capacity, throttle_multiplier in UI
7. Power state changes reflected in next status poll

**Testing requirements:**
- Unit test: Throttle curve calculation at various power levels
- Integration test: Adding hardware increases power_consumed; throttle applies when exceeded
- Load test: Many players consuming power simultaneously

---

## Ticket GMN-EC-03: Cooling Dynamics and Efficiency

Owner: Backend Lead (Economy Domain)  
Priority: P0  
Phase: M2 Slice 1  

**Scope:**
- Implement cooling capacity model: facility provides cooling, hardware generates heat based on base + power
- Implement efficiency curve: when heat exceeds cooling capacity, apply efficiency penalty
- Cooling upgrades increase cooling_capacity
- Track heat_generated, cooling_available, cooling_efficiency in player record

**Acceptance criteria:**
1. Each hardware unit generates heat proportional to power consumption
2. Cooling_available is provided by facility and cooling upgrades
3. When heat > cooling_capacity, apply efficiency penalty to effective hashrate
4. Efficiency penalty stacks multiplicatively with power throttle penalty
5. Client displays heat_generated, cooling_available, cooling_efficiency in UI
6. Cooling state changes reflected in next status poll
7. Heat dissipates over time (not instant) - configurable time constant

**Testing requirements:**
- Unit test: Heat generation and efficiency curves at various loads
- Integration test: Cooling upgrade changes cooling_capacity; efficiency curve applied
- Simulation: Long-term heat buildup and dissipation behavior

---

## Ticket GMN-EC-04: Offline Progression Caps

Owner: Backend Lead (Economy Domain)  
Priority: P0  
Phase: M2 Slice 1  

**Scope:**
- Implement offline cap policy: players returning after extended absence receive capped work contribution
- Cap is based on player state: starter players cap lower, upgraded players cap higher
- Cap is applied at reconnection time using time-based reconstruction
- Off-line contribution is calculated using same engine, but capped before posting to ledger

**Acceptance criteria:**
1. Offline cap is configurable per player state tier (starter, tier1, tier2, etc.)
2. When player reconnects after > cap_interval seconds offline, contribution is capped to cap_amount
3. Cap is transparent to player (they see reconstructed work in UI, but ledger entry is capped)
4. Capped work is auditable: ledger shows cap_applied flag and cap_reason
5. No penalties or punishments; cap is soft policy only
6. Client displays "your offline catch-up was capped at X work" message if applicable

**Testing requirements:**
- Integration test: Player offline 24h; reconnection applies appropriate cap for their state tier
- Replay test: Same progression engine with caps vs. without; outputs match when in-cap
- Edge case: Player offline exactly at cap_interval boundary

---

## Ticket GMN-EC-05: NPC Market Purchase Flow

Owner: Backend Lead (Economy Domain)  
Priority: P1  
Phase: M2 Slice 1  

**Scope:**
- Implement NPC market: stock of items with fixed prices, defined in content
- Implement purchase flow: client submits purchase request, server validates stock and balance, deducts both, adds to inventory
- Purchases are race-safe: stock depletion is atomic, no double-sells
- Purchases post to ledger with item_id, quantity, price, balance_before, balance_after
- Inventory changes are ledger-backed

**Acceptance criteria:**
1. NPC market items are defined in content pack (item_id, name, price, stock, resupply_interval)
2. Purchase endpoint: POST /api/v1/marketplace/npc/purchase with {item_id, quantity}
3. Server validates: player balance >= price * quantity, stock >= quantity
4. On success: balance deducted, inventory increased, ledger entry posted, stock decreased atomically
5. On failure: entire transaction rolls back; player receives clear error (out of stock vs. insufficient balance)
6. Purchases are idempotent: retrying same request (same idempotency key) does not double-purchase
7. Client displays purchase confirmation with new balance and inventory state

**Testing requirements:**
- Integration test: Purchase succeeds when conditions met; balance and inventory correct
- Race test: Multiple concurrent purchase requests; stock depletes correctly, no double-sells
- Idempotency test: Retry same purchase request; only one ledger entry created
- Edge case: Purchase exactly at last stock unit; second request fails with out-of-stock

---

## Ticket GMN-EC-06: Starter Upgrade Loop

Owner: Gameplay Lead (Content) + Backend Lead (Economy)  
Priority: P1  
Phase: M2 Slice 1  

**Scope:**
- Implement first-pass upgrade progression: starter equipment → first upgrade tier → second upgrade tier
- Upgrades consume resources (work, credits) and take time to complete
- Completed upgrades improve effective hashrate via hardware formula changes
- Upgrades are visible in UI: progress bar, estimated completion time, cost/benefit summary

**Acceptance criteria:**
1. Starter player begins with base hardware (e.g., "Starter GPU")
2. First upgrade available: "Improved GPU" costs 1000 work + 5 credits, takes 30 minutes
3. Second upgrade available: "High-End GPU" costs 5000 work + 25 credits, takes 2 hours
4. Upgrade completion is server-authoritative: client submits start request, server validates, begins upgrade job
5. Upgrade progress tracked in player state; reconnecting player sees correct progress
6. On completion: hardware_id updated, effective hashrate recalculated, ledger entry posted for resource consumption
7. Client displays upgrade tree, current progress, completion time, and impact on hashrate

**Testing requirements:**
- Integration test: Start upgrade; costs deducted; progress advances; completion updates hardware
- Time test: Offline during upgrade; reconnection resumes progress at correct point
- Replay test: Upgrade completion replay produces same hardware state

---

## Ticket GMN-EC-07: WebSocket Aggregated Updates

Owner: Backend Lead (Platform)  
Priority: P1  
Phase: M2 Slice 1  

**Scope:**
- Implement WebSocket gateway for aggregated state updates (not detailed block events, but player state changes)
- Messages include: player status (effective_hashrate, power, cooling, heat), network state (active block, block progress), balance updates
- Clients subscribe on login; reconnect resumes from sequence checkpoint
- Backpressure: slow clients do not block other clients

**Acceptance criteria:**
1. WebSocket endpoint: wss://api/v1/realtime/subscribe?session_id=X
2. Client receives aggregated updates every 5 seconds or on state change (whichever is sooner)
3. Messages include: block_number, progress_percent, effective_hashrate, power_state, cooling_state, balance, sequence_id
4. Client must ACK sequence_id to resume from that point on reconnect
5. If client disconnects and reconnects within 1 hour, server replays missed updates from checkpoint
6. If checkpoint is too old (> 1 hour), client receives full state snapshot + resume from that point
7. Slow clients (not ACKing within 30s) are disconnected gracefully; message queue does not grow unbounded

**Testing requirements:**
- Integration test: Subscribe; receive aggregated updates; ACK sequence; verify state accuracy
- Reconnect test: Disconnect and reconnect within 1 hour; replay of missed updates
- Load test: 1000 concurrent subscribers; no message loss, no backpressure on other clients
- Edge case: Client disconnects; reconnects after 2 hours; receives snapshot + normal updates

---

## Ticket GMN-EC-08: Progression Funnel Telemetry

Owner: Backend Lead (Analytics)  
Priority: P2  
Phase: M2 Slice 1  

**Scope:**
- Track player journey: login → first operation started → first upgrade started → first upgrade completed → first market purchase
- Post telemetry events for each milestone to analytics backend
- Create dashboard: funnel visualization showing drop-off at each stage
- Use data to identify early player pain points

**Acceptance criteria:**
1. Telemetry events emitted: player_login, first_operation_started, first_upgrade_started, first_upgrade_completed, first_market_purchase
2. Each event includes: player_id, timestamp, session_id, client_version
3. Events persisted to analytics data store (append-only)
4. Dashboard shows: total players at each stage, drop-off %, time between stages
5. Data is queryable by day and cohort
6. No PII beyond player_id in telemetry (no client IP, no user agent strings)

**Testing requirements:**
- Integration test: New player journey emits events in correct order
- Data quality test: No duplicate events, no missing player_ids
- Dashboard test: Funnel percentages calculate correctly

---

## Delivery Order & Dependencies

**Delivery Sequence:** GMN-EC-01 → GMN-EC-02 → GMN-EC-03 → GMN-EC-04 → GMN-EC-05 → GMN-EC-06 → GMN-EC-07 → GMN-EC-08

**Dependency Graph:**
```
GMN-EC-01 (Hardware Formula)
  ↓
GMN-EC-02 (Power Constraints) ← depends on GMN-EC-01
  ↓
GMN-EC-03 (Cooling Dynamics) ← depends on GMN-EC-02
  ↓
GMN-EC-04 (Offline Caps) ← depends on GMN-EC-01, GMN-EC-03
  ↓
GMN-EC-05 (NPC Market) ← independent
  ↓
GMN-EC-06 (Starter Upgrades) ← depends on GMN-EC-01, GMN-EC-05
  ↓
GMN-EC-07 (WebSocket Updates) ← depends on GMN-EC-01 through GMN-EC-06
  ↓
GMN-EC-08 (Telemetry) ← depends on GMN-EC-06 (first_upgrade_completed tracking)
```

**Parallelization Opportunity:**
- GMN-EC-01, GMN-EC-02, GMN-EC-03 can proceed in strict sequence (each blocks next)
- GMN-EC-04, GMN-EC-05 can start once GMN-EC-01 complete
- GMN-EC-06 can start once GMN-EC-03 and GMN-EC-05 complete
- GMN-EC-07 is final integration; must wait for GMN-EC-06
- GMN-EC-08 is telemetry; lowest priority, can overlap with GMN-EC-07

---

## Acceptance Criteria Rollup (M2 Slice 1 Exit)

All tickets must meet these criteria before M2 Slice 1 closes:

| Criterion | Evidence |
|---|---|
| Player choices around compute, power, cooling affect effective hashrate | GMN-EC-01, GMN-EC-02, GMN-EC-03 test suites pass |
| Offline catch-up respects caps and interval boundaries | GMN-EC-04 integration + replay tests pass |
| NPC market purchases are atomic and auditable | GMN-EC-05 race tests + ledger verification pass |
| Starter upgrade flow is playable end-to-end | GMN-EC-06 integration test + time test pass |
| WebSocket updates reach players with no loss on reconnect | GMN-EC-07 integration + reconnect tests pass |
| Progression funnel is visible in analytics dashboard | GMN-EC-08 dashboard test passes |
| All tests passing, no regressions | Full test suite: 100% pass rate |

---

## Notes for Implementation Team

1. **Economy Invariants:**
   - Effective hashrate = hardware_base × power_multiplier × cooling_multiplier
   - Power throttle and cooling efficiency are both multiplicative, not additive
   - Offline caps are policy, not punishment; messaging should be transparent

2. **Content Dependencies:**
   - Hardware definitions (base_hashrate, base_power, heat_generation) must be in content pack
   - Upgrade tree (costs, times, output improvements) must be in content pack
   - NPC market items and pricing must be in content pack
   - All values are server-authoritative; no client-side calculations

3. **Server Authoritative Principles:**
   - Client never calculates effective hashrate, power state, or cooling state
   - Client never applies throttle or efficiency penalties
   - Client only displays values received from server
   - All state changes (hardware, power, cooling) trigger server recalculation

4. **Testing Strategy:**
   - Each ticket includes unit, integration, and acceptance tests
   - Race and idempotency tests are mandatory for market and upgrade flow
   - Replay tests are mandatory for offline progression
   - Load tests are mandatory for WebSocket

5. **Documentation:**
   - Update API contract docs after each ticket
   - Update architecture docs after GMN-EC-04 (offline policy)
   - Update content schema docs after GMN-EC-06 (upgrade tree)
   - Update telemetry event taxonomy after GMN-EC-08
