"""Macroagent: generates root-cause hypotheses — template-based with optional LLM."""

import json
from collections import Counter
from typing import Optional

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact
from app.inference.client import infer, is_inference_available

RCA_PROMPT = """You are a root cause analysis agent for industrial monitoring.

Evidence summary:
- {n_evidence} evidence artifacts across {n_modalities} modalities ({modalities})
- Classification distribution: {family_dist}
- Key findings: {findings}

Generate a root cause hypothesis. Consider:
1. Which failure family has the strongest signal across multiple modalities?
2. What is the most likely root cause?
3. What confidence level is appropriate?

Respond as JSON: {{"root_cause": "...", "family": "...", "confidence": 0.0-1.0, "reasoning": "..."}}"""


class RootCauseHypothesisAgent:
    name = "root_cause_hypothesis"

    def reason(
        self,
        evidence: list[EvidenceArtifact],
        classifications: list[ClassificationRecord],
        baseline: Optional[BaselineProfile],
    ) -> list[ClassificationRecord]:
        family_counts = Counter(c.class_name for c in classifications if c.taxonomy == "incident_family")
        modalities = {e.modality for e in evidence}

        if is_inference_available():
            return self._reason_with_llm(evidence, classifications, family_counts, modalities)
        return self._reason_with_template(evidence, classifications, family_counts, modalities)

    def _reason_with_llm(self, evidence, classifications, family_counts, modalities):
        high_conf = [c for c in classifications if c.confidence >= 0.7 and c.severity in ("high", "critical")]
        findings = "; ".join(f"{c.agent_name}: {c.class_name} ({c.severity})" for c in high_conf[:5])

        result = infer(
            prompt=RCA_PROMPT.format(
                n_evidence=len(evidence), n_modalities=len(modalities),
                modalities=", ".join(sorted(modalities)),
                family_dist=dict(family_counts), findings=findings or "none",
            ),
            system_prompt="You are a root cause analysis agent. Respond only with JSON.",
            tier="macro", max_tokens=300,
        )

        top_family = family_counts.most_common(1)[0][0] if family_counts else "unknown"
        hypothesis = f"Root cause hypothesis: {top_family}"
        confidence = 0.7 if len(modalities) >= 3 else 0.5
        model_name = "unknown"
        latency = 0.0

        if result and not result.error:
            model_name = result.model
            latency = result.latency_ms
            try:
                parsed = json.loads(result.output.strip().strip("```json").strip("```"))
                top_family = parsed.get("family", top_family)
                confidence = min(parsed.get("confidence", confidence), 1.0)
                hypothesis = parsed.get("reasoning", result.output[:200])
            except (json.JSONDecodeError, AttributeError):
                hypothesis = result.output[:200] if result.output else hypothesis
        elif result and result.error:
            hypothesis = f"LLM error (falling back): {result.error[:80]}. Template: {hypothesis}"

        valid = {"infrastructure", "application", "quality", "security", "capacity", "data_pipeline", "model_serving", "supply_chain", "human_process", "unknown"}
        if top_family not in valid:
            top_family = "unknown"

        return [ClassificationRecord(
            target_type="incident",
            target_id=evidence[0].evidence_id if evidence else classifications[0].target_id,
            agent_tier="macro", agent_name=self.name,
            taxonomy="incident_family", class_name=top_family,
            severity="high" if len(modalities) >= 3 else "medium",
            confidence=confidence,
            rationale=hypothesis,
            evidence_ids=[e.evidence_id for e in evidence],
            metrics={"model": model_name, "runtime": "llm", "latency_ms": round(latency, 1)},
        )]

    def _reason_with_template(self, evidence, classifications, family_counts, modalities):
        top_family = family_counts.most_common(1)[0][0] if family_counts else "unknown"
        hypothesis = (
            f"Root cause hypothesis: {top_family}. "
            f"Based on {len(evidence)} evidence artifacts across {len(modalities)} modalities "
            f"({', '.join(sorted(modalities))}). "
            f"Classification distribution: {dict(family_counts)}."
        )
        return [ClassificationRecord(
            target_type="incident",
            target_id=evidence[0].evidence_id if evidence else classifications[0].target_id,
            agent_tier="macro", agent_name=self.name,
            taxonomy="incident_family", class_name=top_family,
            severity="high" if len(modalities) >= 3 else "medium",
            confidence=0.7 if len(modalities) >= 3 else 0.5,
            rationale=hypothesis,
            evidence_ids=[e.evidence_id for e in evidence],
            metrics={"model": "template", "runtime": "cpu"},
        )]
