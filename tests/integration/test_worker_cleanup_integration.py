from __future__ import annotations

import importlib.util
import json
import socketserver
import sys
import tempfile
import threading
import types
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKER_ROOT = ROOT / "workers"
WORKER_MODULE_PATH = WORKER_ROOT / "app" / "worker.py"

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))


class _MockSettings:
    maintenance_auth_header = "X-Maintenance-Token"
    maintenance_auth_token = "env-token"
    maintenance_auth_token_file = ""
    blockchain_event_retention_seconds = 86400
    blockchain_checkpoint_retention_seconds = 604800
    blockchain_max_network_events = 100000
    blockchain_cleanup_timeout_seconds = 5
    api_base_url = "http://127.0.0.1:0"
    api_v1_prefix = "/api/v1"
    environment = "test"
    blockchain_cleanup_enabled = True
    blockchain_cleanup_interval_seconds = 300
    blockchain_cleanup_backoff_max_seconds = 1800


_mock_app_module = types.ModuleType("app")
_mock_database_module = types.ModuleType("app.database")
_mock_settings_module = types.ModuleType("app.settings")
_mock_database_module.database_is_configured = lambda: True
_mock_settings_module.settings = _MockSettings()

_original_app_module = sys.modules.get("app")
_original_app_database_module = sys.modules.get("app.database")
_original_app_settings_module = sys.modules.get("app.settings")

sys.modules["app"] = _mock_app_module
sys.modules["app.database"] = _mock_database_module
sys.modules["app.settings"] = _mock_settings_module

_worker_spec = importlib.util.spec_from_file_location("gmn_worker_module_integration", WORKER_MODULE_PATH)
if _worker_spec is None or _worker_spec.loader is None:
    raise RuntimeError("Unable to load worker module for integration tests")
_worker_module = importlib.util.module_from_spec(_worker_spec)
_worker_spec.loader.exec_module(_worker_module)

if _original_app_module is None:
    del sys.modules["app"]
else:
    sys.modules["app"] = _original_app_module

if _original_app_database_module is None:
    del sys.modules["app.database"]
else:
    sys.modules["app.database"] = _original_app_database_module

if _original_app_settings_module is None:
    del sys.modules["app.settings"]
else:
    sys.modules["app.settings"] = _original_app_settings_module


class _ThreadingHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True


