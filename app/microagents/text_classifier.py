"""Microagent: text classification — rule-backed with optional LLM inference."""

import json
import re

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.inference.client import infer, is_inference_available
from app.microagents.base import BaseMicroagent

ERROR_PATTERNS = [
    (r'\b(failure|failed|error|crash|down)\b', "infrastructure", "high"),
    (r'\b(bearing|vibration|thermal|defect|wear)\b', "quality", "high"),
    (r'\b(security|breach|unauthorized|exploit)\b', "security", "critical"),
    (r'\b(capacity|full|exceeded|quota)\b', "capacity", "medium"),
    (r'\b(timeout|latency|slow|degraded)\b', "application", "medium"),
]

CLASSIFY_PROMPT = """Classify this text into one incident family.
Families: infrastructure, application, quality, security, capacity, data_pipeline, unknown.
Also assign severity: info, low, medium, high, critical.

Text: {text}

Respond as JSON: {{"family": "...", "severity": "...", "rationale": "..."}}"""


class TextClassifierAgent(BaseMicroagent):
    name = "text_classifier"
    modalities = {"text", "log"}

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            if ev.modality not in self.modalities:
                continue
            text = (ev.content_text or "").lower()

            if is_inference_available():
                record = self._classify_with_llm(ev, text)
            else:
                record = self._classify_with_rules(ev, text)
            records.append(record)
        return records

    def _classify_with_llm(self, ev: EvidenceArtifact, text: str) -> ClassificationRecord:
        result = infer(
            prompt=CLASSIFY_PROMPT.format(text=text[:500]),
            system_prompt="You are a signal classification agent for industrial monitoring. Respond only with JSON.",
            tier="micro", max_tokens=150,
        )
        family = "unclassified"
        severity = "info"
        rationale = "LLM inference"
        model_name = "unknown"
        latency = 0.0

        if result and not result.error:
            model_name = result.model
            latency = result.latency_ms
            try:
                parsed = json.loads(result.output.strip().strip("```json").strip("```"))
                family = parsed.get("family", "unknown")
                severity = parsed.get("severity", "info")
                rationale = parsed.get("rationale", result.output[:100])
            except (json.JSONDecodeError, AttributeError):
                rationale = result.output[:200] if result.output else "LLM parse error"
                fallback = self._classify_with_rules(ev, text)
                family = fallback.class_name
                severity = fallback.severity
        elif result and result.error:
            rationale = f"LLM error: {result.error[:100]} — falling back to rules"
            fallback = self._classify_with_rules(ev, text)
            family = fallback.class_name
            severity = fallback.severity

        valid_families = {"infrastructure", "application", "quality", "security", "capacity", "data_pipeline", "model_serving", "supply_chain", "human_process", "unknown"}
        if family not in valid_families:
            family = "unclassified"
        valid_severities = {"info", "low", "medium", "high", "critical"}
        if severity not in valid_severities:
            severity = "info"

        return ClassificationRecord(
            target_type="evidence", target_id=ev.evidence_id,
            agent_tier="micro", agent_name=self.name,
            taxonomy="incident_family", class_name=family,
            severity=severity, confidence=0.8,
            rationale=rationale,
            evidence_ids=[ev.evidence_id],
            metrics={"model": model_name, "runtime": "llm", "latency_ms": round(latency, 1)},
        )

    def _classify_with_rules(self, ev: EvidenceArtifact, text: str) -> ClassificationRecord:
        for pattern, family, severity in ERROR_PATTERNS:
            if re.search(pattern, text):
                return ClassificationRecord(
                    target_type="evidence", target_id=ev.evidence_id,
                    agent_tier="micro", agent_name=self.name,
                    taxonomy="incident_family", class_name=family,
                    severity=severity, confidence=0.7,
                    rationale=f"Rule match: {pattern}",
                    evidence_ids=[ev.evidence_id],
                    metrics={"model": "rule_backed", "runtime": "cpu"},
                )
        return ClassificationRecord(
            target_type="evidence", target_id=ev.evidence_id,
            agent_tier="micro", agent_name=self.name,
            taxonomy="incident_family", class_name="unclassified",
            severity="info", confidence=0.5,
            rationale="No known pattern matched",
            evidence_ids=[ev.evidence_id],
            metrics={"model": "rule_backed", "runtime": "cpu"},
        )
