"""EDD Evaluator — scores multimodal pipeline quality against rubrics.

Each rubric produces a score: healthy, warning, or failing.
The red/green matrix tracks which dimensions are passing at each milestone.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone


def _score(checks: list) -> str:
    levels = [level for _, level in checks]
    if "failing" in levels:
        return "failing"
    if "warning" in levels:
        return "warning"
    return "healthy"


# ---------------------------------------------------------------------------
# Contract compliance (M1)
# ---------------------------------------------------------------------------

def score_contract_compliance(
    models_importable: bool = False,
    all_literals_enforced: bool = False,
    confidence_ranges_enforced: bool = False,
    serialization_roundtrips: bool = False,
) -> dict:
    checks = []
    checks.append(("models_importable", "healthy" if models_importable else "failing"))
    checks.append(("literals_enforced", "healthy" if all_literals_enforced else "failing"))
    checks.append(("confidence_ranges", "healthy" if confidence_ranges_enforced else "failing"))
    checks.append(("serialization", "healthy" if serialization_roundtrips else "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Fixture scenario coverage (M1)
# ---------------------------------------------------------------------------

def score_fixture_scenarios(
    manifest_loadable: bool = False,
    all_modalities_present: bool = False,
    expected_classifications_defined: bool = False,
) -> dict:
    checks = []
    checks.append(("manifest_loadable", "healthy" if manifest_loadable else "failing"))
    checks.append(("modalities_present", "healthy" if all_modalities_present else "failing"))
    checks.append(("classifications_defined", "healthy" if expected_classifications_defined else "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Evidence normalization (M2)
# ---------------------------------------------------------------------------

def score_evidence_normalization(
    modality_coverage: float = 0.0,
    feature_extraction_complete: bool = False,
    artifact_validity_rate: float = 0.0,
) -> dict:
    checks = []
    if modality_coverage >= 0.8:
        checks.append(("modality_coverage", "healthy"))
    elif modality_coverage >= 0.5:
        checks.append(("modality_coverage", "warning"))
    else:
        checks.append(("modality_coverage", "failing"))
    checks.append(("feature_extraction", "healthy" if feature_extraction_complete else "failing"))
    if artifact_validity_rate >= 0.95:
        checks.append(("artifact_validity", "healthy"))
    elif artifact_validity_rate >= 0.8:
        checks.append(("artifact_validity", "warning"))
    else:
        checks.append(("artifact_validity", "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Baseline quality (M2)
# ---------------------------------------------------------------------------

def score_baseline_quality(
    history_coverage: float = 0.0,
    scope_coverage: float = 0.0,
    confidence: float = 0.0,
    has_thresholds: bool = False,
) -> dict:
    checks = []
    if history_coverage >= 0.7:
        checks.append(("history_coverage", "healthy"))
    elif history_coverage >= 0.3:
        checks.append(("history_coverage", "warning"))
    else:
        checks.append(("history_coverage", "failing"))
    if scope_coverage >= 0.8:
        checks.append(("scope_coverage", "healthy"))
    elif scope_coverage >= 0.5:
        checks.append(("scope_coverage", "warning"))
    else:
        checks.append(("scope_coverage", "failing"))
    if confidence >= 0.6:
        checks.append(("confidence", "healthy"))
    elif confidence >= 0.3:
        checks.append(("confidence", "warning"))
    else:
        checks.append(("confidence", "failing"))
    checks.append(("thresholds", "healthy" if has_thresholds else "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Classification accuracy (M3)
# ---------------------------------------------------------------------------

def score_classification_accuracy(
    taxonomy_compliance: float = 0.0,
    confidence_calibration: float = 0.0,
    evidence_linkage: float = 0.0,
) -> dict:
    checks = []
    if taxonomy_compliance >= 0.9:
        checks.append(("taxonomy_compliance", "healthy"))
    elif taxonomy_compliance >= 0.7:
        checks.append(("taxonomy_compliance", "warning"))
    else:
        checks.append(("taxonomy_compliance", "failing"))
    if confidence_calibration >= 0.8:
        checks.append(("confidence_calibration", "healthy"))
    elif confidence_calibration >= 0.5:
        checks.append(("confidence_calibration", "warning"))
    else:
        checks.append(("confidence_calibration", "failing"))
    if evidence_linkage >= 0.9:
        checks.append(("evidence_linkage", "healthy"))
    elif evidence_linkage >= 0.7:
        checks.append(("evidence_linkage", "warning"))
    else:
        checks.append(("evidence_linkage", "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Cascade efficiency (M3)
# ---------------------------------------------------------------------------

def score_cascade_efficiency(
    nano_retention_rate: float = 0.0,
    micro_escalation_rate: float = 0.0,
    macro_escalation_rate: float = 0.0,
) -> dict:
    checks = []
    if 0.3 <= nano_retention_rate <= 0.9:
        checks.append(("nano_retention", "healthy"))
    elif nano_retention_rate > 0:
        checks.append(("nano_retention", "warning"))
    else:
        checks.append(("nano_retention", "failing"))
    if 0.1 <= micro_escalation_rate <= 0.5:
        checks.append(("micro_escalation", "healthy"))
    elif micro_escalation_rate > 0:
        checks.append(("micro_escalation", "warning"))
    else:
        checks.append(("micro_escalation", "failing"))
    if 0.05 <= macro_escalation_rate <= 0.3:
        checks.append(("macro_escalation", "healthy"))
    elif macro_escalation_rate > 0:
        checks.append(("macro_escalation", "warning"))
    else:
        checks.append(("macro_escalation", "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Agent coverage (M3)
# ---------------------------------------------------------------------------

def score_agent_coverage(
    nano_agent_count: int = 0,
    micro_agent_count: int = 0,
    macro_agent_count: int = 0,
    modalities_covered: int = 0,
) -> dict:
    checks = []
    if nano_agent_count >= 5:
        checks.append(("nano_agents", "healthy"))
    elif nano_agent_count >= 2:
        checks.append(("nano_agents", "warning"))
    else:
        checks.append(("nano_agents", "failing"))
    if micro_agent_count >= 3:
        checks.append(("micro_agents", "healthy"))
    elif micro_agent_count >= 1:
        checks.append(("micro_agents", "warning"))
    else:
        checks.append(("micro_agents", "failing"))
    if macro_agent_count >= 3:
        checks.append(("macro_agents", "healthy"))
    elif macro_agent_count >= 1:
        checks.append(("macro_agents", "warning"))
    else:
        checks.append(("macro_agents", "failing"))
    if modalities_covered >= 5:
        checks.append(("modality_coverage", "healthy"))
    elif modalities_covered >= 3:
        checks.append(("modality_coverage", "warning"))
    else:
        checks.append(("modality_coverage", "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# DB graceful degradation
# ---------------------------------------------------------------------------

def score_db_degradation(
    works_without_db: bool = False,
    writes_silently_skipped: bool = False,
    queries_return_empty: bool = False,
) -> dict:
    checks = []
    checks.append(("works_without_db", "healthy" if works_without_db else "failing"))
    checks.append(("writes_skipped", "healthy" if writes_silently_skipped else "failing"))
    checks.append(("queries_empty", "healthy" if queries_return_empty else "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Safety (M4)
# ---------------------------------------------------------------------------

def score_safety(
    non_destructive_actions: bool = False,
    human_approval_gates: bool = False,
    no_silent_learning: bool = False,
    action_loop_functional: bool = False,
) -> dict:
    checks = []
    checks.append(("non_destructive", "healthy" if non_destructive_actions else "failing"))
    checks.append(("human_approval", "healthy" if human_approval_gates else "failing"))
    checks.append(("no_silent_learning", "healthy" if no_silent_learning else "failing"))
    checks.append(("action_loop", "healthy" if action_loop_functional else "failing"))
    return {"score": _score(checks), "checks": checks}


# ---------------------------------------------------------------------------
# Full evaluation
# ---------------------------------------------------------------------------

def evaluate_pipeline(**kwargs) -> dict:
    rubrics = {
        "contract_compliance": score_contract_compliance(**{
            k: kwargs.get(k, False) for k in [
                "models_importable", "all_literals_enforced",
                "confidence_ranges_enforced", "serialization_roundtrips",
            ]
        }),
        "fixture_scenarios": score_fixture_scenarios(**{
            k: kwargs.get(k, False) for k in [
                "manifest_loadable", "all_modalities_present",
                "expected_classifications_defined",
            ]
        }),
        "evidence_normalization": score_evidence_normalization(**{
            k: kwargs.get(k, 0.0) for k in [
                "modality_coverage", "artifact_validity_rate",
            ] } | {"feature_extraction_complete": kwargs.get("feature_extraction_complete", False)}
        ),
        "baseline_quality": score_baseline_quality(**{
            k: kwargs.get(k, 0.0) for k in [
                "history_coverage", "scope_coverage", "confidence",
            ] } | {"has_thresholds": kwargs.get("has_thresholds", False)}
        ),
        "classification_accuracy": score_classification_accuracy(**{
            k: kwargs.get(k, 0.0) for k in [
                "taxonomy_compliance", "confidence_calibration", "evidence_linkage",
            ]
        }),
        "cascade_efficiency": score_cascade_efficiency(**{
            k: kwargs.get(k, 0.0) for k in [
                "nano_retention_rate", "micro_escalation_rate", "macro_escalation_rate",
            ]
        }),
        "agent_coverage": score_agent_coverage(**{
            k: kwargs.get(k, 0) for k in [
                "nano_agent_count", "micro_agent_count",
                "macro_agent_count", "modalities_covered",
            ]
        }),
        "db_graceful_degradation": score_db_degradation(**{
            k: kwargs.get(k, False) for k in [
                "works_without_db", "writes_silently_skipped", "queries_return_empty",
            ]
        }),
        "safety": score_safety(**{
            k: kwargs.get(k, False) for k in [
                "non_destructive_actions", "human_approval_gates",
                "no_silent_learning", "action_loop_functional",
            ]
        }),
    }

    scores = [r["score"] for r in rubrics.values()]
    if "failing" in scores:
        overall = "failing"
    elif "warning" in scores:
        overall = "warning"
    else:
        overall = "healthy"

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rubrics": rubrics,
        "overall": overall,
    }
