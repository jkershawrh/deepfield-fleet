"""Classification taxonomies — loads from YAML config, falls back to hardcoded."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_HARDCODED = {
    "operational_state": ["normal", "watch", "degraded", "incident", "critical", "unknown"],
    "signal_quality": ["noise", "duplicate", "weak_signal", "actionable", "contradictory", "missing_context"],
    "incident_family": ["infrastructure", "application", "model_serving", "data_pipeline", "security", "capacity", "quality", "supply_chain", "human_process", "unknown"],
    "action_class": ["observe", "notify", "ticket", "scale", "restart", "quarantine", "pause", "rollback", "human_approval", "no_action"],
}

_loaded: Optional[dict] = None


def _get_taxonomies() -> dict:
    global _loaded
    if _loaded is not None:
        return _loaded
    try:
        from app.bootstrap.config_loader import load_taxonomies
        _loaded = load_taxonomies()
        logger.info("Taxonomies loaded from config (%d categories)", len(_loaded))
    except Exception:
        _loaded = dict(_HARDCODED)
    return _loaded


def reload():
    global _loaded
    _loaded = None


OPERATIONAL_STATES = _HARDCODED["operational_state"]
SIGNAL_QUALITIES = _HARDCODED["signal_quality"]
INCIDENT_FAMILIES = _HARDCODED["incident_family"]
ACTION_CLASSES = _HARDCODED["action_class"]
ALL_TAXONOMIES = _HARDCODED


def is_valid_classification(taxonomy: str, class_name: str) -> bool:
    taxonomies = _get_taxonomies()
    values = taxonomies.get(taxonomy)
    if values is None:
        return False
    return class_name in values
