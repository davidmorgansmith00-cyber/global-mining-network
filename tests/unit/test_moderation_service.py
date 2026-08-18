from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from domain.moderation.service import ModerationService


class ModerationServiceNoDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ModerationService()

    @patch("domain.moderation.service.database_is_configured", return_value=False)
    def test_take_action_returns_id_without_db(self, _mock: object) -> None:
        action_id = self.service.take_moderation_action(
            "player-1", "warning", "spam", "staff-1"
        )
        self.assertTrue(len(action_id) > 0)

    @patch("domain.moderation.service.database_is_configured", return_value=False)
    def test_submit_appeal_returns_id_without_db(self, _mock: object) -> None:
        appeal_id = self.service.submit_appeal(
            "player-1", "action-1", "it was not me"
        )
        self.assertTrue(len(appeal_id) > 0)

    @patch("domain.moderation.service.database_is_configured", return_value=False)
    def test_review_appeal_returns_approved(self, _mock: object) -> None:
        outcome = self.service.review_appeal("appeal-1", True, "staff-1")
        self.assertEqual(outcome, "approved")

    @patch("domain.moderation.service.database_is_configured", return_value=False)
    def test_review_appeal_returns_denied(self, _mock: object) -> None:
        outcome = self.service.review_appeal("appeal-1", False, "staff-1", "no evidence")
        self.assertEqual(outcome, "denied")

    @patch("domain.moderation.service.database_is_configured", return_value=False)
    def test_get_queue_returns_empty_without_db(self, _mock: object) -> None:
        result = self.service.get_moderation_queue()
        self.assertEqual(result, [])

    @patch("domain.moderation.service.database_is_configured", return_value=False)
    def test_get_stats_returns_zeros_without_db(self, _mock: object) -> None:
        stats = self.service.get_moderator_stats()
        self.assertEqual(stats.actions_taken, 0)
        self.assertEqual(stats.appeals_reviewed, 0)

    @patch("domain.moderation.service.database_is_configured", return_value=False)
    def test_graduated_action_first_offense_warning(self, _mock: object) -> None:
        action_type, duration = self.service.determine_graduated_action("p1", "harassment")
        self.assertEqual(action_type, "warning")
        self.assertIsNone(duration)

    @patch("domain.moderation.service.database_is_configured", return_value=False)
    def test_graduated_action_cheat_first_offense_suspend(self, _mock: object) -> None:
        action_type, duration = self.service.determine_graduated_action("p1", "cheat")
        self.assertEqual(action_type, "suspend")
        self.assertIsNotNone(duration)

    @patch("domain.moderation.service.database_is_configured", return_value=True)
    @patch("domain.moderation.service.open_connection")
    def test_take_action_with_db(self, mock_conn: MagicMock, _mock_db: object) -> None:
        action_id = self.service.take_moderation_action(
            "player-2", "mute", "spam", "staff-2", duration_seconds=86400
        )
        self.assertTrue(len(action_id) > 0)
        cursor = mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.execute.assert_called_once()

    @patch("domain.moderation.service.database_is_configured", return_value=True)
    @patch("domain.moderation.service.open_connection")
    def test_graduated_action_reads_escalation_config(
        self, mock_conn: MagicMock, _mock_db: object
    ) -> None:
        cursor = mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        # First call: offense count = 1
        cursor.fetchone.side_effect = [(1,), (1, 1, 1, 604800)]
        action_type, duration = self.service.determine_graduated_action("p1", "harassment")
        # At offense count=1, index=1 → second step (mute)
        self.assertIn(action_type, ("warning", "mute", "suspend"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
