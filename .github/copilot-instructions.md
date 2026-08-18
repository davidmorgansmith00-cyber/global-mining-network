# Copilot Instructions for Global Mining Network

**Last Updated:** 2026-08-18 (M4 Slice 1 delivered)  
**Current Phase:** M2 Constraint Systems & Economy Foundations  
**Current Slice:** M2 Slice 1 - Economy Foundations  
**Status:** READY FOR EXECUTION (M1 Complete ✅ → M2 Gate Open ✅)

---

## 🎯 CRITICAL: Always-On Non-Negotiables

These are **never negotiable**, across all phases and all tickets:

1. **Server Authoritative Only**
   - Server owns: balances, rewards, progression, block state, difficulty, finalization, settlement outcomes, effective hashrate, power state, cooling state
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

| Document | Purpose | Key Sections for M2 Slice 1 |
|---|---|---|
| **`docs/progress-tracker.md`** | CURRENT STATE: Where are we? What's done? | Section 3 ("Overall Program Status") + Section 10 ("Next Actions") |
| **`docs/m2-economy-implementation-tickets.md`** | RANKED TICKETS: What to build next? | All 8 tickets (GMN-EC-01 through GMN-EC-08) in P0/P1/P2 order |
| **`docs/m2-economy-foundations-plan.md`** | HOW TO BUILD: Scope, sequence, acceptance criteria | (To be created; reference implementation-plan-v1.md § 6 for now) |

**When you start:** Check progress-tracker.md section 3 first. If it says "M2 Slice 1", then read the tickets in m2-economy-implementation-tickets.md in order (by Priority).

---

### **Tier 2: API/Economy Contracts (Reference while coding)**

Keep these open while implementing:

| Document | Purpose | What to Find |
|---|---|---|
| **`docs/m2-economy-implementation-tickets.md`** | Economy feature contracts | Hardware formula, power/cooling models, market flow, upgrade progression |
| **`docs/m1-slice-1-simulation-kernel-tick-contract.md`** | Block and time contracts | Time-based reconstruction, piecewise intervals (foundation for M2 work) |
| **`docs/operation-intents-api-reference.md`** | Operation intent contracts | Still used in M2; upgrade start is an operation intent |

**When you need:** Economy formulas, purchase flow protocols, upgrade mechanics, time boundaries.

---

### **Tier 3: Architecture & Master Plan (Read for context and constraints)**

Consult these to understand WHY and WHAT constraints apply:

| Document | Purpose | Key Sections |
|---|---|---|
| **`docs/implementation-plan-v1.md`** | Product direction and phase breakdown | Section 1 ("Purpose and Implementation Principles"), Section 6 ("Phase M2") |
| **`docs/master-build-plan-v1.md`** | System architecture and gameplay order | Section 1 ("Program Charter and Non-Negotiables"), Section 8 ("Gameplay System Build Order") |
| **`docs/global-mining-network-official-specification.md`** | Game fiction and product constraints | Section "Authority" and "Economy Philosophy" |
| **`docs/game-design-brief-v1.md`** | Game loop fantasy and economy philosophy | Section "Constraint Systems" and "Progression Loop" |

**When you need:** Understanding WHY a constraint exists, or checking if a design is aligned with overall strategy.

---

## 🚀 QUICK REFERENCE: "I need to implement X"

Use this table to find the right documents for your question:

