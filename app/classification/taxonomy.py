"""Classification taxonomies — hardcoded defaults, YAML-configurable later."""

OPERATIONAL_STATES = [
    "normal", "watch", "degraded", "incident", "critical", "unknown",
]

SIGNAL_QUALITIES = [
    "noise", "duplicate", "weak_signal", "actionable",
    "contradictory", "missing_context",
]

INCIDENT_FAMILIES = [
    "infrastructure", "application", "model_serving", "data_pipeline",
    "security", "capacity", "quality", "supply_chain", "human_process", "unknown",
]

ACTION_CLASSES = [
    "observe", "notify", "ticket", "scale", "restart",
    "quarantine", "pause", "rollback", "human_approval", "no_action",
]

ALL_TAXONOMIES = {
    "operational_state": OPERATIONAL_STATES,
    "signal_quality": SIGNAL_QUALITIES,
    "incident_family": INCIDENT_FAMILIES,
    "action_class": ACTION_CLASSES,
}


def is_valid_classification(taxonomy: str, class_name: str) -> bool:
    values = ALL_TAXONOMIES.get(taxonomy)
    if values is None:
        return False
    return class_name in values
