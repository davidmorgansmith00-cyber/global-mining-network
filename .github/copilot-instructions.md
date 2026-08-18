# Copilot Instructions for Global Mining Network

**Last Updated:** 2026-08-18  
**Current Phase:** M1 Simulation Core Vertical Slice  
**Current Slice:** M1 Slice 2 - Client Gameplay Shell Integration  
**Status:** COMPLETE ✅ (GMN-CL-01 ✅ GMN-CL-02 ✅ GMN-CL-05 ✅ GMN-CL-03 ✅ GMN-CL-06 ✅ GMN-CL-04 ✅)

---

## 🎯 CRITICAL: Always-On Non-Negotiables

These are **never negotiable**, across all phases and all tickets:

1. **Server Authoritative Only**
   - Server owns: balances, rewards, progression, block state, difficulty, finalization, settlement outcomes
   - Client: presentation and input only
   - Client can never author or override authoritative values

2. **One Logical Global Chain**
   - Exactly one active block at a time
   - No duplicate heads, no parallel chains
   - All players contribute to the same shared world state

3. **Time-Based Simulation (Not Per-Second)**
   - Use piecewise interval reconstruction from state-change timestamps
   - No per-player per-second simulation jobs
   - Offline progression = same engine with caps and policy checks

4. **Fictional Simulation Only**
   - No real cryptocurrency, real wallets, real tokens, or real proof-of-work
   - Fictional blockchain game only
   - Fictional resources and fictional rewards

5. **Ledger-Style Immutable Records**
   - Economy ledger entries are write-once, never mutated
   - Balance changes flow through ledger only
   - Replay from ledger must produce identical outcomes every time

If a request conflicts with these, **stop and call out the conflict explicitly**.

---

## 📚 DOCUMENT HIERARCHY: What to Read When

### **Tier 1: Execution Roadmap (Read FIRST for current work)**

Start here for every task:

| Document | Purpose | Key Sections for M1 Slice 2 |
|---|---|---|
| **`docs/progress-tracker.md`** | CURRENT STATE: Where are we? What's done? | Section 3 ("Overall Program Status") + Section 10 ("Next Actions") |
| **`docs/m1-client-gameplay-implementation-tickets.md`** | RANKED TICKETS: What to build next? | All 6 tickets (GMN-CL-01 through GMN-CL-06) in P0/P1 order |
| **`docs/m1-client-gameplay-minimal-slice-plan.md`** | HOW TO BUILD: Scope, sequence, acceptance criteria | Section 4 ("Minimal Surface Backlog") + Section 6 ("Delivery Sequence") |

**When you start:** Check progress-tracker.md section 3 first. If it says "M1 Slice 2", then read the tickets in m1-client-gameplay-implementation-tickets.md in order (by Priority).

---

### **Tier 2: API/Blockchain Contracts (Reference while coding)**

Keep these open while implementing:

| Document | Purpose | What to Find |
|---|---|---|
| **`docs/operation-intents-api-reference.md`** | Operation start/stop endpoint contracts | Request shapes, response shapes, error cases, authority model |
| **`docs/m1-slice-1-simulation-kernel-tick-contract.md`** | Block, reward, difficulty, event stream contracts | What the server sends to the client |

**When you need:** Endpoint signatures, payload fields, error codes, response contract versions.

---

### **Tier 3: Architecture & Master Plan (Read for context and constraints)**

Consult these to understand WHY and WHAT constraints apply:

| Document | Purpose | Key Sections |
|---|---|---|
| **`docs/implementation-plan-v1.md`** | Product direction and phase breakdown | Section 1 ("Purpose and Implementation Principles"), Section 8 ("Phase-by-Phase Implementation Sequence") |
| **`docs/master-build-plan-v1.md`** | System architecture and gameplay order | Section 1 ("Program Charter and Non-Negotiables"), Section 8 ("Gameplay System Build Order") |
| **`docs/global-mining-network-official-specification.md`** | Game fiction and product constraints | Section "Authority" and "Chain Ownership" |
| **`docs/game-design-brief-v1.md`** | Game loop fantasy and economy philosophy | Section "The One-Chain Shared Experience" |

**When you need:** Understanding WHY a constraint exists, or checking if a design is aligned with overall strategy.

---

## 🚀 QUICK REFERENCE: "I need to implement X"

Use this table to find the right documents for your question:

| You're asking... | Answer is in... | Find this section |
|---|---|---|
| "What am I building right now?" | `progress-tracker.md` | "## 3. Overall Program Status" + "## 10. Next Actions" |
| "What's the exact acceptance criteria for this ticket?" | `m1-client-gameplay-implementation-tickets.md` | The ticket's "Acceptance criteria" subsection |
| "What order should I build these 6 things?" | `m1-client-gameplay-minimal-slice-plan.md` | "## 6. Delivery Sequence" |
| "What are the authority rules for the client?" | `m1-client-gameplay-minimal-slice-plan.md` | "## 3. Authority Boundaries" |
| "What does the `/api/v1/blockchain/operations/intents/start` endpoint look like?" | `operation-intents-api-reference.md` | "## Start Intent" |
| "What events does the server emit?" | `m1-slice-1-simulation-kernel-tick-contract.md` | "## Network Event Taxonomy" |
| "What's the overall game vision?" | `global-mining-network-official-specification.md` | "## 1. Executive Summary" |
| "Why are we doing time-based simulation and not per-second loops?" | `implementation-plan-v1.md` | "## 1. Purpose and Implementation Principles" |
| "What are the non-negotiables for the whole project?" | `master-build-plan-v1.md` | "## 1) Program Charter and Non-Negotiables" |

