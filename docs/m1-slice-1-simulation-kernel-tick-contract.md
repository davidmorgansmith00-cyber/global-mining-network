# M1 Slice 1: Simulation Kernel and Tick Contract

Status: Approved for implementation planning  
Version: 1.0  
Date: 2026-08-15

---

## 1. Objective
Define the authoritative server-side simulation contract for M1 so implementation can proceed with deterministic, replay-safe, one-chain behavior.

This contract applies to:
- server simulation progression,
- block contribution aggregation,
- event emission for replay,
- anti-cheat and authority boundaries.

---

## 2. Non-Negotiable Constraints
- One logical global chain only.
- Server authority over balances, rewards, progression, and block state.
- Time-based reconstruction using state changes + timestamps + aggregation.
- No per-player per-second simulation loops.
- Fictional blockchain game simulation only.

---

## 3. Authoritative Tick Model

### 3.1 Tick Inputs (Authoritative Only)
Each tick computes from server-owned state only:
- current server timestamp,
- player operation state snapshot (machine state, modifiers, pause/throttle flags),
- prior processed timestamp per operation,
- active global block state,
- active simulation modifiers in effect during interval segments.

Client payloads can request actions but cannot provide authoritative progression values.

### 3.2 Tick Cadence
- Tick runner executes on a fixed server cadence (implementation-configured).
- Progression is computed per operation as elapsed-time intervals since last processed timestamp.
- Long offline windows are reconstructed with the same interval logic, bounded by configured caps.

### 3.3 Numeric Policy
- Use deterministic numeric representation and rounding policy defined in server code.
- Reward and contribution calculations must use the same policy in realtime and replay paths.

---

## 4. Event-to-State Reconstruction Boundaries

The simulation timeline is split into piecewise intervals whenever authoritative state changes occur.

### 4.1 Interval-Splitting Events
- operation pause/resume,
- hardware install/remove/upgrade,
- power or cooling state transitions affecting effective hashrate,
- pool join/leave,
- timed modifier start/end,
- maintenance or throttling policy transitions,
- block finalization boundary.

### 4.2 Persistence Rule
For each boundary event, persist:
- event type and schema version,
- entity identifiers,
- authoritative server timestamp,
- deterministic payload fields required for replay.

### 4.3 Reconstruction Rule
Reconstruction processes contiguous intervals using the exact modifier set active for each interval. No averaging across boundaries.

---

## 5. Tick Processing Sequence (Per Tick Window)
1. Intake pending validated commands (already authorized).
2. Apply command-side state transitions atomically with authoritative timestamps.
3. Build interval slices from last processed timestamp to current tick timestamp.
4. Compute effective hashrate per interval using authoritative constraints.
5. Aggregate interval contributions into the active block projection.
6. Evaluate finalize condition and execute atomic finalization if threshold reached.
7. Post all balance-changing outcomes via immutable ledger entries only.
8. Emit domain/network events derived from committed state changes.
9. Advance last processed timestamps and commit idempotency markers.

---

## 6. Authority and Anti-Cheat Invariants
- Client cannot directly set hashrate, contribution, reward, block progress, or balances.
- Exactly one active block is valid at a time.
- Finalization and next-block creation must be race-safe and idempotent.
- Every balance mutation must map to immutable ledger entries.
- Replay over the same event history must produce identical balances, contribution totals, and block outcomes.

---

## 7. M1 Slice 1 Acceptance Criteria

Slice is accepted only when all conditions pass:

1. Deterministic replay parity
- Given identical event history, replay reproduces identical operation progression, block contribution totals, and balances.

2. Piecewise interval correctness
- Tests prove boundary events split intervals correctly and apply correct modifiers without cross-boundary blending.

3. One-chain invariant safety
- Tests verify only one active block exists and contention cannot produce duplicate finalization or duplicate next-block creation.

4. Server-authority enforcement
- Tests and API behavior demonstrate client-supplied progression numbers are ignored or rejected.

5. Ledger-only reward posting
- All reward/balance changes in simulation and finalization are recorded through immutable ledger entries.

6. Offline reconstruction consistency
- Return-after-absence scenarios produce server-reconstructed progression consistent with interval rules and configured caps.

---

## 8. Implementation Task Breakdown (M1 Slice 1)

### 8.1 Simulation Kernel Tasks
- Implement authoritative tick clock abstraction in server shared time module.
- Implement interval slicer for operation progression windows.
- Implement deterministic contribution calculator with centralized numeric policy.
- Add idempotent last-processed timestamp updates.

### 8.2 Event Contract Tasks
- Define and register simulation boundary event types and schema versions.
- Persist required replay payload fields for each boundary event.
- Add contract validation checks for event payload completeness.

### 8.3 Validation Tasks
- Add unit tests for interval splitting and numeric determinism.
- Add integration tests for tick-to-block aggregation path.
- Add concurrency tests for finalization and next-block race safety.
- Add replay tests verifying deterministic parity.

### 8.4 Review Gate
- Architecture sign-off: simulation, blockchain, economy order and ownership boundaries.
- QA sign-off: acceptance suite covers all criteria in Section 7.

---

## 9. Out of Scope for This Slice
- Full hardware/power/cooling content balancing.
- Marketplace systems.
- Pool reward policy variants beyond required boundary events.
- Launcher, patching, and distribution flows.

These remain in later milestones per implementation sequencing.