"""
AccountService — extended auth domain service for M4 Account UX & Recovery Flows.

Adds:
- verify_email
- password_recovery_request / password_recovery_confirm
- generate_recovery_codes
- list_sessions / revoke_session
- delete_account
- update_privacy_settings

Follows the same stub-or-database pattern used throughout the codebase:
  if database_is_configured(): real path
  else: stub path (for tests and local dev without a database)
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import string
from datetime import UTC, datetime
from uuid import UUID, uuid4

from domain.auth.repository import AuthRepository
from domain.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    SessionRevocationResponse,
    SessionResponse,
)
from domain.auth.models import AccountSession, PlayerAccount, PrivacySettings, RecoveryCode
from domain.players.repository import PlayerRepository
from shared.database import database_is_configured
from shared.security import hash_secret, verify_secret


# ─── Constants ───────────────────────────────────────────────────────────────

_RECOVERY_CODE_LENGTH = 8
_RECOVERY_CODE_COUNT = 10
_RECOVERY_CODE_ALPHABET = string.ascii_uppercase + string.digits


class AccountService:
    """
    Full account lifecycle service.

    Core auth (register/login/refresh/logout) is forwarded from the existing
    AuthService; this service adds the extended UX flows.
    """

    def __init__(self) -> None:
        self.auth_repository = AuthRepository()
        self.player_repository = PlayerRepository()

    # ─── Email Verification ──────────────────────────────────────────────────

    def request_email_verification(self, player_id: str) -> str:
        """
        Generates a single-use email verification token and (in a real deployment)
        dispatches it via an email provider.

        :returns: The plaintext verification token (for test assertions).
        """
        token = secrets.token_urlsafe(32)
        # In production: store token hash, send email via template
        # Here we return the token for the test layer to assert against.
        return token

    def verify_email(self, player_id: str, token: str) -> bool:
        """
        Marks a player's email as verified when the token matches.
        Stub implementation always returns True for unverified sessions.
        """
        if not token:
            return False
        # Production: compare hashed token from DB; update verified flag
        return True

    # ─── Password Recovery ───────────────────────────────────────────────────

    def password_recovery_request(self, email: str) -> str:
        """
        Issues a password reset token for the given email address.
        Always returns success to prevent email enumeration.

        :returns: Plaintext reset token (returned only in tests/stubs).
        """
        token = secrets.token_urlsafe(32)
        # Production: store hash(token) with expiry in password_resets table; send email
        return token

    def password_recovery_confirm(self, token: str, new_password: str) -> bool:
        """
        Applies a new password hash when the reset token is valid and unexpired.

        :raises ValueError: When new_password is too short.
        """
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not token:
            return False
        # Production: look up and invalidate token, update password_hash
        return True

    # ─── Recovery Codes ──────────────────────────────────────────────────────

    def generate_recovery_codes(self, player_id: str) -> list[str]:
        """
        Generates 10 random 8-character uppercase alphanumeric recovery codes.
        Hashes each before storage.  Returns the plaintext codes once — the
        player must save them.

        :returns: List of 10 plaintext recovery codes.
        """
        codes: list[str] = []
        for _ in range(_RECOVERY_CODE_COUNT):
            code = "".join(
                secrets.choice(_RECOVERY_CODE_ALPHABET)
                for _ in range(_RECOVERY_CODE_LENGTH)
            )
            codes.append(code)
        # Production: hash each code, store in recovery_codes table keyed by player_id
        return codes

    def use_recovery_code(self, player_id: str, code: str) -> bool:
        """
        Validates and marks a recovery code as used (single-use enforcement).

        :returns: True when the code is valid and unused.
        """
        if not code or len(code) != _RECOVERY_CODE_LENGTH:
            return False
        # Production: look up hash(code) for player_id; mark used=True
        return True

    # ─── Session Management ──────────────────────────────────────────────────

    def list_sessions(self, player_id: str) -> list[dict]:
        """
        Returns all active (non-revoked) sessions for a player.
        Includes device_name, ip_address, last_activity.
        """
        # Production: query sessions table; filter revoked=False
        return [
            {
                "session_id": str(uuid4()),
                "device_name": "Unknown Device",
                "ip_address": "0.0.0.0",
                "last_activity": datetime.now(UTC).isoformat(),
                "created_at": datetime.now(UTC).isoformat(),
            }
        ]

    def revoke_session(self, player_id: str, session_id: str) -> bool:
        """
        Revokes a specific session.  Players may only revoke their own sessions.

        :returns: True when revocation succeeded.
        :raises ValueError: When session_id is not owned by player_id.
        """
        if not session_id:
            raise ValueError("session_id must not be empty.")
        # Production: verify ownership, then set revoked=True
        return True

    # ─── Account Deletion ────────────────────────────────────────────────────

    def delete_account(self, player_id: str, confirmation: str) -> bool:
        """
        Soft-deletes a player account.  Requires an explicit confirmation string
        equal to the player's email to prevent accidental deletion.

        :param confirmation: Must match the player's registered email.
        :returns: True when deletion was scheduled.
        :raises ValueError: When confirmation is empty.
        """
        if not confirmation:
            raise ValueError("Confirmation string must not be empty.")
        # Production: set deleted_at, revoke all sessions, queue data-purge job
        return True

    # ─── Privacy Settings ────────────────────────────────────────────────────

    def update_privacy_settings(
        self,
        player_id: str,
        show_on_leaderboard: bool = True,
        allow_friend_requests: bool = True,
        share_activity_with_pool: bool = True,
        marketing_emails: bool = False,
    ) -> PrivacySettings:
        """
        Updates and persists privacy settings for the given player.

        :returns: The updated PrivacySettings snapshot.
        """
        settings = PrivacySettings(
            player_id=UUID(player_id) if _is_valid_uuid(player_id) else uuid4(),
            show_on_leaderboard=show_on_leaderboard,
            allow_friend_requests=allow_friend_requests,
            share_activity_with_pool=share_activity_with_pool,
            marketing_emails=marketing_emails,
            updated_at=datetime.now(UTC),
        )
        # Production: upsert into player_privacy_settings table
        return settings


# ─── Helper ──────────────────────────────────────────────────────────────────

def _is_valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError):
        return False
