-- M7-LAUNCH-01: Genesis block creation and blockchain initialization

CREATE TABLE IF NOT EXISTS genesis_block (
    genesis_id           UUID         PRIMARY KEY,
    block_hash           TEXT         NOT NULL UNIQUE,
    merkle_root          TEXT         NOT NULL,
    chain_id             TEXT         NOT NULL,
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    announced_at         TIMESTAMPTZ,
    created_by_admin_id  TEXT         NOT NULL,
    signature            TEXT         NOT NULL,
    public_message       TEXT         NOT NULL DEFAULT '',
    archived_at          TIMESTAMPTZ,
    rollback_reason      TEXT         NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS genesis_player_snapshot (
    genesis_id            UUID          NOT NULL REFERENCES genesis_block(genesis_id) ON DELETE CASCADE,
    player_id             TEXT          NOT NULL,
    starting_balance      NUMERIC(38,6) NOT NULL,
    starting_tier         INTEGER       NOT NULL,
    joined_at             TIMESTAMPTZ   NOT NULL,
    migrated_from_beta    BOOLEAN       NOT NULL DEFAULT FALSE,
    PRIMARY KEY (genesis_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_genesis_block_created_at
    ON genesis_block (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_genesis_block_announced_at
    ON genesis_block (announced_at DESC);
