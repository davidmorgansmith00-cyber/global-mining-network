from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
import hashlib
import hmac
import json
import os
from typing import Any
from uuid import uuid4

from domain.content.validator import ContentValidator


REQUIRED_REVIEW_ROLES = ("design", "backend", "liveops")
ROLLOUT_STAGES = ("internal", "staging", "canary", "global")


@dataclass(frozen=True)
class ReviewApproval:
    approver_role: str
    approved_at: datetime
    comments: str


@dataclass
class ContentVersionRecord:
    version_id: str
    content_pack_name: str
    version_number: int
    created_at: datetime
    author_id: str
    status: str
    impact_notes: str
    schema_hash: str
    signature: str
    content_pack_data: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    approvals: list[ReviewApproval] = field(default_factory=list)
    active_rollout_stages: list[str] = field(default_factory=list)


class ContentService:
    def __init__(
        self,
        *,
        validator: ContentValidator | None = None,
        signing_secret: str | None = None,
    ) -> None:
        self._validator = validator or ContentValidator()
        self._signing_secret = signing_secret or os.getenv("CONTENT_SIGNING_SECRET", "local-content-signing-secret")
        self._versions: dict[str, ContentVersionRecord] = {}
        self._active_versions_by_stage: dict[str, str | None] = {stage: None for stage in ROLLOUT_STAGES}

    def stage_content_version(self, content_pack_data: dict[str, Any], impact_notes: str) -> str:
        normalized_pack = self._normalize_content_pack(content_pack_data)
        errors, warnings = self._validator.validate_content_pack(normalized_pack, impact_notes)
        if errors:
            raise ValueError("; ".join(errors))
        if warnings:
            raise ValueError("; ".join(warnings))

        content_pack_name = str(content_pack_data.get("content_pack_name") or "default").strip()
        author_id = str(content_pack_data.get("author_id") or "system").strip()
        metadata = deepcopy(content_pack_data.get("metadata", {}))
        version_number = self._next_version_number(content_pack_name)
        version_id = str(uuid4())
        created_at = datetime.now(UTC)
        schema_hash = self._compute_schema_hash()
        signature = self._sign_content_pack(
            content_pack_name=content_pack_name,
            version_number=version_number,
            impact_notes=impact_notes,
            content_pack_data=normalized_pack,
            metadata=metadata,
        )

        self._versions[version_id] = ContentVersionRecord(
            version_id=version_id,
            content_pack_name=content_pack_name,
            version_number=version_number,
            created_at=created_at,
            author_id=author_id,
            status="draft",
            impact_notes=impact_notes,
            schema_hash=schema_hash,
            signature=signature,
            content_pack_data=normalized_pack,
            metadata=metadata,
        )
        return version_id

    def request_review(self, version_id: str) -> ContentVersionRecord:
        version = self.get_version(version_id)
        version.status = "review_requested"
        return version

    def approve_for_rollout(self, version_id: str, approver_role: str, comments: str) -> ContentVersionRecord:
        normalized_role = approver_role.strip().lower()
        if normalized_role not in REQUIRED_REVIEW_ROLES:
            raise ValueError(f"invalid approver role: {approver_role}")

        version = self.get_version(version_id)
        approvals_by_role = {approval.approver_role: approval for approval in version.approvals}
        approvals_by_role[normalized_role] = ReviewApproval(
            approver_role=normalized_role,
            approved_at=datetime.now(UTC),
            comments=comments,
        )
        version.approvals = sorted(approvals_by_role.values(), key=lambda item: item.approver_role)
        version.status = "approved" if self._has_required_approvals(version) else "review_requested"
        return version

    def activate_content(self, version_id: str, rollout_stage: str) -> ContentVersionRecord:
        normalized_stage = rollout_stage.strip().lower()
        if normalized_stage not in ROLLOUT_STAGES:
            raise ValueError(f"invalid rollout stage: {rollout_stage}")

        version = self.get_version(version_id)
        if not self._has_required_approvals(version):
            raise PermissionError("review board approval required before rollout")

        self._active_versions_by_stage[normalized_stage] = version_id
        if normalized_stage not in version.active_rollout_stages:
            version.active_rollout_stages.append(normalized_stage)
            version.active_rollout_stages.sort(key=ROLLOUT_STAGES.index)
        version.status = normalized_stage
        return version

    def rollback_content(self, target_version_id: str) -> ContentVersionRecord:
        target_version = self.get_version(target_version_id)
        updated_mapping = {
            stage: (target_version_id if current_version_id is not None else None)
            for stage, current_version_id in self._active_versions_by_stage.items()
        }
        self._active_versions_by_stage = updated_mapping

        for version in self._versions.values():
            version.active_rollout_stages = [
                stage for stage, active_version_id in self._active_versions_by_stage.items() if active_version_id == version.version_id
            ]
            if version.version_id != target_version_id and version.status in ROLLOUT_STAGES:
                version.status = "rolled_back"

        target_version.active_rollout_stages = [
            stage for stage, active_version_id in self._active_versions_by_stage.items() if active_version_id == target_version_id
        ]
        target_version.status = "active_rollback"
        return target_version

    def get_version(self, version_id: str) -> ContentVersionRecord:
        version = self._versions.get(version_id)
        if version is None:
            raise KeyError(f"unknown content version: {version_id}")
        return version

    def get_active_version(self, rollout_stage: str) -> ContentVersionRecord | None:
        normalized_stage = rollout_stage.strip().lower()
        version_id = self._active_versions_by_stage.get(normalized_stage)
        if version_id is None:
            return None
        return self.get_version(version_id)

    def list_versions(self, content_pack_name: str | None = None) -> list[ContentVersionRecord]:
        versions = list(self._versions.values())
        if content_pack_name:
            versions = [item for item in versions if item.content_pack_name == content_pack_name]
        return sorted(versions, key=lambda item: (item.content_pack_name, item.version_number))

    def _normalize_content_pack(self, content_pack_data: dict[str, Any]) -> dict[str, Any]:
        return {
            content_type: deepcopy(content_pack_data.get(content_type, []))
            for content_type in ("hardware", "buildings", "research", "recipes", "events")
        }

    def _next_version_number(self, content_pack_name: str) -> int:
        matching_versions = [item.version_number for item in self._versions.values() if item.content_pack_name == content_pack_name]
        return (max(matching_versions) + 1) if matching_versions else 1

    def _compute_schema_hash(self) -> str:
        digest = hashlib.sha256()
        for schema_name in ("hardware", "buildings", "research", "recipes", "events"):
            digest.update(
                json.dumps(self._validator.load_schema(schema_name), sort_keys=True, separators=(",", ":")).encode("utf-8")
            )
        return digest.hexdigest()

    def _sign_content_pack(
        self,
        *,
        content_pack_name: str,
        version_number: int,
        impact_notes: str,
        content_pack_data: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        payload = json.dumps(
            {
                "content_pack_name": content_pack_name,
                "version_number": version_number,
                "impact_notes": impact_notes,
                "metadata": metadata,
                "content": content_pack_data,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hmac.new(self._signing_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    @staticmethod
    def _has_required_approvals(version: ContentVersionRecord) -> bool:
        approved_roles = {approval.approver_role for approval in version.approvals}
        return all(role in approved_roles for role in REQUIRED_REVIEW_ROLES)
