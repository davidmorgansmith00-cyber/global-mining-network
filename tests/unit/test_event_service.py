from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.blockchain.network_stream import InMemoryNetworkEventStream
from domain.events.service import EventService


class EventServiceTests(unittest.TestCase):
    @patch("domain.events.service.database_is_configured", return_value=False)
    def test_reward_and_difficulty_modifiers_apply_when_event_is_active(self, _mock_database: object) -> None:
        stream = InMemoryNetworkEventStream()
        service = EventService(network_event_stream=stream)
        now = datetime.now(UTC)
        reward_event_id = service.create_event(
            name="Double rewards",
            type="timed",
            start_at=now - timedelta(minutes=1),
            end_at=now + timedelta(minutes=5),
            modifier_type="reward_multiplier",
            modifier_value=Decimal("2"),
        )
        difficulty_event_id = service.create_event(
            name="Reduced difficulty",
            type="timed",
            start_at=now - timedelta(minutes=1),
            end_at=now + timedelta(minutes=5),
            modifier_type="difficulty_modifier",
            modifier_value=Decimal("1.25"),
        )
        service.activate_event(reward_event_id, "global")
        service.activate_event(difficulty_event_id, "global")

        reward = service.apply_reward_multiplier(base_reward=Decimal("100.000000"))
        required_work = service.apply_difficulty_modifier(base_required_work=Decimal("125.000000"))

        self.assertEqual(reward, Decimal("200.000000"))
        self.assertEqual(required_work, Decimal("100.000000"))
        self.assertEqual(stream.latest_sequence(), 2)

    @patch("domain.events.service.database_is_configured", return_value=False)
    def test_fork_resolution_chooses_branch_with_higher_work_and_tracks_leaderboard(
        self,
        _mock_database: object,
    ) -> None:
        stream = InMemoryNetworkEventStream()
        service = EventService(network_event_stream=stream)
        now = datetime.now(UTC)
        event_id = service.create_event(
            name="Fork sprint",
            type="fork",
            start_at=now - timedelta(minutes=2),
            end_at=now + timedelta(minutes=2),
            modifier_type=None,
            modifier_value=None,
        )
        service.activate_event(event_id, "global")
        branch_a = service.create_fork_event_branch(event_id, "alpha")
        branch_b = service.create_fork_event_branch(event_id, "beta")

        service.record_branch_contribution(branch_a, "player-a", Decimal("50"))
        service.record_branch_contribution(branch_a, "player-b", Decimal("10"))
        service.record_branch_contribution(branch_b, "player-c", Decimal("20"))

        result = service.resolve_fork_event(event_id)
        leaderboard = service.get_event_leaderboard(event_id, limit=3)

        self.assertEqual(result["event_id"], event_id)
        self.assertEqual(result["winning_branch_id"], branch_a)
        self.assertEqual(leaderboard[0]["player_id"], "player-a")
        self.assertEqual(leaderboard[0]["event_contribution_score"], "50")
        self.assertGreaterEqual(stream.latest_sequence(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
