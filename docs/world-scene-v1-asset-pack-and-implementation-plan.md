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

## 5.3 Pixel Asset Production Playbook

This section gives a coding or design agent everything needed to create V1 assets from zero — no prior art files assumed.

### 5.3.1 Art Style Constraints (V1)

| Constraint | Rule |
|---|---|
| **Base unit** | 16×16 px grid; multi-tile objects snap to multiples (e.g. 48×32 = 3×2 tiles) |
| **Silhouette first** | Every object must read as a distinct silhouette at 100% zoom; overlapping silhouettes are a failure |
| **Limited palette** | Maximum **16 colours per asset file** (can share colours across files); use palette file `assets/pixel/palette_v1.png` (a 16×1 strip) |
| **Contrast rule** | World tiles and props: foreground ≥3.0:1 against the background tile they sit on. State icons: ≥4.5:1 against `bg_base #0B0F14` (WCAG AA — enforced at §10.3 gate). |
| **Outline rule** | 1-px dark outline on interactive/important objects; background environment objects may use inset shading instead |
| **Shading** | 2-level shading only — base colour + 1 darker shadow; no gradients, no anti-aliasing, no sub-pixel rendering |
| **State readability** | At least two visual cues differentiate each state (colour change **and** shape/animation change) — never colour alone |
| **V2 palette alignment** | State colours must map to V2 tokens: success → `#4ECCA3`, warning → `#F5A623`, danger → `#E84855`, info → `#5B9BD5`; these are the only non-neutral accent colours allowed |
| **No transparency except** | Sprite sheets use a transparent background; solid colour fill is forbidden as a background substitute |

### 5.3.2 Required Source Files

Every delivered PNG asset must have a matching source file in `assets/pixel/source/`:

```text
assets/pixel/source/
  world/
    shack_tileset_v1.aseprite   ← layers: base, shadow, light, damage_variant
    shack_props_v1.aseprite
  rigs/
    rig_base_v1.aseprite
    rig_skin_rusty_v1.aseprite
    rig_parts_v1.aseprite
  systems/
    power_nodes_v1.aseprite
    cooling_nodes_v1.aseprite
  fx/
    fan_spin_v1.aseprite        ← animation frames on timeline
    monitor_flicker_v1.aseprite
    heat_haze_v1.aseprite
  ui/
    world_state_icons_v1.aseprite
```

> **If Aseprite is unavailable:** use any tool that exports a flat PNG and keeps layers in a companion `.kra` (Krita) or `.xcf` (GIMP) file. The source file naming rule stays the same.

**Export rule:** export to PNG from source tool with:
- Scale: 1× (no upscaling)
- Colour mode: RGBA
- Background: transparent
- No dithering

### 5.3.3 Canvas Sizes and Grid Conventions

| Asset file | Canvas (px) | Grid | Notes |
|---|---|---|---|
| `shack_tileset_v1.png` | 256×128 | 16×16 tiles | 16 cols × 8 rows; leave empty cells blank |
| `shack_props_v1.png` | 128×128 | 16×16 | Mix of 1×1, 2×2, 1×2 objects; document layout in §5.4.3 |
| `rig_base_v1.png` | 48×32 | (3×2 tiles) | Standalone sprite, not atlas |
| `rig_skin_rusty_v1.png` | 48×32 | (3×2 tiles) | Same bounds as base; overlay in scene |
| `rig_parts_v1.png` | 64×16 | 16×16 | 4 cols × 1 row: fan, panel, cable, indicator |
| `power_nodes_v1.png` | 128×64 | 16×16 | 8 cols × 4 rows |
| `cooling_nodes_v1.png` | 128×64 | 16×16 | 8 cols × 4 rows |
| `fan_spin_v1.png` | 64×16 | 16×16 per frame | 4 frames in a single horizontal strip |
| `monitor_flicker_v1.png` | 32×16 | 16×16 per frame | 2 frames horizontal strip |
| `heat_haze_v1.png` | 48×16 | 16×16 per frame | 3 frames horizontal strip |
| `world_state_icons_v1.png` | 112×16 | 16×16 per icon | 7 icons horizontal; order defined in §5.4.3 |

### 5.3.4 Animation Specs

| FX sheet | Frames | FPS | Loop | Behaviour |
|---|---|---|---|---|
| `fan_spin_v1.png` | 4 | 8 | Looping | Plays when `running`; opacity 100% → 30% when `throttle_active` |
| `monitor_flicker_v1.png` | 2 | 4 | Looping | Plays when `running`; stops (show frame 0) when `offline/stale` |
| `heat_haze_v1.png` | 3 | 6 | Looping | Visible only when `heat_warning == true`; hidden otherwise |

