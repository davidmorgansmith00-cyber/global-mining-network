# Global Mining Network — UI V2 Layout Design

**Status:** Ready for Implementation  
**Version:** 2.0 (GMN Network-First)  
**Date:** 2026-08-18  
**Owner:** UI / Gameplay Integration  
**Phase:** Phase 9+ (V1 finalize + V2 rollout)  
**Roadmap:** `docs/client-ui-roadmap-v2.md`

---

## 1. Mission

UI V1 proved data can flow from the server into the Godot UI. V2 upgrades that base into a player-facing, network-first HUD and control layer that communicates the actual identity of Global Mining Network.

The intended progression is:

- **V1** = base UI foundation, authoritative bindings, and debug parity.
- **V2** = upgraded HUD / network-first control layer / persistent screen hierarchy.
- **World UI** = final intended premium look and feel for the full experience, where the world scene, HUD, overlays, and menus all fit together as one cohesive system.

V2 is the bridge from V1 to that world UI target, establishing the player-facing control layer and persistent hierarchy that the final world presentation grows around.

**V2 principle: THE NETWORK IS THE HEARTBEAT OF THE SCREEN.**

The persistent visual hierarchy is:

```
Global Chain → Current Block → Network → Player Contribution → Mining Operation → Economy → Progression
```

**Rule:** V2 extends V1. Do not break working V1 server bindings, events, or read models.

**Visual scope:** "Network-first HUD" encompasses the entire screen composition — including the world scene `BackgroundLayer` that renders beneath the HUD panels. The world scene background is designed in the same visual vocabulary (design tokens, colour palette, state icon language, badge states, layer hierarchy) as the HUD control layers above it, so the full screen reads as one cohesive system. See `docs/world-scene-v1-asset-pack-and-implementation-plan.md §2` for how the world scene integrates into this design language and into the final world UI standard.

---

## 2. Non-Negotiables (Carry Over from V1)

1. Keep all working V1 signals, WebSocket feeds, and REST bindings.
2. Keep existing authoritative data payloads: `BlockStatus`, `PlayerContribution`, `PlayerProfile`, `RewardTimeline`, `MarketListing`, `UpgradeState`, `PowerState`, `CoolingState`, `OperationIntent`.
3. Keep debug widgets behind a developer toggle (not deleted).
4. Server remains authoritative for all game-state values — no client calculations.
5. No regression in frame pacing from UI updates.
6. No hard dependency on final art to proceed.

---

## 3. Player-Facing Screen Flow

```
BOOT
 └── SplashScreen (optional, 1.5–2.0s, GMN identity)
      └── MainMenu
           ├── New Game → InGameHUD
           ├── Continue (if save exists) → InGameHUD
           ├── Settings → SettingsMenu
           ├── Credits → CreditsScreen
           └── Quit

InGameHUD
 ├── [Global Block Header — always visible]
 ├── [Player Operation Panel — always visible]
 ├── [Resource Strip — always visible]
 ├── [GMN Nav Bar — always visible]
 ├── [Surface Area — switches per nav selection]
 ├── Pause (Esc/Start)
 │    └── PauseMenu
 │         ├── Resume
 │         ├── Settings
 │         ├── Main Menu (confirm)
 │         └── Quit (confirm)
 ├── NotificationFeed
 └── ModalLayer (confirm dialogs, purchase flows)
```

---

## 4. Information Architecture

### 4.1 Persistent Global Block Header (Dominant)

**Position:** Top of every in-game screen. Full width. Always visible.  
**Purpose:** Communicate the state of the shared world at a glance.

Required authoritative fields:

| Field | Source |
|---|---|
| Block number | `BlockStatus.block_number` |
| Difficulty | `BlockStatus.difficulty` |
| Global hashrate | `BlockStatus.global_hashrate` |
| Block progress (%) | `BlockStatus.progress` |
| Block state | `BlockStatus.state` |
| Block age / ETA | Server-provided if available; otherwise omit |
| Event state | Server-provided if active event |

