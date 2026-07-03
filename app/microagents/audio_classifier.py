"""Microagent: mock-label/fixture-backed anomaly classification for audio."""

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.microagents.base import BaseMicroagent


class AudioAnomalyClassifierAgent(BaseMicroagent):
    name = "audio_classifier"
    modalities = {"audio"}

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            if ev.modality != "audio":
                continue
            anomaly_score = ev.labels.get("vibration_anomaly_score", 0.0)
            anomaly_type = ev.labels.get("anomaly_type", "unknown")

            if anomaly_score > 0.5:
                records.append(ClassificationRecord(
                    target_type="evidence", target_id=ev.evidence_id,
                    agent_tier="micro", agent_name=self.name,
                    taxonomy="incident_family", class_name="quality",
                    severity="high", confidence=min(anomaly_score, 1.0),
                    rationale=f"Audio anomaly: {anomaly_type} (score={anomaly_score})",
                    evidence_ids=[ev.evidence_id],
                    metrics={"model": "fixture_backed", "runtime": "cpu",
                             "anomaly_type": anomaly_type},
                ))
            else:
                records.append(ClassificationRecord(
                    target_type="evidence", target_id=ev.evidence_id,
                    agent_tier="micro", agent_name=self.name,
                    taxonomy="incident_family", class_name="unclassified",
                    severity="info", confidence=0.5,
                    rationale="No anomaly detected or no labels available",
                    evidence_ids=[ev.evidence_id],
                    metrics={"model": "fixture_backed", "runtime": "cpu"},
                ))
        return records
