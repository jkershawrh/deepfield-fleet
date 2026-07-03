"""Microagent: mock-label/fixture-backed defect classification for images."""

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.microagents.base import BaseMicroagent


class ImageDefectClassifierAgent(BaseMicroagent):
    name = "image_classifier"
    modalities = {"image"}

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            if ev.modality != "image":
                continue
            defect_score = ev.labels.get("surface_defect_score", 0.0)
            defect_type = ev.labels.get("defect_type", "unknown")

            if defect_score > 0.5:
                records.append(ClassificationRecord(
                    target_type="evidence", target_id=ev.evidence_id,
                    agent_tier="micro", agent_name=self.name,
                    taxonomy="incident_family", class_name="quality",
                    severity="high", confidence=min(defect_score, 1.0),
                    rationale=f"Image defect: {defect_type} (score={defect_score})",
                    evidence_ids=[ev.evidence_id],
                    metrics={"model": "fixture_backed", "runtime": "cpu",
                             "defect_type": defect_type},
                ))
            else:
                records.append(ClassificationRecord(
                    target_type="evidence", target_id=ev.evidence_id,
                    agent_tier="micro", agent_name=self.name,
                    taxonomy="incident_family", class_name="unclassified",
                    severity="info", confidence=0.5,
                    rationale="No defect detected or no labels available",
                    evidence_ids=[ev.evidence_id],
                    metrics={"model": "fixture_backed", "runtime": "cpu"},
                ))
        return records
