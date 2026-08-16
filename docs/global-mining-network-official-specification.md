# GLOBAL MINING NETWORK

## Official Game Design and Technical Architecture Specification

**Document ID:** GMN-ARCH-SPEC-001  
**Status:** Official Draft  
**Version:** 1.0  
**Date:** 2026-08-15  
**Owner:** Global Mining Network Team

---

## Purpose
Build a complete persistent online multiplayer mining game centered around a simulated global blockchain.

This document defines the intended finished system from first login through extreme endgame progression.

This specification is not a temporary prototype brief. Early systems must be designed so they do not require fundamental rewrites as the game scales.

Implementation may be delivered in milestones, but all milestones must conform to this architecture.

---

## 1. Core Idea
Every player joins the same simulated mining network.

There is one canonical global blockchain.

Players build increasingly powerful virtual mining operations and contribute simulated computational work toward mining blocks on that shared chain.

Progression path:
- Personal Computer
- Custom Mining Rig
- GPU Farm
- ASIC Farm
- Warehouse
- Datacenter
- Industrial Compute Complex
- Power Plant
- National Compute Infrastructure
- Quantum Computing
- Lunar Datacenter
- Orbital Compute Network
- Planetary Compute Network
- Solar Compute Infrastructure
- Late-game technologies

The player operation grows from a tiny machine into civilization-scale infrastructure while all other players contribute to the same global chain.

Central fantasy:

**One chain. One network. Billions of miners.**

This is not real cryptocurrency mining.
- No real proof-of-work
- No real hardware mining
- No cryptocurrency token

The blockchain is a simulated gameplay system.

---

## 2. Technology Stack
### 2.1 Client
- Godot 4.x
- GDScript initially

Godot responsibilities:
- UI
- World visualization
- Rig visualization
- Building visualization
- Animations
- Audio
- Player interaction
- Network visualization
- Inventory interface
- Research interface
- Marketplace interface
- Chain explorer
- Social systems
- Settings

Godot is not authoritative.

Never trust client-side calculations.

### 2.2 Backend
- Python 3.12+
- FastAPI

Backend responsibilities:
- Game simulation
- Mining calculations
- Economy
- Blockchain simulation
- Rewards
- Progression
- Hardware calculations
- Research
- Marketplace
- Events
- Pools
- Achievements
- Anti-cheat
- Analytics
- Administrative systems

Use async architecture where appropriate.

### 2.3 Database
- PostgreSQL

Canonical persistent state includes:
- Players
- Hardware
- Inventory
- Transactions
- Blocks
- Research
- Buildings
- Marketplace orders
- Pools
- Achievements
- Historical statistics

### 2.4 Realtime Layer
- Redis

Redis usage:
- Cached global state
- Leaderboards
- Distributed locks
- Session information
- Rate limiting
- Pub/sub
- Frequently accessed values
- Temporary event state

### 2.5 Networking
- REST APIs for non-continuous actions
- WebSockets for live updates

WebSocket examples:
- Global block progression
- Network hashrate
- Events
- Marketplace activity
- Pool updates
- Notifications

Do not require clients to send per-second requests.

### 2.6 Infrastructure
- Docker
- Docker Compose for local development

Long-term deployment direction:
- Cloudflare
- Load Balancer
- API Servers
- Game Services
- Redis Cluster
- PostgreSQL
- Workers/Event Processing

Local development must not require full distributed infrastructure.

---

## 3. Server-Authoritative Design
Absolute rule: **THE SERVER OWNS REALITY.**

Client may request actions such as:
- Purchase item
- Install component
- Start research
- Sell item
- Join pool
- Construct building
- Claim reward

Client must never determine:
- Player balance
- Hashrate
- Mining contribution
- Reward amount
- Drop result
- Upgrade cost
- Research completion
- Marketplace settlement
- Block completion
- XP
- Player level

Server validates every meaningful action.

---

## 4. Time-Based Simulation
The architecture must support enormous populations.

Never require one update per player per second.

Core rule:

`state + elapsed time = current state`

Example:
- Player hashrate: `1000 H/s`
- Last state change: `12:00:00`
- Current time: `12:10:00`
- Elapsed: `600 s`
- Work: `1000 x 600 = 600,000 simulated hashes`

Server reconstructs contribution mathematically.

