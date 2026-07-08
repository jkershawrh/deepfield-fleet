"""Nanoagent: detects when inference request queue depth grows beyond healthy levels."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "queue_depth"

_QUEUE_KEYWORDS = ("queue", "inflight", "pending")
_DEFAULT_CAPACITY = 20


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "metric":
            continue
        if not any(kw in ev.artifact_type.lower() for kw in _QUEUE_KEYWORDS):
            continue

        depth = ev.features.get("depth")
        if depth is None:
            depth = ev.features.get("value")
        if depth is None:
            continue

        capacity = ev.features.get("capacity", _DEFAULT_CAPACITY)
        if capacity == 0:
            continue

        ratio = depth / capacity

        if ratio > 0.90:
            cls, sev = "queue_overflow", "critical"
        elif ratio > 0.70:
            cls, sev = "queue_pressure", "high"
        elif ratio > 0.40:
            cls, sev = "queue_elevated", "medium"
        else:
            cls, sev = "queue_normal", "info"

        records.append(_make_record(
            ev, cls, sev, 0.85,
            f"depth={depth}, capacity={capacity}, ratio={ratio:.2f}",
            labels={"depth": depth, "capacity": capacity, "ratio": ratio},
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
