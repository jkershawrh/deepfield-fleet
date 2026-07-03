"""Rule engine — executes nanoagent rules from YAML config.

Each rule config defines:
  name: rule_name
  modality: metric | log | ...
  condition: { field: "vibration_rms", operator: "gt", value: 0.35 }
  classification: { taxonomy: "operational_state", class_name: "degraded", severity: "high", confidence: 0.8 }
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact

logger = logging.getLogger(__name__)

_OPERATORS = {
    "gt": lambda a, b: a > b,
    "lt": lambda a, b: a < b,
    "gte": lambda a, b: a >= b,
    "lte": lambda a, b: a <= b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
    "contains": lambda a, b: str(b) in str(a),
}


class RuleBasedNanoagent:
    def __init__(self, config: dict):
        self.name = config["name"]
        self.modality = config.get("modality")
        self.condition = config["condition"]
        self.classification = config["classification"]

    def classify(
        self,
        evidence: list[EvidenceArtifact],
        baseline: Optional[BaselineProfile] = None,
    ) -> list[ClassificationRecord]:
        records = []
        for ev in evidence:
            if self.modality and ev.modality != self.modality:
                continue
            if self._evaluate(ev):
                val = ev.features.get(self.condition["field"])
                records.append(ClassificationRecord(
                    target_type="evidence",
                    target_id=ev.evidence_id,
                    agent_tier="nano",
                    agent_name=self.name,
                    taxonomy=self.classification["taxonomy"],
                    class_name=self.classification["class_name"],
                    severity=self.classification.get("severity", "medium"),
                    confidence=self.classification.get("confidence", 0.7),
                    rationale=self.classification.get("rationale_template", "{field}={value}").format(
                        field=self.condition["field"], value=val,
                        threshold=self.condition.get("value", ""),
                    ),
                    evidence_ids=[ev.evidence_id],
                ))
        return records

    def _evaluate(self, ev: EvidenceArtifact) -> bool:
        field = self.condition["field"]
        val = ev.features.get(field)
        if val is None:
            return False
        op = _OPERATORS.get(self.condition.get("operator", "gt"))
        if op is None:
            return False
        try:
            return op(float(val), float(self.condition["value"]))
        except (ValueError, TypeError):
            return op(str(val), str(self.condition["value"]))


def load_rules_from_dir(rules_dir: Path) -> list[RuleBasedNanoagent]:
    agents = []
    if not rules_dir.exists():
        return agents
    for yaml_file in sorted(rules_dir.glob("*.yaml")):
        try:
            config = yaml.safe_load(yaml_file.read_text())
            if config and "name" in config and "condition" in config:
                agents.append(RuleBasedNanoagent(config))
                logger.info("Loaded nano rule: %s", config["name"])
        except Exception as e:
            logger.warning("Failed to load rule %s: %s", yaml_file.name, str(e)[:100])
    return agents