Use event-driven state transitions rather than continuous per-player simulation whenever possible.

---

## 5. Global Blockchain
One canonical global chain exists.

Each block includes:
- Block number
- Block ID
- Previous block ID
- Difficulty
- Required work
- Accumulated work
- Network hashrate
- Participating miners
- Start timestamp
- Completion timestamp
- Reward pool
- Special modifiers
- Event information
- Historical statistics

The active block is globally shared.

---

## 6. Block Completion
Concept:

`Global Work = integral(Network Hashrate over Time)`

When:

`Global Work >= Required Work`

The block completes.

Block finalization must be atomic.

Only one server process may finalize a particular block.

Required protections:
- Database transactions
- Distributed locks
- Unique constraints
- Idempotency keys

Must prevent:
- Duplicate blocks
- Duplicate rewards
- Duplicate history
- Duplicate transactions
- Multiple next active blocks

---

## 7. Difficulty
Difficulty must dynamically respond to network power.

- Define target block time (example: `60 seconds`)
- If blocks are faster than target, difficulty rises
- If blocks are slower than target, difficulty falls
- Use moving window (example: last `20` blocks)
- Use bounded adjustment (example: max `+10%` / `-10%` per adjustment)

All values must be configuration-driven.

Difficulty must support astronomical numeric scale.

---

## 8. Number System
Support extremely large values robustly.

Display units:
- H/s
- KH/s
- MH/s
- GH/s
- TH/s
- PH/s
- EH/s
- ZH/s
- YH/s
- Scientific notation beyond standard ranges

Frontend formatting must not break at large magnitudes.

Backend accounting should use integer/decimal-safe representations where exactness is required.

---

## 9. Player Mining
Each player has Effective Hashrate.

Conceptual formula:

`Effective Hashrate = Raw Compute x Efficiency x Power Availability x Cooling Modifier x Research Modifier x Building Modifier x Event Modifier`

All calculations are server-side.

---

## 10. Hardware System
Hardware is modular.

Core categories:
- CPU
- GPU
- ASIC
- Quantum Processor
- Motherboard
- Memory
- Power Supply
- Cooling
- Storage
- Network Equipment
- Rack
- Transformer
- Generator
- Battery
- Industrial Cooling
- Specialized Accelerators

Future categories must be data-driven.

Do not hard-code progression in UI.

---

## 11. Hardware Attributes
Components may include:
- Hashrate
- Power consumption
- Heat generation
- Cooling capacity
- Reliability
- Efficiency
- Bandwidth requirement
- Space requirement
- Maintenance requirement
- Purchase price
- Research requirement
- Player requirement
- Technology tier
- Rarity
- Durability
- Special modifiers

---

## 12. Power System
Power is a major progression axis.

Progression examples:
- Wall outlet
- Dedicated circuits
- Industrial supply
- Substations
- Solar
- Wind
- Hydroelectric
- Natural gas
- Nuclear
- Fusion
- Orbital solar
- Advanced late-game energy technologies

Facility power model includes:
- Power production
- Power consumption
- Power capacity
- Distribution capacity
- Efficiency

Power infrastructure is an optimization system.

---

## 13. Heat and Cooling
Compute generates heat; cooling removes heat.

If:

`Heat Generation > Cooling Capacity`

Hardware throttles.

Extreme overheating can cause:
- Efficiency penalties
- Temporary shutdown
- Increased maintenance
- Hardware degradation

Players must balance:
- Compute
- Power
- Cooling
- Cost
- Space
- Efficiency

---

## 14. Reliability and Maintenance
Hardware does not run forever without tradeoffs.

Reliability states:
- Healthy
- Degraded
- Warning
- Critical
- Offline

Maintenance may consume resources.

Avoid excessive micromanagement.

Automation eventually handles routine maintenance.

---

## 15. Facility Progression
Possible facility progression:
- Bedroom
- Garage
- Basement
- Workshop
- Small Warehouse
- Mining Farm
- Industrial Warehouse
- Datacenter
- Datacenter Campus
- Compute Complex
- National Infrastructure
- Lunar Installation
- Orbital Installation
- Planetary Network
- Solar Network

Facilities define:
- Available space
- Power capacity
- Cooling capacity
- Rack capacity
- Network capacity
- Maximum hardware
- Automation capability

---

## 16. Visual World
Godot should show player growth visually.

