-- Fleet-specific tables for intent tracking and A/B comparison runs.

-- Intent history: every intent emitted by the predictive brain
CREATE TABLE IF NOT EXISTS fleet_intents (
    intent_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_type        TEXT NOT NULL,  -- pre_warm, scale, shed_load, alert, migrate, no_action
    confidence         DOUBLE PRECISION NOT NULL,
    horizon_seconds    INT NOT NULL DEFAULT 0,
    justification      TEXT NOT NULL DEFAULT '',
    state_snapshot     JSONB NOT NULL DEFAULT '{}',
    status             TEXT NOT NULL DEFAULT 'proposed',  -- proposed, executed, refused, deferred
    response_reason    TEXT,
    ledger_entry_id    TEXT,  -- correlation to ARE Ledger

    -- Type-specific fields (flattened)
    model              TEXT,
    pool               TEXT,
    target_replicas    INT,
    desired_replicas   INT,
    current_replicas   INT,
    target_clusters    TEXT[],
    max_inflight       INT,
    duration_seconds   INT,
    severity           TEXT,
    message            TEXT,

    -- Metadata
    predictor_mode     TEXT NOT NULL DEFAULT 'predictive',  -- predictive or reactive
    ab_run_id          UUID,  -- links to ab_runs table
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intent_type       ON fleet_intents (intent_type);
CREATE INDEX IF NOT EXISTS idx_intent_status     ON fleet_intents (status);
CREATE INDEX IF NOT EXISTS idx_intent_model      ON fleet_intents (model);
CREATE INDEX IF NOT EXISTS idx_intent_ab_run     ON fleet_intents (ab_run_id);
CREATE INDEX IF NOT EXISTS idx_intent_created    ON fleet_intents (created_at);

-- A/B comparison runs: tracks predictor ON vs OFF experiments
CREATE TABLE IF NOT EXISTS ab_runs (
    run_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name               TEXT NOT NULL,
    description        TEXT NOT NULL DEFAULT '',
    event_profile      TEXT,  -- name of the event profile used
    predictor_mode     TEXT NOT NULL,  -- 'predictive' or 'reactive'

    -- Timing
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at           TIMESTAMPTZ,
    duration_seconds   INT,

    -- Results
    total_intents      INT NOT NULL DEFAULT 0,
    intents_executed   INT NOT NULL DEFAULT 0,
    intents_refused    INT NOT NULL DEFAULT 0,
    intents_deferred   INT NOT NULL DEFAULT 0,

    -- SLO metrics during run
    p50_latency_ms     DOUBLE PRECISION,
    p95_latency_ms     DOUBLE PRECISION,
    p99_latency_ms     DOUBLE PRECISION,
    error_rate         DOUBLE PRECISION,
    throughput_rps     DOUBLE PRECISION,

    -- Comparison (filled after both A and B complete)
    baseline_run_id    UUID,  -- the reactive run to compare against
    latency_improvement_pct  DOUBLE PRECISION,  -- negative = worse
    error_improvement_pct    DOUBLE PRECISION,

    -- Raw data
    intents_by_type    JSONB NOT NULL DEFAULT '{}',
    classifications_count INT NOT NULL DEFAULT 0,

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ab_run_mode      ON ab_runs (predictor_mode);
CREATE INDEX IF NOT EXISTS idx_ab_run_profile   ON ab_runs (event_profile);
CREATE INDEX IF NOT EXISTS idx_ab_run_started   ON ab_runs (started_at);

-- Prediction outcomes: tracks whether predictions were accurate
CREATE TABLE IF NOT EXISTS prediction_outcomes (
    outcome_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id          UUID NOT NULL REFERENCES fleet_intents(intent_id),
    ab_run_id          UUID REFERENCES ab_runs(run_id),

    -- What was predicted
    predicted_metric   TEXT NOT NULL,  -- e.g. 'p95_latency_ms'
    predicted_value    DOUBLE PRECISION NOT NULL,
    predicted_at       TIMESTAMPTZ NOT NULL,
    prediction_horizon_seconds INT NOT NULL,

    -- What actually happened
    actual_value       DOUBLE PRECISION,
    observed_at        TIMESTAMPTZ,

    -- Accuracy
    absolute_error     DOUBLE PRECISION,
    relative_error     DOUBLE PRECISION,  -- |predicted - actual| / actual
    prediction_correct BOOLEAN,  -- did the predicted event happen?

    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_outcome_intent   ON prediction_outcomes (intent_id);
CREATE INDEX IF NOT EXISTS idx_outcome_ab_run   ON prediction_outcomes (ab_run_id);
