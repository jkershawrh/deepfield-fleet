"""TDD tests for agent loop: actions, verification, learning. RED first."""

from pathlib import Path
from uuid import uuid4

from app.agent_loop.actions import ActionManager
from app.agent_loop.verification import VerificationService
from app.agent_loop.learning import LearningService
from app.agent_loop.loop import AgentLoop
from app.baseline.compiler import BaselineCompiler
from app.classification.engine import ClassificationEngine
from app.domain.models import (
    AgentAction,
    EvidenceArtifact,
    LearningProposal,
    VerificationRecord,
)
from app.multimodal.normalizer import normalize_fixture

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


# ---------------------------------------------------------------------------
# ActionManager
# ---------------------------------------------------------------------------

class TestActionManager:
    def test_propose_action(self):
        mgr = ActionManager()
        action = mgr.propose(
            action_type="notify",
            payload={"target": "maintenance_team", "message": "Bearing alert"},
            created_by_agent="action_planner",
        )
        assert isinstance(action, AgentAction)
        assert action.status == "proposed"
        assert action.requires_human_approval is True

    def test_approve_action(self):
        mgr = ActionManager()
        action = mgr.propose(action_type="notify", payload={}, created_by_agent="test")
        approved = mgr.approve(action.action_id)
        assert approved.status == "approved"

    def test_execute_action(self):
        mgr = ActionManager()
        action = mgr.propose(action_type="notify", payload={}, created_by_agent="test")
        mgr.approve(action.action_id)
        executed = mgr.execute(action.action_id)
        assert executed.status == "executed"
        assert executed.executed_at is not None

    def test_reject_action(self):
        mgr = ActionManager()
        action = mgr.propose(action_type="notify", payload={}, created_by_agent="test")
        rejected = mgr.reject(action.action_id)
        assert rejected.status == "rejected"

    def test_cannot_execute_without_approval(self):
        mgr = ActionManager()
        action = mgr.propose(action_type="notify", payload={}, created_by_agent="test")
        executed = mgr.execute(action.action_id)
        assert executed.status != "executed"

    def test_list_actions(self):
        mgr = ActionManager()
        mgr.propose(action_type="notify", payload={}, created_by_agent="a")
        mgr.propose(action_type="observe", payload={}, created_by_agent="b")
        actions = mgr.list_actions()
        assert len(actions) == 2

    def test_list_actions_by_status(self):
        mgr = ActionManager()
        a1 = mgr.propose(action_type="notify", payload={}, created_by_agent="a")
        mgr.propose(action_type="observe", payload={}, created_by_agent="b")
        mgr.approve(a1.action_id)
        approved = mgr.list_actions(status="approved")
        assert len(approved) == 1


# ---------------------------------------------------------------------------
# VerificationService
# ---------------------------------------------------------------------------

class TestVerificationService:
    def test_create_verification(self):
        svc = VerificationService()
        action_id = uuid4()
        record = svc.create(
            action_id=action_id,
            verification_type="metric_return_to_baseline",
            expected_outcome={"vibration_rms_below": 0.35},
        )
        assert isinstance(record, VerificationRecord)
        assert record.status == "pending"
        assert record.action_id == action_id

    def test_run_verification_pass(self):
        svc = VerificationService()
        action_id = uuid4()
        record = svc.create(
            action_id=action_id,
            verification_type="metric_return_to_baseline",
            expected_outcome={"vibration_rms_below": 0.35},
        )
        result = svc.run(
            record.verification_id,
            observed_outcome={"vibration_rms": 0.22},
        )
        assert result.status == "passed"
        assert result.confidence > 0.0

    def test_run_verification_fail(self):
        svc = VerificationService()
        action_id = uuid4()
        record = svc.create(
            action_id=action_id,
            verification_type="metric_return_to_baseline",
            expected_outcome={"vibration_rms_below": 0.35},
        )
        result = svc.run(
            record.verification_id,
            observed_outcome={"vibration_rms": 0.72},
        )
        assert result.status == "failed"

    def test_list_verifications(self):
        svc = VerificationService()
        svc.create(action_id=uuid4(), verification_type="a", expected_outcome={})
        svc.create(action_id=uuid4(), verification_type="b", expected_outcome={})
        assert len(svc.list_all()) == 2


