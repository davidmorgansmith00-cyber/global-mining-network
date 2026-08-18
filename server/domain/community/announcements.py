from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Callable
from uuid import uuid4


@dataclass(frozen=True)
class Announcement:
    announcement_id: str
    title: str
    body: str
    severity: str
    created_at: datetime
    pin_expires_at: datetime
    archive_at: datetime


class AnnouncementService:
    def __init__(self, sinks: dict[str, Callable[[Announcement], None]] | None = None) -> None:
        self._sinks = sinks or {}
        self._announcements: list[Announcement] = []

    def create_announcement(self, title: str, body: str, severity: str) -> Announcement:
        if severity not in {"info", "warning", "critical"}:
            raise ValueError("invalid_severity")

        now = datetime.now(UTC)
        announcement = Announcement(
            announcement_id=str(uuid4()),
            title=title.strip(),
            body=body.strip(),
            severity=severity,
            created_at=now,
            pin_expires_at=now + timedelta(days=7),
            archive_at=now + timedelta(days=30),
        )
        self._announcements.append(announcement)

        for sink in self._sinks.values():
            sink(announcement)
        return announcement

    def list_announcements(self, *, include_archived: bool = False) -> list[Announcement]:
        now = datetime.now(UTC)
        if include_archived:
            return list(self._announcements)
        return [item for item in self._announcements if item.archive_at > now]

    def archive_expired(self) -> int:
        before = len(self._announcements)
        now = datetime.now(UTC)
        self._announcements = [item for item in self._announcements if item.archive_at > now]
        return before - len(self._announcements)
