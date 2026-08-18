"""Dataclasses for the patcher domain — PatchManifest and PatchFile."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PatchFile:
    """Represents a single file entry inside a PatchManifest."""

    path: str
    """Relative path within the install directory (e.g. 'gmn_client.exe')."""

    sha256: str
    """Hex SHA-256 of the full file."""

    size_bytes: int
    """Size of the full file in bytes."""

    delta_from_version: Optional[str] = None
    """If set, a binary delta is available from this source version."""

    delta_sha256: Optional[str] = None
    """Hex SHA-256 of the binary delta file."""

    delta_size_bytes: Optional[int] = None
    """Size of the binary delta file in bytes."""


@dataclass(frozen=True)
class PatchManifest:
    """
    Describes a complete set of files for one game version.

    The manifest is served from {channel_url}/manifest.json.
    Clients compare ``version`` against the locally installed version and
    download only when a newer one is available.
    """

    version: str
    """Semantic version string, e.g. '0.1.1'."""

    release_date: str
    """ISO-8601 UTC release timestamp, e.g. '2026-08-18T10:00:00Z'."""

    channel: str
    """Release channel: 'stable', 'beta', 'experimental' or 'internal'."""

    files: list[PatchFile] = field(default_factory=list)
    """Ordered list of all files included in this release."""

    signature: Optional[str] = None
    """Base-64 encoded release signature (signed by the release key). Optional in dev."""
