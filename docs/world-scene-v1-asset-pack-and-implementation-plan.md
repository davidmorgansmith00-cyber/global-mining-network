# Global Mining Network — World Scene V1 Asset Pack and Implementation Plan

**Status:** Ready for implementation  
**Date:** 2026-08-18  
**Scope:** First playable world scene (2D pixel-art-first) integrated with current GMN client/server model  
**Alignment:** `docs/client-ui-roadmap-v2.md`, `docs/ui-v2-plan.md`, and server-authoritative non-negotiables  
**Godot version:** 4.x / GDScript  
**Owner (Engineering):** TBD — assign before W1 kickoff  
**Owner (Art):** TBD — assign before asset delivery begins

---

## 1) Purpose

Define a production-usable plan for the first in-game world scene and its supporting pixel asset pack, without breaking current authoritative contracts or existing V1/V2 client architecture.

This document delivers:
1. A clear first-scene world direction (starter property: shack in the woods).
2. A modular pixel asset pack specification using blank bases + skin overlays.
3. A Godot scene/component implementation plan mapped to current systems.
4. Vertical integration slices with validation gates and regression checks.

> **How to use this document:** Engineering starts with §8 (slices) + §7 (authoritative bindings) + §6 (scene architecture). Art starts with §5 (asset pack) and tracks delivery per slice in §9. QA uses §10 and §14 (readiness checklist).

---

## 2) Design Intent (World Fantasy)

The first property should communicate:
- You are small and underpowered.
- You are physically operating from a rough, improvised location.
- You are still connected to a massive global network.

Starter location: **a worn shack in the woods** with a basic “rusty old computer” mining setup.

This scene is not a detached decorative room; it is the physical context for the network-first HUD.

---

## 3) Architectural Constraints (Must Follow)

1. **Server remains authoritative** for all gameplay/economy/network outcomes.
2. World visuals are **presentation only** and react to existing authoritative read models.
3. Do not invent new gameplay systems to support visuals.
4. Do not rewrite stable networking/business logic for art/world work.
5. Keep debug parity path available (V1 debug layer stays behind toggle).

Reference alignment:
- `docs/client-ui-roadmap-v2.md`
- `docs/ui-v2-plan.md`
- `docs/global-mining-network-official-specification.md`
- `docs/game-design-brief-v1.md`

---

## 4) Scene Scope (World Scene V1)

## 4.1 Included in V1
- One starter property scene (`shack in woods`).
- Interior playable composition with readable station zones.
- Basic environmental exterior cues (seen through window/door).
- Mining rig area, power area, cooling area, storage/utility area.
- Simple ambient motion (fan spin, monitor flicker, subtle environmental life).

## 4.2 Excluded from V1
- Final high-detail art pass.
- Complex NPC/world simulation.
- New gameplay calculations.
- New progression mechanics created solely for world visuals.

---

## 5) Pixel Asset Pack Strategy

Use a **modular blank-base + skin overlay** strategy so progression upgrades can reskin objects without changing scene logic.

## 5.1 Standards
- Base tile size: **16x16** (preferred for fast iteration and readability).
- Format: PNG (nearest-neighbor pipeline, no smoothing).
- Layering: base / skin / state-fx where relevant.
- Naming convention:
  - `category_item_variant_state_v1.png`
  - Example: `rig_skin_rusty_running_v1.png`
- Import settings in Godot: `Filter: Nearest`, `Mipmaps: off`, `Compress: Lossless`.
- Atlas packing: all tiles in a category packed into one atlas PNG; tile coordinates documented in a companion `.json` or `.tres` resource alongside the PNG.
- Animation sheets: frame count and fps specified per asset below; use `AnimatedSprite2D` + `SpriteFrames` resource.

## 5.2 Asset Pack Inventory (V1)

### A) Environment Tiles
Path: `assets/pixel/world/`
- `shack_tileset_v1.png`
- Atlas companion: `shack_tileset_v1.tres` (TileSet resource defining tile regions)
- Contents:
  - interior wood floor variants (clean/worn/broken)
  - wall panel variants
  - window and door frames
  - roof/trim edges
  - dirt/grass boundary transitions
  - corner shadows and light occlusion helpers
- **Delivered by (Slice):** W2

### B) Structure + Prop Atlas
Path: `assets/pixel/props/`
- `shack_props_v1.png`
- Contents:
  - desk, chair, shelf, crate, lamp, toolbox, cable spool, utility meter
- **Delivered by (Slice):** W2

