"""Unit tests for PatcherService — manifest generation, checksum validation,
delta logic and rollback scenarios."""
from __future__ import annotations

import hashlib
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

from domain.patcher.models import PatchFile, PatchManifest
from domain.patcher.service import PatcherService


class TestPatcherServiceGenerateManifest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PatcherService()

    def test_raises_when_release_dir_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            self.service.generate_manifest(
                release_dir=Path("/nonexistent/path/gmn_release"),
                version="0.1.1",
                channel="stable",
            )

    def test_generates_manifest_with_correct_version_and_channel(self, tmp_path: Path = None) -> None:
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            release_dir = Path(tmpdir)
            (release_dir / "gmn_client.exe").write_bytes(b"fake_exe_content")
            manifest = self.service.generate_manifest(
                release_dir=release_dir,
                version="0.1.1",
                channel="stable",
            )
        self.assertEqual(manifest.version, "0.1.1")
        self.assertEqual(manifest.channel, "stable")
        self.assertIsNotNone(manifest.release_date)

    def test_manifest_contains_correct_file_checksum(self) -> None:
        import tempfile
        content = b"game_binary_data_v1"
        expected_hash = hashlib.sha256(content).hexdigest()

        with tempfile.TemporaryDirectory() as tmpdir:
            release_dir = Path(tmpdir)
            (release_dir / "gmn_client.exe").write_bytes(content)
            manifest = self.service.generate_manifest(
                release_dir=release_dir,
                version="0.1.1",
                channel="stable",
            )

        self.assertEqual(len(manifest.files), 1)
        self.assertEqual(manifest.files[0].sha256, expected_hash)
        self.assertEqual(manifest.files[0].path, "gmn_client.exe")
        self.assertEqual(manifest.files[0].size_bytes, len(content))

    def test_manifest_includes_all_files_recursively(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            release_dir = Path(tmpdir)
            (release_dir / "gmn_client.exe").write_bytes(b"exe")
            subdir = release_dir / "data"
            subdir.mkdir()
            (subdir / "config.json").write_bytes(b"{}")
            manifest = self.service.generate_manifest(
                release_dir=release_dir,
                version="0.1.1",
                channel="stable",
            )

        self.assertEqual(len(manifest.files), 2)
        paths = {f.path for f in manifest.files}
        self.assertIn("gmn_client.exe", paths)
        self.assertIn("data/config.json", paths)


class TestPatcherServiceGenerateDelta(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PatcherService()

    def test_adds_delta_metadata_to_matching_files(self) -> None:
        base = PatchManifest(
            version="0.1.1",
            release_date="2026-08-18T10:00:00Z",
            channel="stable",
            files=[
                PatchFile(path="gmn_client.exe", sha256="abc123", size_bytes=50_000_000),
                PatchFile(path="data/config.json", sha256="def456", size_bytes=1024),
            ],
        )
        deltas = {"gmn_client.exe": ("delta_sha256_xyz", 2_000_000)}

        result = self.service.generate_delta(base, "0.1.0", deltas)

        client_file = next(f for f in result.files if f.path == "gmn_client.exe")
        self.assertEqual(client_file.delta_from_version, "0.1.0")
        self.assertEqual(client_file.delta_sha256, "delta_sha256_xyz")
        self.assertEqual(client_file.delta_size_bytes, 2_000_000)

    def test_non_delta_files_are_unchanged(self) -> None:
        base = PatchManifest(
            version="0.1.1",
            release_date="2026-08-18T10:00:00Z",
            channel="stable",
            files=[
                PatchFile(path="gmn_client.exe", sha256="abc123", size_bytes=50_000_000),
                PatchFile(path="data/config.json", sha256="def456", size_bytes=1024),
            ],
        )
        result = self.service.generate_delta(base, "0.1.0", {})

        config_file = next(f for f in result.files if f.path == "data/config.json")
        self.assertIsNone(config_file.delta_from_version)
        self.assertIsNone(config_file.delta_sha256)


class TestPatcherServiceVerifyManifest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PatcherService()

    def test_verify_returns_true_for_matching_checksums(self) -> None:
        import tempfile
        content = b"correct_binary_content"
        expected_hash = hashlib.sha256(content).hexdigest()

        with tempfile.TemporaryDirectory() as tmpdir:
            release_dir = Path(tmpdir)
            (release_dir / "gmn_client.exe").write_bytes(content)
            manifest = PatchManifest(
                version="0.1.1",
                release_date="2026-08-18T10:00:00Z",
                channel="stable",
                files=[PatchFile(path="gmn_client.exe", sha256=expected_hash, size_bytes=len(content))],
            )
            results = self.service.verify_manifest(manifest, release_dir)

        self.assertTrue(results["gmn_client.exe"])

    def test_verify_returns_false_for_corrupted_file(self) -> None:
        import tempfile
        content = b"original_content"
        expected_hash = hashlib.sha256(content).hexdigest()

        with tempfile.TemporaryDirectory() as tmpdir:
            release_dir = Path(tmpdir)
            (release_dir / "gmn_client.exe").write_bytes(b"corrupted_content")
            manifest = PatchManifest(
                version="0.1.1",
                release_date="2026-08-18T10:00:00Z",
                channel="stable",
                files=[PatchFile(path="gmn_client.exe", sha256=expected_hash, size_bytes=len(content))],
            )
            results = self.service.verify_manifest(manifest, release_dir)

        self.assertFalse(results["gmn_client.exe"])

    def test_verify_returns_false_for_missing_file(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            release_dir = Path(tmpdir)
            manifest = PatchManifest(
                version="0.1.1",
                release_date="2026-08-18T10:00:00Z",
                channel="stable",
                files=[PatchFile(path="missing.exe", sha256="abc", size_bytes=100)],
            )
            results = self.service.verify_manifest(manifest, release_dir)

        self.assertFalse(results["missing.exe"])

    def test_verify_raises_when_directory_missing(self) -> None:
        manifest = PatchManifest(
            version="0.1.1",
            release_date="2026-08-18T10:00:00Z",
            channel="stable",
            files=[],
        )
        with self.assertRaises(FileNotFoundError):
            self.service.verify_manifest(manifest, Path("/nonexistent/release"))


if __name__ == "__main__":
    unittest.main()
