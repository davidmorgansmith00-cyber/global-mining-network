# Global Mining Network — World Scene V1 Asset Pack and Implementation Plan

**Status:** Ready for implementation  
**Date:** 2026-08-18  
**Scope:** First playable world scene (2D pixel-art-first) integrated with current GMN client/server model  
**Alignment:** `docs/client-ui-roadmap-v2.md`, `docs/ui-v2-plan.md`, and server-authoritative non-negotiables

---

## 1) Purpose

Define a production-usable plan for the first in-game world scene and its supporting pixel asset pack, without breaking current authoritative contracts or existing V1/V2 client architecture.

This document delivers:
1. A clear first-scene world direction (starter property: shack in the woods).
2. A modular pixel asset pack specification using blank bases + skin overlays.
3. A Godot scene/component implementation plan mapped to current systems.
4. Vertical integration slices with validation gates and regression checks.

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

## 5.2 Asset Pack Inventory (V1)

### A) Environment Tiles
Path: `assets/pixel/world/`
- `shack_tileset_v1.png`
- Contents:
  - interior wood floor variants (clean/worn/broken)
  - wall panel variants
  - window and door frames
  - roof/trim edges
  - dirt/grass boundary transitions
  - corner shadows and light occlusion helpers

### B) Structure + Prop Atlas
Path: `assets/pixel/props/`
- `shack_props_v1.png`
- Contents:
  - desk, chair, shelf, crate, lamp, toolbox, cable spool, utility meter

### C) Mining Rig Kit (Modular)
Path: `assets/pixel/rigs/`
- `rig_base_v1.png` (blank neutral frame)
- `rig_skin_rusty_v1.png` (starter skin)
- `rig_parts_v1.png` (fan, panel, cable, indicator pieces)

### D) Power + Cooling Kit
Path: `assets/pixel/systems/`
- `power_nodes_v1.png`
- `cooling_nodes_v1.png`
- Includes breaker box, strip, wire segments, fan housing, vent/duct pieces

### E) Ambient FX Sheets
Path: `assets/pixel/fx/`
- `fan_spin_v1.png`
- `monitor_flicker_v1.png`
- `heat_haze_v1.png` (subtle)

### F) World-State Icon Microset
Path: `assets/pixel/ui/`
- `world_state_icons_v1.png`
- States: online, throttled, overheating, offline, upgrading, upgrade-complete, stale-data

---

## 6) Godot Scene Architecture

## 6.1 New/Updated Scene Files

```text
scenes/world/
  world_root.tscn
  first_property_shack.tscn
```

## 6.2 Suggested Node Layout (first_property_shack.tscn)

```text
FirstPropertyShack (Node2D)
├── GroundTileMap
├── WallsTileMap
├── PropsLayer (Node2D)
├── RigZone (Node2D)
│   ├── RigBase (Sprite2D)
│   ├── RigSkin (Sprite2D)
│   ├── RigStateFx (Node2D)
│   └── RigStateIcon (Sprite2D)
├── PowerZone (Node2D)
│   ├── PowerSprites
│   └── PowerStateIcon
├── CoolingZone (Node2D)
│   ├── CoolingSprites
│   └── CoolingStateFx
├── InteractionZones (Node2D)
├── AmbientFxLayer (Node2D)
├── LightingOverlay (CanvasModulate/Node2D)
└── DebugWorldOverlay (Node2D, hidden by default)
```

Use container/anchoring discipline where UI overlays interact with camera framing. Maintain compatibility with `UIRoot` and network-first header layout.

---

## 7) Integration into Current System (Authoritative Binding)

World scene visuals should map from already-existing authoritative state used by current shell/HUD flows.

## 7.1 Allowed Binding Types
- Operation/machine status (running, idle, starting, stopping, rejected, stale).
- Effective/base hashrate read values.
- Power/heat/cooling/throttle states supplied by server profile/read models.
- Upgrade running/completed state.
- Connectivity/freshness state already represented in UI state model.

