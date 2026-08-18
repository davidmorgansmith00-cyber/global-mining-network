# Accessibility Guide — Global Mining Network Launcher

**Version:** 1.0  
**Last Updated:** 2026-08-18  
**Applies To:** Windows Launcher (M4+)

---

## Overview

Global Mining Network Launcher is designed to be usable by as many players as
possible. This guide explains the built-in accessibility features, how to
enable them, and known limitations in the current release.

---

## 1. Enabling Accessibility Features

### From the Launcher

1. Open the launcher.
2. Click **Settings** (top-right corner).
3. Select the **Accessibility** tab.
4. Adjust the options described below and click **Save**.

Settings are stored in:

```
%LOCALAPPDATA%\GlobalMiningNetwork\launcher.json
```

under the `"accessibility"` key.

---

## 2. Available Settings

### UI Scale

Scales all UI elements proportionally.

| Setting value | Effect |
|---|---|
| `0.75` | 75% — smaller for high-DPI displays |
| `1.0`  | 100% (default) |
| `1.5`  | 150% — enlarged |
| `2.0`  | 200% — maximum |

> **Tip:** If text appears blurry, ensure Windows DPI scaling is set to 100%
> before increasing this value.

### Text Size

Adjusts font size independently of the overall UI scale.  
Range: `0.75`–`2.0`.

### High Contrast Mode

Switches to a black-background, white-text, high-luminosity-accent palette
targeting **WCAG AAA** contrast ratios (≥7:1 for body text).

To enable:

```json
"accessibility": { "high_contrast": true }
```

### Color-Blind Mode

| Mode | Affected type | Strategy |
|---|---|---|
| `"none"` (default) | — | Standard palette |
| `"deuteranopia"` | Red–green (green weak) | Blue/orange Okabe–Ito palette |
| `"protanopia"` | Red–green (red weak) | Cobalt blue / yellow palette |

All color-blind palettes meet **WCAG AA** (≥4.5:1) contrast ratios.

### Reduce Motion

When enabled, animated transitions (loading spinners, slide-in panels) are
replaced with instant state changes.

To enable:

```json
"accessibility": { "reduce_motion": true }
```

---

## 3. Keyboard Navigation

All interactive launcher elements are focusable via `Tab` / `Shift+Tab`.  
Buttons can be activated with `Space` or `Enter`.  
`Esc` closes modal dialogs.

---

## 4. Screen Reader Support

The launcher is built on WPF with standard `AutomationProperties` attributes
on all interactive controls.  It has been manually verified with:

- **NVDA 2024.x** (Windows)
- **Narrator** (Windows 11)

Known limitations:

- The patch-notes scroll area announces "list" but does not read individual
  patch entries automatically on focus. Use arrow keys to navigate entries.
- The maintenance banner is announced as a status bar region; some screen
  readers may not announce it unless focus moves to the banner.

---

## 5. CLI Accessibility Flags

The launcher executable accepts these flags:

| Flag | Effect |
|---|---|
| `--high-contrast` | Forces high-contrast mode regardless of saved settings |
| `--reduce-motion` | Forces reduce-motion mode |
| `--ui-scale <value>` | Overrides UI scale for this session only |

---

## 6. Reporting Accessibility Issues

If you encounter an accessibility barrier, please open an issue on the project
tracker with the tag `[accessibility]` and include:

- Operating system and version
- Assistive technology used (if any)
- Steps to reproduce
- Expected vs actual behaviour

---

## 7. Roadmap

Planned for future slices:

- Deuteranomaly and tritanopia palettes
- Per-element font size overrides
- Full WCAG 2.1 AA automated audit pass
- macOS VoiceOver compatibility (post-M5)

---

*This guide is maintained alongside the launcher source in*
`launcher-windows/src/AccessibilitySettings.cs` *and*
`launcher-windows/src/ColorPalettes.cs`.
