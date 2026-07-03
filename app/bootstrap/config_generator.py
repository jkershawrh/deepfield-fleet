"""Config generator — creates YAML configs from semantic analysis."""

import logging
from dataclasses import asdict
from pathlib import Path

import yaml

from app.bootstrap.semantic_classifier import SourceAnalysis

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def generate_configs(analysis: SourceAnalysis, source_name: str = "source") -> dict:
    configs = {}

    if analysis.taxonomy:
        configs["taxonomies"] = analysis.taxonomy
        _write("taxonomies/generated.yaml", analysis.taxonomy)

    if analysis.nano_rules:
        for rule in analysis.nano_rules:
            rule_config = {
                "name": rule.get("name", "rule"),
                "modality": analysis.modality,
                "condition": {
                    "field": rule.get("field", ""),
                    "operator": rule.get("operator", "gt"),
                    "value": rule.get("value", 0),
                },
                "classification": {
                    "taxonomy": rule.get("taxonomy", "operational_state"),
                    "class_name": rule.get("class_name", "degraded"),
                    "severity": rule.get("severity", "high"),
                    "confidence": 0.8,
                    "rationale_template": f"{rule.get('field', 'value')}={{value}} (threshold: {{threshold}})",
                },
            }
            configs[f"nano_rule_{rule['name']}"] = rule_config
            _write(f"agents/nano/{rule.get('name', 'rule')}.yaml", rule_config)

    if analysis.micro_prompt:
        micro_config = {
            "name": f"{source_name}_classifier",
            "tier": "micro",
            "modalities": [analysis.modality],
            "domain": analysis.domain,
            "prompt": analysis.micro_prompt,
            "system_prompt": f"You are a {analysis.domain} signal classification agent. Classify evidence into the appropriate incident family. Respond only with JSON.",
            "taxonomy": "incident_family",
        }
        configs["micro_agent"] = micro_config
        _write(f"agents/micro/{source_name}_classifier.yaml", micro_config)

    if analysis.macro_prompt:
        macro_config = {
            "name": f"{source_name}_reasoner",
            "tier": "macro",
            "domain": analysis.domain,
            "prompt": analysis.macro_prompt,
            "system_prompt": f"You are a {analysis.domain} root cause analysis agent. Correlate evidence across modalities and generate hypotheses. Respond only with JSON.",
        }
        configs["macro_agent"] = macro_config
        _write(f"agents/macro/{source_name}_reasoner.yaml", macro_config)

    if analysis.thresholds:
        _write("baselines/thresholds.yaml", analysis.thresholds)
        configs["thresholds"] = analysis.thresholds

    if analysis.schema_mapping:
        source_config = {
            "name": source_name,
            "modality": analysis.modality,
            "domain": analysis.domain,
            "domain_description": analysis.domain_description,
            "schema": analysis.schema_mapping,
            "features": analysis.features,
        }
        _write(f"sources/{source_name}.yaml", source_config)
        configs["source"] = source_config

    return configs


def _write(relative_path: str, data: dict | list):
    path = _CONFIG_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    logger.info("Generated config: %s", path)
