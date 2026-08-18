-- M6-BETA-01: Support Ticket System
CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN ('bug', 'player_behavior', 'content', 'exploit')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    first_response_at TIMESTAMPTZ,
    resolved_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    resolution_reason TEXT
);

CREATE TABLE IF NOT EXISTS support_ticket_messages (
    message_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES support_tickets(ticket_id),
    from_role TEXT NOT NULL CHECK (from_role IN ('player', 'staff')),
    message_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS support_ticket_attachments (
    attachment_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES support_tickets(ticket_id),
    file_name TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS support_ticket_evidence (
    evidence_id TEXT PRIMARY KEY,
    ticket_id TEXT NOT NULL REFERENCES support_tickets(ticket_id),
    player_state_snapshot_json JSONB NOT NULL,
    environment_info_json JSONB NOT NULL,
    captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_support_tickets_player ON support_tickets(player_id);
CREATE INDEX IF NOT EXISTS idx_support_tickets_status ON support_tickets(status);
CREATE INDEX IF NOT EXISTS idx_support_tickets_category ON support_tickets(category);
CREATE INDEX IF NOT EXISTS idx_support_ticket_messages_ticket ON support_ticket_messages(ticket_id);

-- M6-BETA-02: Moderation System
CREATE TABLE IF NOT EXISTS moderation_actions (
    action_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    action_type TEXT NOT NULL CHECK (action_type IN ('warning', 'mute', 'suspend', 'escalate')),
    reason TEXT NOT NULL,
    duration_seconds INTEGER,
    taken_by_staff_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    source_ticket_id TEXT
);

CREATE TABLE IF NOT EXISTS moderation_appeals (
    appeal_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    moderation_action_id TEXT NOT NULL REFERENCES moderation_actions(action_id),
    appeal_reason TEXT NOT NULL,
    appeal_evidence JSONB,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'denied')),
    reviewed_by_staff_id TEXT,
    reviewed_at TIMESTAMPTZ,
    denial_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS moderation_offense_history (
    player_id TEXT NOT NULL,
    offense_type TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    last_offense_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (player_id, offense_type)
);

CREATE TABLE IF NOT EXISTS moderation_offense_escalation (
    offense_type TEXT PRIMARY KEY,
    warning_count INTEGER NOT NULL DEFAULT 1,
    mute_count INTEGER NOT NULL DEFAULT 1,
    suspend_count INTEGER NOT NULL DEFAULT 1,
    suspend_duration_seconds INTEGER NOT NULL DEFAULT 604800
);

INSERT INTO moderation_offense_escalation (offense_type, warning_count, mute_count, suspend_count, suspend_duration_seconds)
VALUES
    ('harassment', 1, 1, 1, 604800),
    ('exploit',    1, 0, 1, 604800),
    ('spam',       1, 1, 1, 86400),
    ('cheat',      0, 0, 1, 2592000)
ON CONFLICT (offense_type) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_moderation_actions_player ON moderation_actions(player_id);
CREATE INDEX IF NOT EXISTS idx_moderation_appeals_status ON moderation_appeals(status);
CREATE INDEX IF NOT EXISTS idx_moderation_appeals_player ON moderation_appeals(player_id);
