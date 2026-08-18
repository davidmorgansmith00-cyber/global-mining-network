from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable


@dataclass(frozen=True)
class BotAnnouncement:
    event_type: str
    message: str
    posted_at: datetime


class DiscordBot:
    def __init__(
        self,
        *,
        faq_lookup: Callable[[str], str] | None = None,
        economy_provider: Callable[[], dict] | None = None,
        status_provider: Callable[[], dict] | None = None,
        tier_times_provider: Callable[[], dict] | None = None,
        leaderboard_provider: Callable[[], list[dict]] | None = None,
    ) -> None:
        self._faq_lookup = faq_lookup or (lambda keyword: f"No FAQ entry found for '{keyword}'.")
        self._economy_provider = economy_provider or (lambda: {"difficulty_base": "1.0", "inflation_rate": 0.0})
        self._status_provider = status_provider or (lambda: {"status": "up", "recent_incidents": []})
        self._tier_times_provider = tier_times_provider or (lambda: {"tier_2": 3600, "tier_3": 21600})
        self._leaderboard_provider = leaderboard_provider or (lambda: [])
        self._outbox: list[BotAnnouncement] = []
        self._last_heartbeat_at = datetime.now(UTC)

    def handle_command(self, command: str) -> str:
        text = command.strip()
        if text.startswith("/help"):
            keyword = text.replace("/help", "", 1).strip() or "getting-started"
            return self._faq_lookup(keyword)
        if text == "/economy":
            data = self._economy_provider()
            return (
                "Economy Parameters\n"
                f"Difficulty Base: {data.get('difficulty_base')}\n"
                f"Reward/Work: {data.get('reward_per_work_unit')}\n"
                f"Inflation Rate: {data.get('inflation_rate', data.get('inflation_rate_percent', 0.0))}%"
            )
        if text == "/status":
            status_payload = self._status_provider()
            incidents = status_payload.get("recent_incidents", [])
            return f"Status: {status_payload.get('status', 'unknown')} | Recent incidents: {len(incidents)}"
        if text == "/tier-times":
            tiers = self._tier_times_provider()
            rows = [f"{k}: {v}s" for k, v in sorted(tiers.items())]
            return "Tier Unlock Times\n" + "\n".join(rows) + "\nTip: keep power/cooling balanced to avoid throttling."
        if text == "/leaderboard":
            top = self._leaderboard_provider()[:10]
            if not top:
                return "Leaderboard is warming up. Check back soon."
            formatted = [f"{idx + 1}. {entry.get('player_name', entry.get('player_id', 'player'))}" for idx, entry in enumerate(top)]
            return "Top 10 Players\n" + "\n".join(formatted)
        if text == "/mining-guide":
            return "Mining Guide: Upgrade hardware gradually, keep power under capacity, and maintain cooling efficiency."
        return "Unknown command. Try /help"

    def post_announcement(self, event_type: str, message: str) -> bool:
        allowed = {
            "genesis_announced",
            "major_event_started",
            "major_event_ended",
            "maintenance_scheduled",
            "critical_incident",
            "leaderboard_refreshed_daily",
        }
        if event_type not in allowed:
            return False
        self._outbox.append(
            BotAnnouncement(
                event_type=event_type,
                message=message,
                posted_at=datetime.now(UTC),
            )
        )
        return True

    def run_heartbeat(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(UTC)
        healthy = now - self._last_heartbeat_at <= timedelta(minutes=5)
        self._last_heartbeat_at = now
        return healthy

    def get_outbox(self) -> list[BotAnnouncement]:
        return list(self._outbox)