Early visual:
- Desk and computer

Later visual:
- Multiple rigs
- Racks
- Server aisles
- Cooling equipment
- Transformers
- Warehouses
- Datacenters
- Power stations

Endgame visual:
- Lunar facilities
- Orbital structures
- Planet-scale infrastructure

Progression must be seen, not only counted.

---

## 17. Resources
Resource system must be expandable.

Potential resources:
- Compute Credits
- Copper
- Silicon
- Aluminum
- Lithium
- Gold
- Rare Earth Elements
- Uranium
- Advanced Alloys
- Superconductors
- Quantum Materials
- Exotic Matter

Not all resources exist at start.

Resources unlock by progression.

---

## 18. Resource Generation
Resource sources may include:
- Mining blocks
- Block rewards
- Events
- Production
- Recycling hardware
- Trading
- Achievements
- Exploration
- Contracts
- Research
- Special blocks

Resource definitions must be data-driven.

---

## 19. Economy
Use a ledger-based economy.

Never modify balances without recording a transaction.

Each transaction records:
- Transaction ID
- Player ID
- Resource
- Amount
- Transaction type
- Source
- Destination (if applicable)
- Related block/order/event
- Timestamp
- Balance after transaction (where applicable)

Transactions are immutable.

---

## 20. Hardware Market
Two markets:

### 20.1 NPC Market
- Game-generated equipment
- Stabilizes baseline economy

### 20.2 Player Marketplace
Players can:
- List hardware
- Purchase hardware
- Sell resources
- Purchase resources
- Cancel orders
- View price history

Use listing/order-book architecture as appropriate.

All settlements must be server-side and atomic.

Prevent:
- Duplication
- Negative balances
- Double purchases
- Race conditions
- Fake listings

---

## 21. Manufacturing
Players eventually manufacture hardware.

Manufacturing requirements:
- Blueprint
- Resources
- Facility
- Energy
- Time
- Research

Possible outputs:
- GPUs
- ASICs
- Cooling systems
- Power systems
- Racks
- Quantum components

Players choose buy vs build strategy.

---

## 22. Research Tree
Research categories:
- Compute
- Efficiency
- Cooling
- Power
- Networking
- Manufacturing
- Automation
- Materials
- Quantum
- Space
- Energy

Research unlocks:
- Hardware
- Buildings
- Efficiency modifiers
- Automation
- Resource processing
- Manufacturing recipes
- New gameplay mechanics

---

## 23. Automation
Automation is a major progression mechanic.

Early game: active decisions.

Later automation targets:
- Purchasing
- Maintenance
- Cooling
- Power balancing
- Hardware replacement
- Production
- Resource allocation
- Mining configuration

Late game should emphasize strategy over repetitive clicks.

---

## 24. Player Level
Players earn XP from meaningful activity:
- Mining contribution
- Blocks participated
- Research
- Construction
- Manufacturing
- Achievements
- Events

Player level can gate access but is not the sole progression axis.

Technology and infrastructure are primary.

---

## 25. Offline Progression
Players progress while offline.

Do not simulate per second.

Store:
- Last calculated timestamp
- Hashrate
- Relevant modifiers
- State-change history where needed

Reconstruct elapsed production when required.

Offline progression may include:
- Mining
- Manufacturing
- Research
- Construction
- Maintenance

Use configurable caps for balance.

---

## 26. Global Network Display
Global HUD/system views should include:
- Current miners
- Network hashrate
- Current block
- Difficulty
- Block progress
- Average block time
- Historical hashrate
- Major pools
- Largest contributors
- Network records

Players should always feel part of a worldwide system.

---

## 27. Mining Pools
Players can create and join pools.

Pool properties:
- Name
- Description
- Owner
- Members
- Hashrate
- Contribution
- Statistics
- Achievements
- Pool upgrades
- Pool treasury

Pools compete in rankings while contributing to the same global chain.

---

## 28. Pool Rewards
Support configurable models such as:
- Proportional
- Pay Per Share
- Performance bonuses
- Pool-defined distribution settings

Prevent pool owners from manipulating already-earned rewards.

---

## 29. Leaderboards
Potential leaderboards:
- Hashrate
- Lifetime contribution
- Current block contribution
- Efficiency
- Wealth
- Research
- Blocks participated
- Pool hashrate
- Pool contribution
- Facility size
- Manufacturing output

