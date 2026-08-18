-- M5-CONTENT-01: Data-Driven Content Pipeline
CREATE TABLE IF NOT EXISTS content_versions (
    version_id         UUID        NOT NULL PRIMARY KEY,
    content_pack_name  TEXT        NOT NULL,
    version_number     INTEGER     NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    author_id          TEXT        NOT NULL,
    status             TEXT        NOT NULL,
    impact_notes       TEXT        NOT NULL,
    signature          TEXT        NOT NULL,
    metadata           JSONB       NOT NULL DEFAULT '{}',
    UNIQUE (content_pack_name, version_number)
);

CREATE TABLE IF NOT EXISTS content_pack_contents (
    version_id         UUID        NOT NULL PRIMARY KEY REFERENCES content_versions(version_id) ON DELETE CASCADE,
    hardware_json      JSONB       NOT NULL,
    buildings_json     JSONB       NOT NULL,
    research_json      JSONB       NOT NULL,
    recipes_json       JSONB       NOT NULL,
    events_json        JSONB       NOT NULL,
    schema_hash        TEXT        NOT NULL
);

CREATE TABLE IF NOT EXISTS content_review_approvals (
    approval_id        UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    version_id         UUID        NOT NULL REFERENCES content_versions(version_id) ON DELETE CASCADE,
    approver_role      TEXT        NOT NULL,
    approved_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    comments           TEXT        NOT NULL DEFAULT '',
    UNIQUE (version_id, approver_role)
);

CREATE TABLE IF NOT EXISTS content_rollout_states (
    content_pack_name  TEXT        NOT NULL,
    rollout_stage      TEXT        NOT NULL,
    active_version_id  UUID        NOT NULL REFERENCES content_versions(version_id),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (content_pack_name, rollout_stage)
);

CREATE INDEX IF NOT EXISTS idx_content_versions_pack_created
    ON content_versions (content_pack_name, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_content_versions_status
    ON content_versions (status, created_at DESC);
