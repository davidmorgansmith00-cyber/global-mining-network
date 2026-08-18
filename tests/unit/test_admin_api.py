from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app.main import app
from api.v1.admin import _require_role


class AdminApiTests(unittest.TestCase):
    @patch("api.v1.admin.service.get_roles", return_value={"analyst"})
    def test_require_role_blocks_unauthorized_role(self, _mock_roles: object) -> None:
        class _Req:
            headers = {"X-Admin-Id": "admin-a"}

        with self.assertRaises(HTTPException) as context:
            _require_role(_Req(), {"admin"})  # type: ignore[arg-type]
        self.assertEqual(context.exception.status_code, 403)

    @patch("api.v1.admin.service.get_roles", return_value={"admin"})
    @patch("api.v1.admin.service.get_dashboard_metrics", return_value={"active_players": 5})
    def test_dashboard_endpoint_allows_admin(self, _mock_dashboard: object, _mock_roles: object) -> None:
        client = TestClient(app)
        response = client.get("/api/v1/admin/dashboard", headers={"X-Admin-Id": "admin-a"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["active_players"], 5)

    @patch("api.v1.admin.service.get_roles", return_value={"analyst"})
    def test_admin_config_requires_admin_role(self, _mock_roles: object) -> None:
        client = TestClient(app)
        response = client.get("/api/v1/admin/config", headers={"X-Admin-Id": "analyst-a"})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
