"""TDD tests for agent promotion pipeline. RED first."""

from uuid import uuid4

from app.bootstrap.promotion import (
    PromotionEngine,
    evaluate_agent,
    get_rubric_matrix,
    run_validation_round,
)
from app.domain.models import AgentMaturity, BaselineProfile, EvidenceArtifact


def _evidence(mean=0.22, slope=0.001, z=0.3, modality="metric"):
    return EvidenceArtifact(
        source="test", modality=modality, artifact_type="vibration_rms",
        features={"mean": mean, "std": 0.01, "slope": slope, "z_score_last": z},
    )


def _baseline():
    return BaselineProfile(
        scope_type="site", scope_id="test", modality="metric",
        normal_ranges={"vibration_rms": {"mean": {"low": 0.18, "high": 0.26}}},
        thresholds={"vibration_rms": {"mean_z_warning": 2.0, "mean_z_critical": 3.0}},
        feature_stats={"vibration_rms": {"mean": {"mean": 0.22, "std": 0.012}}},
        confidence=0.8, status="active",
    )


def _draft_agent(name="test_rule"):
    return AgentMaturity(
        name=name, tier="draft", source="bootstrap",
        config={
            "name": name, "modality": "metric",
            "condition": {"field": "mean", "operator": "gt", "value": 0.30},
            "classification": {"taxonomy": "operational_state", "class_name": "degraded", "severity": "high", "confidence": 0.8},
        },
    )


# ---------------------------------------------------------------------------
# AgentMaturity model
# ---------------------------------------------------------------------------

class TestAgentMaturity:
    def test_draft_starts_red(self):
        agent = _draft_agent()
        assert agent.tier == "draft"
        assert agent.rubric_status == "red"
        assert agent.samples_tested == 0

    def test_promotion_fields_default(self):
        agent = _draft_agent()
        assert agent.accuracy == 0.0
        assert agent.false_positive_rate == 0.0
        assert agent.human_reviewed is False
        assert agent.cross_modal_agreement is False
        assert agent.promotion_history == []


# ---------------------------------------------------------------------------
# Promotion engine
# ---------------------------------------------------------------------------

class TestPromotionEngine:
    def test_evaluate_draft_against_normal_evidence(self):
        agent = _draft_agent()
        evidence = [_evidence(mean=0.22)] * 60
        baseline = _baseline()
        updated = evaluate_agent(agent, evidence, baseline)
        assert updated.samples_tested == 60
        assert updated.accuracy > 0.0

    def test_evaluate_draft_against_abnormal_evidence(self):
        agent = _draft_agent()
        normal = [_evidence(mean=0.22)] * 40
        abnormal = [_evidence(mean=0.65, slope=0.08, z=3.5)] * 20
        evidence = normal + abnormal
        baseline = _baseline()
        updated = evaluate_agent(agent, evidence, baseline)
        assert updated.samples_tested == 60
        assert updated.accuracy > 0.0

    def test_promote_passing_candidate_to_nano(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="proven_rule", tier="candidate", source="bootstrap",
            samples_tested=250, accuracy=0.80, false_positive_rate=0.10,
            false_negative_rate=0.15, coverage=0.70,
            confidence_calibration="rough",
            config=_draft_agent().config,
        )
        promoted = engine.check_promotion(agent)
        assert promoted.tier == "nano"
        assert promoted.rubric_status == "green"

    def test_reject_failing_candidate(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="bad_rule", tier="candidate", source="bootstrap",
            samples_tested=250, accuracy=0.40, false_positive_rate=0.35,
            coverage=0.20,
            config=_draft_agent().config,
        )
        result = engine.check_promotion(agent)
        assert result.tier == "candidate"
        assert result.rubric_status != "green"

    def test_draft_promotes_to_candidate(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="new_rule", tier="draft", source="bootstrap",
            samples_tested=60, accuracy=0.65, false_positive_rate=0.25,
            coverage=0.50,
            config=_draft_agent().config,
        )
        promoted = engine.check_promotion(agent)
        assert promoted.tier == "candidate"

    def test_nano_does_not_promote_without_human_review(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="nano_rule", tier="nano", source="bootstrap",
            samples_tested=600, accuracy=0.90, false_positive_rate=0.05,
            coverage=0.80, human_reviewed=False,
            config=_draft_agent().config,
        )
        result = engine.check_promotion(agent)
        assert result.tier == "nano"

    def test_promotion_records_history(self):
        engine = PromotionEngine()
        agent = AgentMaturity(
            name="rule", tier="draft", source="bootstrap",
            samples_tested=60, accuracy=0.70, false_positive_rate=0.20,
            config=_draft_agent().config,
        )
        promoted = engine.check_promotion(agent)
        assert len(promoted.promotion_history) > 0
        assert promoted.promotion_history[-1]["from"] == "draft"
        assert promoted.promotion_history[-1]["to"] == "candidate"


# ---------------------------------------------------------------------------
# Validation round
# ---------------------------------------------------------------------------

class TestValidationRound:
    def test_run_validation_updates_all_agents(self):
        agents = [_draft_agent("rule_a"), _draft_agent("rule_b")]
        evidence = [_evidence(mean=0.22)] * 30 + [_evidence(mean=0.65)] * 30
        baseline = _baseline()
        updated = run_validation_round(agents, evidence, baseline)
        assert len(updated) == 2
        for a in updated:
            assert a.samples_tested > 0


# ---------------------------------------------------------------------------
# Rubric matrix
# ---------------------------------------------------------------------------

class TestRubricMatrix:
    def test_matrix_starts_all_red(self):
        agents = [_draft_agent("a"), _draft_agent("b"), _draft_agent("c")]
        matrix = get_rubric_matrix(agents)
        assert matrix["overall"] == "red"
        assert all(a["rubric_status"] == "red" for a in matrix["agents"])

    def test_matrix_shows_green_for_promoted(self):
        agents = [
            AgentMaturity(name="good", tier="nano", rubric_status="green",
                          samples_tested=200, accuracy=0.85, config={}),
            AgentMaturity(name="ok", tier="candidate", rubric_status="yellow",
                          samples_tested=80, accuracy=0.65, config={}),
        ]
        matrix = get_rubric_matrix(agents)
        statuses = {a["name"]: a["rubric_status"] for a in matrix["agents"]}
        assert statuses["good"] == "green"
        assert statuses["ok"] == "yellow"
