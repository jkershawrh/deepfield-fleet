"""Nanoagent: known error/warning pattern classifier for log evidence."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "log_pattern"


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "log":
            continue
        error_count = ev.features.get("error_count", 0)
        warn_count = ev.features.get("warn_count", 0)
        crit_count = ev.features.get("crit_count", 0)

        if crit_count > 0:
            records.append(_make_record(ev, "actionable", "critical", 0.9,
                                        f"crit={crit_count}, error={error_count}"))
        elif error_count > 0:
            records.append(_make_record(ev, "actionable", "high", 0.8,
                                        f"error={error_count}, warn={warn_count}"))
        elif warn_count > 0:
            records.append(_make_record(ev, "weak_signal", "medium", 0.6,
                                        f"warn={warn_count}"))
        else:
            records.append(_make_record(ev, "noise", "info", 0.9, "No error/warn patterns"))
    return records


def _make_record(ev, class_name, severity, confidence, rationale):
    return ClassificationRecord(
        target_type="evidence", target_id=ev.evidence_id,
        agent_tier="nano", agent_name=name,
        taxonomy="signal_quality", class_name=class_name,
        severity=severity, confidence=confidence, rationale=rationale,
        evidence_ids=[ev.evidence_id],
    )
