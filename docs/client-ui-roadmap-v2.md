# Global Mining Network — Client UI Roadmap V2

**Status:** ✅ Slices 1–7 Delivered (PR #23) — Slice 8 Pending  
**Version:** 2.1  
**Date:** 2026-08-19 (updated from 2026-08-18)  
**Supersedes:** `docs/client-ui-roadmap-v1.md` (historical context only)  
**Owner:** Gameplay and UX  
**Client:** Godot 4.x / GDScript  

---

## Core Design Principle

> **THE NETWORK IS THE HEARTBEAT OF THE SCREEN.**

This is not a survival HUD. It is not a dashboard of isolated stat boxes. It is a window into a living, persistent, globally-shared computational network — and the player is one contributor to it.

Every screen element must reinforce the central fantasy:

> *"I am one miner connected to a gigantic shared network, everyone is attacking the same block, my machine contributes to it, and I am building an operation powerful enough to become increasingly important to that network."*

---

## 1. Foundations: What V2 is Built On

### 1.1 V1 Contracts Preserved

V2 is built **on top of** V1. Do not break:

- All working server WebSocket/REST bindings.
- All authoritative data contracts: `BlockStatus`, `PlayerContribution`, `PlayerProfile`, `RewardTimeline`, `MarketListing`, `UpgradeState`, `PowerState`, `CoolingState`, `OperationIntent`.
- Existing V1 debug UI surfaces (moved behind developer toggle, not deleted).
- Existing scene structure (`UIRoot`, state controller pattern, `HUDRoot`).
- Ledger-style read models.
- Time-based simulation results arriving from server.

### 1.2 Unified UI Progression

The repository should describe a single UI system with a clear migration path:

- **V1** = the base UI foundation. It proves authoritative contracts, debug parity, and scene/data-flow stability.
- **V2** = the upgraded network-first HUD and control layer. It adds the persistent screen hierarchy, shared component library, navigation language, and player-facing presentation that sit on top of V1's contracts.
- **World UI** = the final intended premium visual standard. The world scene, HUD, modal stack, and overlays must read as one cohesive command-center experience using the same visual vocabulary, token palette, state language, iconography, and layer hierarchy.

V2 is therefore the bridge from V1 to the world UI target, establishing the upgraded control layer and screen hierarchy that the final world presentation builds on.

### 1.3 Server Authority Non-Negotiables

The client **never** calculates or authors:

| Value | Authority |
|---|---|
| Block progress / completion | Server |
| Global hashrate | Server |
| Player effective hashrate | Server |
| Difficulty | Server |
| ETA / block age | Server |
| Player reward | Server |
| Power state / throttle | Server |
| Heat / cooling multiplier | Server |
| Economy balances | Server |
| Upgrade completion time | Server |

Animate and interpolate presentation only. Never substitute client-authored values for server values.

---

## 2. UI Visual Hierarchy

The persistent screen hierarchy communicates:

```
Global Chain → Current Block → Network → Player Contribution → Mining Operation → Economy → Progression
```

At a glance the player must be able to answer:

1. What block is the world mining?
2. How close is it to completion?
3. How difficult is it?
4. How powerful is the global network?
5. How powerful am I?
6. What am I contributing?
7. What is my machine doing?
8. What can I improve or interact with next?

---

## 3. Persistent Global Network Header

The **dominant, persistent** top element of every in-game screen.

### Required Authoritative Fields

| Field | Source |
|---|---|
| Block number | `BlockStatus.block_number` |
| Difficulty | `BlockStatus.difficulty` |
| Global hashrate | `BlockStatus.global_hashrate` |
| Block progress (%) | `BlockStatus.progress` |
| Block state (active/solved/propagating) | `BlockStatus.state` |

### Visual Design Intent

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  BLOCK #18421            DIFFICULTY 8.42 TH          GLOBAL 84.7 PH/s       │
│  ████████████████████████████████░░░░░░░░░░░░  73.8%                        │
│  [block age or ETA if server provides it]    [event state if active]        │
└─────────────────────────────────────────────────────────────────────────────┘
```

- Block number: largest text on the screen.
- Progress bar: full width, visually dominant.
- Global hashrate: always visible.
- When block solves: full-screen UI event (see §6).
- Motion: interpolate progress bar presentation; never calculate progress locally.

---

## 4. Player Mining Operation Panel

A compact persistent panel showing the player's current machine and operating state.

### Required Authoritative Fields

| Field | Source |
|---|---|
| Hardware name / tier | `PlayerProfile.hardware` |
| Base hashrate | `PlayerProfile.hardware.base_hashrate` |
| Effective hashrate | `EffectiveHashrateService` |
| Power state | `PowerState.state` |
| Power consumption | `PowerState.consumption` |
| Heat | `CoolingState.heat` |
| Cooling efficiency | `CoolingState.efficiency` |
| Throttle multiplier | Server-authoritative |
| Mining / operation status | `OperationIntent.status` |
| Upgrade state | `UpgradeState` |

### Visual Intent

The panel should feel like a real operating system — not a database table. Use:

- Machine name as a header.
- Status indicator (MINING / IDLE / THROTTLED / OFFLINE / UPGRADING).
- Compact stat rows for hashrate, power, heat, cooling.
- Warning states for overheating, throttling, offline/stale, upgrade completion.

Warnings must have clear visual hierarchy (color + icon, not color alone for accessibility).

---

## 5. Player vs Network Comparison

One of the most important psychological elements: the player's scale relative to the network.

### Required Authoritative Fields

| Field | Source |
|---|---|
| Player effective hashrate | Server |
| Global network hashrate | `BlockStatus.global_hashrate` |
| Player contribution share | Server read model (mark as placeholder if unavailable) |

### Visual Intent

```
YOUR HASHRATE        vs        GLOBAL HASHRATE
   42 GH/s                       84.7 PH/s
   contribution share: 0.00005%  [awaiting server read model]
```

**Do not calculate contribution percentage client-side.** If the server does not yet provide an authoritative contribution value, architect the component and mark it visually as "Awaiting network sync" or equivalent placeholder.

As the player's operation grows, this comparison communicates increasing importance without any additional UI work.

---

## 6. Block Completion Event

When a block is solved, it must feel like a meaningful shared event:

1. Progress bar reaches completion / solved state arrives via server.
2. Block solved visual state (flash, sound, distinct visual treatment).
3. Reward / result notification for participating players.
4. Chain advances animation.
5. Next block appears: new number, new difficulty, new state.

All state comes from server. Client presents only. Animate the transition; do not hold state locally.

---

## 7. GMN Navigation Language

Replace generic game navigation with GMN-specific systems.

### Primary Navigation

```
MINE | HARDWARE | POWER | STORAGE | MARKET | RESEARCH | NETWORK
```

| Section | Initial State | Unlock |
|---|---|---|
| MINE | Enabled | Default |
| HARDWARE | Enabled | Default |
| POWER | Enabled | Default |
| STORAGE | Enabled | Default |
| MARKET | Enabled | Default |
| RESEARCH | Locked | Progression gate |
| NETWORK | Enabled | Default (read-only initially) |

Locked sections may be visible with a lock indicator if useful for progression communication. Do not stub in sections with no backend contract.

### NETWORK Section Surfaces

When built out, the NETWORK section leads to:

- Block explorer
- Chain history
- Global network statistics
- Player history / reward history
- Leaderboards
- Pools
- Global events

Use existing read models (`/api/v1/blockchain/explorer`, `/api/v1/blockchain/history`, etc.) wherever contracts exist.

---

## 8. Economy and Resources

Balance / credits and key resources remain persistently visible — but do not compete with the global block.

### Persistent Resource Strip

Position below the Global Block Header:

```
CREDITS: 4,821 Ƀ    [Resource A]    [Resource B]
```

### Economic Events

Use the notification layer for:

- Block reward received.
- Purchase completed.
- Upgrade started / completed.
- Market events.
- Important economy state changes.

Avoid flooding the screen. Prioritize: critical > operational > informational.

---

## 9. Progressive UI Revelation

The interface grows with the player. Do not expose all systems at full complexity immediately.

### Early Game Emphasis

- YOUR MACHINE
- CURRENT BLOCK
- HASHRATE
- POWER
- FIRST UPGRADE

### Mid Game Additions

- COOLING / HEAT management
- MARKET interactions
- UPGRADE tree
- NETWORK statistics (read)

### Late Game Additions

- RESEARCH
- POOLS
- LEADERBOARD position
- GLOBAL EVENTS
- Full NETWORK explorer

The UI should feel like the player's command center itself becomes more sophisticated over time.

---

## 10. Screen Inventory

| Screen | Status | Notes |
|---|---|---|
| Main Menu | Required | GMN identity, no isolated save-game feel |
| In-Game HUD | Required | Network-first hierarchy |
| Pause Menu | Required | Clean, minimal |
| Settings | Required | Video / Audio / Input / Gameplay tabs |
| MINE surface | Required | Operation detail + action |
| HARDWARE surface | Required | Hardware browser + upgrade |
| POWER surface | Required | Power budget + facility |
| STORAGE surface | Required | Inventory |
| MARKET surface | Required | NPC market purchase flow |
| NETWORK surface | Phase 2 | Block explorer, statistics, history |
| RESEARCH surface | Phase 3 | Progression gate |
| Debug Layer | Always present | Behind developer toggle |

---

## 11. Scene Architecture

> **Note on `UIStateController`:** This component is shown in the scene tree below as the planned V2 state management layer. It is **not yet implemented** in the codebase. Current client code binds authoritative state through `GameplayShellController` (see `docs/world-scene-v1-asset-pack-and-implementation-plan.md §15.1 OQ-01`). Any new scene component — including world scene controllers — must bind to `GameplayShellController.latest_profile_payload` and `get_ui_state()` until `UIStateController` is introduced. Mark `UIStateController` as `[planned — not yet implemented]` in any scene annotation you add.

```
scenes/
  ui/
    UIRoot.tscn
    theme/
      UITheme.tres
      ui_tokens.gd
    hud/
      HUDRoot.tscn
      GlobalBlockHeader.tscn      ← dominant persistent element
      PlayerOperationPanel.tscn   ← machine operating state
      PlayerVsNetworkPanel.tscn   ← contribution comparison
      ResourceStrip.tscn          ← credits + resources
      NotificationFeed.tscn       ← economic/operational events
      GMNNavBar.tscn              ← MINE|HARDWARE|POWER|STORAGE|MARKET|...
    surfaces/
      MineSurface.tscn
      HardwareSurface.tscn
      PowerSurface.tscn
      StorageSurface.tscn
      MarketSurface.tscn
      NetworkSurface.tscn
    menus/
      MainMenu.tscn
      PauseMenu.tscn
      SettingsMenu.tscn
      CreditsScreen.tscn
      ConfirmDialog.tscn
    widgets/
      GMNButton.tscn
      GMNPanel.tscn
      GMNStatChip.tscn
      GMNProgressBar.tscn
      GMNTooltip.tscn
      GMNStatusBadge.tscn
      GMNTabBar.tscn
    debug/
      DebugLayer.tscn             ← V1 surfaces behind toggle
```

---

## 12. Visual Identity

### Palette (Starting Point)

| Token | Value | Usage |
|---|---|---|
| `bg_base` | `#0B0F14` | Screen background |
| `bg_panel` | `#131A22` | Standard panel |
| `bg_panel_alt` | `#1A2430` | Elevated panel |
| `line_subtle` | `#2A3A4A` | Grid lines, separators |
| `text_primary` | `#E8F0F7` | Headings, values |
| `text_secondary` | `#A9BACB` | Labels, secondary |
| `accent_primary` | `#4CC9F0` | Active state, network motif |
| `accent_success` | `#56D364` | Healthy, online, reward |
| `accent_warning` | `#F2C14E` | Throttle, heat warning |
| `accent_danger` | `#FF6B6B` | Overheat, offline, error |
| `accent_network` | `#6E40C9` | Network-specific highlights |

### Typography Scale

| Role | Size |
|---|---|
| Block number (hero) | 48 |
| H1 | 36 |
| H2 | 26 |
| H3 | 20 |
| Body | 16 |
| Small | 13 |
| Micro | 11 |

### Motion

- Restrained: meaningful animation only, not decorative.
- Panel enter/exit: 120–200ms ease-out.
- Block progress bar: smooth interpolation, never jumps.
- Block solved: intentional single-use visual event (≤600ms).
- Number changes: optional subtle value-change flash (80ms).

### Identity Direction

The UI should feel like:
- Global infrastructure
- Distributed computing
- Industrial technology at scale
- Network telemetry
- Something that actually matters

It should **not** feel like a crypto trading site, generic sci-fi greeble, mobile idle game, or survival HUD.

**The world scene background layer carries the same design language as the HUD and overlays.** Where the world scene and HUD share visual elements (state colours, icon vocabulary, badge states, in-world label typography, overlay framing), they use the same design tokens from §12 and `docs/ui-v2-plan.md §11`. Even the starter property environment must feel like part of the same premium network system. The V1 pixel-art constraint in the world scene doc is a production-velocity decision for iteration speed, while the shared visual language remains the long-term standard. The final world UI look-and-feel is the target standard for the whole screen, and V2 is the control-layer bridge that gets the repository there without changing server-authoritative gameplay logic.

---

## 13. Implementation Order (Vertical Slices)

Work vertically. Each slice is shippable.

> **Delivery status (as of PR #23, merged 2026-08-19):**
> Slices 1–7 are ✅ complete. Slice 8 is the remaining pass before the world UI build begins.

| Slice | Status |
|---|---|
| Slice 1 — Foundation + Global Block Header | ✅ Done (PR #23) |
| Slice 2 — Player Operation Panel | ✅ Done (PR #23) |
| Slice 3 — Resources, Notifications, Economy Events | ✅ Done (PR #23) |
| Slice 4 — GMN Navigation | ✅ Done (PR #23) |
| Slice 5 — Incremental Read-Model Surface Integration | ✅ Done (PR #23) |
| Slice 6 — Main Menu, Pause, Settings | ✅ Done (PR #23) |
| Slice 7 — Debug Layer Migration | ✅ Done (PR #23) |
| Slice 8 — Visual Hierarchy and Responsive Pass | ⏳ Pending (world UI phase) |

### Slice 1 — Foundation + Global Block Header ✅
1. Freeze / document all V1 server data bindings in use.
2. Create `UIRoot.tscn` with `BackgroundLayer`, `HUDLayer`, `ModalLayer`, `NotificationLayer`, `DebugLayer` nodes in that order. Migrate or stub `client-godot/scenes/gameplay_shell.tscn` so existing V1 tests pass against the new root. This unblocks world scene integration (world scene `WorldRoot` parented under `BackgroundLayer`).
3. Establish V2 `UITheme.tres`, `ui_tokens.gd`. Add `debug_toggle` input action to `client-godot/project.godot` if not yet present (prerequisite for `DebugLayer` toggle — see `docs/world-scene-v1-asset-pack-and-implementation-plan.md §15.2 OQ-02`).
4. Stub `UIStateController` as a placeholder autoload node (no logic yet); annotate it `[planned — not yet implemented]`. Current bindings remain on `GameplayShellController`.
5. Build `GlobalBlockHeader.tscn` — block number, difficulty, global hashrate, progress bar.
6. Wire to existing `BlockStatus` WebSocket feed.
7. Verify: block number and progress bar update live from server.

### Slice 2 — Player Operation Panel ✅
1. Build `PlayerOperationPanel.tscn` — hardware, tier, hashrate, power, heat, cooling, throttle, status, upgrade state.
2. Wire to existing player profile and machine state endpoints.
3. Build `PlayerVsNetworkPanel.tscn` with placeholder for contribution share.
4. Verify: panel reflects authoritative server values, warnings appear correctly.

### Slice 3 — Resources, Notifications, Economy Events ✅
1. Build `ResourceStrip.tscn` — credits + key resources.
2. Build `NotificationFeed.tscn` with priority queuing.
3. Wire block reward, purchase, upgrade, and market events.
4. Verify: rewards appear in notification feed after block solve.

### Slice 4 — GMN Navigation ✅
1. Build `GMNNavBar.tscn` with `MINE | HARDWARE | POWER | STORAGE | MARKET | RESEARCH | NETWORK`.
2. Implement surface switching with locked-state display for unbuilt sections.
3. Apply focus/keyboard/controller navigation rules.

### Slice 5 — Incremental Read-Model Surface Integration ✅
1. Wire `MarketSurface.tscn` to NPC market purchase flow (GMN-EC-05 contracts).
2. Wire `HardwareSurface.tscn` to upgrade loop (GMN-EC-06 contracts).
3. Wire `PowerSurface.tscn` to power/cooling state.
4. Wire `NetworkSurface.tscn` to block explorer and history read models.

### Slice 6 — Main Menu, Pause, Settings ✅
1. Build `MainMenu.tscn` with GMN network identity (not isolated save-game feel).
2. Build `PauseMenu.tscn`, `SettingsMenu.tscn` using shared component library.
3. Verify full screen state machine: boot → menu → game → pause → menu.

### Slice 7 — Debug Layer Migration ✅
1. Move all V1 debug surfaces under `DebugLayer.tscn`.
2. Confirm developer toggle works; V1 and V2 values comparable during dev.
3. Verify player-facing screens contain no debug artifacts.

### Slice 8 — Visual Hierarchy and Responsive Pass
1. Apply final token pass across all surfaces so HUD, overlays, and world scene read as one world UI system.
2. Verify at 1080p, 1440p, and UI scale options.
3. Accessibility pass: focus graph, WCAG AA contrast, font scale.

---

## 14. Definition of Success

V2 is complete when:

1. Somebody unfamiliar with the code looks at the screen for five seconds and understands:  
   **"I am one miner in a massive shared network, everyone is attacking the same block, my machine contributes, and I am building toward something bigger."**

2. The global block is the dominant, alive element of the screen.

3. The player's machine state is immediately legible (online, throttled, upgrading, etc.).

4. Block solves feel like shared events.

5. The GMN navigation language is present and consistent.

6. V1 data integrations remain intact (no telemetry regression).

7. No client-authoritative calculations have been introduced.

8. Debug surfaces are hidden by default and accessible to developers.

---

## 15. Cross-References

- `docs/client-ui-roadmap-v1.md` — Historical context (V1 data-flow proof phase)
- `docs/ui-v2-plan.md` — Detailed layout spec and component design
- `docs/m2-economy-implementation-tickets.md` — Economy contracts (EC-01–EC-06) used in V2 panels
- `docs/m1-slice-1-simulation-kernel-tick-contract.md` — Time-based simulation: use server timestamps
- `docs/operation-intents-api-reference.md` — Operation intent contracts for upgrade/action surfaces
- `docs/global-mining-network-official-specification.md` — Canonical game spec
- `docs/game-design-brief-v1.md` — Economy and progression philosophy
- `docs/progress-tracker.md` — Execution state