class _CleanupHandler(BaseHTTPRequestHandler):
    expected_header = "X-Maintenance-Token"
    received_token = ""
    received_path = ""

    def do_POST(self) -> None:  # noqa: N802
        _CleanupHandler.received_token = self.headers.get(_CleanupHandler.expected_header, "")
        _CleanupHandler.received_path = self.path
        body = json.dumps(
            {
                "deleted_network_events_by_age": 3,
                "deleted_network_events_by_count": 2,
                "deleted_client_checkpoints": 1,
            }
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class WorkerCleanupIntegrationTests(unittest.TestCase):
    def _run_cleanup_with_server(
        self,
        *,
        token_file_path: str,
        env_token: str = "env-token",
    ) -> tuple[dict[str, int], str, str]:
        server = _ThreadingHTTPServer(("127.0.0.1", 0), _CleanupHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        settings = _worker_module.settings
        snapshot = {
            "api_base_url": settings.api_base_url,
            "api_v1_prefix": settings.api_v1_prefix,
            "maintenance_auth_header": settings.maintenance_auth_header,
            "maintenance_auth_token": settings.maintenance_auth_token,
            "maintenance_auth_token_file": settings.maintenance_auth_token_file,
            "blockchain_event_retention_seconds": settings.blockchain_event_retention_seconds,
            "blockchain_checkpoint_retention_seconds": settings.blockchain_checkpoint_retention_seconds,
            "blockchain_max_network_events": settings.blockchain_max_network_events,
            "blockchain_cleanup_timeout_seconds": settings.blockchain_cleanup_timeout_seconds,
        }

        try:
            _CleanupHandler.expected_header = "X-Maintenance-Token"
            _CleanupHandler.received_token = ""
            _CleanupHandler.received_path = ""

            settings.api_base_url = f"http://127.0.0.1:{server.server_address[1]}"
            settings.api_v1_prefix = "/api/v1"
            settings.maintenance_auth_header = "X-Maintenance-Token"
            settings.maintenance_auth_token = env_token
            settings.maintenance_auth_token_file = token_file_path
            settings.blockchain_event_retention_seconds = 3600
            settings.blockchain_checkpoint_retention_seconds = 7200
            settings.blockchain_max_network_events = 50
            settings.blockchain_cleanup_timeout_seconds = 5

            result = _worker_module._run_cleanup_once()
            received_token = _CleanupHandler.received_token
            received_path = _CleanupHandler.received_path
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

            settings.api_base_url = snapshot["api_base_url"]
            settings.api_v1_prefix = snapshot["api_v1_prefix"]
            settings.maintenance_auth_header = snapshot["maintenance_auth_header"]
            settings.maintenance_auth_token = snapshot["maintenance_auth_token"]
            settings.maintenance_auth_token_file = snapshot["maintenance_auth_token_file"]
            settings.blockchain_event_retention_seconds = snapshot["blockchain_event_retention_seconds"]
            settings.blockchain_checkpoint_retention_seconds = snapshot["blockchain_checkpoint_retention_seconds"]
            settings.blockchain_max_network_events = snapshot["blockchain_max_network_events"]
            settings.blockchain_cleanup_timeout_seconds = snapshot["blockchain_cleanup_timeout_seconds"]

        return result, received_token, received_path

    def test_run_cleanup_once_uses_file_mounted_token_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            secret_dir = Path(temp_dir) / "run" / "secrets"
            secret_dir.mkdir(parents=True, exist_ok=True)
            token_file = secret_dir / "maintenance_token"
            token_file.write_text("file-mounted-token\n", encoding="utf-8")

            result, received_token, received_path = self._run_cleanup_with_server(
                token_file_path=str(token_file)
            )

        self.assertEqual(result["deleted_network_events_by_age"], 3)
        self.assertEqual(result["deleted_network_events_by_count"], 2)
        self.assertEqual(result["deleted_client_checkpoints"], 1)
        self.assertEqual(received_token, "file-mounted-token")
        self.assertIn("/api/v1/blockchain/maintenance/cleanup", received_path)
        self.assertIn("event_retention_seconds=3600", received_path)
        self.assertIn("checkpoint_retention_seconds=7200", received_path)
        self.assertIn("max_network_events=50", received_path)

    def test_run_cleanup_once_falls_back_to_env_token_when_token_file_unreadable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            unreadable_path = Path(temp_dir) / "run" / "secrets" / "missing_token"
            result, received_token, received_path = self._run_cleanup_with_server(
                token_file_path=str(unreadable_path),
                env_token="env-fallback-token",
            )

        self.assertEqual(result["deleted_network_events_by_age"], 3)
        self.assertEqual(result["deleted_network_events_by_count"], 2)
        self.assertEqual(result["deleted_client_checkpoints"], 1)
        self.assertEqual(received_token, "env-fallback-token")
        self.assertIn("/api/v1/blockchain/maintenance/cleanup", received_path)

    def test_run_cleanup_once_falls_back_to_env_token_when_token_file_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            secret_dir = Path(temp_dir) / "run" / "secrets"
            secret_dir.mkdir(parents=True, exist_ok=True)
            token_file = secret_dir / "maintenance_token"
            token_file.write_text("\n", encoding="utf-8")

            result, received_token, received_path = self._run_cleanup_with_server(
                token_file_path=str(token_file),
                env_token="env-fallback-token",
            )

        self.assertEqual(result["deleted_network_events_by_age"], 3)
        self.assertEqual(result["deleted_network_events_by_count"], 2)
        self.assertEqual(result["deleted_client_checkpoints"], 1)
        self.assertEqual(received_token, "env-fallback-token")
        self.assertIn("/api/v1/blockchain/maintenance/cleanup", received_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)