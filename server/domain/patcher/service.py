"""PatcherService — server-side manifest generation, checksum validation, delta logic."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

from domain.patcher.models import PatchFile, PatchManifest


class PatcherService:
    """
    Server-side service responsible for:

    * ``generate_manifest``  — build a PatchManifest from a release directory
    * ``generate_delta``     — record delta metadata between two versions
    * ``verify_manifest``    — re-check all checksums against the manifest
    """

    # ─── Public API ─────────────────────────────────────────────────────────

    def generate_manifest(
        self,
        release_dir: Path,
        version: str,
        channel: str,
        release_date: Optional[str] = None,
    ) -> PatchManifest:
        """
        Walks ``release_dir`` and builds a PatchManifest by computing SHA-256
        checksums for every file found.

        :param release_dir: Root directory of the release build.
        :param version:     Semantic version string (e.g. '0.1.1').
        :param channel:     Target channel (e.g. 'stable').
        :param release_date: ISO-8601 string; defaults to UTC now.
        :returns: A fully populated PatchManifest.
        :raises FileNotFoundError: When ``release_dir`` does not exist.
        """
        if not release_dir.exists():
            raise FileNotFoundError(f"Release directory not found: {release_dir}")

        if not release_date:
            release_date = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

        files: list[PatchFile] = []
        for file_path in sorted(release_dir.rglob("*")):
            if not file_path.is_file():
                continue
            rel_path = file_path.relative_to(release_dir).as_posix()
            sha256 = self._sha256(file_path)
            size = file_path.stat().st_size
            files.append(PatchFile(path=rel_path, sha256=sha256, size_bytes=size))

        return PatchManifest(
            version=version,
            release_date=release_date,
            channel=channel,
            files=files,
        )

    def generate_delta(
        self,
        manifest: PatchManifest,
        delta_from_version: str,
        deltas: dict[str, tuple[str, int]],
    ) -> PatchManifest:
        """
        Returns a new PatchManifest with delta metadata applied to matching file entries.

        :param manifest:           Base manifest to annotate with delta info.
        :param delta_from_version: The source version for the delta (e.g. '0.1.0').
        :param deltas:             Mapping of file_path → (delta_sha256, delta_size_bytes)
                                   for files that have a delta available.
        :returns: Updated PatchManifest with delta fields populated.
        """
        updated_files: list[PatchFile] = []
        for pf in manifest.files:
            if pf.path in deltas:
                delta_sha256, delta_size = deltas[pf.path]
                updated_files.append(
                    PatchFile(
                        path=pf.path,
                        sha256=pf.sha256,
                        size_bytes=pf.size_bytes,
                        delta_from_version=delta_from_version,
                        delta_sha256=delta_sha256,
                        delta_size_bytes=delta_size,
                    )
                )
            else:
                updated_files.append(pf)

        return PatchManifest(
            version=manifest.version,
            release_date=manifest.release_date,
            channel=manifest.channel,
            files=updated_files,
            signature=manifest.signature,
        )

    def verify_manifest(
        self,
        manifest: PatchManifest,
        release_dir: Path,
    ) -> dict[str, bool]:
        """
        Re-computes SHA-256 for each file in ``release_dir`` and compares against
        the manifest.

        :returns: Dict mapping file path → True if checksum matches, False otherwise.
        :raises FileNotFoundError: When ``release_dir`` does not exist.
        """
        if not release_dir.exists():
            raise FileNotFoundError(f"Release directory not found: {release_dir}")

        results: dict[str, bool] = {}
        for pf in manifest.files:
            file_path = release_dir / pf.path
            if not file_path.exists():
                results[pf.path] = False
                continue
            actual = self._sha256(file_path)
            results[pf.path] = actual == pf.sha256.lower()

        return results

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
