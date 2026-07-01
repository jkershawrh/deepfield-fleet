"""Cascade escalation logic — determines what moves from nano to micro to macro."""

from app.domain.models import ClassificationRecord, EvidenceArtifact

MICRO_CONFIDENCE_THRESHOLD = 0.8
MACRO_MODALITY_THRESHOLD = 2


def should_escalate_to_micro(
    nano_results: list[ClassificationRecord],
    evidence: EvidenceArtifact,
) -> bool:
    if evidence.modality in ("image", "audio", "document"):
        return True
    relevant = [r for r in nano_results if evidence.evidence_id in r.evidence_ids]
    for r in relevant:
        if r.class_name in ("actionable", "escalate"):
            return True
        if r.severity in ("high", "critical"):
            return True
        if r.confidence < MICRO_CONFIDENCE_THRESHOLD and r.class_name not in ("normal", "noise"):
            return True
    return False


def should_escalate_to_macro(
    micro_results: list[ClassificationRecord],
    all_evidence: list[EvidenceArtifact],
) -> bool:
    if not micro_results:
        return False
    modalities_with_findings = set()
    for r in micro_results:
        if r.severity in ("high", "critical"):
            for ev in all_evidence:
                if ev.evidence_id in r.evidence_ids:
                    modalities_with_findings.add(ev.modality)
    if len(modalities_with_findings) >= MACRO_MODALITY_THRESHOLD:
        return True
    critical_count = sum(1 for r in micro_results if r.severity == "critical")
    if critical_count > 0:
        return True
    return False
