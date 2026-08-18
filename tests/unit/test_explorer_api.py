from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from api.v1.explorer import get_block_details, get_block_history, search


class ExplorerApiTests(unittest.TestCase):
    @patch("api.v1.explorer.service.get_blocks")
    def test_get_block_history_returns_payload_with_pagination(self, mock_get_blocks: object) -> None:
        mock_get_blocks.return_value = [{"block_number": 10, "difficulty": "100.000000"}]
        response = get_block_history(limit=50, offset=0)
        self.assertEqual(response["limit"], 50)
        self.assertEqual(response["offset"], 0)
        self.assertEqual(response["items"][0]["block_number"], 10)

    @patch("api.v1.explorer.service.get_block_details")
    def test_get_block_details_raises_404_when_not_found(self, mock_get_block_details: object) -> None:
        mock_get_block_details.return_value = None
        with self.assertRaises(HTTPException) as context:
            get_block_details(block_number=99)
        self.assertEqual(context.exception.status_code, 404)

    @patch("api.v1.explorer.service.search")
    def test_search_returns_autocomplete_items(self, mock_search: object) -> None:
        mock_search.return_value = [{"type": "player", "id": "p1", "label": "p1@example.com"}]
        response = search("p1")
        self.assertEqual(len(response["items"]), 1)
        self.assertEqual(response["items"][0]["type"], "player")

    @patch("api.v1.explorer.service.get_block_details")
    def test_get_block_details_returns_genesis_payload_when_available(self, mock_get_block_details: object) -> None:
        mock_get_block_details.return_value = {"block_number": 1, "block_hash": "abc123", "chain_id": "chain"}
        response = get_block_details(block_number=1)
        self.assertEqual(response["block_number"], 1)
        self.assertEqual(response["block_hash"], "abc123")


if __name__ == "__main__":
    unittest.main(verbosity=2)
