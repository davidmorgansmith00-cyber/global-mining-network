"""Unit tests for GMN-EC-08: PlayerTelemetryService.

Tests cover:
- Event emission with correct properties (AC-1, AC-2, AC-3)
- Event batching (buffer fills after N events or T seconds, AC-4)
- Non-blocking / async fire-and-forget (AC-9)
- Balance milestone crossing helper
- Analytics backend noop behaviour
"""

from __future__ import annotations

import queue
import sys
import threading
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.telemetry.service import (
    BALANCE_MILESTONES,
    EVENT_BALANCE_MILESTONE,
    EVENT_HARDWARE_PURCHASED,
    EVENT_OFFLINE_PROGRESS,
    EVENT_SESSION_END,
    EVENT_SESSION_START,
    EVENT_TIER_UPGRADED,
    AnalyticsBackendService,
    PlayerTelemetryService,
    TelemetryEvent,
    _TelemetryWorker,
)


class FakeBackend(AnalyticsBackendService):
    """Test double that captures batches instead of sending them."""

    def __init__(self) -> None:
        self.batches: list[list[TelemetryEvent]] = []

    def send_batch(self, events: list[TelemetryEvent]) -> None:
        self.batches.append(list(events))


class PlayerTelemetryServiceEmissionTests(unittest.TestCase):
    """AC-1, AC-2, AC-3: events are enqueued with correct structure."""

    def _make_service(self) -> tuple[PlayerTelemetryService, queue.Queue]:
        buf: queue.Queue[TelemetryEvent] = queue.Queue()
        svc = PlayerTelemetryService(buf=buf, backend=FakeBackend())
        return svc, buf

    def test_emit_tier_upgraded_enqueues_correct_event(self) -> None:
        svc, buf = self._make_service()
        svc.emit_tier_upgraded(player_id="p1", from_tier=1, to_tier=2, blocks_finalized_count=5)
        event = buf.get(timeout=1)
        self.assertEqual(event.event_type, EVENT_TIER_UPGRADED)
        self.assertEqual(event.player_id, "p1")
        self.assertEqual(event.properties["player_tier"], 1)
        self.assertEqual(event.properties["player_tier_new"], 2)
        self.assertEqual(event.properties["blocks_finalized_count"], 5)

    def test_emit_hardware_purchased_includes_all_fields(self) -> None:
        svc, buf = self._make_service()
        svc.emit_hardware_purchased(
            player_id="p2",
            hardware_id="improved_workstation",
            previous_hardware_id="starter_rusty_home_computer",
            cost=Decimal("2500"),
            player_tier=1,
        )
        event = buf.get(timeout=1)
        self.assertEqual(event.event_type, EVENT_HARDWARE_PURCHASED)
        self.assertEqual(event.properties["hardware_id"], "improved_workstation")
        self.assertEqual(event.properties["hardware_previous"], "starter_rusty_home_computer")
        self.assertAlmostEqual(event.properties["cost_paid"], 2500.0)
        self.assertEqual(event.properties["player_tier"], 1)

    def test_emit_offline_progress_includes_cap_flag(self) -> None:
        svc, buf = self._make_service()
        svc.emit_offline_progress(
            player_id="p3",
            offline_duration_seconds=3600,
            work_credited=Decimal("500"),
            cap_applied=True,
            offline_cap_tier=1,
        )
        event = buf.get(timeout=1)
        self.assertEqual(event.event_type, EVENT_OFFLINE_PROGRESS)
        self.assertTrue(event.properties["offline_cap_applied"])
        self.assertEqual(event.properties["offline_duration_seconds"], 3600)
        self.assertAlmostEqual(event.properties["offline_work_credited"], 500.0)

    def test_emit_session_start_includes_player_tier(self) -> None:
        svc, buf = self._make_service()
        svc.emit_session_start(player_id="p4", session_id="s1", player_tier=2)
        event = buf.get(timeout=1)
        self.assertEqual(event.event_type, EVENT_SESSION_START)
        self.assertEqual(event.session_id, "s1")
        self.assertEqual(event.properties["player_tier"], 2)

    def test_emit_session_end_includes_duration(self) -> None:
        svc, buf = self._make_service()
        svc.emit_session_end(player_id="p5", session_id="s2", session_duration_seconds=1800)
        event = buf.get(timeout=1)
        self.assertEqual(event.event_type, EVENT_SESSION_END)
        self.assertEqual(event.properties["session_duration_seconds"], 1800)

    def test_emit_balance_milestone_includes_before_after(self) -> None:
        svc, buf = self._make_service()
        svc.emit_balance_milestone(
            player_id="p6",
            milestone_amount=Decimal("1000"),
            balance_before=Decimal("900"),
            balance_after=Decimal("1050"),
        )
        event = buf.get(timeout=1)
        self.assertEqual(event.event_type, EVENT_BALANCE_MILESTONE)
        self.assertAlmostEqual(event.properties["milestone_amount"], 1000.0)
        self.assertAlmostEqual(event.properties["balance_before"], 900.0)
        self.assertAlmostEqual(event.properties["balance_after"], 1050.0)

    def test_each_event_has_unique_event_id(self) -> None:
        svc, buf = self._make_service()
        svc.emit_tier_upgraded(player_id="p1", from_tier=1, to_tier=2, blocks_finalized_count=5)
        svc.emit_tier_upgraded(player_id="p1", from_tier=2, to_tier=3, blocks_finalized_count=20)
        e1 = buf.get(timeout=1)
        e2 = buf.get(timeout=1)
        self.assertNotEqual(e1.event_id, e2.event_id)

    def test_event_has_utc_timestamp(self) -> None:
        svc, buf = self._make_service()
        svc.emit_tier_upgraded(player_id="p1", from_tier=1, to_tier=2, blocks_finalized_count=5)
        event = buf.get(timeout=1)
        self.assertIsNotNone(event.timestamp.tzinfo)


