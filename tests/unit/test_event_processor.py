from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.blockchain.network_stream import InMemoryNetworkEventStream
from workers.event_processor import run_once


class EventProcessorTests(unittest.TestCase):
    @patch("workers.event_processor.get_network_event_stream")
    def test_run_once_emits_event_resolved_telemetry(self, mock_stream_factory: object) -> None:
        stream = InMemoryNetworkEventStream()
        mock_stream_factory.return_value = stream

        class _Service:
            def resolve_expired_fork_events(self) -> list[str]:
                return ["event-1", "event-2"]

        resolved_ids = run_once(_Service())  # type: ignore[arg-type]
        self.assertEqual(resolved_ids, ["event-1", "event-2"])
        events = stream.list_after(after_sequence=None, limit=10)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, "event_resolved")


if __name__ == "__main__":
    unittest.main(verbosity=2)
