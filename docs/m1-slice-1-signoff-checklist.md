# M1 Slice 1 Sign-Off Checklist

Status: Active
Version: 1.0
Date: 2026-08-15

Source alignment:
- docs/m1-slice-1-simulation-kernel-tick-contract.md
- docs/implementation-plan-v1.md
- docs/master-build-plan-v1.md

## 1. Sign-Off Order (Required)
Sign-off must occur in this strict sequence:
1. Simulation kernel
2. Blockchain and difficulty
3. Economy and ledger

No downstream sign-off can be marked complete until the upstream gate is complete.

## 2. Simulation Kernel Sign-Off
Owner: Simulation Lead

Required evidence:
- Deterministic replay parity test evidence.
- Piecewise interval-splitting correctness evidence.
- Tick-processing sequence evidence showing authoritative server timestamps.
- Confirmation that client-supplied progression values are ignored or rejected.

Acceptance checks:
- One-chain assumptions remain intact.
- No per-player per-second simulation loops introduced.
- Time-based reconstruction is used for progression and replay.

## 3. Blockchain and Difficulty Sign-Off
Owner: Simulation Lead

Required evidence:
- Active block uniqueness checks pass under contention.
- Atomic finalization and next-block creation checks pass.
- Difficulty adjustment behavior remains bounded and deterministic.
- Network event and reconnect cursor contracts remain versioned and stable.

Acceptance checks:
- Exactly one active block exists at any point in time.
- Finalization cannot double-apply under concurrent processing.
- Difficulty updates follow authoritative finalized-block history only.

## 4. Economy and Ledger Sign-Off
Owner: Economy Lead

Required evidence:
- Ledger-only posting for all reward and balance mutations.
- Immutable reward entry coverage for finalized block outcomes.
- Player-level reward allocation and contribution transparency coverage.

Acceptance checks:
- No direct balance mutation path exists outside ledger posting.
- Replay and settlement produce deterministic ledger outcomes.
- Economy state can be reconstructed from ledger-style records.

## 5. Cross-Gate Completion Criteria
Before marking M1 Slice 1 sign-off complete:
1. All three gates are completed in sequence with owner approval.
2. CI baseline and optional DB-backed integration suite pass for the candidate revision.
3. Tracker entries are updated with date, approver role, and evidence links.
4. Residual risks and follow-up items are listed with owner and due date.

## 6. Sign-Off Record Template
Use the following template in execution logs or PR comments:

- Gate: Simulation kernel | Blockchain and difficulty | Economy and ledger
- Status: Approved | Rework required
- Approver role:
- Date:
- Evidence links:
- Residual risks:
- Follow-up actions:
