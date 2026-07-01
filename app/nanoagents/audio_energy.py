"""Nanoagent: RMS/duration/fixture-label based audio classification."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "audio_energy"


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "audio":
            continue
        anomaly_score = ev.labels.get("vibration_anomaly_score", 0.0)
        anomaly_type = ev.labels.get("anomaly_type", "unknown")

        if anomaly_score > 0.5:
            records.append(_make_record(ev, "actionable", "high", anomaly_score,
                                        f"anomaly_type={anomaly_type}, score={anomaly_score}"))
        else:
            records.append(_make_record(ev, "normal", "info", 0.7, "No anomaly detected"))
    return records


def _make_record(ev, class_name, severity, confidence, rationale):
    return ClassificationRecord(
        target_type="evidence", target_id=ev.evidence_id,
        agent_tier="nano", agent_name=name,
        taxonomy="signal_quality", class_name=class_name,
        severity=severity, confidence=min(confidence, 1.0), rationale=rationale,
        evidence_ids=[ev.evidence_id],
    )