Frame layout: all animation sheets use a **horizontal strip** (frames left-to-right); frame 0 is the leftmost.

For `rig_parts_v1.png` the four pieces (fan, panel, cable, indicator) are **static sprites**, not animation frames — they are selected individually in scene nodes.

### 5.3.5 Naming and Versioning Conventions

```
Source files : assets/pixel/source/<category>/<name>_v<N>.aseprite
Exported PNGs: assets/pixel/<category>/<name>_v<N>.png

Examples:
  assets/pixel/source/world/shack_tileset_v1.aseprite
  assets/pixel/world/shack_tileset_v1.png
  assets/pixel/source/fx/fan_spin_v2.aseprite   ← when V2 art replaces V1
  assets/pixel/fx/fan_spin_v2.png
```

**Rules:**
- Never overwrite an existing versioned PNG; create `_v2` when the art changes.
- Scene and GDScript references point to the version explicitly (e.g. `fan_spin_v1.png`, not `fan_spin.png`).
- Source files are committed to the repo alongside exports.
- When a new version ships, update scene node texture references only after the new PNG passes QA (§5.5.3).

---

## 5.4 Godot Asset Build Workflow

Follow these steps in order whenever a new PNG is ready. All steps run in the Godot 4.x editor unless noted otherwise.

### 5.4.1 Import Presets (Apply Once, Then Auto-Applied)

**One-time setup — create a default import override for all PNGs under `assets/pixel/`:**

1. In Godot editor, open **Project → Project Settings → Import Defaults**.
2. Select resource type `Texture2D`.
3. Set:
   - `compress/mode` = `Lossless`
   - `process/fix_alpha_border` = `false`
   - `process/premult_alpha` = `false`
   - `mipmaps/generate` = `false`
   - `texture/filter` = `Nearest` (integer: `0`)
4. Click **Set as Default for 'Texture2D'**.

> **Verify:** after importing any PNG, open its `.import` file in a text editor and confirm `compress/mode=0` (Lossless), `mipmaps/generate=false`, `texture_filter=0` (Nearest).

For **animation sheets** (`fan_spin_v1.png`, `monitor_flicker_v1.png`, `heat_haze_v1.png`): same import settings; the sprite frames are defined in `.tres` resources (§5.4.3), not in import settings.

### 5.4.2 Creating `shack_tileset_v1.tres` (TileSet Resource)

1. Open `scenes/world/first_property_shack.tscn` in the Godot editor.
2. Select the `GroundTileMap` node.
3. In the TileMap inspector, click **TileSet → New TileSet**; save as `assets/pixel/world/shack_tileset_v1.tres`.
4. In the **TileSet editor** panel, click **Add Texture** and select `assets/pixel/world/shack_tileset_v1.png`.
5. Click **Auto-Create Tiles** → confirm tile size `16×16`, spacing `0`, margin `0`.
6. Assign tiles to layers:
   - `GroundTileMap` → layer 0 — use floor/ground rows (rows 0–2 of the atlas).
   - `WallsTileMap` → layer 1 — use wall/trim rows (rows 3–5).
7. Do **not** add physics/navigation layers in V1 (no collision required for world-scene-only visuals).
8. Save the `.tres` file (**Ctrl+S**).
9. Assign `shack_tileset_v1.tres` to both `GroundTileMap` and `WallsTileMap` nodes (same resource, different layers).

### 5.4.3 Creating `SpriteFrames` Resources for FX Sheets

Repeat for each FX sheet. Example for `fan_spin_v1.png`:

1. In the Godot FileSystem dock, **right-click the `assets/pixel/fx/` folder** (not the PNG) → **New Resource** → search `SpriteFrames` → select it → save as `assets/pixel/fx/fan_spin_frames_v1.tres`.
   - *Alternatively:* select the `AmbientFxLayer/FanSpin` (`AnimatedSprite2D`) node, click its **Frames** property in the Inspector → **New SpriteFrames** → then save with **Ctrl+S** to `assets/pixel/fx/fan_spin_frames_v1.tres`.
2. Open the saved `fan_spin_frames_v1.tres` resource by double-clicking it — the **SpriteFrames editor panel** opens at the bottom.
3. Rename the default animation (`default`) to `spin` by double-clicking the animation name.
4. Click **Add Frames from Sprite Sheet** (film-strip icon):
   - Texture: `fan_spin_v1.png`
   - Horizontal frames: `4`, Vertical frames: `1`
   - Select all 4 frames → **Add 4 frames**.
