"""Microagent: placeholder embedding/clustering classifier."""

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.microagents.base import BaseMicroagent


class EmbeddingClusterClassifierAgent(BaseMicroagent):
    name = "embedding_classifier"

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            records.append(ClassificationRecord(
                target_type="evidence", target_id=ev.evidence_id,
                agent_tier="micro", agent_name=self.name,
                taxonomy="incident_family", class_name="unclassified",
                severity="info", confidence=0.3,
                rationale="Placeholder — embedding classifier not yet connected",
                evidence_ids=[ev.evidence_id],
                metrics={"model": "placeholder", "runtime": "cpu"},
            ))
        return records
