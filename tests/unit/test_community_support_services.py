from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from domain.community.announcements import AnnouncementService
from domain.community.forum import ForumModerationService


class CommunitySupportServiceTests(unittest.TestCase):
    def test_announcement_service_fanout_calls_all_channels(self) -> None:
        called = []

        def sink(_announcement: object) -> None:
            called.append(True)

        service = AnnouncementService(
            sinks={
                "discord": sink,
                "forum": sink,
                "in_game": sink,
                "email": sink,
                "status_page": sink,
            }
        )
        announcement = service.create_announcement("Launch", "Go live now", "info")
        self.assertEqual(announcement.severity, "info")
        self.assertEqual(len(called), 5)

    def test_forum_trust_levels_and_spam_filter(self) -> None:
        service = ForumModerationService()
        trust = service.determine_trust_level(
            joined_at=datetime.now(UTC) - timedelta(days=2),
            post_count=1,
            positive_feedback=0,
        )
        self.assertEqual(trust.level, "new")
        decision = service.submit_post(
            post_id="p1",
            author_id="u1",
            content="BUY NOW HTTP://A.COM HTTP://B.COM HTTP://C.COM HTTP://D.COM HTTP://E.COM HTTP://F.COM",
            trust_profile=trust,
        )
        self.assertTrue(decision.review_required)
        self.assertGreaterEqual(len(service.get_review_queue()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