### C) Mining Rig Kit (Modular)
Path: `assets/pixel/rigs/`
- `rig_base_v1.png` (blank neutral frame — 48x32px minimum to fit a desktop tower)
- `rig_skin_rusty_v1.png` (starter skin — same dimensions, overlaid on base)
- `rig_parts_v1.png` (fan, panel, cable, indicator pieces — used by `RigStateFx`)
- **Delivered by (Slice):** W3
- **Skin swap contract:** `RigVisualController.set_skin(skin_texture: Texture2D)` swaps `RigSkin` sprite; no scene rebuild required.

### D) Power + Cooling Kit
Path: `assets/pixel/systems/`
- `power_nodes_v1.png`
- `cooling_nodes_v1.png`
- Includes breaker box, strip, wire segments, fan housing, vent/duct pieces
- **Delivered by (Slice):** W4

### E) Ambient FX Sheets
Path: `assets/pixel/fx/`
- `fan_spin_v1.png` — **4 frames @ 8 fps**, loop; dims to 30% opacity when `throttle_active`
- `monitor_flicker_v1.png` — **2 frames @ 4 fps**, loop; stops when `offline/stale`
- `heat_haze_v1.png` — **3 frames @ 6 fps**, loop; shown only when `heat_warning == true`
- **Delivered by (Slice):** W5

### F) World-State Icon Microset
Path: `assets/pixel/ui/`
- `world_state_icons_v1.png`
- States (one icon each, 16x16): online, throttled, overheating, offline, upgrading, upgrade-complete, stale-data
- These icons must use the V2 color palette tokens (`accent_success`, `accent_warning`, `accent_danger`) — confirm with art before delivery.
- **Delivered by (Slice):** W4

---

## 6) Godot Scene Architecture

## 6.1 New/Updated Scene Files

```text
scenes/world/
  world_root.tscn
  first_property_shack.tscn
```

## 6.2 Scene Integration with UIRoot

`scenes/world/world_root.tscn` is loaded as a **child of `UIRoot`'s `BackgroundLayer`** (see `docs/ui-v2-plan.md` §9.1 scene tree). It renders behind `HUDLayer`. The persistent V2 HUD (`GlobalBlockHeader`, `PlayerOperationPanel`, `GMNNavBar`) remains on top and is not part of the world scene.

**Layer order (bottom to top):**
1. `BackgroundLayer` → `WorldRoot` (world scene, pixel world)
2. `HUDLayer` → `HUDRoot` (persistent V2 HUD overlays)
3. `ModalLayer` / `NotificationLayer` / `DebugLayer`

> **Constraint:** The world scene must not add any `CanvasLayer` with a higher `layer` value than `HUDLayer`. Use `CanvasModulate` inside `WorldRoot` for lighting effects only.

## 6.3 Suggested Node Layout (first_property_shack.tscn)

```text
FirstPropertyShack (Node2D)
├── GroundTileMap          ← TileMap using shack_tileset_v1.tres, layer 0
├── WallsTileMap           ← TileMap using shack_tileset_v1.tres, layer 1
├── PropsLayer (Node2D)    ← static sprites from shack_props_v1.png
├── RigZone (Node2D)
│   ├── RigBase (Sprite2D)           ← rig_base_v1.png
│   ├── RigSkin (Sprite2D)           ← rig_skin_rusty_v1.png (swapped by RigVisualController)
│   ├── RigStateFx (AnimatedSprite2D) ← SpriteFrames from rig_parts_v1.png
│   └── RigStateIcon (Sprite2D)      ← world_state_icons_v1.png region, driven by server state
├── PowerZone (Node2D)
│   ├── PowerSprites (Node2D)        ← sprites from power_nodes_v1.png
│   └── PowerStateIcon (Sprite2D)    ← world_state_icons_v1.png region
├── CoolingZone (Node2D)
│   ├── CoolingSprites (Node2D)      ← sprites from cooling_nodes_v1.png
│   └── CoolingStateFx (AnimatedSprite2D) ← heat_haze_v1.png frames
├── InteractionZones (Node2D)        ← Area2D hit zones for future click/focus
├── AmbientFxLayer (Node2D)
│   ├── FanSpin (AnimatedSprite2D)   ← fan_spin_v1.png, 4 frames @ 8 fps
│   └── MonitorFlicker (AnimatedSprite2D) ← monitor_flicker_v1.png, 2 frames @ 4 fps
├── LightingOverlay (CanvasModulate) ← tint color driven by time-of-day state if available; default neutral white
└── DebugWorldOverlay (Node2D, hidden by default) ← shows zone boundaries + state labels; exposed via debug toggle
```

