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

from domain.support.service import SupportService, _auto_categorise


class AutoCategorisationTests(unittest.TestCase):
    def test_crash_keyword_maps_to_bug_critical(self) -> None:
        category, priority = _auto_categorise("game crash on startup", "crash")
        self.assertEqual(category, "bug")
        self.assertEqual(priority, "critical")

    def test_exploit_keyword_maps_to_exploit_critical(self) -> None:
        category, priority = _auto_categorise("found a dupe exploit", "infinite credits")
        self.assertEqual(category, "exploit")
        self.assertEqual(priority, "critical")

    def test_harassment_keyword_maps_to_player_behavior_high(self) -> None:
        category, priority = _auto_categorise("player harassment", "offensive language")
        self.assertEqual(category, "player_behavior")
        self.assertEqual(priority, "high")

    def test_unknown_keyword_defaults_to_bug_medium(self) -> None:
        category, priority = _auto_categorise("general question", "nothing specific")
        self.assertEqual(category, "bug")
        self.assertEqual(priority, "medium")


class SupportServiceNoDbTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = SupportService()

    @patch("domain.support.service.database_is_configured", return_value=False)
    def test_create_ticket_returns_uuid_without_db(self, _mock: object) -> None:
        ticket_id = self.service.create_ticket("player-1", "Test title", "desc")
        self.assertTrue(len(ticket_id) > 0)

    @patch("domain.support.service.database_is_configured", return_value=False)
    def test_add_message_returns_uuid_without_db(self, _mock: object) -> None:
        msg_id = self.service.add_message("ticket-1", "player", "hello")
        self.assertTrue(len(msg_id) > 0)

    @patch("domain.support.service.database_is_configured", return_value=False)
    def test_update_status_valid_transitions(self, _mock: object) -> None:
        for status in ("open", "in_progress", "resolved", "closed"):
            result = self.service.update_ticket_status("t1", status, "staff-1")
            self.assertEqual(result, status)

    @patch("domain.support.service.database_is_configured", return_value=False)
    def test_update_status_invalid_raises(self, _mock: object) -> None:
        with self.assertRaises(ValueError):
            self.service.update_ticket_status("t1", "invalid_state", "staff-1")

    @patch("domain.support.service.database_is_configured", return_value=False)
    def test_search_tickets_returns_empty_without_db(self, _mock: object) -> None:
        result = self.service.search_tickets(player_id="p1")
        self.assertEqual(result, [])

    @patch("domain.support.service.database_is_configured", return_value=False)
    def test_sla_metrics_returns_zeros_without_db(self, _mock: object) -> None:
        metrics = self.service.get_ticket_sla_metrics()
        self.assertEqual(metrics.total_tickets, 0)
        self.assertIsNone(metrics.avg_first_response_seconds)

    @patch("domain.support.service.database_is_configured", return_value=True)
    @patch("domain.support.service.open_connection")
    def test_create_ticket_with_db(self, mock_conn: MagicMock, _mock_db: object) -> None:
        cursor = mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        ticket_id = self.service.create_ticket(
            "p1", "bug report", "game crashed",
            player_state={"balance": 100},
            environment_info={"os": "Windows"},
        )
        self.assertTrue(len(ticket_id) > 0)
        # Evidence insert should have been called
        self.assertEqual(cursor.execute.call_count, 2)

    @patch("domain.support.service.database_is_configured", return_value=True)
    @patch("domain.support.service.open_connection")
    def test_sla_metrics_with_db(self, mock_conn: MagicMock, _mock_db: object) -> None:
        cursor = mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (3600.0, 86400.0, 10, 3)
        metrics = self.service.get_ticket_sla_metrics()
        self.assertEqual(metrics.avg_first_response_seconds, 3600.0)
        self.assertEqual(metrics.total_tickets, 10)
        self.assertEqual(metrics.open_tickets, 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