5. Set **FPS** = `8`, **Loop** = enabled (loop icon active).
6. Save the resource (**Ctrl+S**).
7. Assign `fan_spin_frames_v1.tres` to `AmbientFxLayer/FanSpin` (`AnimatedSprite2D`) → **Frames** property in the Inspector.

| FX sheet | Resource file | Animation name | Frames | FPS | Loop |
|---|---|---|---|---|---|
| `fan_spin_v1.png` | `fan_spin_frames_v1.tres` | `spin` | 4 | 8 | true |
| `monitor_flicker_v1.png` | `monitor_flicker_frames_v1.tres` | `flicker` | 2 | 4 | true |
| `heat_haze_v1.png` | `heat_haze_frames_v1.tres` | `haze` | 3 | 6 | true |

### 5.4.4 Icon Atlas Region Mapping (`world_state_icons_v1.png`)

The icon strip is 112×16 px; icons are 16×16, ordered left-to-right as follows:

| Index | State | Rect (x,y,w,h) | Colour token |
|---|---|---|---|
| 0 | `online` | `(0,0,16,16)` | `accent_success` `#4ECCA3` |
| 1 | `throttled` | `(16,0,16,16)` | `accent_warning` `#F5A623` |
| 2 | `overheating` | `(32,0,16,16)` | `accent_danger` `#E84855` |
| 3 | `offline` | `(48,0,16,16)` | neutral dark `#3A3F47` |
| 4 | `upgrading` | `(64,0,16,16)` | `accent_info` `#5B9BD5` |
| 5 | `upgrade_complete` | `(80,0,16,16)` | `accent_success` `#4ECCA3` |
| 6 | `stale_data` | `(96,0,16,16)` | `accent_warning` `#F5A623` |

**In GDScript**, set an icon region with:
```gdscript
$RigStateIcon.region_rect = Rect2(icon_index * 16, 0, 16, 16)
$RigStateIcon.region_enabled = true
```

### 5.4.5 Expected Generated Resource Files

All `.tres` files are committed to the repo alongside their source PNG:

```text
assets/pixel/world/
  shack_tileset_v1.tres          ← TileSet resource
assets/pixel/fx/
  fan_spin_frames_v1.tres        ← SpriteFrames
  monitor_flicker_frames_v1.tres ← SpriteFrames
  heat_haze_frames_v1.tres       ← SpriteFrames
```

No other generated resources are required for V1. `.import` sidecar files (auto-generated by Godot) are committed to the repo.

---

## 5.5 From-Zero Production Sequence

### 5.5.1 Delivery Order (Unblocking Engineering Slices)

Execute art production and engineering integration in this order to avoid blocking:

```
Step 1 — Unblocks W1 (no art needed)
  → Create ColorRect placeholders in scene; no PNGs required.

Step 2 — Unblocks W2 (required by W2 gate)
  Art: shack_tileset_v1 (source + export)
  Art: shack_props_v1   (source + export)
  Engineering: import + TileSet resource creation (§5.4.2)

Step 3 — Unblocks W3
  Art: rig_base_v1, rig_skin_rusty_v1, rig_parts_v1
  Engineering: import + RigVisualController wiring

Step 4 — Unblocks W4 (can start after Step 3 in parallel for art)
  Art: power_nodes_v1, cooling_nodes_v1, world_state_icons_v1
  Engineering: import + PowerVisualController + CoolingVisualController
               + icon atlas region mapping (§5.4.4)

Step 5 — Unblocks W5
  Art: fan_spin_v1, monitor_flicker_v1, heat_haze_v1
  Engineering: SpriteFrames resources (§5.4.3) + AmbientFxController wiring
```

### 5.5.2 Minimal Viable Placeholder Art (If Final Art Is Delayed)

If final pixel art is not ready for a slice, use this fallback so engineering is never blocked:

| Placeholder type | How to create | When to replace |
|---|---|---|
| **Solid-colour tile** | 16×16 PNG, solid fill; floor = `#2C2416`, wall = `#3A3020` | W2 art delivery |
| **Outline-box prop** | 16×16 or 32×32 PNG; 1-px `#FFFFFF` outline on transparent background | W2 art delivery |
| **Rig stand-in** | 48×32 PNG; `#4A4A4A` fill + label pixel "RIG" in 5×3 pixel font | W3 art delivery |
| **FX single-frame** | One 16×16 frame repeated to meet minimum frame count; tint = state colour | W5 art delivery |
| **Icon stand-in** | 7-cell 112×16 strip; each cell = solid state colour only, no detail | W4 art delivery |

