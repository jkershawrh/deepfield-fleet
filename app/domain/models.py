"""DeepField Multimodal domain models.

CDD contracts: every model here is a typed contract that the rest of the system
builds against. Ported patterns from DeepField core, extended for multimodal.
"""

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Core signal models (lean port from DeepField)
# ---------------------------------------------------------------------------

class RawSignal(BaseModel):
    signal_id: UUID = Field(default_factory=uuid4)
    cluster_id: UUID
    namespace: str
    resource_kind: str
    resource_name: str
    source: str
    signal_type: str
    raw_payload: dict = Field(default_factory=dict)
    timestamp: datetime


class NormalizedSignal(BaseModel):
    signal_id: UUID
    cluster_id: UUID
    namespace: str
    resource_kind: str
    resource_name: str
    signal_type: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)
    deterministic: bool = True
    labels: dict = Field(default_factory=dict)
    evidence: dict = Field(default_factory=dict)
    timestamp: datetime


class FilterDecision(BaseModel):
    decision_id: UUID = Field(default_factory=uuid4)
    signal_id: UUID
    filter_name: str
    outcome: Literal["keep", "drop", "suppress", "dedupe", "enrich", "escalate"]
    reason_code: str
    evidence: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Multimodal evidence
# ---------------------------------------------------------------------------

class EvidenceArtifact(BaseModel):
    evidence_id: UUID = Field(default_factory=uuid4)
    signal_id: Optional[UUID] = None
    cluster_id: Optional[UUID] = None
    namespace: Optional[str] = None
    resource_kind: Optional[str] = None
    resource_name: Optional[str] = None
    source: str
    source_uri: Optional[str] = None
    modality: Literal[
        "metric", "log", "event", "text", "document",
        "image", "video", "audio", "trace", "human_note", "unknown",
    ]
    artifact_type: str
    content_ref: Optional[str] = None
    content_text: Optional[str] = None
    features: dict = Field(default_factory=dict)
    labels: dict = Field(default_factory=dict)
    sensitivity: Literal["public", "internal", "confidential", "restricted"] = "internal"
    timestamp: datetime = Field(default_factory=_now)
    created_at: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

class ClassificationRecord(BaseModel):
    classification_id: UUID = Field(default_factory=uuid4)
    target_type: Literal["signal", "evidence", "finding", "incident", "action", "verification"]
    target_id: UUID
    agent_tier: Literal["nano", "micro", "macro", "human"]
    agent_name: str
    taxonomy: str
    class_name: str
    severity: Literal["info", "low", "medium", "high", "critical"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""
    evidence_ids: list[UUID] = Field(default_factory=list)
    labels: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_now)


# ---------------------------------------------------------------------------
# Baseline
# ---------------------------------------------------------------------------

class BaselineProfile(BaseModel):
    baseline_id: UUID = Field(default_factory=uuid4)
    scope_type: Literal["cluster", "namespace", "resource", "site", "domain", "global"]
    scope_id: str
    modality: str
    profile_version: int = 1
    normal_ranges: dict = Field(default_factory=dict)
    known_anomaly_families: dict = Field(default_factory=dict)
    class_priors: dict = Field(default_factory=dict)
    feature_stats: dict = Field(default_factory=dict)
    thresholds: dict = Field(default_factory=dict)
    false_positive_rules: list[dict] = Field(default_factory=list)
    source_window: dict = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    status: Literal["draft", "active", "archived"] = "draft"
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class BaselineBuildJob(BaseModel):
    job_id: UUID = Field(default_factory=uuid4)
    status: Literal["pending", "running", "complete", "failed", "cancelled"] = "pending"
    source_specs: list[dict] = Field(default_factory=list)
    scope: dict = Field(default_factory=dict)
    time_range: dict = Field(default_factory=dict)
    outputs: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Agent actions
# ---------------------------------------------------------------------------

class AgentAction(BaseModel):
    action_id: UUID = Field(default_factory=uuid4)
    incident_id: Optional[UUID] = None
    finding_id: Optional[UUID] = None
    action_type: str
    status: Literal["proposed", "approved", "executing", "executed", "failed", "rejected"] = "proposed"
    requires_human_approval: bool = True
    policy_result: dict = Field(default_factory=dict)
    payload: dict = Field(default_factory=dict)
    created_by_agent: str
    created_at: datetime = Field(default_factory=_now)
    executed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

class VerificationRecord(BaseModel):
    verification_id: UUID = Field(default_factory=uuid4)
    action_id: UUID
    verification_type: str
    expected_outcome: dict = Field(default_factory=dict)
    observed_outcome: dict = Field(default_factory=dict)
    status: Literal["pending", "passed", "failed", "inconclusive"] = "pending"
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    evidence_ids: list[UUID] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    completed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------

class LearningProposal(BaseModel):
    proposal_id: UUID = Field(default_factory=uuid4)
    source_type: Literal["incident", "replay", "feedback", "verification", "baseline_job"]
    source_id: UUID
    proposal_type: Literal[
        "threshold_update", "classifier_label", "false_positive_rule",
        "new_anomaly_family", "prompt_update", "routing_update",
    ]
    target_scope: dict = Field(default_factory=dict)
    before: dict = Field(default_factory=dict)
    after: dict = Field(default_factory=dict)
    rationale: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    status: Literal["proposed", "accepted", "rejected", "applied"] = "proposed"
    created_at: datetime = Field(default_factory=_now)
    reviewed_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Agent maturity / promotion
# ---------------------------------------------------------------------------

class AgentMaturity(BaseModel):
    agent_id: UUID = Field(default_factory=uuid4)
    name: str
    tier: Literal["draft", "candidate", "nano", "micro", "macro"] = "draft"
    source: Literal["bootstrap", "manual", "builtin"] = "bootstrap"
    config: dict = Field(default_factory=dict)

    samples_tested: int = 0
    accuracy: float = Field(ge=0.0, le=1.0, default=0.0)
    false_positive_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    false_negative_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    coverage: float = Field(ge=0.0, le=1.0, default=0.0)
    confidence_calibration: Literal["none", "rough", "calibrated"] = "none"
    human_reviewed: bool = False
    cross_modal_agreement: bool = False

    rubric_status: Literal["red", "yellow", "green"] = "red"
    promotion_history: list[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    promoted_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Evidence-based constraints
# ---------------------------------------------------------------------------

class ConstraintRule(BaseModel):
    constraint_id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    constraint_type: Literal["single_event", "evidence_based"] = "single_event"
    conditions: list[dict] = Field(default_factory=list)
    min_evidence_count: int = 1
    taxonomy: str = "compliance_state"
    class_name_on_violation: str = "policy_violation"
    severity: str = "medium"