---

## 🎬 EXECUTION WORKFLOW: The 8-Step Cycle

Every ticket gets executed via an 8-step cycle defined in `.github/agents/slice-executor.agent.md`:

1. **Slice Planning** — Pick the next highest-impact ticket from `m1-client-gameplay-implementation-tickets.md`
2. **Task Breakdown** — Split into concrete deliverables
3. **Implementation** — Write code following authority boundaries
4. **Validation** — Run full test suite; all tests must pass
5. **Fix Regressions** — Fix any failing tests
6. **Tracker Update** — Mark item as "Done" in `progress-tracker.md`
7. **Commit** — One scoped commit with ticket ID in message
8. **Push** — To main branch + immediately kickoff next ticket

---

## 📋 CURRENT SLICE CHECKLIST: M1 Slice 2

The tickets for M1 Slice 2 (Client Gameplay Shell Integration) are:

- [x] **GMN-CL-01: Session Bootstrap Wiring** (P0) ✅ DONE
  - Acceptance: Client can bootstrap a session, values available to authorized requests, no client progression
  - Reference: `m1-client-gameplay-implementation-tickets.md` line 12
  - Completed: 2026-08-17T23:24:29Z

- [x] **GMN-CL-02: Global Chain Status HUD** (P0) ✅ DONE
  - Acceptance: HUD displays authoritative block number/work/progress, no local derivation
  - Reference: `m1-client-gameplay-implementation-tickets.md` line 25
  - Completed: 2026-08-18T00:28:35Z

- [x] **GMN-CL-05: Gameplay Shell Scene Scaffold** (P0) ✅ DONE
  - Acceptance: Controller orchestrates session/status/snapshot/events, contracts centralized
  - Reference: `m1-client-gameplay-implementation-tickets.md` line 65
  - Completed: 2026-08-18T00:38:48Z

- [x] **GMN-CL-03: Snapshot + Reconnect Event Stream** (P0) ✅ DONE
  - Acceptance: Reconnect resumes from saved cursor, duplicates avoided, cursor persistent
  - Reference: `m1-client-gameplay-implementation-tickets.md` line 38
  - Completed: 2026-08-18T00:57:18Z

- [x] **GMN-CL-06: Operation Intent Session-Bound Contract** (P0) ✅ DONE
  - Acceptance: Start/stop calls succeed/fail with session binding, no player_id in payload
  - Reference: `m1-client-gameplay-implementation-tickets.md` line 81
  - Completed: 2026-08-18T01:04:52Z

- [x] **GMN-CL-04: Player Reward Timeline Panel** (P1) ✅ DONE
  - Acceptance: Timeline renders server entries without mutation, empty states handled
  - Reference: `m1-client-gameplay-implementation-tickets.md` line 52
  - Completed: 2026-08-18T01:10:10Z
  - Files: `client-godot/scripts/network/gmn_player_reward_timeline_service.gd`, `client-godot/scenes/ui/gmn_player_reward_timeline_panel.gd`

**Delivery order:** GMN-CL-01 ✅ → GMN-CL-02 ✅ → GMN-CL-05 ✅ → GMN-CL-03 ✅ → GMN-CL-06 ✅ → GMN-CL-04 ✅

---

## 🔐 PHASE-SPECIFIC CONSTRAINTS: M1 Slice 2

For Client Gameplay Shell Integration, enforce:

1. **No Client Progression Mutation**
   - Client cannot set or modify `accumulated_work`, `required_work`, `difficulty`, rewards, balances
   - Client displays server-provided values only
   - Reference: `m1-client-gameplay-minimal-slice-plan.md` section 3

2. **Session Binding Required**
   - All operation intents must include `session_id` query parameter
   - Server derives `player_id` from session, client never sends it
   - Reference: `operation-intents-api-reference.md` section "Authority Model"

3. **Reconnect-Safe Event Consumption**
   - All network events must include sequence IDs
   - Client must persist reconnect cursor on disk
   - Client must resume from saved cursor after disconnect
   - Reference: `m1-client-gameplay-minimal-slice-plan.md` section 4, item 3

4. **No Speculative Balances**
   - Client must not show calculated/estimated rewards as authoritative
   - Only server-returned values are displayed
   - Reference: `m1-client-gameplay-minimal-slice-plan.md` section 4, item 5

5. **Version Contracts Must Be Stable**
   - Request/response fields must match contract exactly
   - If server adds new fields, they are read-only by client
   - If server removes fields, client must handle gracefully
   - Reference: `operation-intents-api-reference.md` section "Field Contract Summary"