Placeholder files use the **same file names and paths** as final art so no scene changes are needed at swap time.

### 5.5.3 Handoff Checklist (Art → Engineering)

Before any PNG is handed off for scene integration, art must confirm:

- [ ] Source file committed to `assets/pixel/source/<category>/`
- [ ] Exported PNG matches canvas size in §5.3.3 exactly (check with `file` command or Godot import preview)
- [ ] Palette ≤16 colours (verify in Aseprite palette panel, or with `identify -verbose <file>.png | grep Colors` via ImageMagick)
- [ ] No anti-aliasing or sub-pixel smoothing (zoom to 800% and inspect edges)
- [ ] Transparent background (no solid fill behind sprites)
- [ ] Animation frames are in a horizontal strip, leftmost = frame 0
- [ ] Icon strip colours match V2 tokens in §5.4.4
- [ ] Art reviewer sign-off obtained (name + date in PR description)

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

## 10) Asset QA Checklist

### 10.1 Pixel Art Quality (Art Review Gate — required before merge of W2+)

- [ ] **Pixel crispness:** zoom to 400% in Godot preview — no blurred or anti-aliased edges; every pixel has a solid, intentional colour.
- [ ] **No filtering artefacts:** open the `.import` sidecar for each new PNG and confirm `texture_filter=0` (Nearest), `mipmaps/generate=false`.
- [ ] **No tile bleeding:** place tiles adjacent in TileMap; verify no 1-px colour leakage between neighbours at any zoom level.
- [ ] **Palette compliance:** each asset file uses ≤16 colours; accent colours match V2 tokens exactly (§5.3.1).
- [ ] **Silhouette readability:** every object reads as a distinct shape at 100% zoom without colour labels.
- [ ] **Contrast:** foreground vs background luminance ratio ≥3.0:1 (use browser DevTools contrast checker or Aseprite contrast tool).
- [ ] **Consistent outline:** 1-px dark outline present on all interactive/important objects; absent on pure background tiles.

### 10.2 Animation Quality (W5 Gate)

- [ ] **Frame strip layout:** horizontal strip confirmed; frame 0 leftmost; no blank columns inside strip.
- [ ] **Loop readability:** play animation in Godot SpriteFrames editor — loop transition (frame N → frame 0) has no visual jump.
- [ ] **State transitions:** FX starts/stops cleanly on state change (no mid-frame freeze artefacts); verify by triggering state changes in debug overlay.
- [ ] **FX opacity:** `fan_spin` dims to 30% when `throttle_active`; verify with `modulate.a` in debugger.
- [ ] **Performance budget:** in Godot Profiler, confirm all FX together consume ≤0.5 ms/frame while running.

### 10.3 Icon State Distinguishability (W4 Gate)

- [ ] **7 icons visible and distinct:** display `world_state_icons_v1.png` at 1× in Godot; all 7 icons are individually recognisable by silhouette alone (not colour alone).
- [ ] **WCAG AA contrast on dark background:** each icon colour meets ≥4.5:1 contrast against `bg_base #0B0F14`; verify with a contrast checker using the exact hex values from §5.4.4.
- [ ] **Region mapping correct:** in a test scene, cycle through all 7 `region_rect` values (§5.4.4) and confirm the correct icon appears for each.
- [ ] **Stale-data icon distinct from offline icon:** the two must not look identical in isolation.

### 10.4 Scene Integration (All Slices)

- [ ] No new client-side gameplay/economy/network logic introduced.
- [ ] All visual state transitions driven by existing authoritative payloads only (see §7.2 binding table).
- [ ] UI V2 global block header dominant — world scene in `BackgroundLayer`, not above `HUDLayer`.
- [ ] No new `CanvasLayer` with layer value ≥ `HUDLayer` value.
- [ ] `DebugWorldOverlay` hidden in normal play; visible and showing live server values after debug hotkey.
- [ ] Responsive layout valid at 1920×1080, 2560×1440, and 125%/150% UI scale.
- [ ] No regressions in `PlayerOperationPanel` or `GlobalBlockHeader` behaviour.
- [ ] Art reviewer sign-off obtained for any new art asset before merge (W2+).

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
