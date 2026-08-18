from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app
from api.v1.economy import _experiment_service


class EconomyApiTests(unittest.TestCase):
    def test_public_parameters_endpoint_is_accessible(self) -> None:
        client = TestClient(app)
        response = client.get("/api/v1/economy/parameters")
        self.assertEqual(response.status_code, 200)
        self.assertIn("difficulty_base", response.json())

    def test_analysis_endpoint_returns_cached_shape(self) -> None:
        client = TestClient(app)
        response = client.get("/api/v1/economy/analysis")
        self.assertEqual(response.status_code, 200)
        self.assertIn("inflation_rate_percent", response.json())

    @patch.dict("os.environ", {"MAINTENANCE_AUTH_TOKEN": "token-value"}, clear=False)
    def test_admin_history_requires_token(self) -> None:
        client = TestClient(app)
        denied = client.get("/api/v1/admin/economy/parameters/history")
        self.assertEqual(denied.status_code, 403)

        allowed = client.get(
            "/api/v1/admin/economy/parameters/history",
            headers={"X-Maintenance-Token": "local-maintenance-token"},
        )
        self.assertEqual(allowed.status_code, 200)

    def test_active_experiments_endpoint_lists_active(self) -> None:
        exp_id = _experiment_service.create_experiment("api-test", {"difficulty_base": "1.1"}, {"difficulty_base": "1.0"}, 2)
        client = TestClient(app)
        response = client.get("/api/v1/economy/experiments/active")
        self.assertEqual(response.status_code, 200)
        ids = [item["experiment_id"] for item in response.json()["experiments"]]
        self.assertIn(exp_id, ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