| You're asking... | Answer is in... | Find this section |
|---|---|---|
| "What am I building right now?" | `progress-tracker.md` | "## 3. Overall Program Status" + "## 10. Next Actions" |
| "What's the exact acceptance criteria for this ticket?" | `m2-economy-implementation-tickets.md` | The ticket's "Acceptance criteria" subsection |
| "What order should I build these 8 things?" | `m2-economy-implementation-tickets.md` | "## Delivery Order & Dependencies" |
| "How do I calculate effective hashrate?" | `m2-economy-implementation-tickets.md` | "## Ticket GMN-EC-01" |
| "What's the power throttle curve?" | `m2-economy-implementation-tickets.md` | "## Ticket GMN-EC-02" |
| "How do offline caps work?" | `m2-economy-implementation-tickets.md` | "## Ticket GMN-EC-04" |
| "What's the NPC market purchase protocol?" | `m2-economy-implementation-tickets.md` | "## Ticket GMN-EC-05" |
| "How do upgrades work?" | `m2-economy-implementation-tickets.md` | "## Ticket GMN-EC-06" |
| "Why are we using time-based simulation?" | `implementation-plan-v1.md` | "## 1. Purpose and Implementation Principles" |
| "What are the non-negotiables?" | `master-build-plan-v1.md` | "## 1) Program Charter and Non-Negotiables" |

---

## 🎬 EXECUTION WORKFLOW: The 8-Step Cycle

Every ticket gets executed via an 8-step cycle defined in `.github/agents/slice-executor.agent.md`:

1. **Slice Planning** — Pick the next highest-impact ticket from `m2-economy-implementation-tickets.md`
2. **Task Breakdown** — Split into concrete deliverables
3. **Implementation** — Write code following authority boundaries
4. **Validation** — Run full test suite; all tests must pass
5. **Fix Regressions** — Fix any failing tests
6. **Tracker Update** — Mark item as "Done" in `progress-tracker.md`
7. **Commit** — One scoped commit with ticket ID in message
8. **Push** — To main branch + immediately kickoff next ticket

---

## 📋 M4 SLICE 1 CHECKLIST (Productization & Launcher Beta)

- [x] **M4-LAUNCH-01: Windows Launcher MVP**
  - Acceptance: WPF launcher with MainWindow, ConfigManager, InstallManager, ChannelManager, GameLauncher, PatchNotesService, MaintenanceService
  - Status: ✅ Done (2026-08-18)

- [x] **M4-LAUNCH-02: Patcher/Updater System**
  - Acceptance: PatcherService (Python) + C# Updater with 1MB chunks, exponential backoff, rollback
  - Tests: 10/10 passing
  - Status: ✅ Done (2026-08-18)

- [x] **M4-LAUNCH-03: Account UX & Recovery Flows**
  - Acceptance: AccountService extended with verify_email, recovery codes (10×8-char), session management, account delete, privacy settings; DB migration 020; email templates
  - Tests: 24/24 passing
  - Status: ✅ Done (2026-08-18)

- [x] **M4-LAUNCH-04: Accessibility Baseline (Pass 1)**
  - Acceptance: AccessibilitySettings + ColorPalettes (Default/HighContrast/Deuteranopia/Protanopia WCAG AA); docs/accessibility-guide.md
  - Tests: 15/15 passing
  - Status: ✅ Done (2026-08-18)

---

## 📋 CURRENT SLICE CHECKLIST: M2 Slice 1

The tickets for M2 Slice 1 (Economy Foundations) are:

- [ ] **GMN-EC-01: Hardware Effective Hashrate Formula** (P0)
  - Acceptance: Effective hashrate calculated server-side from hardware base + power + cooling
  - Reference: `m2-economy-implementation-tickets.md` line 11
  - Status: Not Started

- [ ] **GMN-EC-02: Power Constraints and Facility Limits** (P0)
  - Acceptance: Power budget enforced, throttle curve applied, client displays state
  - Reference: `m2-economy-implementation-tickets.md` line 45
  - Status: Not Started

- [ ] **GMN-EC-03: Cooling Dynamics and Efficiency** (P0)
  - Acceptance: Heat generation, cooling efficiency, curve applied multiplicatively with power throttle
  - Reference: `m2-economy-implementation-tickets.md` line 81
  - Status: Not Started

- [ ] **GMN-EC-04: Offline Progression Caps** (P0)
  - Acceptance: Offline work capped by player state tier, transparent to player, auditable in ledger
  - Reference: `m2-economy-implementation-tickets.md` line 117
  - Status: Not Started