Use Redis sorted sets or equivalent scalable ranking structures.

---

## 30. Special Blocks
Not all blocks are identical.

Examples:
- Mega Block
- Encrypted Block
- High-Difficulty Block
- Resource-Rich Block
- Unstable Block
- Quantum Block
- Historical Milestone Block
- Community Block

Possible modifiers:
- Difficulty
- Rewards
- Hardware efficiency
- Power usage
- Resource drops
- Completion requirements

---

## 31. Global Events
Server-controlled events include examples like:
- Solar storm
- Energy crisis
- Semiconductor shortage
- Technology breakthrough
- Resource discovery
- Cooling breakthrough
- Global compute surge
- Network attack simulation
- Quantum breakthrough
- Lunar discovery

Each event defines:
- Start
- End
- Modifiers
- Description
- Requirements
- Rewards
- Historical record

---

## 32. Chain Forks
Late-game events may trigger forks.

Example choice:
- Chain A: lower difficulty, stable rewards
- Chain B: extreme difficulty, rare technology

Players vote or contribute compute toward branches.

Winning branch becomes canonical.

Losing branch remains visible historically.

Forks are gameplay events only and never real cryptocurrency behavior.

---

## 33. Chain Explorer
Provide full explorer capability:
- Blocks
- Difficulty
- Completion times
- Network hashrate
- Rewards
- Special events
- Top contributors
- Pool contributions
- Historical records
- Forks
- Milestones

The chain is the persistent history of the game civilization.

---

## 34. Player History
Maintain historical player stats:
- Join date
- First block
- Blocks participated
- Lifetime hashes
- Highest hashrate
- Hardware owned
- Resources earned
- Marketplace activity
- Research completed
- Facilities built
- Achievements
- Pool history
- Major event participation

---

## 35. Achievements
Examples:
- First Hash
- First Block
- 1 KH/s
- 1 MH/s
- 1 GH/s
- 1 TH/s
- First ASIC
- First Datacenter
- First Nuclear Plant
- First Quantum Miner
- First Lunar Facility
- One Million Blocks
- Top 1%
- Top 100
- Network milestone participation

Achievement rewards may include:
- Cosmetics
- Titles
- Small rewards
- Profile badges

---

## 36. Prestige and Endgame
Avoid reset models that erase progress without meaning.

Endgame expands scale:
- Earth
- Moon
- Orbital Infrastructure
- Solar System
- Civilization-scale compute

New environments add constraints rather than only multipliers, such as:
- Lunar cooling
- Launch logistics
- Solar energy constraints
- Communication latency
- Radiation
- Orbital construction
- Rare materials

---

## 37. Social Systems
Support:
- Friends
- Player profiles
- Pool chat
- Global event chat
- Private messages (if approved)
- Player inspection
- Achievement sharing
- Marketplace identity

Moderation must be implemented before unrestricted public communication.

---

## 38. Notifications
Persistent notifications include:
- Block completed
- Research finished
- Construction finished
- Item sold
- Purchase completed
- Hardware failure
- Achievement earned
- Pool event
- Global event
- Special block discovered

---

## 39. Anti-Cheat
Assume clients are hostile.

Never trust Godot client state.

Use:
- Rate limiting
- Server timestamps
- Action validation
- Idempotency
- Transaction locking
- Behavior analysis
- Impossible-state detection
- Audit logs

Do not rely on obscurity of client code.

---

## 40. Authentication
Support secure account models:
- Email/password
- OAuth providers
- Session tokens
- Refresh tokens

Security requirements:
- Modern password hashing
- Email verification
- Password reset
- Session revocation
- Account deletion
- Security logs

Never store plaintext passwords.

---

## 41. Administration
Provide internal admin interface.

Admin visibility:
- Players
- Blocks
- Economy
- Transactions
- Marketplace
- Pools
- Events
- Network statistics
- Suspicious accounts
- Game configuration

Admin configuration control:
- Difficulty
- Rewards
- Hardware
- Resources
- Recipes
- Research
- Events
- Buildings
- Offline limits
- XP
- Marketplace fees
- Balance parameters

Routine balancing must not require code deployment.

---

