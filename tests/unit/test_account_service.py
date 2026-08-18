"""Unit tests for AccountService — account creation, email verification,
password recovery, recovery codes, session management and privacy settings."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.auth.account_service import AccountService, _RECOVERY_CODE_COUNT, _RECOVERY_CODE_LENGTH


class TestEmailVerification(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AccountService()

    def test_request_returns_non_empty_token(self) -> None:
        token = self.service.request_email_verification("player_test")
        self.assertTrue(len(token) > 0)

    def test_verify_email_returns_true_for_valid_token(self) -> None:
        token = self.service.request_email_verification("player_test")
        result = self.service.verify_email("player_test", token)
        self.assertTrue(result)

    def test_verify_email_returns_false_for_empty_token(self) -> None:
        result = self.service.verify_email("player_test", "")
        self.assertFalse(result)


class TestPasswordRecovery(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AccountService()

    def test_recovery_request_returns_token(self) -> None:
        token = self.service.password_recovery_request("player@example.invalid")
        self.assertTrue(len(token) > 0)

    def test_recovery_confirm_succeeds_with_valid_token_and_password(self) -> None:
        token = self.service.password_recovery_request("player@example.invalid")
        result = self.service.password_recovery_confirm(token, "NewStrongPassword1!")
        self.assertTrue(result)

    def test_recovery_confirm_raises_for_short_password(self) -> None:
        token = self.service.password_recovery_request("player@example.invalid")
        with self.assertRaises(ValueError):
            self.service.password_recovery_confirm(token, "short")

    def test_recovery_confirm_returns_false_for_empty_token(self) -> None:
        result = self.service.password_recovery_confirm("", "ValidPassword1!")
        self.assertFalse(result)


class TestRecoveryCodes(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AccountService()

    def test_generates_correct_number_of_codes(self) -> None:
        codes = self.service.generate_recovery_codes(str(uuid4()))
        self.assertEqual(len(codes), _RECOVERY_CODE_COUNT)

    def test_codes_have_correct_length(self) -> None:
        codes = self.service.generate_recovery_codes(str(uuid4()))
        for code in codes:
            self.assertEqual(len(code), _RECOVERY_CODE_LENGTH, f"Code '{code}' has wrong length")

    def test_codes_are_uppercase_alphanumeric(self) -> None:
        codes = self.service.generate_recovery_codes(str(uuid4()))
        for code in codes:
            self.assertTrue(code.isalnum(), f"Code '{code}' contains non-alphanumeric characters")
            self.assertTrue(code.isupper(), f"Code '{code}' is not uppercase")

    def test_codes_are_unique(self) -> None:
        codes = self.service.generate_recovery_codes(str(uuid4()))
        self.assertEqual(len(set(codes)), _RECOVERY_CODE_COUNT, "Duplicate recovery codes generated")

    def test_use_recovery_code_returns_true_for_valid_format(self) -> None:
        codes = self.service.generate_recovery_codes(str(uuid4()))
        result = self.service.use_recovery_code(str(uuid4()), codes[0])
        self.assertTrue(result)

    def test_use_recovery_code_returns_false_for_invalid_format(self) -> None:
        result = self.service.use_recovery_code(str(uuid4()), "short")
        self.assertFalse(result)

    def test_use_recovery_code_returns_false_for_empty_code(self) -> None:
        result = self.service.use_recovery_code(str(uuid4()), "")
        self.assertFalse(result)


class TestSessionManagement(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AccountService()

    def test_list_sessions_returns_list(self) -> None:
        sessions = self.service.list_sessions(str(uuid4()))
        self.assertIsInstance(sessions, list)

    def test_list_sessions_entries_have_required_fields(self) -> None:
        sessions = self.service.list_sessions(str(uuid4()))
        for s in sessions:
            self.assertIn("session_id", s)
            self.assertIn("device_name", s)
            self.assertIn("ip_address", s)
            self.assertIn("last_activity", s)

    def test_revoke_session_returns_true(self) -> None:
        result = self.service.revoke_session(str(uuid4()), str(uuid4()))
        self.assertTrue(result)

    def test_revoke_session_raises_for_empty_session_id(self) -> None:
        with self.assertRaises(ValueError):
            self.service.revoke_session(str(uuid4()), "")


class TestDeleteAccount(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AccountService()

    def test_delete_returns_true_with_confirmation(self) -> None:
        result = self.service.delete_account(str(uuid4()), "player@example.invalid")
        self.assertTrue(result)

    def test_delete_raises_for_empty_confirmation(self) -> None:
        with self.assertRaises(ValueError):
            self.service.delete_account(str(uuid4()), "")


class TestPrivacySettings(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AccountService()

    def test_update_returns_privacy_settings_object(self) -> None:
        from domain.auth.models import PrivacySettings
        result = self.service.update_privacy_settings(str(uuid4()))
        self.assertIsInstance(result, PrivacySettings)

    def test_update_persists_supplied_values(self) -> None:
        player_id = str(uuid4())
        result = self.service.update_privacy_settings(
            player_id,
            show_on_leaderboard=False,
            allow_friend_requests=False,
            share_activity_with_pool=False,
            marketing_emails=True,
        )
        self.assertFalse(result.show_on_leaderboard)
        self.assertFalse(result.allow_friend_requests)
        self.assertFalse(result.share_activity_with_pool)
        self.assertTrue(result.marketing_emails)

    def test_update_default_values(self) -> None:
        result = self.service.update_privacy_settings(str(uuid4()))
        self.assertTrue(result.show_on_leaderboard)
        self.assertTrue(result.allow_friend_requests)
        self.assertTrue(result.share_activity_with_pool)
        self.assertFalse(result.marketing_emails)

    def test_update_sets_updated_at_timestamp(self) -> None:
        result = self.service.update_privacy_settings(str(uuid4()))
        self.assertIsNotNone(result.updated_at)


if __name__ == "__main__":
    unittest.main()
