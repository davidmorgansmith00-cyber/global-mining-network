## GMN UI Design Tokens
## Canonical palette and typography shared by V1, V2, and World UI layers.
## This is the single source of truth for all colour, spacing, and scale values
## across HUD panels, overlays, menus, and world scene labels.
## DO NOT compute or override these values on the client — they are presentation constants.

class_name GmnUiTokens
extends RefCounted

# ─── Background ────────────────────────────────────────────────────────────────
const BG_BASE        := Color(0.043, 0.059, 0.078)  ## #0B0F14
const BG_PANEL       := Color(0.075, 0.102, 0.133)  ## #131A22
const BG_PANEL_ALT   := Color(0.102, 0.141, 0.188)  ## #1A2430
const LINE_SUBTLE    := Color(0.165, 0.227, 0.290)  ## #2A3A4A

# ─── Text ──────────────────────────────────────────────────────────────────────
const TEXT_PRIMARY   := Color(0.910, 0.941, 0.969)  ## #E8F0F7
const TEXT_SECONDARY := Color(0.663, 0.729, 0.796)  ## #A9BACB

# ─── Accents ───────────────────────────────────────────────────────────────────
const ACCENT_PRIMARY  := Color(0.298, 0.788, 0.941)  ## #4CC9F0  active / network
const ACCENT_SUCCESS  := Color(0.337, 0.827, 0.392)  ## #56D364  healthy / online / reward
const ACCENT_WARNING  := Color(0.949, 0.757, 0.306)  ## #F2C14E  throttle / heat warning
const ACCENT_DANGER   := Color(1.000, 0.420, 0.420)  ## #FF6B6B  overheat / offline / error
const ACCENT_NETWORK  := Color(0.431, 0.251, 0.788)  ## #6E40C9  network-specific highlights

# ─── Typography scale (point sizes) ────────────────────────────────────────────
const SIZE_HERO   := 48  ## Block number
const SIZE_H1     := 36
const SIZE_H2     := 26
const SIZE_H3     := 20
const SIZE_BODY   := 16
const SIZE_SMALL  := 13
const SIZE_MICRO  := 11

# ─── Motion ────────────────────────────────────────────────────────────────────
## Panel enter/exit duration (seconds)
const ANIM_PANEL_MS     := 0.15
## Block-solved single event max duration (seconds)
const ANIM_BLOCK_SOLVED := 0.60
## Number value-change flash (seconds)
const ANIM_VALUE_FLASH  := 0.08
