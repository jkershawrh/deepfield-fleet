"""Nanoagent: decides whether evidence should be ignored, retained, or escalated."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "evidence_gate"

ESCALATION_MODALITIES = {"image", "audio", "document"}


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality in ESCALATION_MODALITIES:
            has_labels = bool(ev.labels)
            has_content = bool(ev.content_text)
            if has_labels or has_content:
                records.append(_make_record(ev, "actionable", "medium", 0.7,
                                            f"Modality {ev.modality} with content/labels — escalate to micro"))
            else:
                records.append(_make_record(ev, "missing_context", "low", 0.5,
                                            f"Modality {ev.modality} without content — retain"))
        elif ev.modality == "metric":
            z_score = abs(ev.features.get("z_score_last", 0.0))
            slope = abs(ev.features.get("slope", 0.0))
            if z_score > 2.0 or slope > 0.02:
                records.append(_make_record(ev, "actionable", "medium", 0.75,
                                            f"Metric drift detected — z={z_score:.2f}, slope={slope:.4f}"))
            else:
                records.append(_make_record(ev, "normal", "info", 0.85, "Metric within normal bounds"))
        elif ev.modality == "log":
            error_count = ev.features.get("error_count", 0)
            if error_count > 0:
                records.append(_make_record(ev, "actionable", "high", 0.8,
                                            f"Log has {error_count} errors — escalate"))
            else:
                records.append(_make_record(ev, "noise", "info", 0.8, "Log is informational"))
        else:
            records.append(_make_record(ev, "weak_signal", "low", 0.5,
                                        f"Unknown modality {ev.modality} — retain"))
    return records


def _make_record(ev, class_name, severity, confidence, rationale):
    return ClassificationRecord(
        target_type="evidence", target_id=ev.evidence_id,
        agent_tier="nano", agent_name=name,
        taxonomy="signal_quality", class_name=class_name,
        severity=severity, confidence=confidence, rationale=rationale,
        evidence_ids=[ev.evidence_id],
    )
