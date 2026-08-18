from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.content.service import ContentService
from tests.unit.test_content_validator import VALID_CONTENT_PACK


class ContentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ContentService(signing_secret="test-signing-secret")

    def _stage_version(self, *, impact_notes: str = "No major economy disruption expected.") -> str:
        payload = copy.deepcopy(VALID_CONTENT_PACK)
        payload["content_pack_name"] = "starter"
        payload["author_id"] = "backend-bot"
        return self.service.stage_content_version(payload, impact_notes)

    def test_stage_content_version_records_version_metadata_and_signature(self) -> None:
        version_id = self._stage_version()

        version = self.service.get_version(version_id)

        self.assertEqual(version.version_number, 1)
        self.assertEqual(version.content_pack_name, "starter")
        self.assertEqual(version.author_id, "backend-bot")
        self.assertEqual(version.status, "draft")
        self.assertTrue(version.signature)
        self.assertTrue(version.schema_hash)

    def test_stage_content_version_requires_impact_notes(self) -> None:
        with self.assertRaises(ValueError):
            self._stage_version(impact_notes="")

    def test_service_requires_configured_signing_secret_outside_local_and_test(self) -> None:
        with patch.dict("os.environ", {"ENVIRONMENT": "production", "CONTENT_SIGNING_SECRET": ""}, clear=False):
            with patch("domain.content.service.settings.environment", "production"):
                with self.assertRaises(ValueError):
                    ContentService()

    def test_activate_content_requires_review_board_approval(self) -> None:
        version_id = self._stage_version()
        self.service.request_review(version_id)
        self.service.approve_for_rollout(version_id, "design", "Looks good.")
        self.service.approve_for_rollout(version_id, "backend", "Schema is valid.")

        with self.assertRaises(PermissionError):
            self.service.activate_content(version_id, "canary")

    def test_activate_content_only_updates_requested_rollout_stage(self) -> None:
        version_id = self._stage_version()
        self.service.request_review(version_id)
        self.service.approve_for_rollout(version_id, "design", "Looks good.")
        self.service.approve_for_rollout(version_id, "backend", "Schema is valid.")
        self.service.approve_for_rollout(version_id, "liveops", "Canary approved.")

        version = self.service.activate_content(version_id, "canary")

        self.assertEqual(version.status, "canary")
        self.assertEqual(version.active_rollout_stages, ["canary"])
        self.assertEqual(self.service.get_active_version("canary").version_id, version_id)
        self.assertIsNone(self.service.get_active_version("global"))

    def test_rollback_content_repoints_all_active_stages_atomically(self) -> None:
        first_version_id = self._stage_version()
        self.service.request_review(first_version_id)
        self.service.approve_for_rollout(first_version_id, "design", "Approved.")
        self.service.approve_for_rollout(first_version_id, "backend", "Approved.")
        self.service.approve_for_rollout(first_version_id, "liveops", "Approved.")
        self.service.activate_content(first_version_id, "internal")
        self.service.activate_content(first_version_id, "global")

        second_payload = copy.deepcopy(VALID_CONTENT_PACK)
        second_payload["content_pack_name"] = "starter"
        second_payload["author_id"] = "backend-bot"
        second_payload["hardware"][1]["cost"] = 2200
        second_payload["metadata"] = {"data_only_hotfix": True, "reason": "Reduce mid-tier hardware inflation"}
        second_version_id = self.service.stage_content_version(
            second_payload,
            "Reduces garage rig cost to soften early-game progression friction.",
        )
        self.service.request_review(second_version_id)
        self.service.approve_for_rollout(second_version_id, "design", "Approved.")
        self.service.approve_for_rollout(second_version_id, "backend", "Approved.")
        self.service.approve_for_rollout(second_version_id, "liveops", "Approved.")
        self.service.activate_content(second_version_id, "internal")
        self.service.activate_content(second_version_id, "global")

        rolled_back = self.service.rollback_content(first_version_id)

        self.assertEqual(rolled_back.version_id, first_version_id)
        self.assertEqual(self.service.get_active_version("internal").version_id, first_version_id)
        self.assertEqual(self.service.get_active_version("global").version_id, first_version_id)
        self.assertEqual(self.service.get_version(second_version_id).status, "rolled_back")


if __name__ == "__main__":
    unittest.main()
