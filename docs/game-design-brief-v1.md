# GLOBAL MINING NETWORK

## Game Design Brief v1

**Document ID:** GMN-GDB-V1  
**Status:** Collaborator Draft  
**Version:** 1.0  
**Date:** 2026-08-15  
**Audience:** Design, Engineering, Product, Art, LiveOps

---

## 1) One-Sentence Pitch
A persistent online multiplayer simulation where every player contributes to one shared fictional global blockchain, growing from a weak home computer to civilization-scale compute infrastructure.

---

## 2) Vision
Global Mining Network is a long-horizon engineering strategy game with a living shared world.

Players optimize compute, power, cooling, and infrastructure while participating in a global network race where blocks, milestones, and events become permanent world history.

Core fantasy:
- One chain
- One network
- Billions of simulated miners

---

## 3) Non-Negotiable Design Principles
1. One Global Chain: all players contribute to one logical chain.
2. Server Owns Reality: client requests and displays; server validates and calculates.
3. Time as Simulation Engine: state changes plus elapsed time drive progression.
4. Engineering Over Clicking: meaningful system tradeoffs beat repetitive actions.
5. Cooperative Competition: players compete while advancing shared global progress.
6. Persistent History: blocks, events, records, and achievements are permanent.
7. Fictional Blockchain Only: no real crypto, no real mining, no financial tokenization.

---

## 4) Core Player Experience
### Starting Fantasy
The player starts tiny and almost irrelevant:
- Very weak starter machine
- Microscopic contribution to a massive global network
- Immediate visibility of a much larger world in progress

### Session Experience
Each session should feel like:
- Solve an optimization problem
- Make 2-5 meaningful infrastructure decisions
- See measurable impact on efficiency and contribution
- React to market changes, events, and pool dynamics

### Long-Term Experience
The player evolves from:
- Room-scale hardware
- Facility-scale operations
- Datacenter and industrial infrastructure
- Planetary and off-world computation systems

---

## 5) Core Gameplay Loops
### Moment-to-Moment Loop
1. Inspect constraints (power, heat, budget, uptime).
2. Adjust operation (hardware layout, cooling, energy, automation rules).
3. Contribute simulated work to active global block.
4. Earn rewards/resources and reinvest.

### Session Loop
1. Upgrade bottlenecks.
2. Progress research and manufacturing.
3. Trade in markets.
4. Coordinate with pools.
5. Participate in events/special blocks.

### Long-Horizon Loop
1. Scale facilities.
2. Unlock strategic systems.
3. Shift from micromanagement to automation.
4. Compete for rankings while contributing to global milestones.

---

## 6) Strategic Depth (Why It Stays Interesting)
The game remains engaging through tradeoffs, not linear upgrades.

Example tradeoff dimensions:
- High hashrate vs high efficiency
- Lower heat vs higher output
- Upfront cost vs long-term operating cost
- Stability vs peak performance
- Self-manufacture vs market dependence

Target outcome: many viable strategies, no permanent single best build.

---

## 7) Progression Phases (Collaborator Scope)
1. Phase A: Starter Compute
- Learn core systems: hashrate, power, heat, efficiency.

2. Phase B: Rigs and Small Facilities
- Modular hardware and first real optimization choices.

3. Phase C: Industrial Expansion
- Warehouses, large power/cooling decisions, scaling constraints.

4. Phase D: Datacenter Operations
- Automation, manufacturing, market strategy, pool competition.

5. Phase E: Global Infrastructure Influence
- Event participation, large-scale contribution identity, governance-like decisions.

6. Phase F: Off-World and Civilization Scale
- New environments with unique constraints (moon/orbit/solar systems).

---

## 8) Social and Competitive Layer
- Pools as key social-competitive unit
- Global and pool leaderboards
- Persistent player history and world milestones
- Events that encourage collective and rival behavior

Principle: players should feel both part of a global machine and in direct competition.

---

## 9) Economy and Fairness Boundaries
- Ledger-driven economy with immutable transaction history.
- Marketplace must be authoritative and race-safe.
- Anti-exploit and anti-cheat enforced server-side.
- Monetization (if introduced later) must avoid pay-to-win.

Allowed monetization direction:
- Cosmetics
- Identity/profile customization
- Non-competitive convenience

Not allowed by default:
- Buying direct mining dominance
- Buying exclusive competitive power

---

## 10) MVP Vertical Slice (Design Intent)
The first playable milestone should prove the fantasy without architectural debt.

Include:
- Shared global active block
- Starter-to-early progression path
- Power and cooling as real constraints
- Offline progression via elapsed-time reconstruction
- One pool flow
- One market flow
- One special block or global event
- Basic chain explorer and player history

Success criteria:
- Players understand the core fantasy quickly.
- Optimization choices feel meaningful.
- Shared-world feeling is visible from first session.

---

## 11) Collaboration Expectations by Discipline
### Design
- Define progression pacing and strategic build diversity.
- Specify event cadence and pool reward behavior.

### Engineering
- Preserve authority, determinism, and scalability constraints.
- Build data-driven systems that can expand without rewrites.

### Art/UX
- Visualize scale growth clearly from room to megastructure.
- Keep global network context visible and emotionally legible.

### Product/LiveOps
- Plan long-term event calendars, milestones, and balance updates.
- Protect fairness and historical continuity.

---

## 12) Immediate Open Decisions (v1)
1. What is the target session length by player type?
2. How aggressive should offline progression caps be?
3. Which pool reward model is launch default?
4. Which 3 economy sinks are mandatory at launch?
5. What is the first major world event cadence (weekly, biweekly, seasonal)?

---

## 13) Out of Scope for This Brief
- Detailed API contracts
- Full database schema
- Complete balancing tables
- Infrastructure deployment runbooks

These are covered in the full architecture specification and follow-on technical docs.

---

## 14) Reference
Canonical source:
- Official Specification: `docs/global-mining-network-official-specification.md`