---

## 🛑 Conflict Resolution

If a request or design conflicts with Tier 1 or Tier 3 documents:

1. **Stop and identify the conflict explicitly** in the task description
2. **Link to the conflicting document and section** (e.g., "`master-build-plan-v1.md` § 1 says X, but task asks Y")
3. **Propose an architecture-compliant alternative** that satisfies both the intent and the constraint
4. **Do NOT proceed** until the conflict is resolved

Example:
```
CONFLICT: Ticket asks client to calculate effective hashrate locally.
Constraint: `implementation-plan-v1.md` § 1 says "Keep the server authoritative for balances, rewards, progression, block state, settlement, and all meaningful outcomes."
Resolution: Client receives effective_hashrate from server in status endpoint instead.
```

---

## 📖 When Starting a New Phase

When `progress-tracker.md` section 3 moves to a new phase (e.g., M1 → M2, or M2 → M3):

1. **Read the phase-exit checklist** from `implementation-plan-v1.md` or `master-build-plan-v1.md` for the completed phase
2. **Read the phase-entry plan** for the new phase
3. **Create a new "Current Slice Checklist" section** in `progress-tracker.md` with the tickets from the phase's implementation document
4. **Update this file** to reflect phase-specific constraints in the section "## 🔐 PHASE-SPECIFIC CONSTRAINTS"

---

## 🔗 Key File References

**Execution tracking:**
- `.github/copilot-instructions.md` (this file)
- `docs/progress-tracker.md` (source of truth for what's done/next)
- `docs/m1-client-gameplay-implementation-tickets.md` (ranked task queue)

**Contracts & Specifications:**
- `docs/m1-slice-1-simulation-kernel-tick-contract.md` (server-to-client contracts)
- `docs/operation-intents-api-reference.md` (operation intent endpoints)
- `docs/m1-client-gameplay-minimal-slice-plan.md` (minimal scope for this slice)

**Architecture & Direction:**
- `docs/master-build-plan-v1.md` (overall strategy and non-negotiables)
- `docs/implementation-plan-v1.md` (phases and their exit criteria)
- `docs/global-mining-network-official-specification.md` (game vision and constraints)

**Code execution:**
- `.github/agents/slice-executor.agent.md` (8-step execution cycle)

---

## ✅ Checklist Before Submitting a PR

Every PR should:

- [x] Link to the ticket it solves (in PR description)
- [x] Reference the acceptance criteria from `m1-client-gameplay-implementation-tickets.md` (or current phase tickets)
- [x] Verify no non-negotiables were violated (read "Always-On Non-Negotiables" section above)
- [x] Include a test case for the acceptance criterion
- [x] Update `docs/progress-tracker.md` section "## 6. Current Slice Checklist" to mark the ticket "Done"
- [x] Ensure commit message includes the ticket ID (e.g., "GMN-CL-04: Player Reward Timeline Panel")

---

## 🚨 Escalation Path

If you encounter:

- **Architecture conflict** → Open the corresponding Tier 3 document, identify the conflict, propose compliant alternative
- **Missing API endpoint** → Check `operation-intents-api-reference.md` and `m1-slice-1-simulation-kernel-tick-contract.md`; if endpoint is missing, file a blocker and link to the spec
- **Ambiguous acceptance criteria** → Re-read the ticket in `m1-client-gameplay-implementation-tickets.md`, then the relevant section in `m1-client-gameplay-minimal-slice-plan.md`
- **Constraint conflict** → Follow "Conflict Resolution" section above
- **Next phase unclear** → Check `progress-tracker.md` section 10, then read the next phase's entry from `implementation-plan-v1.md`

---

## 📊 M1 SLICE 2 EXIT REVIEW

**Status:** ✅ COMPLETE

**All 6 tickets delivered:**
- GMN-CL-01: Session Bootstrap Wiring ✅
- GMN-CL-02: Global Chain Status HUD ✅
- GMN-CL-05: Gameplay Shell Scene Scaffold ✅
- GMN-CL-03: Snapshot + Reconnect Event Stream ✅
- GMN-CL-06: Operation Intent Session-Bound Contract ✅
- GMN-CL-04: Player Reward Timeline Panel ✅

**Test coverage:** 61 tests across all 6 tickets, all passing ✅

**Architecture validation:**
- ✅ Server authoritative throughout
- ✅ Session binding enforced on all operations
- ✅ No client progression mutations
- ✅ Reconnect-safe event handling with cursor persistence
- ✅ Reward history rendered without inferred calculations
- ✅ Empty states handled gracefully

**Next phase:** M2 Constraint Systems and Economy Foundations (locked until M1 Slice 2 proof is complete)

---

**Version:** 1.7 (M1 Slice 2 COMPLETE)  
**Last Reviewed:** 2026-08-18T01:10:10Z  
**Maintained By:** Program Lead  
**Status:** Archived for M1 Slice 2 | Ready for M2 Transition
