"""Macroagent: proposes safe actions based on classification."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact


class ActionPlannerAgent:
    name = "action_planner"

    def reason(
        self,
        evidence: list[EvidenceArtifact],
        classifications: list[ClassificationRecord],
        baseline: Optional[BaselineProfile],
    ) -> list[ClassificationRecord]:
        severities = {c.severity for c in classifications}
        has_critical = "critical" in severities
        has_high = "high" in severities

        if has_critical:
            action = "notify"
            rationale = "Critical severity detected — notify immediately"
        elif has_high:
            action = "notify"
            rationale = "High severity detected — notify for review"
        else:
            action = "observe"
            rationale = "No urgent action required — continue monitoring"

        return [ClassificationRecord(
            target_type="action",
            target_id=evidence[0].evidence_id if evidence else classifications[0].target_id,
            agent_tier="macro", agent_name=self.name,
            taxonomy="action_class", class_name=action,
            severity="high" if has_critical or has_high else "info",
            confidence=0.75,
            rationale=rationale,
            evidence_ids=[e.evidence_id for e in evidence],
        )]
