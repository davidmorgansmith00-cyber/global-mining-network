from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import re
from typing import Any


BANNED_KEYWORDS = {"malware", "doxx", "hate-slur"}


@dataclass(frozen=True)
class TrustProfile:
    level: str
    max_posts_per_day: int | None
    can_moderate: bool


@dataclass(frozen=True)
class ModerationDecision:
    published: bool
    review_required: bool
    reason: str
    trust_level: str


class ForumModerationService:
    def __init__(self) -> None:
        self._review_queue: list[dict[str, Any]] = []
        self._pinned_posts: dict[str, datetime] = {}

    def determine_trust_level(
        self,
        *,
        joined_at: datetime,
        post_count: int,
        positive_feedback: int,
        now: datetime | None = None,
    ) -> TrustProfile:
        now = now or datetime.now(UTC)
        age = now - joined_at.astimezone(UTC)

        if age >= timedelta(days=30) and post_count >= 50 and positive_feedback >= 20:
            return TrustProfile(level="veteran", max_posts_per_day=None, can_moderate=True)
        if age >= timedelta(days=7) and post_count >= 5:
            return TrustProfile(level="member", max_posts_per_day=None, can_moderate=False)
        return TrustProfile(level="new", max_posts_per_day=3, can_moderate=False)

    def evaluate_spam(self, content: str) -> list[str]:
        reasons: list[str] = []
        links = re.findall(r"https?://", content)
        if len(links) > 5:
            reasons.append("too_many_links")

        alpha = [c for c in content if c.isalpha()]
        if alpha:
            uppercase_ratio = sum(1 for c in alpha if c.isupper()) / len(alpha)
            if uppercase_ratio > 0.8 and len(alpha) > 20:
                reasons.append("all_caps")

        words = re.findall(r"\b\w+\b", content.lower())
        if words:
            max_repeat = max(words.count(word) for word in set(words))
            if max_repeat >= 8:
                reasons.append("repeated_content")

        return reasons

    def submit_post(
        self,
        *,
        post_id: str,
        author_id: str,
        content: str,
        trust_profile: TrustProfile,
    ) -> ModerationDecision:
        lowered = content.lower()
        if any(keyword in lowered for keyword in BANNED_KEYWORDS):
            self._review_queue.append(
                {"post_id": post_id, "author_id": author_id, "reason": "banned_keyword", "content": content}
            )
            return ModerationDecision(False, True, "banned_keyword", trust_profile.level)

        spam_reasons = self.evaluate_spam(content)
        if spam_reasons:
            self._review_queue.append(
                {
                    "post_id": post_id,
                    "author_id": author_id,
                    "reason": ",".join(spam_reasons),
                    "content": content,
                }
            )
            return ModerationDecision(False, True, ",".join(spam_reasons), trust_profile.level)

        return ModerationDecision(True, False, "published", trust_profile.level)

    def get_review_queue(self) -> list[dict[str, Any]]:
        return list(self._review_queue)

    def pin_post(self, post_id: str, *, days: int = 7) -> None:
        self._pinned_posts[post_id] = datetime.now(UTC) + timedelta(days=days)

    def is_post_pinned(self, post_id: str) -> bool:
        expiry = self._pinned_posts.get(post_id)
        return expiry is not None and expiry > datetime.now(UTC)
