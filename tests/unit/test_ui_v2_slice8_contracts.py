"""Contracts for UI V2 Slice 8 completion artifacts."""
from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]


class TestUiV2WidgetLibraryArtifacts(unittest.TestCase):
    def test_widget_scenes_exist(self) -> None:
        widget_scene_dir = ROOT / "client-godot" / "scenes" / "ui" / "widgets"
        required = [
            "GMNButton.tscn",
            "GMNPanel.tscn",
            "GMNProgressBar.tscn",
            "GMNTooltip.tscn",
            "GMNTabBar.tscn",
            "GMNStatusBadge.tscn",
            "GMNStatChip.tscn",
        ]
        for filename in required:
            self.assertTrue((widget_scene_dir / filename).exists(), f"Missing widget scene: {filename}")

    def test_widget_scripts_expose_required_classes(self) -> None:
        widget_script_dir = ROOT / "client-godot" / "scenes" / "ui" / "widgets"
        required = {
            "gmn_button.gd": "class_name GmnButton",
            "gmn_panel.gd": "class_name GmnPanel",
            "gmn_progress_bar.gd": "class_name GmnProgressBar",
            "gmn_tooltip.gd": "class_name GmnTooltip",
            "gmn_tab_bar.gd": "class_name GmnTabBar",
            "gmn_status_badge.gd": "class_name GmnStatusBadge",
            "gmn_stat_chip.gd": "class_name GmnStatChip",
        }
        for filename, marker in required.items():
            content = (widget_script_dir / filename).read_text(encoding="utf-8")
            self.assertIn(marker, content, f"Widget class marker missing in {filename}")


class TestUiV2Slice8Documentation(unittest.TestCase):
    def test_signoff_document_exists_and_confirms_success(self) -> None:
        signoff = ROOT / "docs" / "ui-v2-slice-8-signoff.md"
        self.assertTrue(signoff.exists(), "Expected UI V2 Slice 8 sign-off document")
        content = signoff.read_text(encoding="utf-8")
        self.assertIn("Definition of Success", content)
        self.assertIn("Status:** ✅ Approved", content)

    def test_progress_tracker_marks_slice8_done(self) -> None:
        tracker = ROOT / "docs" / "progress-tracker.md"
        content = tracker.read_text(encoding="utf-8")
        self.assertIn("Slices 1–8 Complete and Merged", content)
        self.assertIn("| Slice 8 | Visual hierarchy, responsive, accessibility pass | ✅ Done |", content)


if __name__ == "__main__":
    unittest.main()
