"""Unit tests for accessibility settings — persistence, validation and palette selection."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

# The accessibility classes are in the C# launcher, but we validate the settings
# schema and palette logic using pure Python equivalents so we can run them in CI.
# These tests document the expected contract; the C# MSTest suite covers runtime
# WPF behavior.


class AccessibilitySettingsDataPython:
    """Pure-Python mirror of LauncherConfig's AccessibilitySettingsData for CI tests."""

    VALID_MODES = {"none", "deuteranopia", "protanopia"}

    def __init__(
        self,
        ui_scale: float = 1.0,
        text_size: float = 1.0,
        high_contrast: bool = False,
        color_blind_mode: str = "none",
        reduce_motion: bool = False,
    ) -> None:
        self.ui_scale = ui_scale
        self.text_size = text_size
        self.high_contrast = high_contrast
        self.color_blind_mode = color_blind_mode
        self.reduce_motion = reduce_motion

    def validate(self) -> None:
        if not (0.75 <= self.ui_scale <= 2.0):
            raise ValueError(f"UIScale out of range: {self.ui_scale}")
        if not (0.75 <= self.text_size <= 2.0):
            raise ValueError(f"TextSize out of range: {self.text_size}")
        if self.color_blind_mode.lower() not in self.VALID_MODES:
            raise ValueError(f"Unknown color_blind_mode: {self.color_blind_mode}")

    def to_dict(self) -> dict:
        return {
            "ui_scale": self.ui_scale,
            "text_size": self.text_size,
            "high_contrast": self.high_contrast,
            "color_blind_mode": self.color_blind_mode,
            "reduce_motion": self.reduce_motion,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AccessibilitySettingsDataPython":
        return cls(
            ui_scale=d.get("ui_scale", 1.0),
            text_size=d.get("text_size", 1.0),
            high_contrast=d.get("high_contrast", False),
            color_blind_mode=d.get("color_blind_mode", "none"),
            reduce_motion=d.get("reduce_motion", False),
        )


class TestAccessibilitySettingsValidation(unittest.TestCase):
    def test_default_settings_are_valid(self) -> None:
        s = AccessibilitySettingsDataPython()
        s.validate()  # should not raise

    def test_ui_scale_below_minimum_raises(self) -> None:
        s = AccessibilitySettingsDataPython(ui_scale=0.5)
        with self.assertRaises(ValueError):
            s.validate()

    def test_ui_scale_above_maximum_raises(self) -> None:
        s = AccessibilitySettingsDataPython(ui_scale=2.5)
        with self.assertRaises(ValueError):
            s.validate()

    def test_text_size_below_minimum_raises(self) -> None:
        s = AccessibilitySettingsDataPython(text_size=0.1)
        with self.assertRaises(ValueError):
            s.validate()

    def test_text_size_above_maximum_raises(self) -> None:
        s = AccessibilitySettingsDataPython(text_size=3.0)
        with self.assertRaises(ValueError):
            s.validate()

    def test_unknown_color_blind_mode_raises(self) -> None:
        s = AccessibilitySettingsDataPython(color_blind_mode="tritanopia")
        with self.assertRaises(ValueError):
            s.validate()

    def test_valid_color_blind_modes_pass_validation(self) -> None:
        for mode in ("none", "deuteranopia", "protanopia", "NONE", "Deuteranopia"):
            s = AccessibilitySettingsDataPython(color_blind_mode=mode)
            s.validate()  # should not raise

    def test_boundary_ui_scale_values_are_valid(self) -> None:
        for scale in (0.75, 1.0, 1.5, 2.0):
            s = AccessibilitySettingsDataPython(ui_scale=scale)
            s.validate()  # should not raise


class TestAccessibilitySettingsPersistence(unittest.TestCase):
    def test_round_trip_serialisation(self) -> None:
        original = AccessibilitySettingsDataPython(
            ui_scale=1.5,
            text_size=1.25,
            high_contrast=True,
            color_blind_mode="deuteranopia",
            reduce_motion=True,
        )
        d = original.to_dict()
        restored = AccessibilitySettingsDataPython.from_dict(d)

        self.assertAlmostEqual(restored.ui_scale, 1.5)
        self.assertAlmostEqual(restored.text_size, 1.25)
        self.assertTrue(restored.high_contrast)
        self.assertEqual(restored.color_blind_mode, "deuteranopia")
        self.assertTrue(restored.reduce_motion)

    def test_from_dict_uses_defaults_for_missing_keys(self) -> None:
        restored = AccessibilitySettingsDataPython.from_dict({})
        self.assertAlmostEqual(restored.ui_scale, 1.0)
        self.assertAlmostEqual(restored.text_size, 1.0)
        self.assertFalse(restored.high_contrast)
        self.assertEqual(restored.color_blind_mode, "none")
        self.assertFalse(restored.reduce_motion)


class TestColorPaletteSelection(unittest.TestCase):
    """Validates palette selection logic (mirrors ColorPalettes.ForMode in C#)."""

    _PALETTES = {
        "default":      {"name": "Default",      "accent_r": 0x00, "accent_g": 0xB4, "accent_b": 0xD8},
        "high_contrast": {"name": "HighContrast", "accent_r": 0xFF, "accent_g": 0xFF, "accent_b": 0x00},
        "deuteranopia": {"name": "Deuteranopia",  "accent_r": 0x56, "accent_g": 0xB4, "accent_b": 0xE9},
        "protanopia":   {"name": "Protanopia",    "accent_r": 0x00, "accent_g": 0x72, "accent_b": 0xB2},
    }

    def _select_palette(self, color_blind_mode: str, high_contrast: bool) -> dict:
        if high_contrast:
            return self._PALETTES["high_contrast"]
        return self._PALETTES.get(color_blind_mode.lower(), self._PALETTES["default"])

    def test_default_mode_returns_default_palette(self) -> None:
        p = self._select_palette("none", high_contrast=False)
        self.assertEqual(p["name"], "Default")

    def test_high_contrast_overrides_color_blind_mode(self) -> None:
        p = self._select_palette("deuteranopia", high_contrast=True)
        self.assertEqual(p["name"], "HighContrast")

    def test_deuteranopia_mode_returns_deuteranopia_palette(self) -> None:
        p = self._select_palette("deuteranopia", high_contrast=False)
        self.assertEqual(p["name"], "Deuteranopia")

    def test_protanopia_mode_returns_protanopia_palette(self) -> None:
        p = self._select_palette("protanopia", high_contrast=False)
        self.assertEqual(p["name"], "Protanopia")

    def test_palettes_have_distinguishable_accent_colors(self) -> None:
        """Accent colors across all palettes must be distinct."""
        accents = {
            (p["accent_r"], p["accent_g"], p["accent_b"])
            for p in self._PALETTES.values()
        }
        self.assertEqual(len(accents), len(self._PALETTES),
                         "Two or more palettes share an identical accent color")


if __name__ == "__main__":
    unittest.main()
