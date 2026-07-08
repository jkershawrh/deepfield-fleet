"""Nanoagent: detects approaching scheduled events for pre-warming."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

name = "event_calendar"

_EVENT_KEYWORDS = ("calendar", "schedule", "event")


def classify(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile],
) -> list[ClassificationRecord]:
    records = []
    for ev in evidence:
        if ev.modality != "event":
            continue
        if not any(kw in ev.artifact_type.lower() for kw in _EVENT_KEYWORDS):
            continue

        event_start_minutes = ev.features.get("event_start_minutes")
        if event_start_minutes is None:
            continue

        expected_users = ev.features.get("expected_users", 0)

        if event_start_minutes <= 5:
            cls, sev = "event_starting", "critical"
        elif event_start_minutes <= 30:
            cls, sev = "pre_warm_needed", "high"
        elif event_start_minutes <= 60:
            cls, sev = "event_approaching", "medium"
        else:
            cls, sev = "event_scheduled", "info"

        records.append(_make_record(
            ev, cls, sev, 0.90,
            f"event in {event_start_minutes}min, {expected_users} expected users",
            labels={"event_start_minutes": event_start_minutes, "expected_users": expected_users},
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
