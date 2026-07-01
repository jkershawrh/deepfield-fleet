"""Macroagent: builds verification plan for actions taken."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact


class VerificationPlannerAgent:
    name = "verification_planner"

    def reason(
        self,
        evidence: list[EvidenceArtifact],
        classifications: list[ClassificationRecord],
        baseline: Optional[BaselineProfile],
    ) -> list[ClassificationRecord]:
        metric_evidence = [e for e in evidence if e.modality == "metric"]
        verification_type = "metric_return_to_baseline" if metric_evidence else "signal_volume_change"

        rationale = (
            f"Verification plan: {verification_type}. "
            f"Monitor {len(metric_evidence)} metric sources for return to baseline values."
        )

        return [ClassificationRecord(
            target_type="verification",
            target_id=evidence[0].evidence_id if evidence else classifications[0].target_id,
            agent_tier="macro", agent_name=self.name,
            taxonomy="action_class", class_name="observe",
            severity="info", confidence=0.7,
            rationale=rationale,
            evidence_ids=[e.evidence_id for e in evidence],
        )]