- [ ] **GMN-EC-05: NPC Market Purchase Flow** (P1)
  - Acceptance: Purchases atomic, stock race-safe, ledger-backed, idempotent
  - Reference: `m2-economy-implementation-tickets.md` line 149
  - Status: Not Started

- [ ] **GMN-EC-06: Starter Upgrade Loop** (P1)
  - Acceptance: Upgrades consume resources, take time, improve hashrate, visible in UI
  - Reference: `m2-economy-implementation-tickets.md` line 187
  - Status: Not Started

- [ ] **GMN-EC-07: WebSocket Aggregated Updates** (P1)
  - Acceptance: Clients receive state updates, reconnect-safe, slow clients handled, no backpressure
  - Reference: `m2-economy-implementation-tickets.md` line 221
  - Status: Not Started

- [ ] **GMN-EC-08: Progression Funnel Telemetry** (P2)
  - Acceptance: Telemetry events tracked, dashboard shows funnel, drop-off visible
  - Reference: `m2-economy-implementation-tickets.md` line 259
  - Status: Not Started

**Delivery order:** GMN-EC-01 → GMN-EC-02 → GMN-EC-03 → GMN-EC-04 → GMN-EC-05 → GMN-EC-06 → GMN-EC-07 → GMN-EC-08

**Parallelization:** GMN-EC-04 and GMN-EC-05 can start after GMN-EC-01 completes (not dependent on EC-02/03)

---

## 🔐 PHASE-SPECIFIC CONSTRAINTS: M2 Slice 1

For Economy Foundations, enforce:

1. **No Client-Side Economy Calculations**
   - Client cannot calculate effective hashrate, power state, cooling state, or throttle multipliers
   - Client displays server-returned values only
   - Reference: `m2-economy-implementation-tickets.md` "Notes for Implementation Team" section 2

2. **Effective Hashrate Formula is Server-Authoritative**
   - effective_hashrate = hardware_base × power_multiplier × cooling_multiplier
   - All three factors calculated server-side; client receives final value
   - Reference: GMN-EC-01 acceptance criteria

3. **Power and Cooling Modifiers are Multiplicative**
   - Not additive (e.g., 0.8 × 0.9 = 0.72, not 0.8 + 0.9 - 1 = 0.7)
   - Reference: GMN-EC-02 and GMN-EC-03 testing requirements

4. **Offline Caps are Policy, Not Punishment**
   - Messaging must be transparent; no "penalty" language
   - Caps are auditable in ledger with cap_applied flag
   - Reference: GMN-EC-04 acceptance criteria

5. **Market Purchases are Atomic and Race-Safe**
   - Stock depletion, balance deduction, inventory increase all happen or none happen
   - No double-sells even under concurrent requests
   - Reference: GMN-EC-05 acceptance criteria

6. **Upgrade Progression is Time-Based and Server-Owned**
   - Upgrade start is an operation intent; server determines actual start time
   - Upgrade progress is server-tracked; client sees progress from status endpoint
   - Upgrade completion is server-authoritative; hardware changes only after server confirmation
   - Reference: GMN-EC-06 acceptance criteria

---

## 🛑 Conflict Resolution

If a request or design conflicts with Tier 1 or Tier 3 documents:

1. **Stop and identify the conflict explicitly** in the task description
2. **Link to the conflicting document and section** (e.g., "`master-build-plan-v1.md` § 1 says X, but ticket asks Y")
3. **Propose an architecture-compliant alternative** that satisfies both the intent and the constraint
4. **Do NOT proceed** until the conflict is resolved

Example:
```
CONFLICT: Ticket asks client to calculate effective hashrate locally.
Constraint: `m2-economy-implementation-tickets.md` GMN-EC-01 says "All calculations server-side only."
Resolution: Client receives effective_hashrate from status endpoint, displays it directly.
```

