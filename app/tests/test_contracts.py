"""CDD contract compliance tests.

These tests verify that every domain model satisfies its typed contract:
valid construction, literal enforcement, default factories, and round-trips.
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.domain.models import (
    AgentAction,
    BaselineBuildJob,
    BaselineProfile,
    ClassificationRecord,
    EvidenceArtifact,
    FilterDecision,
    LearningProposal,
    NormalizedSignal,
    RawSignal,
    VerificationRecord,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TS = datetime.now(timezone.utc)
_ID = uuid4()


def _raw_signal(**kw):
    defaults = dict(
        cluster_id=_ID, namespace="ns", resource_kind="Pod",
        resource_name="web-1", source="synthetic", signal_type="pod_restart",
        timestamp=_TS,
    )
    return RawSignal(**(defaults | kw))


def _normalized_signal(**kw):
    defaults = dict(
        signal_id=_ID, cluster_id=_ID, namespace="ns", resource_kind="Pod",
        resource_name="web-1", signal_type="pod_restart", severity="medium",
        confidence=0.8, timestamp=_TS,
    )
    return NormalizedSignal(**(defaults | kw))


def _evidence(**kw):
    defaults = dict(source="fixture", modality="metric", artifact_type="vibration")
    return EvidenceArtifact(**(defaults | kw))


def _classification(**kw):
    defaults = dict(
        target_type="evidence", target_id=_ID, agent_tier="nano",
        agent_name="baseline_distance", taxonomy="operational_state",
        class_name="watch", severity="medium", confidence=0.75,
    )
    return ClassificationRecord(**(defaults | kw))


def _baseline(**kw):
    defaults = dict(scope_type="cluster", scope_id="cluster-1", modality="metric")
    return BaselineProfile(**(defaults | kw))


# ---------------------------------------------------------------------------
# Valid construction
# ---------------------------------------------------------------------------

class TestValidConstruction:
    def test_raw_signal(self):
        s = _raw_signal()
        assert isinstance(s.signal_id, UUID)
        assert s.namespace == "ns"

    def test_normalized_signal(self):
        s = _normalized_signal()
        assert s.severity == "medium"
        assert 0.0 <= s.confidence <= 1.0

    def test_filter_decision(self):
        d = FilterDecision(signal_id=_ID, filter_name="dedupe", outcome="keep", reason_code="unique")
        assert isinstance(d.decision_id, UUID)
        assert d.outcome == "keep"

    def test_evidence_artifact(self):
        e = _evidence()
        assert e.modality == "metric"
        assert isinstance(e.evidence_id, UUID)
        assert e.sensitivity == "internal"

    def test_classification_record(self):
        c = _classification()
        assert c.agent_tier == "nano"
        assert c.taxonomy == "operational_state"

    def test_baseline_profile(self):
        b = _baseline()
        assert b.status == "draft"
        assert b.profile_version == 1

    def test_baseline_build_job(self):
        j = BaselineBuildJob()
        assert j.status == "pending"
        assert isinstance(j.job_id, UUID)

    def test_agent_action(self):
        a = AgentAction(action_type="notify", created_by_agent="action_planner")
        assert a.status == "proposed"
        assert a.requires_human_approval is True

    def test_verification_record(self):
        v = VerificationRecord(action_id=_ID, verification_type="metric_return")
        assert v.status == "pending"
        assert v.confidence == 0.0

    def test_learning_proposal(self):
        lp = LearningProposal(
            source_type="incident", source_id=_ID,
            proposal_type="threshold_update",
        )
        assert lp.status == "proposed"


# ---------------------------------------------------------------------------
# Literal enforcement
# ---------------------------------------------------------------------------

class TestLiteralEnforcement:
    def test_severity_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _normalized_signal(severity="extreme")

    def test_modality_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _evidence(modality="radar")

    def test_sensitivity_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _evidence(sensitivity="top_secret")

    def test_agent_tier_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _classification(agent_tier="mega")

    def test_target_type_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _classification(target_type="cluster")

    def test_scope_type_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _baseline(scope_type="planet")

    def test_baseline_status_rejects_invalid(self):
        with pytest.raises(ValidationError):
            _baseline(status="deleted")

    def test_filter_outcome_rejects_invalid(self):
        with pytest.raises(ValidationError):
            FilterDecision(signal_id=_ID, filter_name="x", outcome="yeet", reason_code="y")

    def test_action_status_rejects_invalid(self):
        with pytest.raises(ValidationError):
            AgentAction(action_type="notify", created_by_agent="x", status="done")

    def test_verification_status_rejects_invalid(self):
        with pytest.raises(ValidationError):
            VerificationRecord(action_id=_ID, verification_type="x", status="done")

    def test_proposal_source_type_rejects_invalid(self):
        with pytest.raises(ValidationError):
            LearningProposal(source_type="magic", source_id=_ID, proposal_type="threshold_update")

    def test_proposal_type_rejects_invalid(self):
        with pytest.raises(ValidationError):
            LearningProposal(source_type="incident", source_id=_ID, proposal_type="magic")

    def test_job_status_rejects_invalid(self):
        with pytest.raises(ValidationError):
            BaselineBuildJob(status="done")


# ---------------------------------------------------------------------------
# Confidence range
# ---------------------------------------------------------------------------

class TestConfidenceRange:
    def test_normalized_signal_too_high(self):
        with pytest.raises(ValidationError):
            _normalized_signal(confidence=1.5)

    def test_normalized_signal_negative(self):
        with pytest.raises(ValidationError):
            _normalized_signal(confidence=-0.1)

    def test_classification_too_high(self):
        with pytest.raises(ValidationError):
            _classification(confidence=2.0)

    def test_baseline_too_high(self):
        with pytest.raises(ValidationError):
            _baseline(confidence=1.01)

    def test_verification_too_high(self):
        with pytest.raises(ValidationError):
            VerificationRecord(action_id=_ID, verification_type="x", confidence=1.1)

    def test_proposal_negative(self):
        with pytest.raises(ValidationError):
            LearningProposal(source_type="incident", source_id=_ID,
                             proposal_type="threshold_update", confidence=-0.5)

    def test_boundary_zero(self):
        c = _classification(confidence=0.0)
        assert c.confidence == 0.0

    def test_boundary_one(self):
        c = _classification(confidence=1.0)
        assert c.confidence == 1.0


# ---------------------------------------------------------------------------
# Default factories
# ---------------------------------------------------------------------------

class TestDefaultFactories:
    def test_uuid_uniqueness(self):
        a = _evidence()
        b = _evidence()
        assert a.evidence_id != b.evidence_id

    def test_timestamp_is_utc(self):
        e = _evidence()
        assert e.created_at.tzinfo is not None

    def test_dict_defaults_are_independent(self):
        a = _evidence()
        b = _evidence()
        a.features["key"] = "val"
        assert "key" not in b.features

    def test_list_defaults_are_independent(self):
        a = _classification()
        b = _classification()
        a.evidence_ids.append(_ID)
        assert len(b.evidence_ids) == 0


# ---------------------------------------------------------------------------
# Serialization round-trips
# ---------------------------------------------------------------------------

class TestSerialization:
    def test_evidence_round_trip(self):
        e = _evidence(features={"mean": 42.0}, labels={"env": "prod"})
        data = e.model_dump()
        restored = EvidenceArtifact.model_validate(data)
        assert restored.evidence_id == e.evidence_id
        assert restored.features == {"mean": 42.0}

    def test_classification_round_trip(self):
        c = _classification(evidence_ids=[_ID])
        data = c.model_dump()
        restored = ClassificationRecord.model_validate(data)
        assert restored.evidence_ids == [_ID]

    def test_baseline_round_trip(self):
        b = _baseline(
            normal_ranges={"vibration": [0.1, 0.5]},
            thresholds={"vibration_z": 2.0},
        )
        data = b.model_dump()
        restored = BaselineProfile.model_validate(data)
        assert restored.normal_ranges == {"vibration": [0.1, 0.5]}

    def test_learning_proposal_round_trip(self):
        lp = LearningProposal(
            source_type="incident", source_id=_ID,
            proposal_type="threshold_update",
            before={"z_score": 2.0}, after={"z_score": 2.5},
        )
        data = lp.model_dump()
        restored = LearningProposal.model_validate(data)
        assert restored.before == {"z_score": 2.0}

    def test_json_mode_serialization(self):
        e = _evidence()
        json_str = e.model_dump_json()
        assert isinstance(json_str, str)
        restored = EvidenceArtifact.model_validate_json(json_str)
        assert restored.evidence_id == e.evidence_id


# ---------------------------------------------------------------------------
# Optional fields
# ---------------------------------------------------------------------------

class TestOptionalFields:
    def test_evidence_optional_nulls(self):
        e = _evidence()
        assert e.signal_id is None
        assert e.cluster_id is None
        assert e.source_uri is None
        assert e.content_ref is None
        assert e.content_text is None

    def test_action_optional_nulls(self):
        a = AgentAction(action_type="notify", created_by_agent="x")
        assert a.incident_id is None
        assert a.finding_id is None
        assert a.executed_at is None

    def test_job_optional_nulls(self):
        j = BaselineBuildJob()
        assert j.error is None
        assert j.started_at is None
        assert j.completed_at is None

    def test_verification_optional_nulls(self):
        v = VerificationRecord(action_id=_ID, verification_type="x")
        assert v.completed_at is None

    def test_proposal_optional_nulls(self):
        lp = LearningProposal(
            source_type="incident", source_id=_ID,
            proposal_type="threshold_update",
        )
        assert lp.reviewed_at is None
