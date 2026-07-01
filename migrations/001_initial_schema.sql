-- DeepField Multimodal: initial schema
-- All tables for multimodal evidence, classification, baselines, actions, verification, and learning.

CREATE TABLE IF NOT EXISTS evidence_artifacts (
    evidence_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id      UUID,
    cluster_id     UUID,
    namespace      TEXT,
    resource_kind  TEXT,
    resource_name  TEXT,
    source         TEXT NOT NULL,
    source_uri     TEXT,
    modality       TEXT NOT NULL,
    artifact_type  TEXT NOT NULL,
    content_ref    TEXT,
    content_text   TEXT,
    features       JSONB NOT NULL DEFAULT '{}',
    labels         JSONB NOT NULL DEFAULT '{}',
    sensitivity    TEXT NOT NULL DEFAULT 'internal',
    timestamp      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evidence_timestamp ON evidence_artifacts (timestamp);
CREATE INDEX IF NOT EXISTS idx_evidence_cluster   ON evidence_artifacts (cluster_id);
CREATE INDEX IF NOT EXISTS idx_evidence_modality  ON evidence_artifacts (modality);

CREATE TABLE IF NOT EXISTS classification_records (
    classification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    target_type       TEXT NOT NULL,
    target_id         UUID NOT NULL,
    agent_tier        TEXT NOT NULL,
    agent_name        TEXT NOT NULL,
    taxonomy          TEXT NOT NULL,
    class_name        TEXT NOT NULL,
    severity          TEXT NOT NULL,
    confidence        DOUBLE PRECISION NOT NULL,
    rationale         TEXT NOT NULL DEFAULT '',
    evidence_ids      UUID[] NOT NULL DEFAULT '{}',
    labels            JSONB NOT NULL DEFAULT '{}',
    metrics           JSONB NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_class_target     ON classification_records (target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_class_tier       ON classification_records (agent_tier);
CREATE INDEX IF NOT EXISTS idx_class_timestamp  ON classification_records (created_at);

CREATE TABLE IF NOT EXISTS baseline_profiles (
    baseline_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_type             TEXT NOT NULL,
    scope_id               TEXT NOT NULL,
    modality               TEXT NOT NULL,
    profile_version        INTEGER NOT NULL DEFAULT 1,
    normal_ranges          JSONB NOT NULL DEFAULT '{}',
    known_anomaly_families JSONB NOT NULL DEFAULT '{}',
    class_priors           JSONB NOT NULL DEFAULT '{}',
    feature_stats          JSONB NOT NULL DEFAULT '{}',
    thresholds             JSONB NOT NULL DEFAULT '{}',
    false_positive_rules   JSONB NOT NULL DEFAULT '[]',
    source_window          JSONB NOT NULL DEFAULT '{}',
    confidence             DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status                 TEXT NOT NULL DEFAULT 'draft',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_baseline_scope    ON baseline_profiles (scope_type, scope_id, modality);
CREATE INDEX IF NOT EXISTS idx_baseline_status   ON baseline_profiles (status);

CREATE TABLE IF NOT EXISTS baseline_build_jobs (
    job_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status       TEXT NOT NULL DEFAULT 'pending',
    source_specs JSONB NOT NULL DEFAULT '[]',
    scope        JSONB NOT NULL DEFAULT '{}',
    time_range   JSONB NOT NULL DEFAULT '{}',
    outputs      JSONB NOT NULL DEFAULT '{}',
    metrics      JSONB NOT NULL DEFAULT '{}',
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at   TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_job_status ON baseline_build_jobs (status);

CREATE TABLE IF NOT EXISTS agent_actions (
    action_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id            UUID,
    finding_id             UUID,
    action_type            TEXT NOT NULL,
    status                 TEXT NOT NULL DEFAULT 'proposed',
    requires_human_approval BOOLEAN NOT NULL DEFAULT true,
    policy_result          JSONB NOT NULL DEFAULT '{}',
    payload                JSONB NOT NULL DEFAULT '{}',
    created_by_agent       TEXT NOT NULL,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    executed_at            TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_action_status ON agent_actions (status);

CREATE TABLE IF NOT EXISTS verification_records (
    verification_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_id        UUID NOT NULL,
    verification_type TEXT NOT NULL,
    expected_outcome JSONB NOT NULL DEFAULT '{}',
    observed_outcome JSONB NOT NULL DEFAULT '{}',
    status           TEXT NOT NULL DEFAULT 'pending',
    confidence       DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    evidence_ids     UUID[] NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_verif_status ON verification_records (status);

CREATE TABLE IF NOT EXISTS learning_proposals (
    proposal_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type  TEXT NOT NULL,
    source_id    UUID NOT NULL,
    proposal_type TEXT NOT NULL,
    target_scope JSONB NOT NULL DEFAULT '{}',
    before       JSONB NOT NULL DEFAULT '{}',
    after        JSONB NOT NULL DEFAULT '{}',
    rationale    TEXT NOT NULL DEFAULT '',
    confidence   DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status       TEXT NOT NULL DEFAULT 'proposed',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    reviewed_at  TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_proposal_status ON learning_proposals (status);
