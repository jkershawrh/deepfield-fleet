"""Nanoagent: deterministic slope and z-score checks on metric evidence."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "metric_drift"

SLOPE_WARNING = 0.02
SLOPE_CRITICAL = 0.05
Z_WARNING = 2.0
Z_CRITICAL = 3.0


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "metric":
            continue
        slope = ev.features.get("slope", 0.0)
        z_score = abs(ev.features.get("z_score_last", 0.0))

        if slope > SLOPE_CRITICAL or z_score > Z_CRITICAL:
            records.append(_make_record(ev, "degraded", "high", 0.85,
                                        f"slope={slope:.4f}, z={z_score:.2f}"))
        elif slope > SLOPE_WARNING or z_score > Z_WARNING:
            records.append(_make_record(ev, "watch", "medium", 0.7,
                                        f"slope={slope:.4f}, z={z_score:.2f}"))
        else:
            records.append(_make_record(ev, "normal", "info", 0.9,
                                        f"slope={slope:.4f}, z={z_score:.2f}"))
    return records


def _make_record(ev, class_name, severity, confidence, rationale):
    return ClassificationRecord(
        target_type="evidence", target_id=ev.evidence_id,
        agent_tier="nano", agent_name=name,
        taxonomy="operational_state", class_name=class_name,
        severity=severity, confidence=confidence, rationale=rationale,
        evidence_ids=[ev.evidence_id],
    )
