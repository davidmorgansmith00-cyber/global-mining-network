from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = ROOT / "bot"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(BOT_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_ROOT))

from discord_bot import DiscordBot


class DiscordBotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bot = DiscordBot(
            faq_lookup=lambda keyword: f"faq:{keyword}",
            economy_provider=lambda: {
                "difficulty_base": "1.2",
                "reward_per_work_unit": "0.2",
                "inflation_rate_percent": 1.5,
            },
            status_provider=lambda: {"status": "up", "recent_incidents": ["none"]},
            tier_times_provider=lambda: {"tier_2": 3000, "tier_3": 6000},
            leaderboard_provider=lambda: [{"player_name": "alice"}, {"player_name": "bob"}],
        )

    def test_help_command_uses_faq_lookup(self) -> None:
        self.assertEqual(self.bot.handle_command("/help migration"), "faq:migration")

    def test_economy_command_includes_parameters(self) -> None:
        response = self.bot.handle_command("/economy")
        self.assertIn("Difficulty Base", response)
        self.assertIn("Inflation Rate", response)

    def test_announcement_only_for_supported_events(self) -> None:
        self.assertTrue(self.bot.post_announcement("genesis_announced", "Genesis is live"))
        self.assertFalse(self.bot.post_announcement("unknown_event", "No post"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
