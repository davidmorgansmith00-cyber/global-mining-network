from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from app.main import app


class DocsApiTests(unittest.TestCase):
    def test_categories_endpoint_returns_known_category(self) -> None:
        client = TestClient(app)
        response = client.get("/api/v1/docs/categories")
        self.assertEqual(response.status_code, 200)
        self.assertIn("faq", response.json()["categories"])

    def test_search_endpoint_finds_launch_docs(self) -> None:
        client = TestClient(app)
        response = client.get("/api/v1/docs/search", params={"q": "genesis"})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()["results"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
