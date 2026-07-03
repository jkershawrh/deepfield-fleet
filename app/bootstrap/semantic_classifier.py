"""Semantic classifier — LLM analyzes raw samples and proposes configuration."""

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

from app.inference.client import infer

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """Analyze these {n_samples} data samples. Determine modality, domain, and classification config.

Samples:
{samples}

Respond as JSON:
{{"modality":"metric|log|event|text|document","domain":"manufacturing|telecom|healthcare|energy|finance|it_ops","domain_description":"...","schema_mapping":{{"timestamp_field":"...","value_field":"..."}},"features":[{{"name":"...","field":"...","type":"numeric"}}],"taxonomy":{{"operational_state":["normal","watch","degraded","critical"],"incident_family":["...","..."],"action_class":["observe","notify","ticket"]}},"thresholds":{{"field":{{"warning":0,"critical":0}}}},"nano_rules":[{{"name":"...","field":"...","operator":"gt","value":0,"class_name":"degraded","taxonomy":"operational_state","severity":"high"}}],"micro_prompt":"Classify this signal...","macro_prompt":"Correlate these signals...","confidence":0.8,"reasoning":"..."}}}"""


@dataclass
class SourceAnalysis:
    modality: str = "unknown"
    domain: str = "unknown"
    domain_description: str = ""
    schema_mapping: dict = field(default_factory=dict)
    features: list[dict] = field(default_factory=list)
    taxonomy: dict = field(default_factory=dict)
    thresholds: dict = field(default_factory=dict)
    nano_rules: list[dict] = field(default_factory=list)
    micro_prompt: str = ""
    macro_prompt: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    raw_samples: list[dict] = field(default_factory=list)
    inference_latency_ms: float = 0.0
    error: Optional[str] = None


def analyze_samples(samples: list[dict], hints: str = "") -> SourceAnalysis:
    if not samples:
        return SourceAnalysis(error="No samples provided")

    display_samples = samples[:5]
    samples_text = json.dumps(display_samples, default=str)[:1000]

    prompt = ANALYSIS_PROMPT.format(n_samples=len(display_samples), samples=samples_text)
    if hints:
        prompt += f"\n\nAdditional context from the user: {hints}"

    result = infer(
        prompt=prompt,
        system_prompt="You are a data analysis agent. Respond only with valid JSON. No markdown, no explanation.",
        tier="macro",
        max_tokens=800,
    )

    if result is None:
        return SourceAnalysis(
            error="No LLM available — set LITELLM_API_BASE to enable semantic analysis",
            raw_samples=display_samples,
        )

    if result.error:
        return SourceAnalysis(
            error=f"LLM error: {result.error[:200]}",
            raw_samples=display_samples,
            inference_latency_ms=result.latency_ms,
        )

    try:
        output = result.output.strip()
        if output.startswith("```"):
            output = output.split("```")[1]
            if output.startswith("json"):
                output = output[4:]
        parsed = json.loads(output)
    except (json.JSONDecodeError, IndexError) as e:
        return SourceAnalysis(
            error=f"Failed to parse LLM response: {str(e)[:100]}",
            reasoning=result.output[:500],
            raw_samples=display_samples,
            inference_latency_ms=result.latency_ms,
        )

    return SourceAnalysis(
        modality=parsed.get("modality", "unknown"),
        domain=parsed.get("domain", "unknown"),
        domain_description=parsed.get("domain_description", ""),
        schema_mapping=parsed.get("schema_mapping", {}),
        features=parsed.get("features", []),
        taxonomy=parsed.get("taxonomy", {}),
        thresholds=parsed.get("thresholds", {}),
        nano_rules=parsed.get("nano_rules", []),
        micro_prompt=parsed.get("micro_prompt", ""),
        macro_prompt=parsed.get("macro_prompt", ""),
        confidence=min(float(parsed.get("confidence", 0.5)), 1.0),
        reasoning=parsed.get("reasoning", ""),
        raw_samples=display_samples,
        inference_latency_ms=result.latency_ms,
    )
