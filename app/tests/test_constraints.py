"""TDD tests for evidence-based constraint classification. RED first."""

from uuid import uuid4

from app.domain.models import (
    ClassificationRecord,
    ConstraintRule,
    EvidenceArtifact,
)
from app.bootstrap.constraints import evaluate_constraint


class TestConstraintRule:
    def test_valid_construction(self):
        rule = ConstraintRule(
            name="maintenance_skipped",
            description="Maintenance window skipped while vibration trending",
            constraint_type="evidence_based",
            conditions=[
                {"type": "classification", "agent": "metric_drift", "class_name": "watch"},
                {"type": "evidence", "modality": "log", "feature": "error_count", "operator": "gt", "value": 0},
            ],
            min_evidence_count=2,
        )
        assert rule.constraint_type == "evidence_based"
        assert len(rule.conditions) == 2

    def test_single_event_constraint(self):
        rule = ConstraintRule(
            name="privileged_container",
            description="Privileged container detected",
            constraint_type="single_event",
            conditions=[{"type": "evidence", "field": "privileged", "operator": "eq", "value": "true"}],
        )
        assert rule.min_evidence_count == 1


class TestConstraintEvaluation:
    def test_evidence_based_violation(self):
        rule = ConstraintRule(
            name="drift_with_errors",
            description="Drift detected alongside log errors",
            constraint_type="evidence_based",
            conditions=[
                {"type": "classification", "class_name": "watch"},
                {"type": "classification", "class_name": "actionable"},
            ],
            min_evidence_count=2,
        )
        classifications = [
            ClassificationRecord(
                target_type="evidence", target_id=uuid4(),
                agent_tier="nano", agent_name="metric_drift",
                taxonomy="operational_state", class_name="watch",
                severity="medium", confidence=0.7,
            ),
            ClassificationRecord(
                target_type="evidence", target_id=uuid4(),
                agent_tier="nano", agent_name="log_pattern",
                taxonomy="signal_quality", class_name="actionable",
                severity="high", confidence=0.8,
            ),
        ]
        result = evaluate_constraint(rule, classifications, [])
        assert result is not None
        assert result.taxonomy == "compliance_state"
        assert result.class_name == "policy_violation"

    def test_evidence_based_no_violation(self):
        rule = ConstraintRule(
            name="drift_with_errors",
            description="Drift detected alongside log errors",
            constraint_type="evidence_based",
            conditions=[
                {"type": "classification", "class_name": "watch"},
                {"type": "classification", "class_name": "actionable"},
            ],
            min_evidence_count=2,
        )
        classifications = [
            ClassificationRecord(
                target_type="evidence", target_id=uuid4(),
                agent_tier="nano", agent_name="metric_drift",
                taxonomy="operational_state", class_name="normal",
                severity="info", confidence=0.9,
            ),
        ]
        result = evaluate_constraint(rule, classifications, [])
        assert result is None

    def test_single_event_violation(self):
        rule = ConstraintRule(
            name="high_restart",
            description="Pod restart count excessive",
            constraint_type="single_event",
            conditions=[{"type": "evidence", "modality": "event", "feature": "restarts", "operator": "gt", "value": 5}],
        )
        evidence = [EvidenceArtifact(
            source="test", modality="event", artifact_type="pod",
            features={"restarts": 8},
        )]
        result = evaluate_constraint(rule, [], evidence)
        assert result is not None
        assert result.class_name == "policy_violation"
