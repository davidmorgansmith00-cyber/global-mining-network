-- M7-LAUNCH-02 economy tuning and experimentation infrastructure

CREATE TABLE IF NOT EXISTS economy_parameters (
    version BIGINT PRIMARY KEY,
    difficulty_base NUMERIC(38, 6) NOT NULL,
    reward_per_work_unit NUMERIC(38, 6) NOT NULL,
    tier_unlock_times_json JSONB NOT NULL,
    cosmetic_prices_json JSONB NOT NULL,
    battle_pass_price NUMERIC(38, 6) NOT NULL,
    event_frequency TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reason TEXT NOT NULL,
    admin_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS economy_parameter_history (
    parameter_version BIGINT PRIMARY KEY,
    previous_version BIGINT,
    change_log JSONB NOT NULL,
    reverted_at TIMESTAMPTZ,
    reverted_by_admin_id TEXT,
    FOREIGN KEY (parameter_version) REFERENCES economy_parameters(version)
);

CREATE TABLE IF NOT EXISTS ab_experiments (
    experiment_id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    cohort_a_params_json JSONB NOT NULL,
    cohort_b_params_json JSONB NOT NULL,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'cancelled')),
    results_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_admin_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiment_cohort_assignment (
    player_id TEXT NOT NULL,
    experiment_id UUID NOT NULL REFERENCES ab_experiments(experiment_id) ON DELETE CASCADE,
    cohort TEXT NOT NULL CHECK (cohort IN ('a', 'b')),
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (player_id, experiment_id)
);

CREATE INDEX IF NOT EXISTS idx_ab_experiments_status ON ab_experiments(status, start_at, end_at);
CREATE INDEX IF NOT EXISTS idx_experiment_assignment_experiment ON experiment_cohort_assignment(experiment_id);
