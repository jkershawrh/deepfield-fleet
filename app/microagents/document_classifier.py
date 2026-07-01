"""Microagent: document type and sensitivity classification."""

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.microagents.base import BaseMicroagent


class DocumentClassifierAgent(BaseMicroagent):
    name = "document_classifier"
    modalities = {"document"}

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            if ev.modality != "document":
                continue
            text = (ev.content_text or "").lower()
            if any(kw in text for kw in ["maintenance", "inspection", "repair", "failure"]):
                family = "quality"
                severity = "medium"
                confidence = 0.7
            elif any(kw in text for kw in ["security", "breach", "unauthorized"]):
                family = "security"
                severity = "high"
                confidence = 0.75
            else:
                family = "unknown"
                severity = "info"
                confidence = 0.4

            records.append(ClassificationRecord(
                target_type="evidence", target_id=ev.evidence_id,
                agent_tier="micro", agent_name=self.name,
                taxonomy="incident_family", class_name=family,
                severity=severity, confidence=confidence,
                rationale=f"Document keyword analysis",
                evidence_ids=[ev.evidence_id],
                metrics={"model": "rule_backed", "runtime": "cpu"},
            ))
        return records