Use container/anchoring discipline where UI overlays interact with camera framing. Maintain compatibility with `UIRoot` and network-first header layout.

## 6.4 Camera Framing
- No dedicated camera in the world scene; the scene renders at a fixed world origin.
- If a `Camera2D` is needed (e.g., pan/zoom), it must be gated behind a feature flag and not active in W1.
- The world scene must be legible at the configured viewport (1920×1080 baseline) without any camera transform.

---

## 7) Integration into Current System (Authoritative Binding)

World scene visuals should map from already-existing authoritative state used by current shell/HUD flows.

## 7.1 Allowed Binding Types
- Operation/machine status (running, idle, starting, stopping, rejected, stale).
- Effective/base hashrate read values.
- Power/heat/cooling/throttle states supplied by server profile/read models.
- Upgrade running/completed state.
- Connectivity/freshness state already represented in UI state model.

## 7.2 Authoritative Payload → World Visual Mapping

The following is the **complete V1 binding table**. All fields are read from existing server contracts already consumed by V2 HUD panels (see `docs/client-ui-roadmap-v2.md` §4). No new server contracts are required for W1–W6.

| Server field | Source contract | World visual effect | GDScript signal/property |
|---|---|---|---|
| `OperationIntent.status == "running"` | `OperationIntent` | `FanSpin` plays; `MonitorFlicker` plays; `RigStateFx` active | `rig_visual_controller.set_operation_status(status)` |
| `OperationIntent.status == "idle"` | `OperationIntent` | All FX paused; rig dim | same |
| `PowerState.throttle_active == true` | `PowerState` (GMN-EC-02) | `PowerStateIcon` = throttled icon; FX dim to 30% | `power_visual_controller.set_throttle(active: bool)` |
| `CoolingState.heat_warning == true` | `CoolingState` (GMN-EC-03) | `CoolingStateFx` (heat haze) visible; `CoolingStateIcon` = overheating | `cooling_visual_controller.set_heat_warning(active: bool)` |
| `stale_data == true` (connection lost / no update > threshold) | UIStateController freshness flag | All state icons → stale-data icon; rig lights dimmed | `rig_visual_controller.set_stale(stale: bool)` |
| `UpgradeState.running == true` | `UpgradeState` (GMN-EC-06) | `RigStateIcon` = upgrading icon | `rig_visual_controller.set_upgrade_running(active: bool)` |
| `UpgradeState.complete_pending == true` | `UpgradeState` | `RigStateIcon` = upgrade-complete icon | same |

> **Rule:** World scene GDScript must **receive** these values from the existing UI state model — it must never call server APIs directly or calculate values locally. The UIStateController (or equivalent signal bus) is the single source of truth that both HUD panels and world visuals read from.

## 7.3 Presentation Mapping Examples
- `operation_status == running` → rig animation ON + monitor flicker.
- `throttle_active` → warning icon + reduced fan/lights pulse.
- `heat_warning` → heat haze/fx + warning icon.
- `offline/stale` → dimmed rig lights + stale badge.
- `upgrade_running` → subtle maintenance indicator.

No client-authored formulas for hashrate contribution, rewards, completion, or difficulty.

---

## 8) Implementation Plan (Vertical Slices)

**Delivery order:** W1 → W2 → W3 → W4 → W5 → W6 (sequential; each slice unblocks the next).  
**Owner per slice:** must be assigned before kickoff (see §14 Readiness Review Checklist and §15 Open Questions).

## Slice W1 — Scene Skeleton + Placeholders
**Goal:** establish playable world composition without final art.
- Create `scenes/world/world_root.tscn` as a `Node2D` child inserted into `UIRoot`'s `BackgroundLayer`.
- Create `scenes/world/first_property_shack.tscn` with placeholder `ColorRect` nodes for each zone (RigZone, PowerZone, CoolingZone, AmbientFxLayer).
- All placeholder nodes use distinct colors (not grey-on-grey) so zones are distinguishable.
- Verify camera framing at 1920×1080 with existing HUD overlays visible.
- Add `DebugWorldOverlay` node (hidden by default); toggle via the same developer hotkey used by `DebugLayer`.