class TelemetryNonBlockingTests(unittest.TestCase):
    """AC-9: emission must return immediately without blocking."""

    def test_emit_returns_immediately(self) -> None:
        buf: queue.Queue[TelemetryEvent] = queue.Queue()
        svc = PlayerTelemetryService(buf=buf, backend=FakeBackend())
        start = time.monotonic()
        for _ in range(200):
            svc.emit_tier_upgraded(
                player_id="px",
                from_tier=1,
                to_tier=2,
                blocks_finalized_count=5,
            )
        elapsed = time.monotonic() - start
        # 200 fire-and-forget emissions should complete well under 1 second
        self.assertLess(elapsed, 1.0)


class TelemetryBatchingTests(unittest.TestCase):
    """AC-4: buffer is drained by worker thread in batches."""

    def test_worker_flushes_events_to_backend(self) -> None:
        buf: queue.Queue[TelemetryEvent] = queue.Queue()
        backend = FakeBackend()

        # Worker with a very short flush interval for testing
        worker = _TelemetryWorker(buf, backend)

        # Patch database_is_configured so _persist is a no-op
        with patch("domain.telemetry.service.database_is_configured", return_value=False):
            worker.daemon = True
            worker.start()

            # Enqueue exactly _BATCH_SIZE events to trigger a flush
            from domain.telemetry.service import _BATCH_SIZE
            for i in range(_BATCH_SIZE):
                buf.put(
                    TelemetryEvent(
                        event_id=f"evt-{i}",
                        event_type=EVENT_TIER_UPGRADED,
                        player_id="px",
                        session_id=None,
                        timestamp=__import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        ),
                        properties={"player_tier": 1, "player_tier_new": 2, "blocks_finalized_count": 5},
                    )
                )

            # Wait for the flush to happen (up to 5 seconds)
            deadline = time.monotonic() + 5.0
            while not backend.batches and time.monotonic() < deadline:
                time.sleep(0.05)

        self.assertTrue(backend.batches, "Expected at least one flush batch")
        total_events = sum(len(b) for b in backend.batches)
        self.assertEqual(total_events, _BATCH_SIZE)


class BalanceMilestoneHelperTests(unittest.TestCase):
    """crossed_milestones returns correct thresholds."""

    def test_crosses_single_milestone(self) -> None:
        milestones = PlayerTelemetryService.crossed_milestones(
            Decimal("900"), Decimal("1100")
        )
        self.assertEqual(milestones, [Decimal("1000")])

    def test_crosses_multiple_milestones(self) -> None:
        milestones = PlayerTelemetryService.crossed_milestones(
            Decimal("0"), Decimal("10001")
        )
        self.assertEqual(
            milestones,
            [Decimal("1000"), Decimal("5000"), Decimal("10000")],
        )

    def test_no_milestone_crossed(self) -> None:
        milestones = PlayerTelemetryService.crossed_milestones(
            Decimal("1100"), Decimal("1200")
        )
        self.assertEqual(milestones, [])

    def test_exactly_at_milestone_boundary(self) -> None:
        # balance_after == milestone (<=, so it IS crossed)
        milestones = PlayerTelemetryService.crossed_milestones(
            Decimal("999"), Decimal("1000")
        )
        self.assertEqual(milestones, [Decimal("1000")])

    def test_already_above_milestone_not_recrossed(self) -> None:
        # balance already above milestone
        milestones = PlayerTelemetryService.crossed_milestones(
            Decimal("1001"), Decimal("1500")
        )
        self.assertEqual(milestones, [])


class AnalyticsBackendServiceTests(unittest.TestCase):
    """AC-5: noop backend silently discards events."""

    def test_noop_backend_does_not_raise(self) -> None:
        from unittest.mock import patch as _patch
        with _patch("shared.settings.settings") as mock_settings:
            mock_settings.analytics_backend = "noop"
            mock_settings.analytics_http_url = ""
            mock_settings.analytics_api_key = ""
            backend = AnalyticsBackendService()
            from datetime import datetime, timezone
            events = [
                TelemetryEvent(
                    event_id="eid",
                    event_type=EVENT_TIER_UPGRADED,
                    player_id="p1",
                    session_id=None,
                    timestamp=datetime.now(tz=timezone.utc),
                    properties={},
                )
            ]
            # Should not raise
            backend.send_batch(events)

    def test_http_backend_skips_when_no_url(self) -> None:
        from unittest.mock import patch as _patch
        with _patch("shared.settings.settings") as mock_settings:
            mock_settings.analytics_backend = "http"
            mock_settings.analytics_http_url = ""
            mock_settings.analytics_api_key = ""
            backend = AnalyticsBackendService()
            from datetime import datetime, timezone
            events = [
                TelemetryEvent(
                    event_id="eid2",
                    event_type=EVENT_HARDWARE_PURCHASED,
                    player_id="p2",
                    session_id=None,
                    timestamp=datetime.now(tz=timezone.utc),
                    properties={},
                )
            ]
            # Should not raise (no URL configured → silent noop)
            backend.send_batch(events)


if __name__ == "__main__":
    unittest.main()
