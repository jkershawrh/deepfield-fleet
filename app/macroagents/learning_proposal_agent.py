"""Macroagent: proposes threshold and rule updates based on incident analysis."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact


class LearningProposalMacroAgent:
    name = "learning_proposal"

    def reason(
        self,
        evidence: list[EvidenceArtifact],
        classifications: list[ClassificationRecord],
        baseline: Optional[BaselineProfile],
    ) -> list[ClassificationRecord]:
        high_confidence = [c for c in classifications if c.confidence >= 0.7 and c.severity in ("high", "critical")]

        if high_confidence:
            rationale = (
                f"Learning proposal: update thresholds based on {len(high_confidence)} "
                f"high-confidence findings. Consider tightening baseline ranges for "
                f"earlier detection."
            )
            class_name = "observe"
        else:
            rationale = "No significant findings to drive learning updates."
            class_name = "no_action"

        return [ClassificationRecord(
            target_type="verification",
            target_id=evidence[0].evidence_id if evidence else classifications[0].target_id,
            agent_tier="macro", agent_name=self.name,
            taxonomy="action_class", class_name=class_name,
            severity="info", confidence=0.6,
            rationale=rationale,
            evidence_ids=[e.evidence_id for e in evidence],
        )]
