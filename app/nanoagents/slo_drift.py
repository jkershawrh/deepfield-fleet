"""Nanoagent: detects when latency metrics trend toward SLO thresholds."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "slo_drift"

_LATENCY_KEYWORDS = ("latency", "ttft", "p95", "p99")


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "metric":
            continue
        if not any(kw in ev.artifact_type.lower() for kw in _LATENCY_KEYWORDS):
            continue

        value = ev.features.get("value")
        slo_target = ev.features.get("slo_target")
        if value is None or slo_target is None or slo_target == 0:
            continue

        utilization = value / slo_target
        sample_count = ev.features.get("sample_count", 1)
        base_confidence = min(0.95, 0.5 + 0.05 * min(sample_count, 9))

        if utilization > 0.95:
            cls, sev = "slo_breach_imminent", "critical"
        elif utilization > 0.80:
            cls, sev = "slo_degraded", "high"
        elif utilization > 0.60:
            cls, sev = "slo_warning", "medium"
        else:
            cls, sev = "slo_healthy", "info"

        records.append(_make_record(
            ev, cls, sev, base_confidence,
            f"utilization={utilization:.2f} (value={value}, target={slo_target})",
            labels={"slo_utilization": utilization, "metric": ev.artifact_type},
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
