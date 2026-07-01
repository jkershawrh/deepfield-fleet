"""Nanoagent: size/hash/fixture-label based image classification."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "image_metadata"


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "image":
            continue
        defect_score = ev.labels.get("surface_defect_score", 0.0)
        defect_type = ev.labels.get("defect_type", "unknown")

        if defect_score > 0.5:
            records.append(_make_record(ev, "actionable", "high", defect_score,
                                        f"defect_type={defect_type}, score={defect_score}"))
        else:
            records.append(_make_record(ev, "normal", "info", 0.7, "No defect detected"))
    return records


def _make_record(ev, class_name, severity, confidence, rationale):
    return ClassificationRecord(
        target_type="evidence", target_id=ev.evidence_id,
        agent_tier="nano", agent_name=name,
        taxonomy="signal_quality", class_name=class_name,
        severity=severity, confidence=min(confidence, 1.0), rationale=rationale,
        evidence_ids=[ev.evidence_id],
    )
