from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app


class GenesisApiTests(unittest.TestCase):
    @patch("app.main.get_genesis_service")
    @patch("api.v1.blockchain._genesis_service.get_status_payload")
    def test_genesis_status_endpoint_returns_service_payload(
        self,
        mock_status_payload: object,
        mock_startup_service: object,
    ) -> None:
        mock_startup_service.return_value.initialize_runtime.return_value = {"status": "pre-genesis"}
        mock_status_payload.return_value = {"status": "genesis-created", "ready": True, "checks": [], "genesis": None}
        client = TestClient(app)
        response = client.get("/api/v1/blockchain/genesis/status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "genesis-created")

    @patch("app.main.get_genesis_service")
    @patch("api.v1.blockchain._genesis_service.get_current_genesis_block", return_value=None)
    def test_genesis_details_endpoint_returns_404_when_missing(
        self,
        _mock_current: object,
        mock_startup_service: object,
    ) -> None:
        mock_startup_service.return_value.initialize_runtime.return_value = {"status": "pre-genesis"}
        client = TestClient(app)
        response = client.get("/api/v1/blockchain/genesis")
        self.assertEqual(response.status_code, 404)

    @patch("api.v1.admin.genesis_service.create_genesis_block", return_value="genesis-1")
    @patch("api.v1.admin.genesis_service.get_genesis_block")
    @patch("api.v1.admin.genesis_service.serialize_genesis_block", return_value={"genesis_id": "genesis-1"})
    @patch("api.v1.admin.service.verify_password", return_value=True)
    @patch("api.v1.admin.verify_totp_code", return_value=True)
    @patch("api.v1.admin.service.get_roles", return_value={"admin"})
    @patch("app.main.get_genesis_service")
    def test_admin_can_create_genesis_via_launch_endpoint(
        self,
        mock_startup_service: object,
        _mock_roles: object,
        _mock_totp: object,
        _mock_password: object,
        _mock_serialize: object,
        mock_get_genesis_block: object,
        _mock_create: object,
    ) -> None:
        mock_startup_service.return_value.initialize_runtime.return_value = {"status": "pre-genesis"}
        mock_get_genesis_block.return_value = object()
        with patch.dict("os.environ", {"ADMIN_TOTP_SECRET": "test-secret"}, clear=False):
            client = TestClient(app)
            response = client.post(
                "/api/v1/admin/launch/genesis",
                headers={
                    "X-Admin-Id": "admin-a",
                    "X-Admin-Password": "pw",
                    "X-Admin-2FA-Code": "123456",
                },
                json={
                    "starting_balance": "1000.000000",
                    "player_snapshot": [{"player_id": "player-a"}],
                    "tier_assignments": {"player-a": 1},
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