## 7.2 Presentation Mapping Examples
- `operation_status == running` → rig animation ON + monitor flicker.
- `throttle_active` → warning icon + reduced fan/lights pulse.
- `heat_warning` → heat haze/fx + warning icon.
- `offline/stale` → dimmed rig lights + stale badge.
- `upgrade_running` → subtle maintenance indicator.

No client-authored formulas for hashrate contribution, rewards, completion, or difficulty.

---

## 8) Implementation Plan (Vertical Slices)

## Slice W1 — Scene Skeleton + Placeholders
**Goal:** establish playable world composition without final art.
- Create `world_root.tscn` and `first_property_shack.tscn`.
- Block out all world zones with placeholder geometry/colors.
- Verify camera framing with existing HUD overlays.

**Exit criteria:** scene loads cleanly; no overlap conflict with persistent UI hierarchy.

## Slice W2 — Tileset + Props Pass
**Goal:** replace placeholders with pixel tile/prop pack v1.
- Add `shack_tileset_v1.png` and `shack_props_v1.png`.
- Build tilemap layers for floor/walls/depth.
- Add starter props for lived-in environment readability.

**Exit criteria:** shack visually legible at 1080p; depth hierarchy readable.

## Slice W3 — Rig Modular System
**Goal:** make starter machine skin-based and progression-ready.
- Implement rig base + skin overlay rendering.
- Add starter `rig_skin_rusty_v1.png`.
- Define script hooks for future skin swap by authoritative progression state.

**Exit criteria:** rig can switch skin asset without scene refactor.

## Slice W4 — Server-Driven Visual States
**Goal:** bind world visuals to existing authoritative states.
- Map current payload fields to rig/power/cooling state visuals.
- Add stale/offline visual fallback.
- Ensure debug parity with V1 data views.

**Exit criteria:** all world state changes trace to server-backed data; no local gameplay calculations introduced.

## Slice W5 — Ambient Motion + Readability
**Goal:** increase world life without noise.
- Add restrained fan spin, flicker, dust/subtle motion.
- Keep visual priority aligned with top global block header.

**Exit criteria:** world feels alive but does not compete with network-first UI hierarchy.

## Slice W6 — QA + Documentation Sync
**Goal:** ship-safe integration.
- Run relevant Godot/client tests and smoke flows.
- Validate keyboard/controller focus not regressed by scene integration.
- Update `docs/progress-tracker.md` and related roadmap references.

**Exit criteria:** no regressions, docs synchronized to actual repo state.

---

## 9) File/Task Checklist

## 9.1 Planned Files
- `docs/world-scene-v1-asset-pack-and-implementation-plan.md` (this document)
- `scenes/world/world_root.tscn`
- `scenes/world/first_property_shack.tscn`
- `assets/pixel/world/shack_tileset_v1.png`
- `assets/pixel/props/shack_props_v1.png`
- `assets/pixel/rigs/rig_base_v1.png`
- `assets/pixel/rigs/rig_skin_rusty_v1.png`
- `assets/pixel/systems/power_nodes_v1.png`
- `assets/pixel/systems/cooling_nodes_v1.png`
- `assets/pixel/fx/fan_spin_v1.png`
- `assets/pixel/fx/monitor_flicker_v1.png`
- `assets/pixel/ui/world_state_icons_v1.png`

## 9.2 Planned Scripts (minimal)
- `scripts/world/world_root.gd`
- `scripts/world/rig_visual_controller.gd`
- `scripts/world/power_visual_controller.gd`
- `scripts/world/cooling_visual_controller.gd`
- `scripts/world/ambient_fx_controller.gd`

---

## 10) Validation Checklist (Implementing Correctly)

Before merge of each slice, confirm:
1. No new client-auth gameplay/economy/network logic introduced.
2. Visual state transitions are driven by existing authoritative payloads.
3. UI V2 global block header remains dominant in composition.
4. World additions do not break existing shell scene/state controller behavior.
5. Debug toggle still permits V1↔V2 parity checks.
6. Responsive behavior remains valid at 1080p baseline.

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