**Exit criteria:**
- Scene loads without errors in Godot editor and at runtime.
- HUD elements (`GlobalBlockHeader`, `PlayerOperationPanel`, `GMNNavBar`) render above the world scene with no overlap or z-order conflict.
- No performance regression: frame time delta does not increase by more than 1ms at idle versus baseline without world scene.
- `DebugWorldOverlay` is hidden in normal play; visible after debug hotkey.

## Slice W2 — Tileset + Props Pass
**Goal:** replace placeholders with pixel tile/prop pack v1.
- Import `shack_tileset_v1.png` + `shack_tileset_v1.tres` into Godot (Nearest filter, no mipmaps, lossless).
- Build `GroundTileMap` and `WallsTileMap` layers using the TileSet resource.
- Import `shack_props_v1.png` and place starter props in `PropsLayer`.
- Verify depth hierarchy: props in front of walls, walls in front of floor.

**Exit criteria:**
- Shack interior visually legible at 1920×1080; depth hierarchy readable without debug labels.
- No import artifacts (smoothing, bleeding between tiles).
- Art sign-off: at least one designated art reviewer must approve the tileset pass before merge.

## Slice W3 — Rig Modular System
**Goal:** make starter machine skin-based and progression-ready.
- Import `rig_base_v1.png`, `rig_skin_rusty_v1.png`, `rig_parts_v1.png`.
- Implement `RigVisualController.gd`:
  - `set_skin(skin_texture: Texture2D)` — swaps `RigSkin` sprite texture; no scene reload.
  - `set_operation_status(status: String)` — drives `RigStateFx` animation state.
  - `set_stale(stale: bool)` — dims rig to 50% modulate.
  - `set_upgrade_running(active: bool)` — sets `RigStateIcon` region.
- All methods accept only values from the server payload table in §7.2; no client calculations.

**Exit criteria:**
- Calling `set_skin()` with a different `Texture2D` swaps the visual without reloading the scene.
- `RigStateFx` animates when `status == "running"` and pauses when `"idle"`.
- No new server API calls introduced.

## Slice W4 — Server-Driven Visual States
**Goal:** bind world visuals to existing authoritative states.
- Implement `PowerVisualController.gd` and `CoolingVisualController.gd` per the contracts in §7.2.
- Wire controllers to receive state from UIStateController (or its existing signal bus) — not from direct REST calls.
- Import `power_nodes_v1.png`, `cooling_nodes_v1.png`, `world_state_icons_v1.png`.
- Implement stale/offline visual fallback: all state icons switch to `stale-data` icon when `stale == true`.
- Ensure `DebugWorldOverlay` shows current bound values (operation status, throttle, heat warning) as text labels when debug hotkey active.

**Exit criteria:**
- All world state changes (running ↔ idle, throttle on/off, heat warning on/off, stale on/off) trace visually to the server-backed payload with no additional client logic.
- Debug overlay shows live server values matching HUD panel values (parity check).
- No regressions in `PlayerOperationPanel` or `GlobalBlockHeader` behavior.

## Slice W5 — Ambient Motion + Readability
**Goal:** increase world life without noise.
- Import `fan_spin_v1.png`, `monitor_flicker_v1.png`, `heat_haze_v1.png`.
- Wire `AmbientFxController.gd`:
  - `FanSpin` animates only when `operation_status == "running"`.
  - `MonitorFlicker` animates only when `operation_status == "running"`.
  - `CoolingStateFx` (heat haze) visible only when `heat_warning == true`.
  - All FX pause when `stale == true`.
- Visual priority check: all ambient FX must not obscure or compete with HUD text readability.

**Exit criteria:**
- World feels alive during `running` state and visibly quiet during `idle`/`stale`.
- No FX visible in `offline/stale` state except the stale-data icon.
- FX do not cause dropped frames (profile in Godot Profiler; FX budget ≤ 0.5ms/frame).

## Slice W6 — QA + Documentation Sync
**Goal:** ship-safe integration.
- Run full Godot client smoke flow: boot → main menu → in-game HUD with world scene → all nav surface switches → pause → resume → quit.
- Validate keyboard and controller focus not regressed by scene integration (use existing input focus test procedure).
- Validate accessibility: world scene does not introduce color-only state communication — each state has both icon + color (matching V2 accessibility tokens from `docs/accessibility-guide.md`).
- Validate at 1920×1080, 2560×1440, and at 125%/150% UI scale.
- Update `docs/progress-tracker.md` to mark world scene W1–W6 complete.
- Update `docs/client-ui-roadmap-v2.md` cross-references if world scene scope changed anything.

