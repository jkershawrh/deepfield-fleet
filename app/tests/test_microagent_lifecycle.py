"""TDD tests for configurable microagent + cross-modal macro promotion. RED first."""

from uuid import uuid4

from app.bootstrap.promotion import (
    PromotionEngine,
    evaluate_agent,
    detect_cross_modal_convergence,
    run_validation_round,
)
from app.domain.models import (
    AgentMaturity,
    BaselineProfile,
    ClassificationRecord,
    EvidenceArtifact,
)
from app.microagents.configurable import ConfigurableMicroagent


# ---------------------------------------------------------------------------
# ConfigurableMicroagent
# ---------------------------------------------------------------------------

class TestConfigurableMicroagent:
    def test_classifies_with_rule_fallback(self):
        agent = ConfigurableMicroagent({
            "name": "test_micro",
            "modalities": ["metric"],
            "prompt": "Classify this metric signal...",
            "taxonomy": "incident_family",
        })
        evidence = [EvidenceArtifact(
            source="test", modality="metric", artifact_type="vibration",
            content_text="vibration threshold exceeded on bearing unit 7",
            features={"mean": 0.65},
        )]
        records = agent.classify(evidence)
        assert len(records) > 0
        assert all(r.agent_tier == "micro" for r in records)
        assert all(r.agent_name == "test_micro" for r in records)

    def test_filters_by_modality(self):
        agent = ConfigurableMicroagent({
            "name": "image_only",
            "modalities": ["image"],
            "prompt": "Classify this image...",
            "taxonomy": "incident_family",
        })
        evidence = [
            EvidenceArtifact(source="test", modality="metric", artifact_type="temp", features={}),
            EvidenceArtifact(source="test", modality="image", artifact_type="surface", labels={"defect": 0.8}),
        ]
        records = agent.classify(evidence)
        assert len(records) == 1

    def test_returns_low_confidence_without_llm(self):
        agent = ConfigurableMicroagent({
            "name": "llm_needed",
            "modalities": ["text"],
            "prompt": "Classify...",
            "taxonomy": "incident_family",
        })
        evidence = [EvidenceArtifact(
            source="test", modality="text", artifact_type="note",
            content_text="something happened",
        )]
        records = agent.classify(evidence)
        assert records[0].confidence <= 0.5


# ---------------------------------------------------------------------------
# Cross-modal convergence detection
# ---------------------------------------------------------------------------

class TestCrossModalConvergence:
    def _make_classification(self, modality, resource="unit-7", agent_tier="micro"):
        ev = EvidenceArtifact(source="test", modality=modality, artifact_type="test",
                              namespace=resource, features={})
        return ClassificationRecord(
            target_type="evidence", target_id=ev.evidence_id,
            agent_tier=agent_tier, agent_name=f"{modality}_classifier",
            taxonomy="incident_family", class_name="quality",
            severity="high", confidence=0.8,
            evidence_ids=[ev.evidence_id],
        ), ev

    def test_detects_convergence_across_modalities(self):
        c1, e1 = self._make_classification("metric", "unit-7")
        c2, e2 = self._make_classification("image", "unit-7")
        c3, e3 = self._make_classification("audio", "unit-7")
        evidence = [e1, e2, e3]
        classifications = [c1, c2, c3]
        result = detect_cross_modal_convergence(classifications, evidence)
        assert result is True

    def test_no_convergence_single_modality(self):
        c1, e1 = self._make_classification("metric", "unit-7")
        c2, e2 = self._make_classification("metric", "unit-7")
        evidence = [e1, e2]
        classifications = [c1, c2]
        result = detect_cross_modal_convergence(classifications, evidence)
        assert result is False

    def test_no_convergence_different_resources(self):
        c1, e1 = self._make_classification("metric", "unit-7")
        c2, e2 = self._make_classification("image", "unit-99")
        evidence = [e1, e2]
        classifications = [c1, c2]
        result = detect_cross_modal_convergence(classifications, evidence)
        assert result is False


# ---------------------------------------------------------------------------
# Macro promotion with cross-modal requirement
# ---------------------------------------------------------------------------

class TestMacroPromotion:
    def test_macro_requires_cross_modal_and_human(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="correlator", tier="nano", source="bootstrap",
            samples_tested=1200, accuracy=0.90, false_positive_rate=0.03,
            coverage=0.80, human_reviewed=True, cross_modal_agreement=True,
            config={},
        )
        promoted = engine.check_promotion(agent)
        assert promoted.tier == "micro"

    def test_macro_blocked_without_cross_modal(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="single_modal", tier="micro", source="bootstrap",
            samples_tested=1200, accuracy=0.90, false_positive_rate=0.03,
            coverage=0.80, human_reviewed=True, cross_modal_agreement=False,
            config={},
        )
        result = engine.check_promotion(agent)
        assert result.tier == "micro"

    def test_macro_blocked_without_human_review(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="unreviewed", tier="micro", source="bootstrap",
            samples_tested=1200, accuracy=0.90, false_positive_rate=0.03,
            coverage=0.80, human_reviewed=False, cross_modal_agreement=True,
            config={},
        )
        result = engine.check_promotion(agent)
        assert result.tier == "micro"

    def test_macro_promotion_full_path(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="full_path", tier="micro", source="bootstrap",
            samples_tested=1200, accuracy=0.90, false_positive_rate=0.03,
            coverage=0.80, human_reviewed=True, cross_modal_agreement=True,
            config={},
        )
        promoted = engine.check_promotion(agent)
        assert promoted.tier == "macro"
        assert promoted.rubric_status == "green"
        assert len(promoted.promotion_history) > 0