Layout:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  BLOCK #18421            DIFFICULTY 8.42 TH        GLOBAL HASHRATE 84.7 PH/s │
│  ████████████████████████████████░░░░░░░░░  73.8%                            │
│  [Block age or ETA — server value only]      [Event state if active]         │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Block number: hero text, largest on screen.
- Progress bar: full width, visually dominant, smooth interpolation only (no local calculation).
- Motion: interpolate presentation; never calculate progress or ETA locally.

### 4.2 Player Mining Operation Panel

**Position:** Persistent left or bottom-left panel.  
**Purpose:** Machine operating state — feels like an actual system, not a stat table.

Required authoritative fields (from existing contracts):

| Field | Source |
|---|---|
| Hardware name | `PlayerProfile.hardware.name` |
| Tier | `PlayerProfile.hardware.tier` |
| Base hashrate | `PlayerProfile.hardware.base_hashrate` |
| Effective hashrate | `EffectiveHashrateService` (server, GMN-EC-01) |
| Power state | `PowerState.state` |
| Power consumption | `PowerState.consumption` |
| Heat | `CoolingState.heat` |
| Cooling efficiency | `CoolingState.efficiency` |
| Throttle multiplier | Server-authoritative (GMN-EC-02/03) |
| Mining/operation status | `OperationIntent.status` |
| Upgrade state | `UpgradeState` |

Status badges (color + icon + label):

- `● MINING` — green
- `● IDLE` — grey
- `⚠ THROTTLED` — amber
- `⚠ OVERHEATING` — red
- `● UPGRADING` — blue (with timer from server)
- `✕ OFFLINE` — red (stale/disconnected)

Upgrade completion warning: prominent badge, not hidden in a row.

### 4.3 Player vs Network Comparison

**Position:** Adjacent to operation panel, or inline within it.  
**Purpose:** Communicate scale; reinforce the psychology of growing importance.

Required authoritative fields:

| Field | Source |
|---|---|
| Player effective hashrate | Server |
| Global network hashrate | `BlockStatus.global_hashrate` |
| Player contribution share | Server read model (mark placeholder if not available) |

Layout:

```
YOUR HASHRATE              GLOBAL HASHRATE
42 GH/s          vs        84.7 PH/s

CONTRIBUTION SHARE
[Awaiting server read model]
```

**Do not calculate contribution percentage client-side.** If unavailable from server, show placeholder with explicit label ("Contribution data unavailable — awaiting server sync"). Component must be architected ready for the value to arrive.

### 4.4 Resource Strip

**Position:** Persistent strip below the Global Block Header or alongside it.  
**Purpose:** Credits and key resources visible without dominating.

```
CREDITS: 4,821 Ƀ    [Resource A: value]    [Resource B: value]
```

All values from server economy ledger read models.

### 4.5 GMN Navigation Bar

**Purpose:** Persistent navigation between game surfaces. GMN-specific language.

```
MINE | HARDWARE | POWER | STORAGE | MARKET | RESEARCH | NETWORK
```

| Section | State | Condition |
|---|---|---|
| MINE | Enabled | Default |
| HARDWARE | Enabled | Default |
| POWER | Enabled | Default |
| STORAGE | Enabled | Default |
| MARKET | Enabled | Default |
| RESEARCH | Locked | Progression gate |
| NETWORK | Enabled (read-only) | Default |

Locked sections: visible with lock icon and locked styling; tapping/clicking shows unlock condition.

### 4.6 Surface Area

The central content area switches per navigation selection.

| Surface | Content | Backend Contracts |
|---|---|---|
| MINE | Active operation detail, hashrate, contribute actions | `OperationIntent`, `BlockStatus` |
| HARDWARE | Hardware browser, tier, upgrade initiation | `PlayerProfile.hardware`, `UpgradeState` |
| POWER | Power budget, facility state, capacity | `PowerState`, GMN-EC-02 |
| STORAGE | Inventory, resource overview | Economy read models |
| MARKET | NPC market listings, purchase flow | `MarketListing`, GMN-EC-05 |
| NETWORK | Block explorer, history, statistics, events | Blockchain read models, GMN-EC-07 |

### 4.7 Notification Feed

**Position:** Right side, collapsible.  
**Purpose:** Economy and operational events.

Priority levels:

1. **Critical:** Overheat, offline, block solved reward, upgrade failed.
2. **Operational:** Upgrade started/completed, purchase completed, throttle triggered.
3. **Informational:** Market restock, block advance, network event.

