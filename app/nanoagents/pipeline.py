"""Nanoagent pipeline — runs all multimodal nanoagents in sequence."""

import importlib
from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

AGENT_MODULES = [
    "app.nanoagents.baseline_distance",
    "app.nanoagents.metric_drift",
    "app.nanoagents.log_pattern",
    "app.nanoagents.document_heuristic",
    "app.nanoagents.image_metadata",
    "app.nanoagents.audio_energy",
    "app.nanoagents.evidence_gate",
]


def run_pipeline(
    evidence: list[EvidenceArtifact],
    baseline: Optional[BaselineProfile] = None,
) -> list[ClassificationRecord]:
    all_records = []
    for module_path in AGENT_MODULES:
        module = importlib.import_module(module_path)
        records = module.classify(evidence, baseline)
        all_records.extend(records)
    return all_records