## 42. Data-Driven Content
Primary game content should be in configuration/database definitions:
- Hardware
- Buildings
- Research
- Resources
- Recipes
- Events
- Special blocks
- Achievements

Do not scatter content definitions throughout frontend logic.

This enables large-scale expansion without core rewrites.

---

## 43. Game Engine Services
Backend should be modular by domain, for example:

```text
server/
    api/
    auth/
    players/
    mining/
    blockchain/
    difficulty/
    rigs/
    hardware/
    facilities/
    power/
    cooling/
    resources/
    economy/
    marketplace/
    manufacturing/
    research/
    automation/
    pools/
    events/
    achievements/
    progression/
    social/
    notifications/
    admin/
    analytics/
    anti_cheat/
    workers/
    database/
    cache/
    websocket/
```

Avoid a monolithic `game.py` architecture.

---

## 44. Godot Client Structure
Example structure:

```text
client/
    scenes/
        login/
        mining/
        facility/
        rig/
        research/
        marketplace/
        network/
        explorer/
        pools/
        profile/
    scripts/
    ui/
    assets/
    audio/
    networking/
    models/
    animations/
```

Separate server communication from UI logic.

---

## 45. API Design
Version APIs, for example: `/api/v1/...`

Potential endpoint groups:
- `/auth`
- `/player`
- `/rig`
- `/inventory`
- `/hardware`
- `/facility`
- `/research`
- `/market`
- `/network`
- `/chain`
- `/blocks`
- `/pools`
- `/events`
- `/achievements`

Use clear schemas and auto-generate OpenAPI through FastAPI.

---

## 46. WebSocket Design
Use WebSockets for live aggregated updates.

Do not send per-hash events.

Example payload:

```json
{
  "type": "network_update",
  "block": 8291842,
  "progress": 0.7182,
  "network_hashrate": 8.281e18,
  "difficulty": 9218281
}
```

Clients may interpolate visual progress locally.

---

## 47. Background Workers
Use workers for asynchronous tasks, including:
- Block finalization
- Reward settlement
- Marketplace matching
- Event processing
- Notifications
- Analytics
- Leaderboards
- Scheduled maintenance

Do not run heavy processing synchronously in API requests.

---

## 48. Block Reward Scalability
Do not loop synchronously through millions of players on block completion.

Requirements:
- Store aggregated contribution
- Support asynchronous/batched reward settlement
- Use immutable block contribution snapshots
- Materialize player reward lazily or through workers

Design this before large-scale load testing.

---

## 49. Sharding Strategy
One logical global chain does not require one physical database machine.

Design player state for partitioning (example key: Player ID).

Global systems remain logically centralized while implementation may use distributed aggregation.

Do not expose partitioning as separate worlds unless explicitly intended.

Players should perceive one unified network.

---

## 50. Observability
Implement structured logging and metrics.

Track:
- API latency
- Error rates
- Connected clients
- Database latency
- Redis latency
- Block processing
- Worker queues
- Network hashrate
- Economy creation/destruction
- Marketplace volume
- Suspicious behavior

Ensure compatibility with Prometheus/Grafana-class tooling.

---

## 51. Testing
Required testing layers:
- Unit tests
- Integration tests
- Database tests
- Economy tests
- Mining tests
- Concurrency tests
- API tests
- Simulation tests

Critical scenarios:
- Duplicate purchases
- Double rewards
- Simultaneous block completion
- Marketplace races
- Negative balances
- Offline progression exploits
- Timestamp manipulation

---

## 52. Mass-Player Simulator
Create a Python simulation harness for virtual miners without real network clients.

Scale targets:
- 10
- 100
- 1,000
- 10,000
- 100,000
- 1,000,000+

Simulate diversity in:
- Hardware
- Hashrates
- Progression
- Online patterns
- Upgrade behavior

Use simulator for:
- Block timing
- Difficulty adjustment
- Economy behavior
- Database load
- Reward calculations
- Network aggregation

Do not spawn one OS process per simulated player.

Use mathematical aggregation where possible.

---

## 53. Economy Simulator
Create accelerated simulation tools for months/years of game time.

Track:
- Currency creation
- Currency destruction
- Hardware inflation
- Resource scarcity
- Marketplace prices
- Average progression
- Wealth concentration
- Upgrade timing
- Difficulty behavior
- Retention proxies

Use this for balance iteration without real-time waiting.

---

