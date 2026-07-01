"""Agent loop orchestrator — Signals → Decide → Act → Verify → Learn."""

from typing import Optional

from app.agent_loop.actions import ActionManager
from app.agent_loop.learning import LearningService
from app.agent_loop.verification import VerificationService
from app.classification.engine import ClassificationEngine
from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact


class AgentLoop:
    def __init__(self):
        self._engine = ClassificationEngine()
        self._actions = ActionManager()
        self._verification = VerificationService()
        self._learning = LearningService()

    def run(
        self,
        evidence: list[EvidenceArtifact],
        baseline: Optional[BaselineProfile] = None,
    ) -> dict:
        classifications = self._engine.classify(evidence, baseline)

        actions = self._decide_and_act(classifications, evidence)

        verifications = self._verify(actions, evidence, baseline)

        proposals = self._learn(classifications, verifications, evidence, baseline)

        return {
            "classifications": classifications,
            "actions": actions,
            "verifications": verifications,
            "learning_proposals": proposals,
        }

    def _decide_and_act(self, classifications, evidence):
        action_records = [
            c for c in classifications
            if c.agent_name == "action_planner" and c.taxonomy == "action_class"
        ]
        actions = []
        for rec in action_records:
            action = self._actions.propose(
                action_type=rec.class_name,
                payload={"rationale": rec.rationale, "evidence_count": len(evidence)},
                created_by_agent=rec.agent_name,
            )
            actions.append(action)

        if not actions:
            severities = {c.severity for c in classifications}
            if "critical" in severities or "high" in severities:
                action = self._actions.propose(
                    action_type="notify",
                    payload={"reason": "High severity classifications detected"},
                    created_by_agent="agent_loop",
                )
                actions.append(action)
            else:
                action = self._actions.propose(
                    action_type="observe",
                    payload={"reason": "No urgent action required"},
                    created_by_agent="agent_loop",
                )
                actions.append(action)
        return actions

    def _verify(self, actions, evidence, baseline):
        verifications = []
        metric_evidence = [e for e in evidence if e.modality == "metric"]
        for action in actions:
            if action.action_type in ("notify", "ticket"):
                expected = {}
                for ev in metric_evidence:
                    mean = ev.features.get("mean")
                    if mean and baseline and baseline.normal_ranges:
                        ranges = baseline.normal_ranges.get(ev.artifact_type, {})
                        for key, bounds in ranges.items():
                            if isinstance(bounds, dict) and "high" in bounds:
                                expected[f"{key}_below"] = bounds["high"]
                if not expected:
                    expected = {"signal_volume_decreased": True}
                record = self._verification.create(
                    action_id=action.action_id,
                    verification_type="metric_return_to_baseline",
                    expected_outcome=expected,
                )
                verifications.append(record)
        if not verifications:
            record = self._verification.create(
                action_id=actions[0].action_id if actions else None,
                verification_type="continued_monitoring",
                expected_outcome={"status": "stable"},
            )
            verifications.append(record)
        return verifications

    def _learn(self, classifications, verifications, evidence, baseline):
        proposals = []
        high_confidence = [
            c for c in classifications
            if c.confidence >= 0.7 and c.severity in ("high", "critical")
        ]
        if high_confidence and baseline:
            source_id = high_confidence[0].classification_id
            proposal = self._learning.propose(
                source_type="incident",
                source_id=source_id,
                proposal_type="threshold_update",
                target_scope={"scope_type": baseline.scope_type, "scope_id": baseline.scope_id},
                before={"thresholds": baseline.thresholds},
                after={"recommendation": "tighten thresholds for earlier detection"},
                rationale=f"Based on {len(high_confidence)} high-confidence findings",
                confidence=0.65,
            )
            proposals.append(proposal)
        if not proposals:
            proposal = self._learning.propose(
                source_type="feedback",
                source_id=classifications[0].classification_id if classifications else verifications[0].verification_id,
                proposal_type="classifier_label",
                target_scope={},
                before={}, after={},
                rationale="No significant findings for learning update",
                confidence=0.3,
            )
            proposals.append(proposal)
        return proposals