Auto-expire non-critical notifications: 4–6s. Critical: require dismiss.

Max visible stacked: 4.

### 4.8 Block Completion Event

When `BlockStatus.state` transitions to `solved` / `propagating`:

1. Progress bar fills and distinct solved visual state activates.
2. Block solved indicator (visual flash, sound cue).
3. Reward notification for participating player.
4. Chain advance animation.
5. Next block state: new number, difficulty, clean progress bar.

All state from server. Client presents only. No client-side assumption about when a block "should" solve.

---

## 5. Main Menu

GMN identity — not an isolated save-game entry point.

**Background:** Communicates connection to a persistent, massive computational network. Subtle live-data integration acceptable only if zero additional API overhead. Avoid API calls solely for decoration.

**Layout:**

```
[GMN Logo / Title]
[Background: network/infrastructure motif — static or subtle animation]

[Continue]          ← only if save exists
[New Game]
[Settings]
[Credits]
[Quit]

[Build version — bottom corner]
```

Components use the same GMN component library as the in-game UI.

---

## 6. Pause Menu

Minimal. Focused. Uses GMN component language.

```
[Dimmed / blurred game world behind]
  ┌──────────────────┐
  │  PAUSED          │
  │  Resume          │
  │  Settings        │
  │  Main Menu       │
  │  Quit            │
  └──────────────────┘
[Input legend footer]
```

---

## 7. Settings Menu

Tabs:

1. **Video:** resolution / window / fullscreen / vsync / UI scale / brightness
2. **Audio:** master / music / SFX / UI / voice
3. **Input:** rebinds / sensitivity / invert axes / controller deadzone
4. **Gameplay:** subtitles / tutorials / accessibility toggles

---

## 8. Approximate 1920×1080 Composition

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  BLOCK #18421    DIFFICULTY 8.42 TH    GLOBAL HASHRATE 84.7 PH/s            │
│  ████████████████████████████████░░░░░░░░░░░  73.8%                         │
│  CREDITS: 4,821 Ƀ    Ore: 120    Fuel: 48                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ MINE | HARDWARE | POWER | STORAGE | MARKET | RESEARCH🔒 | NETWORK           │
├──────────────────────┬──────────────────────────────────────────────────────┤
│  YOUR MACHINE        │                                                       │
│  Antminer S1 [T1]    │         [SURFACE AREA]                                │
│  Base:  1.2 TH/s     │         switches per nav selection                    │
│  Eff:   0.98 TH/s    │                                                       │
│  Power: 1,350 W ●OK  │                                                       │
│  Heat:  64°C  ●OK    │                                                       │
│  Cool:  92%   ●OK    │                                                       │
│  ● MINING            │                                                       │
│                      │                                                 [notif│
│  YOUR HASHRATE  vs   │                                                  feed]│
│  0.98 TH/s           │                                                       │
│  84.7 PH/s (global)  │                                                       │
│  contribution:       │                                                       │
│  [awaiting server]   │                                                       │
└──────────────────────┴──────────────────────────────────────────────────────┘
```

Use Godot Container nodes for responsive layout. This is a design intent diagram, not a hardcoded coordinate spec.

---

## 9. Scene and Node Layout

### 9.1 UIRoot.tscn

> **`UIRoot.tscn` does not yet exist in the codebase.** Current entry point is `client-godot/scenes/gameplay_shell.tscn`. Create `UIRoot.tscn` in V2 Slice 1 and migrate or stub the existing scene so V1 integration tests pass. See `docs/client-ui-roadmap-v2.md §13 Slice 1` for steps.

> **`UIStateController` is planned, not yet implemented.** Scene components — including world scene visual controllers — must bind authoritative state through `GameplayShellController` until `UIStateController` is introduced. See `docs/world-scene-v1-asset-pack-and-implementation-plan.md §15.1 OQ-01`.

```
UIRoot (CanvasLayer)
├── BackgroundLayer (Control)   ← WorldRoot (world scene) parented here
├── ScreenStack (Control)
│   ├── MainMenu
│   ├── SettingsMenu (hidden)
│   ├── CreditsScreen (hidden)
│   └── PauseMenu (hidden)
├── HUDLayer (Control)           ← visible in-game only
│   └── HUDRoot
│       ├── GlobalBlockHeader
│       ├── ResourceStrip
│       ├── GMNNavBar
│       ├── SurfaceArea (container, swaps child per nav)
│       ├── PlayerOperationPanel
│       └── PlayerVsNetworkPanel
├── ModalLayer (Control)
│   └── ConfirmDialog (hidden)
├── NotificationLayer (Control)
│   └── NotificationFeed
└── DebugLayer (Control, hidden) ← V1 debug surfaces
```

### 9.2 Directory Structure

```
scenes/
  ui/
    UIRoot.tscn
    theme/
      UITheme.tres
      ui_tokens.gd
    hud/
      HUDRoot.tscn
      GlobalBlockHeader.tscn
      PlayerOperationPanel.tscn
      PlayerVsNetworkPanel.tscn
      ResourceStrip.tscn
      GMNNavBar.tscn
      NotificationFeed.tscn
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
      DebugLayer.tscn