**Exit criteria:**
- Zero regressions in existing Godot smoke flow.
- All state icons meet WCAG AA contrast on the V2 dark background (`bg_base: #0B0F14`).
- Docs synchronized to actual repo state.
- Scene renders correctly at all three tested viewport sizes.

---

## 9) File/Task Checklist

## 9.1 Planned Files
- `docs/world-scene-v1-asset-pack-and-implementation-plan.md` (this document)
- `scenes/world/world_root.tscn` ← W1
- `scenes/world/first_property_shack.tscn` ← W1
- `assets/pixel/world/shack_tileset_v1.png` ← W2
- `assets/pixel/world/shack_tileset_v1.tres` (TileSet resource) ← W2
- `assets/pixel/props/shack_props_v1.png` ← W2
- `assets/pixel/rigs/rig_base_v1.png` ← W3
- `assets/pixel/rigs/rig_skin_rusty_v1.png` ← W3
- `assets/pixel/rigs/rig_parts_v1.png` ← W3
- `assets/pixel/systems/power_nodes_v1.png` ← W4
- `assets/pixel/systems/cooling_nodes_v1.png` ← W4
- `assets/pixel/fx/fan_spin_v1.png` ← W5
- `assets/pixel/fx/monitor_flicker_v1.png` ← W5
- `assets/pixel/fx/heat_haze_v1.png` ← W5
- `assets/pixel/ui/world_state_icons_v1.png` ← W4

## 9.2 Planned Scripts (minimal)
- `scripts/world/world_root.gd` ← W1; wires world scene into UIRoot signal bus; no gameplay logic
- `scripts/world/rig_visual_controller.gd` ← W3; public API: `set_skin(skin_texture: Texture2D)`, `set_operation_status(status: String)`, `set_stale(stale: bool)`, `set_upgrade_running(active: bool)`
- `scripts/world/power_visual_controller.gd` ← W4; `set_throttle(active: bool)`
- `scripts/world/cooling_visual_controller.gd` ← W4; `set_heat_warning(active: bool)`
- `scripts/world/ambient_fx_controller.gd` ← W5; `set_running(active: bool)`, `set_stale(stale: bool)`

---

## 10) Validation Checklist (Implementing Correctly)

Before merge of each slice, confirm:
1. No new client-auth gameplay/economy/network logic introduced.
2. Visual state transitions are driven by existing authoritative payloads (see §7.2 binding table).
3. UI V2 global block header remains dominant in composition — world scene renders in `BackgroundLayer`, not above HUD.
4. World additions do not break existing shell scene/state controller behavior.
5. Debug toggle still permits V1↔V2 parity checks; `DebugWorldOverlay` shows live server values matching HUD values.
6. Responsive behavior remains valid at 1920×1080, 2560×1440, and 125%/150% UI scale.
7. All Godot import settings for new assets: `Filter: Nearest`, `Mipmaps: off`, `Compress: Lossless`.
8. No new `CanvasLayer` with layer value higher than `HUDLayer`.
9. Art sign-off obtained for any new art asset before merge (W2+).

---

## 11) Success Criteria

World Scene V1 is successful when:
- The player starts in a believable shack-in-the-woods environment.
- The rusty starter rig visually communicates humble beginnings.
- World visuals react to authoritative system state (running, throttled, hot, stale, upgrading).
- The scene strengthens the GMN fantasy without breaking existing contracts.
- The implementation is extensible for future skins/assets and property upgrades.

---

## 12) Next Recommended Action

Implement Slice W1 immediately (scene skeleton + placeholders), then iterate W2–W6 vertically with regression checks after each slice.

---

## 13) Cross-References

- `docs/client-ui-roadmap-v2.md` — V2 HUD architecture; scene hierarchy that WorldRoot integrates into
- `docs/ui-v2-plan.md` — UIRoot node tree; layer order; GMN visual design tokens
- `docs/global-mining-network-official-specification.md` — Canonical game spec
- `docs/game-design-brief-v1.md` — Economy and progression philosophy
- `docs/m2-economy-implementation-tickets.md` — Economy contracts (GMN-EC-01–EC-06) supplying server state bound in §7.2
- `docs/accessibility-guide.md` — WCAG AA requirements for icon/color states
- `docs/progress-tracker.md` — Execution state; update after each W-slice merge

---

## 14) Readiness Review Checklist

Use this checklist before starting each slice to confirm prerequisites are met.

