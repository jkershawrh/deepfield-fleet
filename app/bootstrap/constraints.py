"""Evidence-based constraint evaluation.

Constraints require accumulated evidence before triggering — not a single
event, but a pattern of evidence building a case.
"""

from typing import Optional

from app.domain.models import ClassificationRecord, ConstraintRule, EvidenceArtifact


_OPERATORS = {
    "gt": lambda a, b: float(a) > float(b),
    "lt": lambda a, b: float(a) < float(b),
    "gte": lambda a, b: float(a) >= float(b),
    "lte": lambda a, b: float(a) <= float(b),
    "eq": lambda a, b: str(a) == str(b),
    "ne": lambda a, b: str(a) != str(b),
    "contains": lambda a, b: str(b) in str(a),
}


def evaluate_constraint(
    rule: ConstraintRule,
    classifications: list[ClassificationRecord],
    evidence: list[EvidenceArtifact],
) -> Optional[ClassificationRecord]:
    if rule.constraint_type == "evidence_based":
        return _evaluate_evidence_based(rule, classifications, evidence)
    elif rule.constraint_type == "single_event":
        return _evaluate_single_event(rule, classifications, evidence)
    return None


def _evaluate_evidence_based(
    rule: ConstraintRule,
    classifications: list[ClassificationRecord],
    evidence: list[EvidenceArtifact],
) -> Optional[ClassificationRecord]:
    met_count = 0

    for condition in rule.conditions:
        if condition.get("type") == "classification":
            target_class = condition.get("class_name", "")
            min_conf = condition.get("min_confidence", 0.0)
            matching = [
                c for c in classifications
                if c.class_name == target_class and c.confidence >= min_conf
            ]
            if matching:
                met_count += 1

        elif condition.get("type") == "evidence":
            modality = condition.get("modality")
            feature = condition.get("feature", "")
            operator = condition.get("operator", "gt")
            value = condition.get("value", 0)
            op_fn = _OPERATORS.get(operator)
            if op_fn:
                for ev in evidence:
                    if modality and ev.modality != modality:
                        continue
                    feat_val = ev.features.get(feature)
                    if feat_val is not None:
                        try:
                            if op_fn(feat_val, value):
                                met_count += 1
                                break
                        except (ValueError, TypeError):
                            pass

    if met_count >= rule.min_evidence_count:
        target_id = classifications[0].target_id if classifications else (evidence[0].evidence_id if evidence else None)
        if target_id is None:
            return None
        return ClassificationRecord(
            target_type="evidence",
            target_id=target_id,
            agent_tier="macro",
            agent_name=f"constraint:{rule.name}",
            taxonomy=rule.taxonomy,
            class_name=rule.class_name_on_violation,
            severity=rule.severity,
            confidence=min(met_count / len(rule.conditions), 1.0) if rule.conditions else 0.5,
            rationale=f"Constraint '{rule.name}' violated: {met_count}/{len(rule.conditions)} conditions met (requires {rule.min_evidence_count}). {rule.description}",
        )
    return None


def _evaluate_single_event(
    rule: ConstraintRule,
    classifications: list[ClassificationRecord],
    evidence: list[EvidenceArtifact],
) -> Optional[ClassificationRecord]:
    for condition in rule.conditions:
        if condition.get("type") == "evidence":
            field = condition.get("feature", condition.get("field", ""))
            operator = condition.get("operator", "eq")
            value = condition.get("value")
            op_fn = _OPERATORS.get(operator)
            if op_fn:
                for ev in evidence:
                    modality = condition.get("modality")
                    if modality and ev.modality != modality:
                        continue
                    feat_val = ev.features.get(field)
                    if feat_val is not None:
                        try:
                            if op_fn(feat_val, value):
                                return ClassificationRecord(
                                    target_type="evidence",
                                    target_id=ev.evidence_id,
                                    agent_tier="nano",
                                    agent_name=f"constraint:{rule.name}",
                                    taxonomy=rule.taxonomy,
                                    class_name=rule.class_name_on_violation,
                                    severity=rule.severity,
                                    confidence=0.9,
                                    rationale=f"Constraint '{rule.name}': {field}={feat_val} {operator} {value}. {rule.description}",
                                )
                        except (ValueError, TypeError):
                            pass
    return None
