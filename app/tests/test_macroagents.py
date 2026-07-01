"""TDD tests for macroagents. RED first."""

from uuid import uuid4

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact
from app.macroagents.incident_timeline import IncidentTimelineAgent
from app.macroagents.root_cause_hypothesis import RootCauseHypothesisAgent
from app.macroagents.action_planner import ActionPlannerAgent
from app.macroagents.verification_planner import VerificationPlannerAgent
from app.macroagents.learning_proposal_agent import LearningProposalMacroAgent


def _sample_evidence():
    return [
        EvidenceArtifact(source="test", modality="metric", artifact_type="vibration_rms",
                         features={"mean": 0.65, "slope": 0.08}),
        EvidenceArtifact(source="test", modality="log", artifact_type="maintenance_log",
                         content_text="ERROR bearing failure", features={"error_count": 1}),
        EvidenceArtifact(source="test", modality="image", artifact_type="surface_inspection",
                         labels={"defect_type": "bearing_wear", "surface_defect_score": 0.72}),
    ]


def _sample_classifications():
    eid = uuid4()
    return [
        ClassificationRecord(target_type="evidence", target_id=eid, agent_tier="nano",
                             agent_name="metric_drift", taxonomy="operational_state",
                             class_name="degraded", severity="high", confidence=0.85),
        ClassificationRecord(target_type="evidence", target_id=eid, agent_tier="micro",
                             agent_name="image_classifier", taxonomy="incident_family",
                             class_name="quality", severity="high", confidence=0.72),
    ]


def _sample_baseline():
    return BaselineProfile(scope_type="site", scope_id="test", modality="metric", confidence=0.8)


class TestIncidentTimeline:
    def test_builds_timeline(self):
        agent = IncidentTimelineAgent()
        records = agent.reason(_sample_evidence(), _sample_classifications(), _sample_baseline())
        assert len(records) > 0
        assert all(r.agent_tier == "macro" for r in records)

    def test_timeline_has_rationale(self):
        agent = IncidentTimelineAgent()
        records = agent.reason(_sample_evidence(), _sample_classifications(), _sample_baseline())
        assert records[0].rationale != ""


class TestRootCauseHypothesis:
    def test_generates_hypothesis(self):
        agent = RootCauseHypothesisAgent()
        records = agent.reason(_sample_evidence(), _sample_classifications(), _sample_baseline())
        assert len(records) > 0
        assert all(r.agent_tier == "macro" for r in records)


class TestActionPlanner:
    def test_proposes_safe_action(self):
        agent = ActionPlannerAgent()
        records = agent.reason(_sample_evidence(), _sample_classifications(), _sample_baseline())
        assert len(records) > 0
        safe_actions = {"observe", "notify", "ticket", "human_approval", "no_action"}
        for r in records:
            assert r.class_name in safe_actions or r.taxonomy == "action_class"


class TestVerificationPlanner:
    def test_creates_plan(self):
        agent = VerificationPlannerAgent()
        records = agent.reason(_sample_evidence(), _sample_classifications(), _sample_baseline())
        assert len(records) > 0
        assert all(r.agent_tier == "macro" for r in records)


class TestLearningProposalMacro:
    def test_proposes_learning(self):
        agent = LearningProposalMacroAgent()
        records = agent.reason(_sample_evidence(), _sample_classifications(), _sample_baseline())
        assert len(records) > 0
        assert all(r.agent_tier == "macro" for r in records)
