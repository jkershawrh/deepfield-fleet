"""Nanoagent pipeline — runs nanoagents from config, falls back to hardcoded list."""

import importlib
import logging
from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

logger = logging.getLogger(__name__)

_DEFAULT_MODULES = [
    "app.nanoagents.baseline_distance",
    "app.nanoagents.metric_drift",
    "app.nanoagents.log_pattern",
    "app.nanoagents.document_heuristic",
    "app.nanoagents.image_metadata",
    "app.nanoagents.audio_energy",
    "app.nanoagents.evidence_gate",
]

AGENT_MODULES = list(_DEFAULT_MODULES)


def _load_agent_list() -> list[str]:
    try:
        from app.bootstrap.config_loader import load_nano_agent_list
        configured = load_nano_agent_list()
        if configured:
            return configured
    except Exception:
        pass
    return list(_DEFAULT_MODULES)


def run_pipeline(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile] = None,
) -> list[ClassificationRecord]:
    agent_list = _load_agent_list()
    all_records = []
    for module_path in agent_list:
        try:
            module = importlib.import_module(module_path)
            records = module.classify(evidence, baseline)
            all_records.extend(records)
        except Exception as e:
            logger.warning("Nanoagent %s failed: %s", module_path, str(e)[:100])
    return all_records
