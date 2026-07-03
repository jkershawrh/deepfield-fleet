"""Configurable microagent — LLM-backed classifier from bootstrap-generated prompt."""

import json

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.inference.client import infer, is_inference_available
from app.microagents.base import BaseMicroagent


class ConfigurableMicroagent(BaseMicroagent):
    def __init__(self, config: dict):
        self.name = config.get("name", "configurable")
        self.modalities = set(config.get("modalities", []))
        self.prompt_template = config.get("prompt", "Classify this signal.")
        self.system_prompt = config.get("system_prompt", "You are a classification agent. Respond only with JSON.")
        self.taxonomy = config.get("taxonomy", "incident_family")

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            if self.modalities and ev.modality not in self.modalities:
                continue

            if is_inference_available():
                record = self._classify_with_llm(ev)
            else:
                record = self._classify_fallback(ev)
            records.append(record)
        return records

    def _classify_with_llm(self, ev: EvidenceArtifact) -> ClassificationRecord:
        content = ev.content_text or json.dumps(ev.features)
        result = infer(
            prompt=f"{self.prompt_template}\n\nEvidence ({ev.modality}/{ev.artifact_type}):\n{content[:500]}",
            system_prompt=self.system_prompt,
            tier="micro", max_tokens=150,
        )

        class_name = "unclassified"
        severity = "info"
        confidence = 0.5
        rationale = "LLM classification"
        model_name = "unknown"
        latency = 0.0

        if result and not result.error:
            model_name = result.model
            latency = result.latency_ms
            confidence = 0.8
            try:
                parsed = json.loads(result.output.strip().strip("```json").strip("```"))
                class_name = parsed.get("family", parsed.get("class", "unclassified"))
                severity = parsed.get("severity", "info")
                rationale = parsed.get("rationale", result.output[:100])
            except (json.JSONDecodeError, AttributeError):
                rationale = result.output[:200] if result.output else "LLM parse error"

        return ClassificationRecord(
            target_type="evidence", target_id=ev.evidence_id,
            agent_tier="micro", agent_name=self.name,
            taxonomy=self.taxonomy, class_name=class_name,
            severity=severity, confidence=confidence,
            rationale=rationale,
            evidence_ids=[ev.evidence_id],
            metrics={"model": model_name, "runtime": "llm", "latency_ms": round(latency, 1)},
        )

    def _classify_fallback(self, ev: EvidenceArtifact) -> ClassificationRecord:
        return ClassificationRecord(
            target_type="evidence", target_id=ev.evidence_id,
            agent_tier="micro", agent_name=self.name,
            taxonomy=self.taxonomy, class_name="unclassified",
            severity="info", confidence=0.3,
            rationale="No LLM available — configurable agent requires inference endpoint",
            evidence_ids=[ev.evidence_id],
            metrics={"model": "none", "runtime": "fallback"},
        )