```

---

## 10. Component Library

### GMNButton
- Variants: Primary / Secondary / Danger / Ghost
- States: Default / Hover / Focus / Pressed / Disabled

### GMNPanel
- Variants: Solid / Glass / Outline
- Slots: Header / Body / Footer

### GMNStatChip
- Icon + label + value
- Optional trend arrow (↑/↓)

### GMNProgressBar
- Fill + optional delayed-damage bar
- Color thresholds: green → amber → red

### GMNStatusBadge
- Color + icon + text label
- Used for machine status (MINING / IDLE / THROTTLED / UPGRADING / OFFLINE / OVERHEATING)

### GMNTooltip
- Delay: 0.25s hover
- Max width: 320px

### GMNTabBar
- For Settings tabs and nav sub-tabs
- Keyboard / controller focus order enforced

---

## 11. Visual Design Tokens

### Color Palette

| Token | Value | Usage |
|---|---|---|
| `bg_base` | `#0B0F14` | Screen background |
| `bg_panel` | `#131A22` | Standard panel |
| `bg_panel_alt` | `#1A2430` | Elevated panel |
| `line_subtle` | `#2A3A4A` | Grid, separators |
| `text_primary` | `#E8F0F7` | Headings, values |
| `text_secondary` | `#A9BACB` | Labels, secondary |
| `accent_primary` | `#4CC9F0` | Active state, network motif; also used for `upgrading` state (world scene icons and `GMNStatusBadge`) |
| `accent_success` | `#56D364` | Healthy, online, reward |
| `accent_warning` | `#F2C14E` | Throttle, heat warning |
| `accent_danger` | `#FF6B6B` | Overheat, offline, error |
| `accent_network` | `#6E40C9` | Network highlights |

> **Palette is the single source of truth.** All world-scene pixel art state colours must match these hex values exactly. The world scene document's `accent_info` token is resolved as `accent_primary` (`#4CC9F0`). No separate accent hex values may be introduced for world assets. The palette file `assets/pixel/palette_v1.png` must use these four accent slots.

> **These tokens define one shared UI system.** V1 debug parity surfaces, V2 HUD widgets, and the final world UI presentation all inherit this palette, icon language, and state semantics. World-scene art may gain fidelity over time, but it must continue to fit this same token system.

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

### Spacing Scale

`4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48`

### Radius and Depth

| Token | Value |
|---|---|
| `radius_sm` | 6 |
| `radius_md` | 10 |
| `radius_lg` | 14 |
| Shadow card | Single-layer |
| Shadow modal | Two-layer |

---

## 12. Input and Navigation

### Keyboard / Mouse

| Action | Input |
|---|---|
| Pause / Back | Esc |
| Confirm | Enter / Space |
| Navigate menus | Arrow keys / WASD |
| Tab focus | Tab / Shift+Tab |

### Controller

| Action | Input |
|---|---|
| Pause | Start |
| Navigate | D-pad / Left stick |
| Confirm | A / Cross |
| Back | B / Circle |
| Tab switch | LB / RB |

### Focus Rules

