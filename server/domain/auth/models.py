"""
Account authentication domain models — extended for M4 Productization.

These dataclasses cover the full Account UX surface:
player accounts, email verification, sessions with device metadata,
recovery codes and privacy settings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class PlayerAccount:
    """Represents a registered player account."""

    player_id: UUID
    email: str
    display_name: str
    email_verified: bool
    created_at: datetime
    deleted_at: Optional[datetime] = None


@dataclass(frozen=True)
class AccountSession:
    """
    Tracks an authenticated session with device metadata.
    device_id is a hash of (user_agent + ip_address).
    """

    session_id: UUID
    player_id: UUID
    device_id: str
    device_name: str
    ip_address: str
    created_at: datetime
    last_activity: datetime
    revoked: bool = False


@dataclass(frozen=True)
class RecoveryCode:
    """
    A single-use account recovery code.
    The code itself is stored hashed (SHA-256 with salt or bcrypt).
    """

    code_id: UUID
    player_id: UUID
    code_hash: str
    """Hashed representation of the recovery code — never store plaintext."""
    used: bool = False
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class PrivacySettings:
    """Player privacy preferences."""

    player_id: UUID
    show_on_leaderboard: bool = True
    allow_friend_requests: bool = True
    share_activity_with_pool: bool = True
    marketing_emails: bool = False
    updated_at: Optional[datetime] = None