## 54. Starting Experience
A new player should start intentionally small.

Example starter machine:

```text
RUSTY HOME COMPUTER

Hashrate: 12 H/s
Power: 80 W
Heat: 14
Cooling: 20
Efficiency: 0.15 H/W
```

Example global context display:

```text
GLOBAL BLOCK #1,842,918

[Progress] 81.4%
Network Hashrate: 8.42 PH/s
Your Hashrate: 12 H/s
Your Contribution: 0.00000000014%
```

The tiny contribution is intentional and thematic.

---

## 55. Early Game
Early progression should be reasonably fast.

Typical upgrades:
- CPU
- Cooling
- Power supply
- GPU
- Multiple GPUs
- ASIC
- Rack
- Garage facility

Core concepts learned:
- Hashrate
- Power
- Heat
- Efficiency
- Global contribution

---

## 56. Mid Game
Player operation includes:
- Multiple racks
- Industrial cooling
- Dedicated power
- ASIC arrays
- Warehouses
- Manufacturing
- Marketplace activity
- Mining pools
- Advanced research

Optimization becomes increasingly strategic.

---

## 57. Late Game
Player controls:
- Datacenter campuses
- Power generation
- Advanced manufacturing
- Massive ASIC infrastructure
- Automation systems
- Quantum compute
- Large mining pools
- Global event participation

---

## 58. Extreme Endgame
Progression expands beyond terrestrial compute.

Endgame assets include:
- Lunar facilities
- Orbital compute arrays
- Solar collectors
- Advanced quantum systems
- Planetary networking
- Civilization-scale infrastructure

Do not fully detail distant content immediately, but ensure architecture supports future locations and tiers without fundamental rewrites.

---

## 59. Gameplay Philosophy
Avoid flat progression where only upgrade levels increase numbers.

Players should make meaningful engineering tradeoffs.

Example tradeoffs:
- ASIC A: very high hashrate, poor efficiency
- ASIC B: lower hashrate, excellent efficiency
- ASIC C: expensive, low heat
- ASIC D: high output, requires advanced cooling

No permanent universal best component.

---

## 60. Strategic Builds
Support multiple viable strategies:
- Maximum raw hashrate
- Maximum efficiency
- Low-power mining
- Low-cost hardware at massive scale
- High-reliability infrastructure
- Manufacturing empire
- Marketplace trader
- Pool-focused miner
- Advanced tech specialist

No single strategy should dominate permanently.

---

## 61. Global History
Persist major world milestones, such as:
- First player reaches 1 TH/s
- Network reaches 1 EH/s
- Block #1,000,000
- First quantum miner
- First lunar datacenter
- Largest block mined
- Major fork
- Major global event

The game should generate a permanent historical timeline.

---

## 62. Genesis Block
Production chain begins with a Genesis Block.

Genesis record includes:
- Launch timestamp
- Initial difficulty
- Initial reward
- Initial network state

Genesis block must never be deleted or regenerated after production launch.

---

## 63. Player Legacy
Early players should gain historical recognition without unfair economic permanence.

Examples:
- Genesis Miner badge
- Founding Pool marker
- Early Block achievements
- Historical profile records
- Cosmetics
- Titles

Avoid permanent pay-to-win advantage.

---

## 64. Monetization Boundary
Monetization is separate from core economy.

Do not implement real-money systems unless explicitly requested later.

If introduced, prefer:
- Cosmetics
- Facility skins
- Rig skins
- Profile customization
- Visual effects
- Optional convenience that preserves competitive integrity

Do not allow direct purchase of global mining dominance.

---

## 65. No Real Crypto
Project-wide hard rule:
- Blockchain is fictional
- Hashrate is simulated
- Blocks are simulated
- Compute Credits are game currency
- No wallet
- No token
- No real proof-of-work
- No mining of player hardware
- No blockchain financial promises

Terminology is simulation-only.

---

## 66. Initial Repository
Use a monorepo:

```text
global-mining-network/
    client/
    server/
    simulator/
    database/
    infrastructure/
    docs/
    tests/
    docker-compose.yml
    README.md
    .env.example
```

Never commit secrets.

---

## 67. Documentation
Maintain `/docs` with at minimum:

