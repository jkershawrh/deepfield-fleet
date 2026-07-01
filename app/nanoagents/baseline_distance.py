"""Nanoagent: compares feature values to active baseline thresholds."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "baseline_distance"


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "metric":
            continue
        if baseline is None or not baseline.normal_ranges:
            records.append(_make_record(ev, "unknown", "info", 0.3, "No baseline available"))
            continue

        ranges = baseline.normal_ranges.get(ev.artifact_type, {})
        if not ranges:
            records.append(_make_record(ev, "unknown", "info", 0.3, "No range for artifact type"))
            continue

        max_deviation = 0.0
        deviation_details = []
        for key, bounds in ranges.items():
            if isinstance(bounds, dict) and "low" in bounds and "high" in bounds:
                val = ev.features.get(key)
                if val is not None and isinstance(val, (int, float)):
                    if val < bounds["low"] or val > bounds["high"]:
                        deviation = abs(val - (bounds["low"] + bounds["high"]) / 2)
                        range_width = bounds["high"] - bounds["low"]
                        if range_width > 0:
                            normalized = deviation / (range_width / 2)
                            max_deviation = max(max_deviation, normalized)
                            deviation_details.append(f"{key}={val:.3f} outside [{bounds['low']:.3f}, {bounds['high']:.3f}]")

        if max_deviation > 3.0:
            records.append(_make_record(ev, "critical", "critical", min(0.9, max_deviation / 5), "; ".join(deviation_details)))
        elif max_deviation > 2.0:
            records.append(_make_record(ev, "degraded", "high", min(0.85, max_deviation / 4), "; ".join(deviation_details)))
        elif max_deviation > 1.0:
            records.append(_make_record(ev, "watch", "medium", 0.7, "; ".join(deviation_details)))
        else:
            records.append(_make_record(ev, "normal", "info", 0.9, "Within baseline ranges"))

    return records


def _make_record(ev, class_name, severity, confidence, rationale):
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
    )