# ---------------------------------------------------------------------------
# LearningService
# ---------------------------------------------------------------------------

class TestLearningService:
    def test_propose_learning(self):
        svc = LearningService()
        proposal = svc.propose(
            source_type="incident",
            source_id=uuid4(),
            proposal_type="threshold_update",
            target_scope={"scope_type": "site", "scope_id": "factory-line-01"},
            before={"z_score_warning": 2.0},
            after={"z_score_warning": 1.8},
            rationale="Earlier detection of vibration drift",
            confidence=0.7,
        )
        assert isinstance(proposal, LearningProposal)
        assert proposal.status == "proposed"

    def test_accept_proposal(self):
        svc = LearningService()
        proposal = svc.propose(
            source_type="incident", source_id=uuid4(),
            proposal_type="threshold_update",
            target_scope={}, before={}, after={},
            rationale="test", confidence=0.5,
        )
        accepted = svc.accept(proposal.proposal_id)
        assert accepted.status == "accepted"
        assert accepted.reviewed_at is not None

    def test_reject_proposal(self):
        svc = LearningService()
        proposal = svc.propose(
            source_type="incident", source_id=uuid4(),
            proposal_type="threshold_update",
            target_scope={}, before={}, after={},
            rationale="test", confidence=0.5,
        )
        rejected = svc.reject(proposal.proposal_id)
        assert rejected.status == "rejected"

    def test_list_proposals(self):
        svc = LearningService()
        svc.propose(source_type="incident", source_id=uuid4(),
                    proposal_type="threshold_update", target_scope={},
                    before={}, after={}, rationale="a", confidence=0.5)
        svc.propose(source_type="verification", source_id=uuid4(),
                    proposal_type="false_positive_rule", target_scope={},
                    before={}, after={}, rationale="b", confidence=0.6)
        assert len(svc.list_all()) == 2


# ---------------------------------------------------------------------------
# AgentLoop orchestrator
# ---------------------------------------------------------------------------

class TestAgentLoop:
    def _get_evidence_and_baseline(self):
        evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        compiler = BaselineCompiler()
        baseline = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        baseline.status = "active"
        return evidence, baseline

    def test_full_loop_produces_results(self):
        evidence, baseline = self._get_evidence_and_baseline()
        loop = AgentLoop()
        result = loop.run(evidence, baseline)
        assert "classifications" in result
        assert "actions" in result
        assert "verifications" in result
        assert "learning_proposals" in result

    def test_loop_produces_classifications(self):
        evidence, baseline = self._get_evidence_and_baseline()
        loop = AgentLoop()
        result = loop.run(evidence, baseline)
        assert len(result["classifications"]) > 0

    def test_loop_produces_action(self):
        evidence, baseline = self._get_evidence_and_baseline()
        loop = AgentLoop()
        result = loop.run(evidence, baseline)
        assert len(result["actions"]) > 0
        assert result["actions"][0].status == "proposed"

    def test_loop_produces_verification(self):
        evidence, baseline = self._get_evidence_and_baseline()
        loop = AgentLoop()
        result = loop.run(evidence, baseline)
        assert len(result["verifications"]) > 0

    def test_loop_produces_learning_proposal(self):
        evidence, baseline = self._get_evidence_and_baseline()
        loop = AgentLoop()
        result = loop.run(evidence, baseline)
        assert len(result["learning_proposals"]) > 0

    def test_loop_actions_are_safe(self):
        evidence, baseline = self._get_evidence_and_baseline()
        loop = AgentLoop()
        result = loop.run(evidence, baseline)
        safe = {"notify", "observe", "ticket", "human_approval", "no_action"}
        for action in result["actions"]:
            assert action.action_type in safe
