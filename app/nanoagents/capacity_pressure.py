"""Nanoagent: detects when CPU utilization or capacity approaches limits."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "capacity_pressure"

_CAPACITY_KEYWORDS = ("cpu", "utilization", "capacity")


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "metric":
            continue
        if not any(kw in ev.artifact_type.lower() for kw in _CAPACITY_KEYWORDS):
            continue

        utilization = ev.features.get("utilization")
        if utilization is None:
            utilization = ev.features.get("value")
        if utilization is None:
            continue

        if utilization > 0.90:
            cls, sev = "capacity_saturated", "critical"
        elif utilization > 0.75:
            cls, sev = "capacity_pressure", "high"
        elif utilization > 0.50:
            cls, sev = "capacity_elevated", "medium"
        else:
            cls, sev = "capacity_normal", "info"

        records.append(_make_record(
            ev, cls, sev, 0.85,
            f"utilization={utilization:.2f}",
            labels={"utilization": utilization},
        ))

    return records


def _make_record(ev, class_name, severity, confidence, rationale, labels=None):
    return ClassificationRecord(
        target_type="evidence",
        target_id=ev.evidence_id,
        agent_tier="nano",
        agent_name=name,
        taxonomy="operational_state",
        class_name=class_name,
        severity=severity,
        confidence=confidence,
        rationale=rationale,
        evidence_ids=[ev.evidence_id],
        labels=labels or {},
    )
