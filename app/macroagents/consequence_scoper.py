"""Macroagent: consequence scoper. Assesses blast radius of predicted SLO breaches."""

from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact


name = "consequence_scoper"


def reason(
    evidence: list[EvidenceArtifact],
    classifications: list[ClassificationRecord],
    baseline: Optional[BaselineProfile] = None,
) -> list[ClassificationRecord]:
    """Assess the blast radius when SLO breach or capacity saturation is predicted.

    Examines classifications from nanoagents and microagents for:
    - slo_breach_predicted / slo_breach_imminent
    - capacity_saturated / capacity_pressure
    - queue_overflow

    For each, computes:
    - affected_models: which models are impacted
    - affected_tenants: estimated tenant count
    - user_impact: estimated users affected
    - severity_score: users x violation_magnitude x priority
    - requires_human_gate: True if severity_score exceeds critical threshold
    """
    records = []

    # Find critical classifications that need consequence scoping
    critical_classifications = [
        c for c in classifications
        if c.class_name in (
            "slo_breach_predicted", "slo_breach_imminent",
            "capacity_saturated", "queue_overflow",
        )
    ]

    if not critical_classifications:
        return records

    # Gather context from evidence
    context = _gather_context(evidence)

    for classification in critical_classifications:
        scope = _compute_blast_radius(classification, context)
        severity_score = _compute_severity_score(scope)
        requires_human = severity_score > 100  # critical threshold

        overall_severity = "critical" if severity_score > 100 else "high" if severity_score > 50 else "medium"

        records.append(ClassificationRecord(
            target_type="finding",
            target_id=classification.classification_id,
            agent_tier="macro",
            agent_name=name,
            taxonomy="fleet.consequence",
            class_name="blast_radius_assessed",
            severity=overall_severity,
            confidence=classification.confidence * 0.9,  # slightly lower than source
            rationale=(
                f"Blast radius for {classification.class_name}: "
                f"{scope['affected_models']} model(s), "
                f"~{scope['estimated_users']} users affected, "
                f"severity score {severity_score:.0f}. "
                f"{'REQUIRES HUMAN APPROVAL.' if requires_human else 'Auto-action permitted.'}"
            ),
            evidence_ids=classification.evidence_ids,
            labels={
                "source_classification": classification.class_name,
                "requires_human_gate": requires_human,
            },
            metrics={
                "affected_models": scope["affected_models"],
                "affected_tenants": scope["affected_tenants"],
                "estimated_users": scope["estimated_users"],
                "severity_score": severity_score,
                "violation_magnitude": scope["violation_magnitude"],
                "requires_human_gate": requires_human,
            },
        ))

    return records


def _gather_context(evidence: list[EvidenceArtifact]) -> dict:
    """Extract context from evidence: active models, tenant count, user estimates."""
    models = set()
    tenants = set()
    total_users = 0

    for ev in evidence:
        if ev.features.get("model"):
            models.add(ev.features["model"])
        if ev.features.get("models"):
            for m in ev.features["models"]:
                models.add(m)
        if ev.features.get("tenant_id"):
            tenants.add(ev.features["tenant_id"])
        if ev.features.get("active_users"):
            total_users = max(total_users, int(ev.features["active_users"]))
        if ev.features.get("expected_users"):
            total_users = max(total_users, int(ev.features["expected_users"]))

    return {
        "models": models or {"unknown"},
        "tenants": tenants or {"default"},
        "total_users": total_users or 10,  # conservative default
    }


def _compute_blast_radius(classification: ClassificationRecord, context: dict) -> dict:
    """Compute the blast radius of a predicted incident."""
    # How many models affected
    affected_models = len(context["models"])

    # How many tenants
    affected_tenants = len(context["tenants"])

    # User estimate
    estimated_users = context["total_users"]

    # Violation magnitude (from classification metrics or severity)
    magnitude = 1.0
    if classification.metrics.get("forecast_value") and classification.metrics.get("slo_target"):
        forecast = classification.metrics["forecast_value"]
        target = classification.metrics["slo_target"]
        if target > 0:
            magnitude = forecast / target  # >1.0 means exceeding SLO
    elif classification.severity == "critical":
        magnitude = 2.0
    elif classification.severity == "high":
        magnitude = 1.5

    return {
        "affected_models": affected_models,
        "affected_tenants": affected_tenants,
        "estimated_users": estimated_users,
        "violation_magnitude": magnitude,
    }


def _compute_severity_score(scope: dict) -> float:
    """Score = users x violation_magnitude x model_count.

    >100 = critical (requires human gate)
    >50  = high (auto-action with monitoring)
    >10  = medium (auto-action)
    """
    return (
        scope["estimated_users"]
        * scope["violation_magnitude"]
        * scope["affected_models"]
    )
