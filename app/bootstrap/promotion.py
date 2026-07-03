"""Agent promotion engine — rules earn their tier through empirical validation.

Ground truth is baseline-derived: evidence within normal ranges = normal,
evidence outside ranges = abnormal. No human labeling required.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import yaml
from pathlib import Path

from collections import defaultdict

from app.bootstrap.rule_engine import RuleBasedNanoagent
from app.domain.models import AgentMaturity, BaselineProfile, ClassificationRecord, EvidenceArtifact

logger = logging.getLogger(__name__)

_THRESHOLDS_PATH = Path(__file__).resolve().parents[2] / "config" / "defaults" / "promotion.yaml"


def _load_thresholds() -> dict:
    try:
        return yaml.safe_load(_THRESHOLDS_PATH.read_text())
    except Exception:
        return {
            "candidate": {"min_samples": 50, "min_accuracy": 0.60, "max_false_positive": 0.30},
            "nano": {"min_samples": 200, "min_accuracy": 0.75, "max_false_positive": 0.15, "max_false_negative": 0.20},
            "micro": {"min_samples": 500, "min_accuracy": 0.85, "max_false_positive": 0.10, "human_reviewed": True},
            "macro": {"min_samples": 1000, "min_accuracy": 0.85, "max_false_positive": 0.05, "human_reviewed": True, "cross_modal_agreement": True},
        }


def _is_abnormal(ev: EvidenceArtifact, baseline: BaselineProfile) -> bool:
    ranges = baseline.normal_ranges.get(ev.artifact_type, {})
    for key, bounds in ranges.items():
        if isinstance(bounds, dict) and "low" in bounds and "high" in bounds:
            val = ev.features.get(key)
            if val is not None and isinstance(val, (int, float)):
                if val < bounds["low"] or val > bounds["high"]:
                    return True
    return False


def evaluate_agent(
    agent: AgentMaturity,
    evidence: list[EvidenceArtifact],
    baseline: BaselineProfile,
) -> AgentMaturity:
    if not evidence:
        return agent

    rule_agent = None
    if agent.config and "condition" in agent.config:
        rule_agent = RuleBasedNanoagent(agent.config)

    tp = 0
    tn = 0
    fp = 0
    fn = 0
    classified = 0

    for ev in evidence:
        actually_abnormal = _is_abnormal(ev, baseline)

        if rule_agent:
            records = rule_agent.classify([ev], baseline)
            agent_flagged = len(records) > 0 and any(
                r.class_name not in ("normal", "noise") for r in records
            )
        else:
            agent_flagged = False

        if agent_flagged:
            classified += 1

        if agent_flagged and actually_abnormal:
            tp += 1
        elif not agent_flagged and not actually_abnormal:
            tn += 1
        elif agent_flagged and not actually_abnormal:
            fp += 1
        elif not agent_flagged and actually_abnormal:
            fn += 1

    total = len(evidence)
    agent.samples_tested = total
    agent.accuracy = (tp + tn) / total if total > 0 else 0.0
    agent.false_positive_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    agent.false_negative_rate = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    agent.coverage = classified / total if total > 0 else 0.0

    if agent.accuracy >= 0.8:
        agent.confidence_calibration = "calibrated"
    elif agent.accuracy >= 0.6:
        agent.confidence_calibration = "rough"
    else:
        agent.confidence_calibration = "none"

    if agent.accuracy >= 0.75 and agent.false_positive_rate <= 0.15:
        agent.rubric_status = "green"
    elif agent.accuracy >= 0.60:
        agent.rubric_status = "yellow"
    else:
        agent.rubric_status = "red"

    return agent


class PromotionEngine:
    def __init__(self):
        self.thresholds = _load_thresholds()

    def check_promotion(self, agent: AgentMaturity) -> AgentMaturity:
        current = agent.tier
        next_tier = self._next_tier(current)
        if next_tier is None:
            return agent

        reqs = self.thresholds.get(next_tier, {})
        if self._meets_requirements(agent, reqs):
            agent.promotion_history.append({
                "from": current,
                "to": next_tier,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "accuracy": agent.accuracy,
                "samples": agent.samples_tested,
                "fp_rate": agent.false_positive_rate,
            })
            agent.tier = next_tier
            agent.promoted_at = datetime.now(timezone.utc)
            agent.rubric_status = "green"
            logger.info("Agent '%s' promoted: %s → %s (accuracy=%.2f, FP=%.2f)",
                        agent.name, current, next_tier, agent.accuracy, agent.false_positive_rate)
        return agent

    def _next_tier(self, current: str) -> Optional[str]:
        order = {"draft": "candidate", "candidate": "nano", "nano": "micro", "micro": "macro"}
        return order.get(current)

    def _meets_requirements(self, agent: AgentMaturity, reqs: dict) -> bool:
        if agent.samples_tested < reqs.get("min_samples", 0):
            return False
        if agent.accuracy < reqs.get("min_accuracy", 0):
            return False
        if agent.false_positive_rate > reqs.get("max_false_positive", 1.0):
            return False
        if "max_false_negative" in reqs and agent.false_negative_rate > reqs["max_false_negative"]:
            return False
        if reqs.get("human_reviewed") and not agent.human_reviewed:
            return False
        if reqs.get("cross_modal_agreement") and not agent.cross_modal_agreement:
            return False
        return True


def run_validation_round(
    agents: list[AgentMaturity],
    evidence: list[EvidenceArtifact],
    baseline: BaselineProfile,
) -> list[AgentMaturity]:
    engine = PromotionEngine()
    updated = []
    for agent in agents:
        evaluated = evaluate_agent(agent, evidence, baseline)
        promoted = engine.check_promotion(evaluated)
        updated.append(promoted)
    return updated


def detect_cross_modal_convergence(
    classifications: list[ClassificationRecord],
    evidence: list[EvidenceArtifact],
    min_modalities: int = 2,
) -> bool:
    evidence_map = {e.evidence_id: e for e in evidence}
    resource_modalities: dict[str, set] = defaultdict(set)

    high_conf = [c for c in classifications if c.confidence >= 0.6 and c.severity in ("high", "critical")]

    for c in high_conf:
        for eid in c.evidence_ids:
            ev = evidence_map.get(eid)
            if ev:
                resource_key = ev.namespace or str(ev.evidence_id)
                resource_modalities[resource_key].add(ev.modality)

    for resource, modalities in resource_modalities.items():
        if len(modalities) >= min_modalities:
            return True
    return False


def get_rubric_matrix(agents: list[AgentMaturity]) -> dict:
    agent_rows = []
    for a in agents:
        agent_rows.append({
            "agent_id": str(a.agent_id),
            "name": a.name,
            "tier": a.tier,
            "rubric_status": a.rubric_status,
            "samples_tested": a.samples_tested,
            "accuracy": round(a.accuracy, 3),
            "false_positive_rate": round(a.false_positive_rate, 3),
            "false_negative_rate": round(a.false_negative_rate, 3),
            "coverage": round(a.coverage, 3),
            "confidence_calibration": a.confidence_calibration,
            "human_reviewed": a.human_reviewed,
            "promotion_history": a.promotion_history,
        })

    greens = sum(1 for a in agents if a.rubric_status == "green")
    yellows = sum(1 for a in agents if a.rubric_status == "yellow")
    total = len(agents)

    if total == 0:
        overall = "red"
    elif greens / total >= 0.5:
        overall = "green"
    elif (greens + yellows) / total >= 0.3:
        overall = "yellow"
    else:
        overall = "red"

    return {
        "overall": overall,
        "total_agents": total,
        "green": greens,
        "yellow": yellows,
        "red": total - greens - yellows,
        "agents": agent_rows,
    }