### Before W1 (Scene Skeleton)
- [ ] Engineering owner assigned
- [ ] Art owner assigned
- [ ] Godot 4.x project confirmed available and loadable in repo
- [ ] `UIRoot.tscn` and `BackgroundLayer` node exist and are confirmed accessible (check `scenes/ui/UIRoot.tscn`)
- [ ] Developer debug hotkey confirmed (what key/action name triggers `DebugLayer` toggle?)
- [ ] `UIStateController` (or equivalent signal bus) identified — confirm the GDScript node/autoload name that emits operation status, throttle, heat warning, stale state

### Before W2 (Tileset + Props)
- [ ] W1 merged and passing
- [ ] Art owner has confirmed `shack_tileset_v1.png` and `shack_props_v1.png` delivery date
- [ ] Art reviewer(s) assigned for sign-off

### Before W3 (Rig Modular System)
- [ ] W2 merged and passing
- [ ] `rig_base_v1.png`, `rig_skin_rusty_v1.png`, `rig_parts_v1.png` delivered and reviewed
- [ ] `OperationIntent.status` enum values confirmed (running, idle, starting, stopping, rejected — any others?)

### Before W4 (Server-Driven Visual States)
- [ ] W3 merged and passing
- [ ] `PowerState` and `CoolingState` contracts confirmed available in current server build (GMN-EC-02/03 shipped)
- [ ] `world_state_icons_v1.png` delivered and reviewed; colors match V2 palette tokens

### Before W5 (Ambient FX)
- [ ] W4 merged and passing
- [ ] All FX sheets delivered: `fan_spin_v1.png`, `monitor_flicker_v1.png`, `heat_haze_v1.png`
- [ ] Frame counts and fps confirmed with art (see §5.2E defaults; art to confirm or override)

### Before W6 (QA + Documentation Sync)
- [ ] W5 merged and passing
- [ ] Godot smoke flow test procedure documented (or referenced from existing QA doc)
- [ ] Controller focus test procedure documented (or referenced)

---

## 15) Open Questions and Assumptions

The following items are explicitly uncertain. They must be resolved before or during the relevant slice. **Do not silently decide these — capture the answer here when resolved.**

| # | Question | Relevant slice | Assumption if not resolved before slice starts |
|---|---|---|---|
| OQ-01 | What is the exact GDScript autoload/node name for `UIStateController`? Does it already emit the signals needed (operation status, throttle, heat warning, stale)? | W1/W4 | Assume an autoload named `UIStateController` with signals `operation_status_changed(status: String)`, `throttle_changed(active: bool)`, `heat_warning_changed(active: bool)`, `stale_changed(stale: bool)` |
| OQ-02 | What developer hotkey exposes `DebugLayer`? Is it the same hotkey as the existing `DebugLayer` toggle? | W1 | Assume the existing debug hotkey (document the actual key name once confirmed) |
| OQ-03 | Are `PowerState` and `CoolingState` server contracts (GMN-EC-02/03) shipped at the time of W4? If not, W4 must stub those bindings. | W4 | Treat as stubbed placeholders if not shipped; stub must be replaced before W6 merge |
| OQ-04 | What is the full set of `OperationIntent.status` enum values? Any values beyond running/idle/starting/stopping/rejected? | W3 | Use the set above; expand if server adds values |
| OQ-05 | Does the world scene need a `Camera2D`? Or is a fixed-origin render sufficient for V1? | W1 | Fixed-origin render only; no `Camera2D` in W1–W6 unless explicitly re-opened |
| OQ-06 | Who is the art reviewer for sign-off on W2+ assets? | W2 | Must be named before W2 kickoff; W2 cannot merge without a named reviewer |
| OQ-07 | Should the world scene be visible on the `MainMenu` screen, or only during in-game (after session start)? | W1 | In-game only (after session bootstrap); MainMenu uses its own background |
| OQ-08 | Are there interaction zones (click-to-inspect) needed for V1, or are `InteractionZones` placeholder-only? | W1–W6 | Placeholder-only for V1; no interaction logic in W1–W6 |
| OQ-09 | What is the Godot node name / `CanvasLayer.layer` value for `HUDLayer` in `UIRoot.tscn`? | W1 | Must be confirmed before scene integration; world scene `BackgroundLayer` must be a lower layer value |
| OQ-10 | Is `heat_warning` a boolean flag on `CoolingState` or a threshold-crossed condition derived from `CoolingState.heat`? | W4 | Treat as a boolean server-provided flag; do not threshold-check client-side |
