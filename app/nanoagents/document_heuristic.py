"""Nanoagent: document type and sensitivity classification."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "document_heuristic"


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "document":
            continue
        text = (ev.content_text or "").lower()
        has_keywords = any(kw in text for kw in [
            "error", "failure", "warning", "critical", "urgent",
            "maintenance", "inspection", "defect", "anomaly",
        ])
        if has_keywords:
            records.append(_make_record(ev, "actionable", "medium", 0.65,
                                        "Document contains actionable keywords"))
        else:
            records.append(_make_record(ev, "noise", "info", 0.7,
                                        "No actionable keywords found"))
    return records


def _make_record(ev, class_name, severity, confidence, rationale):
    return ClassificationRecord(
        target_type="evidence", target_id=ev.evidence_id,
        agent_tier="nano", agent_name=name,
        taxonomy="signal_quality", class_name=class_name,
        severity=severity, confidence=confidence, rationale=rationale,
        evidence_ids=[ev.evidence_id],
    )