```text
architecture.md
game-design.md
mining-engine.md
blockchain-engine.md
difficulty.md
economy.md
hardware.md
power-and-cooling.md
facilities.md
research.md
marketplace.md
pools.md
events.md
security.md
scaling.md
database.md
api.md
simulation.md
deployment.md
```

Update docs whenever architecture changes.

---

## 68. Development Rule
Do not build isolated features that contradict final architecture.

Before implementing a system, define:
- Authoritative owner
- Database representation
- API boundary
- Cross-system interactions
- Concurrency requirements
- Scaling implications
- Test strategy

Then implement.

---

## 69. Critical Scalability Rule
Never design around per-second per-player updates.

Design around:

`State changes + timestamps + aggregation`

Example:
A stable `100 TH/s` rig does not need per-second pings.

Store state-change timestamps and reconstruct work mathematically.

Apply this model across mining, research, manufacturing, construction, and all time-based systems.

---

## 70. Target Scale
Architect conceptually for:
- 1 player
- 100 players
- 10,000 players
- 1,000,000 players
- 100,000,000 players
- Potentially billions of accounts

Do not prematurely deploy billion-scale infrastructure.

Ensure domain architecture does not block eventual distribution.

Scale infrastructure based on measured need.

---

## 71. First Local Development Environment
Local development runs entirely with Docker Compose.

Compose services should include:
- PostgreSQL
- Redis
- Python backend
- Worker
- Supporting services

Godot connects to local API.

Conceptual topology:

```text
Godot Client
   |
   v
localhost API
   |- PostgreSQL
   |- Redis
   '- Worker
```

Provide setup commands in README.

---

## 72. Development Seed Data
Create seed data to exercise every major system:
- Hardware
- Buildings
- Research
- Resources
- Recipes
- Events
- Achievements

Seed content must be clearly separate from production content.

---

## 73. Final Player Experience
Target end-to-end journey:
- Player creates account
- Starts in a tiny room with a weak computer
- Contributes microscopic simulated hashpower to global chain
- Earns resources and improves hardware
- Introduces GPUs, then ASICs
- Encounters power and cooling constraints
- Expands room to garage, warehouse, datacenter
- Unlocks research, manufacturing, trading, and pools
- Participates in special blocks and global events
- Helps advance ever-growing global chain
- Reaches quantum, lunar, and orbital infrastructure
- Leaves a persistent historical footprint in world history

All players always contribute to one logical global chain.

---

## 74. Core Design Statement
Every technical and gameplay decision must preserve:

- **ONE GLOBAL CHAIN**: all players on one logical network.
- **SERVER OWNS REALITY**: client requests and renders; server validates and computes.
- **TIME IS THE SIMULATION ENGINE**: reconstruct mathematically when possible.
- **ENGINEERING OVER CLICKING**: power/cooling/efficiency/infrastructure choices matter.
- **COOPERATIVE COMPETITION**: players compete while advancing one chain together.
- **THE WORLD REMEMBERS**: blocks, milestones, and events are permanent history.
- **START WITH A COMPUTER. END WITH A CIVILIZATION.**

---

## 75. Coder Agent Instruction (Implementation Gate)
Before substantial implementation code:
1. Read this full specification.
2. Define complete repository architecture.
3. Define database/domain model.
4. Map dependencies between major systems.
5. Define authoritative ownership of major state.
6. Define global mining aggregation algorithm.
7. Define block completion concurrency protection.
8. Define difficulty algorithm.
9. Define offline/time-based progression.
10. Define economy ledger model.
11. Define API and WebSocket boundaries.
12. Define worker responsibilities.
13. Define scaling boundaries.
14. Define Godot/server communication model.
15. Define testing and simulation architecture.
16. Identify architectural contradictions/risks.
17. Resolve them at design level before implementation debt forms.

Then produce an implementation plan aligned to this architecture.

Do not:
- Simplify this into a browser idle game
- Shift authority to client calculations
- Create fake per-second mining request traffic
- Implement real cryptocurrency mining
- Prematurely split everything into microservices

Start with a structured modular Python backend and extract services only when measured scale requires it.

The intended product is a persistent global multiplayer simulated blockchain game with evolving civilization-scale computation.

The architecture foundation must be capable of growing with that vision.

---

## Appendix A: Approval and Change Control
- This document is the architectural baseline.
- Material design changes should be versioned.
- Major revisions should include rationale and migration impact notes.
