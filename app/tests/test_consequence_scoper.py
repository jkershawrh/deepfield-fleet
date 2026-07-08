"""Tests for consequence scoping macroagent."""

import pytest
from uuid import uuid4

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.macroagents import consequence_scoper


class TestConsequenceScoper:
    def _make_classification(self, class_name, severity="critical", metrics=None):
        return ClassificationRecord(
            target_type="evidence",
            target_id=uuid4(),
            agent_tier="micro",
            agent_name="slo_forecaster",
            taxonomy="fleet.slo",
            class_name=class_name,
            severity=severity,
            confidence=0.85,
            rationale="Test classification",
            metrics=metrics or {},
        )

    def _make_evidence(self, models=None, users=50, tenants=None):
        features = {"active_users": users}
        if models:
            features["models"] = models
        if tenants:
            features["tenant_id"] = tenants[0]
        return [EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type="latency_p95",
            features=features,
        )]

    def test_assesses_slo_breach(self):
        classifications = [self._make_classification(
            "slo_breach_predicted",
            metrics={"forecast_value": 7000, "slo_target": 5000},
        )]
        evidence = self._make_evidence(models=["model-a", "model-b"], users=50)

        records = consequence_scoper.reason(evidence, classifications)
        assert len(records) == 1
        assert records[0].class_name == "blast_radius_assessed"
        assert records[0].metrics["affected_models"] == 2
        assert records[0].metrics["estimated_users"] == 50
        assert records[0].metrics["severity_score"] > 0

    def test_critical_requires_human_gate(self):
        # 200 users x 1.4 magnitude x 3 models = 840 -> critical
        classifications = [self._make_classification(
            "slo_breach_predicted",
            metrics={"forecast_value": 7000, "slo_target": 5000},
        )]
        evidence = self._make_evidence(models=["a", "b", "c"], users=200)

        records = consequence_scoper.reason(evidence, classifications)
        assert records[0].metrics["requires_human_gate"] is True
        assert records[0].severity == "critical"

    def test_small_blast_radius_no_human_gate(self):
        # 5 users x 1.2 magnitude x 1 model = 6 -> medium, no gate
        classifications = [self._make_classification(
            "capacity_saturated",
            metrics={"forecast_value": 6000, "slo_target": 5000},
        )]
        evidence = self._make_evidence(models=["model-a"], users=5)

        records = consequence_scoper.reason(evidence, classifications)
        assert records[0].metrics["requires_human_gate"] is False
        assert records[0].severity in ("medium", "high")

    def test_no_scope_on_healthy(self):
        classifications = [self._make_classification("slo_forecast_safe", severity="info")]
        evidence = self._make_evidence()

        records = consequence_scoper.reason(evidence, classifications)
        assert len(records) == 0

    def test_queue_overflow_scoped(self):
        classifications = [self._make_classification("queue_overflow")]
        evidence = self._make_evidence(models=["model-x"], users=30)

        records = consequence_scoper.reason(evidence, classifications)
        assert len(records) == 1
        assert records[0].metrics["affected_models"] >= 1

    def test_multiple_critical_classifications(self):
        classifications = [
            self._make_classification("slo_breach_predicted"),
            self._make_classification("capacity_saturated"),
        ]
        evidence = self._make_evidence(models=["a", "b"], users=100)

        records = consequence_scoper.reason(evidence, classifications)
        assert len(records) == 2

    def test_severity_score_calculation(self):
        # 50 users x 1.4 (7000/5000) x 2 models = 140 -> critical
        classifications = [self._make_classification(
            "slo_breach_predicted",
            metrics={"forecast_value": 7000, "slo_target": 5000},
        )]
        evidence = self._make_evidence(models=["a", "b"], users=50)

        records = consequence_scoper.reason(evidence, classifications)
        score = records[0].metrics["severity_score"]
        assert score == pytest.approx(50 * 1.4 * 2, rel=0.01)

    def test_rationale_includes_human_gate_info(self):
        classifications = [self._make_classification(
            "slo_breach_predicted",
            metrics={"forecast_value": 8000, "slo_target": 5000},
        )]
        evidence = self._make_evidence(models=["a", "b", "c"], users=100)

        records = consequence_scoper.reason(evidence, classifications)
        assert "HUMAN APPROVAL" in records[0].rationale.upper() or "human" in records[0].rationale.lower()