- Every screen has a default focused control on entry.
- No dead ends in the focus graph.
- Modal layers trap focus until dismissed.
- Navigation bar items are focusable and activatable via keyboard and controller.

---

## 13. Debug vs Player Mode

- `DebugLayer` hidden by default in release and normal play.
- Developer hotkey exposes debug layer. The hotkey is wired via a **`debug_toggle` input action** in `client-godot/project.godot`. This action must be added before Slice 7 (Debug Layer Migration) — and before Slice 1 world-scene W1 merge. See `docs/world-scene-v1-asset-pack-and-implementation-plan.md §15.2 OQ-02` for status and resolution path.
- V1 debug values remain visible in debug mode for parity comparison with V2.
- Player-facing screens contain no debug artifacts.

---

## 14. Implementation Order

Work vertically — each slice is shippable:

| Slice | Deliverable |
|---|---|
| 1 | Freeze V1 bindings + V2 UIRoot, theme, state controller + GlobalBlockHeader |
| 2 | PlayerOperationPanel + PlayerVsNetworkPanel (with placeholder) |
| 3 | ResourceStrip + NotificationFeed + economy event wiring |
| 4 | GMNNavBar + surface switching + locked-state display |
| 5 | Market, Hardware, Power, Network surface integrations |
| 6 | Main Menu, Pause, Settings (GMN identity) |
| 7 | Debug layer migration; V1 behind toggle |
| 8 | Visual hierarchy pass + responsive + accessibility |

---

## 15. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| V1 bindings break during refactor | Adapter layer between data source and V2 widget API |
| Contribution share unavailable from server | Component architected + explicit placeholder text |
| Block completion feels anticlimactic | Dedicated block-solve event flow in `GlobalBlockHeader` |
| UI scope creep | Lock V2 core to slices 1–4 before expanding to 5–8 |
| Controller navigation gaps | Explicit focus graph test pass per screen |
| World scene pixel art colours diverge from HUD palette | Resolved: `ui-v2-plan.md §11` palette is canonical; world scene doc §5.3.1 and §5.4.4 updated to match. `assets/pixel/palette_v1.png` must use V2 hex values. |
| `UIStateController` does not exist when world scene ships | Resolved: world scene controllers bind `GameplayShellController` until `UIStateController` is introduced; annotated in §9.1 and `docs/world-scene-v1-asset-pack-and-implementation-plan.md §15.1 OQ-01`. |
| `UIRoot.tscn` does not exist at W1 kickoff | Resolved: world scene uses `gameplay_shell.tscn` background-equivalent node as temporary parent; migrates to `UIRoot.tscn` `BackgroundLayer` in Slice 1. See §9.1 note and `client-ui-roadmap-v2.md §13 Slice 1`. |
| `debug_toggle` input action missing from `project.godot` | Resolved: add action before Slice 1 / W1 merge; tracked in `docs/world-scene-v1-asset-pack-and-implementation-plan.md §15.2 OQ-02`. |

---

## 16. Definition of Success

V2 is complete for this phase when:

1. Somebody unfamiliar with the code looks at the screen for five seconds and understands:  
   **"I am one miner in a massive shared network, everyone is attacking the same block, my machine contributes, and I am building toward something bigger."**
2. The global block number, progress, and network hashrate are the dominant persistent elements.
3. The player's machine operating state is immediately legible.
4. Block solves feel like meaningful shared events.
5. The GMN navigation language is present and consistent.
6. All V1 data integrations remain intact — zero telemetry regression.
7. No client-authoritative calculations introduced.
8. Debug surfaces hidden by default; accessible to developers.

---

## 17. Cross-References

- `docs/client-ui-roadmap-v2.md` — V2 roadmap (slices, identity, surfaces)
- `docs/client-ui-roadmap-v1.md` — V1 historical context
- `docs/m2-economy-implementation-tickets.md` — Economy contracts (GMN-EC-01–EC-08)
- `docs/m1-slice-1-simulation-kernel-tick-contract.md` — Time-based simulation: use server timestamps
- `docs/operation-intents-api-reference.md` — Operation intent contracts
- `docs/global-mining-network-official-specification.md` — Canonical game spec
- `docs/game-design-brief-v1.md` — Economy and progression philosophy
