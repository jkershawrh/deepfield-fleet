"""Microagent: rule-backed text classification."""

import re

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.microagents.base import BaseMicroagent

ERROR_PATTERNS = [
    (r'\b(failure|failed|error|crash|down)\b', "infrastructure", "high"),
    (r'\b(bearing|vibration|thermal|defect|wear)\b', "quality", "high"),
    (r'\b(security|breach|unauthorized|exploit)\b', "security", "critical"),
    (r'\b(capacity|full|exceeded|quota)\b', "capacity", "medium"),
    (r'\b(timeout|latency|slow|degraded)\b', "application", "medium"),
]


class TextClassifierAgent(BaseMicroagent):
    name = "text_classifier"
    modalities = {"text", "log"}

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            if ev.modality not in self.modalities:
                continue
            text = (ev.content_text or "").lower()
            matched = False
            for pattern, family, severity in ERROR_PATTERNS:
                if re.search(pattern, text):
                    records.append(ClassificationRecord(
                        target_type="evidence", target_id=ev.evidence_id,
                        agent_tier="micro", agent_name=self.name,
                        taxonomy="incident_family", class_name=family,
                        severity=severity, confidence=0.7,
                        rationale=f"Pattern match: {pattern}",
                        evidence_ids=[ev.evidence_id],
                        metrics={"model": "rule_backed", "runtime": "cpu"},
                    ))
                    matched = True
                    break
            if not matched:
                records.append(ClassificationRecord(
                    target_type="evidence", target_id=ev.evidence_id,
                    agent_tier="micro", agent_name=self.name,
                    taxonomy="incident_family", class_name="unknown",
                    severity="info", confidence=0.5,
                    rationale="No known pattern matched",
                    evidence_ids=[ev.evidence_id],
                    metrics={"model": "rule_backed", "runtime": "cpu"},
                ))
        return records
