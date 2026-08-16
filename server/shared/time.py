from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime


class UtcClock:
    def now(self) -> datetime:
        raise NotImplementedError


class SystemUtcClock(UtcClock):
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class FixedUtcClock(UtcClock):
    fixed_now: datetime

    def now(self) -> datetime:
        if self.fixed_now.tzinfo is None:
            return self.fixed_now.replace(tzinfo=UTC)
        return self.fixed_now.astimezone(UTC)
