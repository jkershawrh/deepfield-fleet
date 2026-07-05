"""Microagent: image defect classification with optional ONNX CPU backend."""

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.microagents.base import BaseMicroagent
from app.multimodal.media_adapter import classify_image


class ImageDefectClassifierAgent(BaseMicroagent):
    name = "image_classifier"
    modalities = {"image"}

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            if ev.modality != "image":
                continue
            result = classify_image(ev)
            metrics = dict(result.metrics)
            if result.fallback_reason:
                metrics["fallback_reason"] = result.fallback_reason

            if result.class_name != "unclassified":
                records.append(ClassificationRecord(
                    target_type="evidence", target_id=ev.evidence_id,
                    agent_tier="micro", agent_name=self.name,
                    taxonomy="incident_family", class_name="quality",
                    severity="high", confidence=result.score,
                    rationale=f"Image defect: {result.label} (score={result.score})",
                    evidence_ids=[ev.evidence_id],
                    metrics=metrics,
                ))
            else:
                records.append(ClassificationRecord(
                    target_type="evidence", target_id=ev.evidence_id,
                    agent_tier="micro", agent_name=self.name,
                    taxonomy="incident_family", class_name="unclassified",
                    severity="info", confidence=result.score,
                    rationale="No defect detected or no labels available",
                    evidence_ids=[ev.evidence_id],
                    metrics=metrics,
                ))
        return records
