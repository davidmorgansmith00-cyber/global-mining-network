from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKER_ROOT = ROOT / "workers"
WORKER_MODULE_PATH = WORKER_ROOT / "app" / "worker.py"

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

# Ensure worker-local imports resolve even when server `app` package is already loaded.
_mock_app_module = types.ModuleType("app")
_mock_database_module = types.ModuleType("app.database")
_mock_settings_module = types.ModuleType("app.settings")


def _mock_database_is_configured() -> bool:
    return True


class _MockSettings:
    maintenance_auth_header = "X-Maintenance-Token"
    maintenance_auth_token = "local-maintenance-token"
    maintenance_auth_token_file = ""
    blockchain_event_retention_seconds = 86400
    blockchain_checkpoint_retention_seconds = 604800
    blockchain_max_network_events = 100000
    blockchain_cleanup_timeout_seconds = 10
    api_base_url = "http://api:8000"
    api_v1_prefix = "/api/v1"
    environment = "test"
    blockchain_cleanup_enabled = True
    blockchain_cleanup_interval_seconds = 300
    blockchain_cleanup_backoff_max_seconds = 1800


_mock_database_module.database_is_configured = _mock_database_is_configured
_mock_settings_module.settings = _MockSettings()

_original_app_module = sys.modules.get("app")
_original_app_database_module = sys.modules.get("app.database")
_original_app_settings_module = sys.modules.get("app.settings")

sys.modules["app"] = _mock_app_module
sys.modules["app.database"] = _mock_database_module
sys.modules["app.settings"] = _mock_settings_module

_worker_spec = importlib.util.spec_from_file_location("gmn_worker_module", WORKER_MODULE_PATH)
if _worker_spec is None or _worker_spec.loader is None:
    raise RuntimeError("Unable to load worker module for tests")
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

_compute_sleep_seconds = _worker_module._compute_sleep_seconds
_compute_startup_jitter_seconds = _worker_module._compute_startup_jitter_seconds
_maintenance_token_source_mode = _worker_module._maintenance_token_source_mode
_resolve_maintenance_auth_token = _worker_module._resolve_maintenance_auth_token
_should_warn_missing_maintenance_token = _worker_module._should_warn_missing_maintenance_token


class WorkerCleanupBackoffTests(unittest.TestCase):
    def test_should_warn_missing_token_non_local_when_both_sources_empty(self) -> None:
        should_warn = _should_warn_missing_maintenance_token(
            environment="staging",
            token_file_path="",
            fallback_token="",
        )
        self.assertTrue(should_warn)

    def test_should_not_warn_missing_token_in_local_environment(self) -> None:
        should_warn = _should_warn_missing_maintenance_token(
            environment="local",
            token_file_path="",
            fallback_token="",
        )
        self.assertFalse(should_warn)

    def test_should_not_warn_when_file_source_is_configured(self) -> None:
        should_warn = _should_warn_missing_maintenance_token(
            environment="production",
            token_file_path="/run/secrets/maintenance_token",
            fallback_token="",
        )
        self.assertFalse(should_warn)

    def test_should_not_warn_when_env_token_is_configured(self) -> None:
        should_warn = _should_warn_missing_maintenance_token(
            environment="production",
            token_file_path="",
            fallback_token="env-token",
        )
        self.assertFalse(should_warn)

    def test_maintenance_token_source_mode_file(self) -> None:
        mode = _maintenance_token_source_mode(token_file_path="/run/secrets/maintenance_token")
        self.assertEqual(mode, "file")

    def test_maintenance_token_source_mode_env(self) -> None:
        mode = _maintenance_token_source_mode(token_file_path="")
        self.assertEqual(mode, "env")

    def test_resolve_maintenance_token_prefers_file_value(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as handle:
            handle.write("file-secret-token\n")
            file_path = handle.name
        try:
            resolved = _resolve_maintenance_auth_token(
                token_file_path=file_path,
                fallback_token="env-token",
            )
            self.assertEqual(resolved, "file-secret-token")
        finally:
            os.unlink(file_path)

    def test_resolve_maintenance_token_falls_back_to_env_token(self) -> None:
        resolved = _resolve_maintenance_auth_token(
            token_file_path="",
            fallback_token="env-token",
        )
        self.assertEqual(resolved, "env-token")

    def test_resolve_maintenance_token_uses_fallback_when_file_missing(self) -> None:
        resolved = _resolve_maintenance_auth_token(
            token_file_path="C:/nonexistent/gmn/token.txt",
            fallback_token="env-token",
        )
        self.assertEqual(resolved, "env-token")

    def test_startup_jitter_defaults_to_zero_when_disabled(self) -> None:
        self.assertEqual(
            _compute_startup_jitter_seconds(max_jitter_seconds=0, random_fraction=0.8),
            0,
        )

    def test_startup_jitter_scales_with_fraction(self) -> None:
        self.assertEqual(
            _compute_startup_jitter_seconds(max_jitter_seconds=10, random_fraction=0.0),
            0,
        )
        self.assertEqual(
            _compute_startup_jitter_seconds(max_jitter_seconds=10, random_fraction=0.5),
            5,
        )
        self.assertEqual(
            _compute_startup_jitter_seconds(max_jitter_seconds=10, random_fraction=1.0),
            10,
        )

    def test_startup_jitter_fraction_is_bounded(self) -> None:
        self.assertEqual(
            _compute_startup_jitter_seconds(max_jitter_seconds=10, random_fraction=-0.2),
            0,
        )
        self.assertEqual(
            _compute_startup_jitter_seconds(max_jitter_seconds=10, random_fraction=1.7),
            10,
        )

    def test_sleep_uses_base_interval_without_failures(self) -> None:
        self.assertEqual(
            _compute_sleep_seconds(
                elapsed_seconds=12.5,
                base_interval_seconds=300,
                consecutive_failures=0,
                backoff_max_seconds=1800,
            ),
            288,
        )

    def test_sleep_doubles_with_consecutive_failures(self) -> None:
        self.assertEqual(
            _compute_sleep_seconds(
                elapsed_seconds=0,
                base_interval_seconds=30,
                consecutive_failures=1,
                backoff_max_seconds=1800,
            ),
            30,
        )
        self.assertEqual(
            _compute_sleep_seconds(
                elapsed_seconds=0,
                base_interval_seconds=30,
                consecutive_failures=2,
                backoff_max_seconds=1800,
            ),
            60,
        )
        self.assertEqual(
            _compute_sleep_seconds(
                elapsed_seconds=0,
                base_interval_seconds=30,
                consecutive_failures=3,
                backoff_max_seconds=1800,
            ),
            120,
        )

    def test_sleep_caps_at_backoff_max(self) -> None:
        self.assertEqual(
            _compute_sleep_seconds(
                elapsed_seconds=0,
                base_interval_seconds=60,
                consecutive_failures=10,
                backoff_max_seconds=300,
            ),
            300,
        )

    def test_sleep_never_drops_below_one_second(self) -> None:
        self.assertEqual(
            _compute_sleep_seconds(
                elapsed_seconds=120,
                base_interval_seconds=60,
                consecutive_failures=1,
                backoff_max_seconds=300,
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
