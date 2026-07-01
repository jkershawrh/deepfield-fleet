"""Macroagent: builds incident timeline from evidence and classifications."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact


class IncidentTimelineAgent:
    name = "incident_timeline"

    def reason(
        self,
        evidence: list[EvidenceArtifact],
        classifications: list[ClassificationRecord],
        baseline: Optional[BaselineProfile],
    ) -> list[ClassificationRecord]:
        sorted_evidence = sorted(evidence, key=lambda e: e.timestamp)
        modalities = {e.modality for e in evidence}
        severity_levels = {c.severity for c in classifications}

        timeline_entries = []
        for ev in sorted_evidence:
            related = [c for c in classifications if ev.evidence_id in c.evidence_ids]
            if related:
                best = max(related, key=lambda c: c.confidence)
                timeline_entries.append(
                    f"[{ev.timestamp.isoformat()}] {ev.modality}/{ev.artifact_type}: "
                    f"{best.class_name} ({best.severity}, conf={best.confidence:.2f})"
                )

        rationale = "Incident timeline:\n" + "\n".join(timeline_entries) if timeline_entries else "No timeline events"

        max_severity = "critical" if "critical" in severity_levels else \
                       "high" if "high" in severity_levels else "medium"

        return [ClassificationRecord(
            target_type="incident",
            target_id=evidence[0].evidence_id if evidence else classifications[0].target_id,
            agent_tier="macro", agent_name=self.name,
            taxonomy="operational_state",
            class_name="incident" if max_severity in ("critical", "high") else "watch",
            severity=max_severity,
            confidence=0.8 if len(modalities) >= 3 else 0.6,
            rationale=rationale,
            evidence_ids=[e.evidence_id for e in evidence],
        )]
