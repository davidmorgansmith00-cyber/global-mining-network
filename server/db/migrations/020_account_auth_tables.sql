-- Migration 020: Account Auth Tables (M4-LAUNCH-03)
-- Creates extended account management tables for the Account UX & Recovery Flows.
-- Follows the immutable-ledger pattern: no UPDATE on core data rows;
-- soft-deletes use deleted_at / revoked columns.

-- ─── Player Accounts (extended view) ──────────────────────────────────────
-- The core players table already exists from M0/M1.
-- This migration adds email_verifications and extended account state.

CREATE TABLE IF NOT EXISTS email_verifications (
    verification_id   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id         UUID         NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    token_hash        TEXT         NOT NULL,
    verified          BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at        TIMESTAMPTZ  NOT NULL,
    used_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_email_verifications_player
    ON email_verifications (player_id);

CREATE INDEX IF NOT EXISTS idx_email_verifications_token
    ON email_verifications (token_hash);

-- ─── Password Resets ──────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS password_resets (
    reset_id          UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id         UUID         NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    token_hash        TEXT         NOT NULL,
    used              BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at        TIMESTAMPTZ  NOT NULL,
    used_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_password_resets_player
    ON password_resets (player_id);

CREATE INDEX IF NOT EXISTS idx_password_resets_token
    ON password_resets (token_hash);

-- ─── Recovery Codes ───────────────────────────────────────────────────────
-- 10 codes generated per player; each is single-use.
-- code_hash uses SHA-256 with a per-code salt stored alongside.

CREATE TABLE IF NOT EXISTS recovery_codes (
    code_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id         UUID         NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    code_hash         TEXT         NOT NULL,
    code_salt         TEXT         NOT NULL,
    used              BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    used_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_recovery_codes_player
    ON recovery_codes (player_id, used);

-- ─── Sessions (extended with device metadata) ─────────────────────────────
-- Augments the existing sessions table where it lacks device columns.
-- Uses ALTER TABLE … ADD COLUMN IF NOT EXISTS for idempotency.

ALTER TABLE sessions
    ADD COLUMN IF NOT EXISTS device_id     TEXT,
    ADD COLUMN IF NOT EXISTS device_name   TEXT,
    ADD COLUMN IF NOT EXISTS ip_address    TEXT,
    ADD COLUMN IF NOT EXISTS last_activity TIMESTAMPTZ DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_sessions_player_active
    ON sessions (player_id, revoked)
    WHERE revoked = FALSE;

-- ─── Player Privacy Settings ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS player_privacy_settings (
    player_id                  UUID         PRIMARY KEY REFERENCES players(player_id) ON DELETE CASCADE,
    show_on_leaderboard        BOOLEAN      NOT NULL DEFAULT TRUE,
    allow_friend_requests      BOOLEAN      NOT NULL DEFAULT TRUE,
    share_activity_with_pool   BOOLEAN      NOT NULL DEFAULT TRUE,
    marketing_emails           BOOLEAN      NOT NULL DEFAULT FALSE,
    updated_at                 TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