---

## 📖 When Starting a New Phase

When `progress-tracker.md` section 3 moves to a new phase (e.g., M2 → M3):

1. **Read the phase-exit checklist** from `implementation-plan-v1.md` for the completed phase
2. **Read the phase-entry plan** for the new phase
3. **Create a new "Current Slice Checklist" section** in this file with the tickets from the phase's implementation document
4. **Update this file** to reflect phase-specific constraints in the section "## 🔐 PHASE-SPECIFIC CONSTRAINTS"

---

## 🔗 Key File References

**Execution tracking:**
- `.github/copilot-instructions.md` (this file)
- `docs/progress-tracker.md` (source of truth for what's done/next)
- `docs/m2-economy-implementation-tickets.md` (ranked task queue for M2 Slice 1)

**Contracts & Specifications:**
- `docs/m2-economy-implementation-tickets.md` (economy feature contracts)
- `docs/m1-slice-1-simulation-kernel-tick-contract.md` (time-based simulation foundation)
- `docs/operation-intents-api-reference.md` (operation intent contracts, still used in M2)

**Architecture & Direction:**
- `docs/master-build-plan-v1.md` (overall strategy and non-negotiables)
- `docs/implementation-plan-v1.md` (phases and their exit criteria)
- `docs/global-mining-network-official-specification.md` (game vision and constraints)
- `docs/game-design-brief-v1.md` (economy and progression design)

**Code execution:**
- `.github/agents/slice-executor.agent.md` (8-step execution cycle)

---

## ✅ Checklist Before Submitting a PR

Every PR should:

- [ ] Link to the ticket it solves (in PR description)
- [ ] Reference the acceptance criteria from `m2-economy-implementation-tickets.md`
- [ ] Verify no non-negotiables were violated (read "Always-On Non-Negotiables" section above)
- [ ] Include test cases for each acceptance criterion
- [ ] Update `docs/progress-tracker.md` section "## Current Slice Checklist" to mark the ticket "Done"
- [ ] Ensure commit message includes the ticket ID (e.g., "GMN-EC-01: Hardware Effective Hashrate Formula")

---

## 🚨 Escalation Path

If you encounter:

- **Economy formula conflict** → Check `m2-economy-implementation-tickets.md`, then `game-design-brief-v1.md`
- **Authority boundary violation** → Stop; refer to "## 🔐 PHASE-SPECIFIC CONSTRAINTS" section above
- **Missing contract field** → Check the ticket's "Acceptance criteria" section
- **Time-based simulation edge case** → Check `m1-slice-1-simulation-kernel-tick-contract.md`
- **Constraint conflict** → Follow "Conflict Resolution" section above
- **Next phase unclear** → Check `progress-tracker.md` section 10, then read the next phase's entry from `implementation-plan-v1.md`

---

## 📊 M1 SLICE 2 ARCHIVE (Reference Only)

**Previous phase:** M1 Simulation Core Vertical Slice - Client Gameplay Shell Integration

**Status:** ✅ Complete (6/6 tickets)
- GMN-CL-01: Session Bootstrap Wiring ✅
- GMN-CL-02: Global Chain Status HUD ✅
- GMN-CL-05: Gameplay Shell Scene Scaffold ✅
- GMN-CL-03: Snapshot + Reconnect Event Stream ✅
- GMN-CL-06: Operation Intent Session-Bound Contract ✅
- GMN-CL-04: Player Reward Timeline Panel ✅

**Archive documents:**
- `docs/m1-client-gameplay-implementation-tickets.md`
- `docs/m1-client-gameplay-minimal-slice-plan.md`
- `docs/m1-exit-review-m2-transition.md` (exit review report)

---

**Version:** 2.0 (M2 Slice 1 Active)  
**Last Reviewed:** 2026-08-18T01:31:04Z  
**Maintained By:** Program Lead  
**Status:** Active & Ready for M2 Execution
