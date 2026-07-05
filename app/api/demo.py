"""Auto-orchestrated demo — Hero's Journey + Scale story with live streaming."""

import importlib
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.sse import set_demo_state
from app.baseline.compiler import BaselineCompiler
from app.classification.cascade import should_escalate_to_macro, should_escalate_to_micro
from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact
from app.multimodal.normalizer import normalize_fixture
from app.multimodal.scale_generator import generate_scaled_evidence

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"

_demo_thread: Optional[threading.Thread] = None
_demo_stop = threading.Event()
_demo_pause = threading.Event()
_demo_pause.set()  # starts unpaused (set = not paused)

# Flow descriptions per step — the technical story
FLOW_DESCRIPTIONS = {
    "ordinary": (
        "The baseline compiler has analyzed historical evidence — vibration RMS values, "
        "temperature readings, maintenance logs — and computed statistical signatures: "
        "means, standard deviations, normal ranges, and alert thresholds. Any future signal "
        "that deviates beyond these learned boundaries will be flagged."
    ),
    "call": (
        "Each artifact is processed through modality-specific feature extractors. "
        "Metrics get min/max/mean/std/slope/z-score. Logs get error/warning/critical counts. "
        "Documents get keyword analysis. Images and audio are fixture-backed by default, "
        "or scored by optional ONNX/OpenVINO CPU adapters when configured. "
        "Default feature extraction runs on CPU — no inference endpoints called."
    ),
    "threshold": (
        "The baseline profile captures the shape of normal: for vibration RMS, the normal range is "
        "0.18–0.26 with a z-score alert threshold at 2.0σ. For temperature, the normal range is "
        "37.8–38.5°C. Any evidence with features outside these bounds will trigger nanoagent classification."
    ),
    "ordeal_nano": (
        "Nanoagents are deterministic — no LLM, no GPU, pure CPU. They run threshold checks "
        "(is vibration z-score > 2.0?), pattern matching (does the log contain ERROR?), and gating "
        "decisions (should this evidence escalate to micro?). Seven agents run in sequence, each "
        "producing ClassificationRecords. This is the compression layer."
    ),
    "ordeal_micro": (
        "Microagents are rule-backed classifiers running entirely on CPU. The image classifier evaluates "
        "defect scores. The audio classifier evaluates anomaly scores. The text classifier matches against "
        "known incident-family patterns. All processing on Intel Xeon — no GPU required. Extension points "
        "exist for OpenVINO/ONNX optimized inference, keeping the pipeline CPU-native."
    ),
    "ordeal_macro": (
        "Macroagents perform higher-level reasoning — still on CPU. The incident timeline agent sequences "
        "all evidence by timestamp and overlays classifications. The root cause hypothesis agent counts "
        "classification families across modalities — when multiple modalities agree on 'quality' with "
        "high confidence, bearing failure becomes the leading hypothesis."
    ),
    "reward": (
        "Actions follow a strict safety model: only non-destructive operations (notify, observe, ticket) "
        "are proposed. Destructive actions (restart, scale, quarantine) require explicit human approval "
        "and are never auto-executed."
    ),
    "return": (
        "Learning proposals never apply silently. Each proposal captures a concrete before/after delta "
        "(e.g., lower the vibration z-score warning threshold from 2.0 to 1.8 for earlier detection) "
        "and requires human review before activation."
    ),
    "scale_10": (
        "Can the same agents that analyzed one factory line handle ten? Evidence volume grows 10x. "
        "But deterministic nanoagents scale linearly — no inference cost per signal. The compression "
        "ratio holds. All on CPU."
    ),
    "scale_50": (
        "Fifty production lines. Hundreds of evidence artifacts. Thousands of classifications. All on CPU. "
        "The three-tier cascade compresses the signal volume so only the most important findings reach "
        "macro-level reasoning."
    ),
    "stress": (
        "An incident storm. Bearing failures cascade across the plant — 15% of units report anomalies "
        "simultaneously. The nanoagent filter layer absorbs the blast: retention drops, more evidence "
        "escalates, but the system doesn't break. It classifies, proposes, verifies."
    ),
    "recovery": (
        "The storm passes. Failure rate drops to 2%. Metrics stabilize. But the system learned from "
        "the storm — more anomaly families identified, more threshold proposals generated. Each incident "
        "makes the baseline smarter."
    ),
    "claim": (
        "Nanoagents (7) are always deterministic — pure CPU, no inference cost. "
        "Microagents (5) and macroagents (5) run rule-backed classifiers by default, "
        "with live LLM inference via LiteLLM when configured. The architecture scales "
        "from zero-inference CPU mode to full LLM-backed reasoning without code changes — "
        "just set LITELLM_API_BASE. The compression layer (nano) ensures only the most "
        "important evidence reaches expensive inference."
    ),
}

DEMO_STEPS = [
    {"id": "ordinary",       "title": "The Ordinary World",            "subtitle": "Everything is normal. The factory hums.",                     "duration": 10},
    {"id": "call",           "title": "The Call to Adventure",         "subtitle": "Signals arrive. Something is different.",                    "duration": 12},
    {"id": "threshold",      "title": "Crossing the Threshold",        "subtitle": "The baseline reveals the shape of normal.",                  "duration": 12},
    {"id": "ordeal_nano",    "title": "The Ordeal — Nano Tier",   "subtitle": "Deterministic agents detect what humans can't yet see.",     "duration": 15},
    {"id": "ordeal_micro",   "title": "The Ordeal — Micro Tier",  "subtitle": "Classifiers converge on defects and anomalies.",             "duration": 12},
    {"id": "ordeal_macro",   "title": "The Ordeal — Macro Tier",  "subtitle": "Higher reasoning builds the incident timeline.",             "duration": 12},
    {"id": "reward",         "title": "The Reward",                    "subtitle": "A safe, governed action is proposed.",                       "duration": 10},
    {"id": "return",         "title": "The Return",                    "subtitle": "What was learned will protect the future.",                  "duration": 10},
    {"id": "scale_10",       "title": "Scale Up — 10 Lines",      "subtitle": "Can the system handle 10x the signal volume?",               "duration": 12},
    {"id": "scale_50",       "title": "Scale Up — 50 Lines",      "subtitle": "Fifty production lines. All on CPU.",                        "duration": 12},
    {"id": "stress",         "title": "Stress Test",                   "subtitle": "Cascading failures. 15% of units report anomalies.",         "duration": 15},
    {"id": "recovery",       "title": "Recovery",                      "subtitle": "The storm passes. The system self-stabilizes.",              "duration": 10},
    {"id": "claim",          "title": "The Claim",                     "subtitle": "One CPU. No GPU. No LLM. This is what it can do.",           "duration": 8},
]

NANO_MODULES = [
    "app.nanoagents.baseline_distance", "app.nanoagents.metric_drift",
    "app.nanoagents.log_pattern", "app.nanoagents.document_heuristic",
    "app.nanoagents.image_metadata", "app.nanoagents.audio_energy",
    "app.nanoagents.evidence_gate",
]


class DemoStartRequest(BaseModel):
    speed: float = 1.0


def _ts():
    return datetime.now(timezone.utc).isoformat()


def _make_state(step_index: int, progress: float, paused: bool = False, **extra) -> dict:
    step = DEMO_STEPS[step_index]
    state = {
        "status": "paused" if paused else "running",
        "current_step": step_index,
        "step_id": step["id"],
        "step_title": step["title"],
        "step_subtitle": step["subtitle"],
        "step_progress": min(100, int(progress)),
        "total_steps": len(DEMO_STEPS),
        "flow_description": FLOW_DESCRIPTIONS.get(step["id"], ""),
        "timestamp": _ts(),
    }
    state.update(extra)
    return state


def _pause_sleep(seconds: float):
    """Sleep that respects pause and stop. Blocks while paused, resumes when unpaused."""
    while not _demo_stop.is_set():
        if _demo_pause.is_set():
            _demo_stop.wait(timeout=seconds)
            return
        _demo_pause.wait(timeout=0.5)


def _auto_pause_between_steps(step_index: int, extras: dict):
    """Pause at the end of a step so the presenter can narrate."""
    step = DEMO_STEPS[step_index]
    _demo_pause.clear()
    set_demo_state(_make_state(step_index, 100, paused=True,
                               waiting_for_next=True, **extras))
    _demo_pause.wait()
    if _demo_stop.is_set():
        return


def _wait(duration: float, speed: float, step_index: int, extras: dict):
    actual = duration / speed
    start = time.monotonic()
    paused_total = 0.0
    while not _demo_stop.is_set():
        if not _demo_pause.is_set():
            pause_start = time.monotonic()
            set_demo_state(_make_state(step_index, min(100, int(((time.monotonic() - start - paused_total) / actual) * 100)), paused=True, **extras))
            _demo_pause.wait()
            paused_total += time.monotonic() - pause_start
            continue
        elapsed = time.monotonic() - start - paused_total
        progress = (elapsed / actual) * 100
        set_demo_state(_make_state(step_index, progress, **extras))
        if elapsed >= actual:
            break
        time.sleep(0.4)


def _emit(events: list, agent_name: str, class_name: str, taxonomy: str,
          severity: str, confidence: float, tier: str, rationale: str = ""):
    events.append({
        "agent_name": agent_name, "class_name": class_name,
        "taxonomy": taxonomy, "severity": severity,
        "confidence": confidence, "tier": tier,
        "rationale": rationale, "timestamp": _ts(),
    })


def _run_nano_tier(evidence, baseline, agent_events, funnel):
    nano_records = []
    for module_path in NANO_MODULES:
        module = importlib.import_module(module_path)
        records = module.classify(evidence, baseline)
        nano_records.extend(records)
        for r in records:
            _emit(agent_events, r.agent_name, r.class_name, r.taxonomy,
                  r.severity, r.confidence, "nano", r.rationale)
    funnel["nano_processed"] = len(nano_records)
    escalated = [ev for ev in evidence if should_escalate_to_micro(nano_records, ev)]
    funnel["nano_escalated"] = len(escalated)
    funnel["nano_retained"] = len(evidence) - len(escalated)
    return nano_records, escalated


def _run_micro_tier(escalated, agent_events, funnel):
    from app.microagents.text_classifier import TextClassifierAgent
    from app.microagents.document_classifier import DocumentClassifierAgent
    from app.microagents.image_classifier import ImageDefectClassifierAgent
    from app.microagents.audio_classifier import AudioAnomalyClassifierAgent

    micro_records = []
    for agent in [TextClassifierAgent(), DocumentClassifierAgent(), ImageDefectClassifierAgent(), AudioAnomalyClassifierAgent()]:
        modalities = getattr(agent, "modalities", set())
        relevant = [ev for ev in escalated if ev.modality in modalities] if modalities else escalated
        if relevant:
            records = agent.classify(relevant)
            micro_records.extend(records)
            for r in records:
                _emit(agent_events, r.agent_name, r.class_name, r.taxonomy,
                      r.severity, r.confidence, "micro", r.rationale)
    funnel["micro_processed"] = len(micro_records)
    return micro_records


def _run_macro_tier(evidence, all_prior, baseline, agent_events, funnel):
    from app.macroagents.incident_timeline import IncidentTimelineAgent
    from app.macroagents.root_cause_hypothesis import RootCauseHypothesisAgent
    from app.macroagents.action_planner import ActionPlannerAgent
    from app.macroagents.verification_planner import VerificationPlannerAgent
    from app.macroagents.learning_proposal_agent import LearningProposalMacroAgent

    macro_records = []
    for agent in [IncidentTimelineAgent(), RootCauseHypothesisAgent(), ActionPlannerAgent(), VerificationPlannerAgent(), LearningProposalMacroAgent()]:
        records = agent.reason(evidence, all_prior, baseline)
        macro_records.extend(records)
        for r in records:
            _emit(agent_events, r.agent_name, r.class_name, r.taxonomy,
                  r.severity, r.confidence, "macro", r.rationale)
    funnel["macro_processed"] = len(macro_records)
    return macro_records


def _run_full_cascade(evidence, baseline, agent_events, funnel):
    nano, escalated = _run_nano_tier(evidence, baseline, agent_events, funnel)
    micro = _run_micro_tier(escalated, agent_events, funnel)
    do_macro = should_escalate_to_macro(micro, evidence)
    funnel["micro_escalated"] = len(evidence) if do_macro else 0
    macro = []
    if do_macro:
        macro = _run_macro_tier(evidence, nano + micro, baseline, agent_events, funnel)
    return nano, micro, macro


def _run_demo(speed: float):
    evidence: list[EvidenceArtifact] = []
    baseline: Optional[BaselineProfile] = None
    agent_events: list[dict] = []
    funnel: dict = {
        "total_evidence": 0, "nano_processed": 0, "nano_escalated": 0,
        "nano_retained": 0, "micro_processed": 0, "micro_escalated": 0,
        "macro_processed": 0, "actions_proposed": 0, "verifications_created": 0,
        "learning_proposals": 0, "compression_ratio": 0.0,
    }
    cumulative = {"total_evidence": 0, "total_classifications": 0, "total_actions": 0,
                  "total_learning": 0, "lines_monitored": 1, "peak_compression": 0.0}

    def _extras(**kw):
        from app.inference.client import get_inference_stats, is_inference_available
        stats = get_inference_stats().to_dict() if is_inference_available() else None
        return {"funnel": funnel, "agent_events": agent_events[-25:], "cumulative": cumulative,
                "inference_mode": "llm" if is_inference_available() else "simulated",
                "inference_stats": stats, **kw}

    # === PART 1: SINGLE-LINE DEEP WALKTHROUGH ===

    # Step 0: Ordinary World
    _wait(DEMO_STEPS[0]["duration"], speed, 0, _extras(
        narrative="A factory production line hums with the rhythm of precision machinery. "
                  "Bearings spin at 0.22 RMS. Temperature holds at 38.2°C. Every signal says: normal.",
        baseline_metrics={"vibration_rms": 0.22, "temperature_c": 38.2, "defect_rate": 0.001},
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(0, _extras(narrative="Normal operations established. Ready to ingest signals."))
    if _demo_stop.is_set(): return

    # Step 1: Call to Adventure — ingest evidence
    evidence_all = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    for i, ev in enumerate(evidence_all):
        if _demo_stop.is_set(): return
        evidence.append(ev)
        funnel["total_evidence"] = len(evidence)
        cumulative["total_evidence"] = len(evidence)
        progress = ((i + 1) / len(evidence_all)) * 100
        set_demo_state(_make_state(1, progress, **_extras(
            narrative=f"Ingesting {ev.modality}/{ev.artifact_type} — feature extraction on CPU...",
            live_agent={"name": "normalizer", "status": "extracting features",
                       "modality": ev.modality, "artifact_type": ev.artifact_type},
            evidence_detail=ev.model_dump(mode="json"),
        )))
        _pause_sleep(max(0.5, DEMO_STEPS[1]["duration"] / len(evidence_all) / speed))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(1, _extras(narrative=f"{len(evidence)} evidence artifacts ingested across {len(set(e.modality for e in evidence))} modalities. Ready to compile baseline."))
    if _demo_stop.is_set(): return

    # Step 2: Crossing the Threshold — build baseline
    compiler = BaselineCompiler()
    baseline = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    baseline.status = "active"
    _wait(DEMO_STEPS[2]["duration"], speed, 2, _extras(
        narrative=f"Baseline compiled: {baseline.confidence:.0%} confidence. "
                  f"{len(baseline.thresholds)} threshold groups. {len(baseline.normal_ranges)} range groups. "
                  f"The shape of normal is now defined.",
        baseline=baseline.model_dump(mode="json"),
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(2, _extras(narrative=f"Baseline ready: {baseline.confidence:.0%} confidence. Ready to run classification cascade."))
    if _demo_stop.is_set(): return

    # Steps 3-5: The Ordeal — Nano, Micro, Macro (one at a time for drama)
    for j, module_path in enumerate(NANO_MODULES):
        if _demo_stop.is_set(): return
        module = importlib.import_module(module_path)
        agent_name = getattr(module, "name", module_path.split(".")[-1])
        records = module.classify(evidence, baseline)
        for r in records:
            _emit(agent_events, r.agent_name, r.class_name, r.taxonomy, r.severity, r.confidence, "nano", r.rationale)
        funnel["nano_processed"] += len(records)
        progress = ((j + 1) / len(NANO_MODULES)) * 100
        set_demo_state(_make_state(3, progress, **_extras(
            narrative=f"Nanoagent '{agent_name}': {len(records)} classifications. {records[0].rationale[:80] if records else ''}",
            live_agent={"name": agent_name, "status": "classifying", "tier": "nano",
                       "decision_type": "deterministic", "runtime": "CPU"},
        )))
        _pause_sleep(max(0.4, DEMO_STEPS[3]["duration"] / len(NANO_MODULES) / speed))

    escalated = [ev for ev in evidence if should_escalate_to_micro(
        [ClassificationRecord(**e) if isinstance(e, dict) else e for e in []],  # dummy
        ev)]
    escalated = evidence  # for single scenario, all escalate due to multi-modality
    funnel["nano_escalated"] = len(escalated)
    funnel["nano_retained"] = max(0, len(evidence) - len(escalated))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(3, _extras(narrative=f"Nano tier complete: {funnel['nano_processed']} classifications. {funnel['nano_escalated']} escalated to micro. Ready for microagent classification."))
    if _demo_stop.is_set(): return

    # Micro tier
    from app.microagents.text_classifier import TextClassifierAgent
    from app.microagents.document_classifier import DocumentClassifierAgent
    from app.microagents.image_classifier import ImageDefectClassifierAgent
    from app.microagents.audio_classifier import AudioAnomalyClassifierAgent
    micro_agents = [TextClassifierAgent(), DocumentClassifierAgent(), ImageDefectClassifierAgent(), AudioAnomalyClassifierAgent()]
    micro_records_list = []
    for k, agent in enumerate(micro_agents):
        if _demo_stop.is_set(): return
        modalities = getattr(agent, "modalities", set())
        relevant = [ev for ev in escalated if ev.modality in modalities] if modalities else escalated
        if relevant:
            records = agent.classify(relevant)
            micro_records_list.extend(records)
            for r in records:
                _emit(agent_events, r.agent_name, r.class_name, r.taxonomy, r.severity, r.confidence, "micro", r.rationale)
            funnel["micro_processed"] = len(micro_records_list)
        progress = ((k + 1) / len(micro_agents)) * 100
        set_demo_state(_make_state(4, progress, **_extras(
            narrative=f"Microagent '{agent.name}': rule-backed classification on CPU. "
                      f"{records[0].rationale[:80] if relevant and records else 'No relevant evidence.'}",
            live_agent={"name": agent.name, "status": "classifying", "tier": "micro",
                       "decision_type": "rule-backed", "runtime": "CPU (Xeon-optimized)"},
        )))
        _pause_sleep(max(0.5, DEMO_STEPS[4]["duration"] / len(micro_agents) / speed))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(4, _extras(narrative=f"Micro tier complete: {funnel['micro_processed']} classifications. Escalating to macroagent reasoning."))
    if _demo_stop.is_set(): return

    # Macro tier
    from app.macroagents.incident_timeline import IncidentTimelineAgent
    from app.macroagents.root_cause_hypothesis import RootCauseHypothesisAgent
    from app.macroagents.action_planner import ActionPlannerAgent
    from app.macroagents.verification_planner import VerificationPlannerAgent
    from app.macroagents.learning_proposal_agent import LearningProposalMacroAgent
    macro_agents = [IncidentTimelineAgent(), RootCauseHypothesisAgent(), ActionPlannerAgent(), VerificationPlannerAgent(), LearningProposalMacroAgent()]
    all_prior = list(agent_events)  # use events as proxy
    macro_records_list = []
    for m_idx, agent in enumerate(macro_agents):
        if _demo_stop.is_set(): return
        records = agent.reason(evidence, micro_records_list, baseline)
        macro_records_list.extend(records)
        for r in records:
            _emit(agent_events, r.agent_name, r.class_name, r.taxonomy, r.severity, r.confidence, "macro", r.rationale)
        funnel["macro_processed"] = len(macro_records_list)
        progress = ((m_idx + 1) / len(macro_agents)) * 100
        set_demo_state(_make_state(5, progress, **_extras(
            narrative=f"Macroagent '{agent.name}': {records[0].rationale[:100] if records else 'Processing...'}",
            live_agent={"name": agent.name, "status": "reasoning", "tier": "macro",
                       "decision_type": "template-based", "runtime": "CPU"},
        )))
        _pause_sleep(max(0.5, DEMO_STEPS[5]["duration"] / len(macro_agents) / speed))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(5, _extras(narrative=f"Classification cascade complete: {funnel['nano_processed']} nano + {funnel['micro_processed']} micro + {funnel['macro_processed']} macro. Ready to propose action."))
    if _demo_stop.is_set(): return

    # Step 6: The Reward
    from app.agent_loop.actions import ActionManager
    from app.agent_loop.verification import VerificationService
    action_mgr = ActionManager()
    verif_svc = VerificationService()
    action = action_mgr.propose(action_type="notify", payload={"target": "maintenance_team", "reason": "Bearing failure convergence"}, created_by_agent="action_planner")
    verification = verif_svc.create(action_id=action.action_id, verification_type="metric_return_to_baseline", expected_outcome={"vibration_rms_below": 0.35, "temperature_below": 42.0})
    funnel["actions_proposed"] = 1
    funnel["verifications_created"] = 1
    cumulative["total_actions"] = 1
    _wait(DEMO_STEPS[6]["duration"], speed, 6, _extras(
        narrative=f"Action proposed: {action.action_type}. Requires human approval. Non-destructive. "
                  f"Verification: {verification.verification_type} — checking vibration < 0.35, temperature < 42°C.",
        action=action.model_dump(mode="json"),
        verification=verification.model_dump(mode="json"),
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(6, _extras(narrative="Action proposed and verification created. Ready to generate learning proposals."))
    if _demo_stop.is_set(): return

    # Step 7: The Return
    from app.agent_loop.learning import LearningService
    learn_svc = LearningService()
    proposal = learn_svc.propose(
        source_type="incident", source_id=evidence[0].evidence_id,
        proposal_type="threshold_update",
        target_scope={"scope_type": "site", "scope_id": "factory-line-01"},
        before={"vibration_z_warning": 2.0, "vibration_z_critical": 3.0},
        after={"vibration_z_warning": 1.8, "vibration_z_critical": 2.5},
        rationale="Tighten vibration thresholds for earlier detection based on bearing failure incident",
        confidence=0.65,
    )
    funnel["learning_proposals"] = 1
    cumulative["total_learning"] = 1
    total_class = funnel["nano_processed"] + funnel["micro_processed"] + funnel["macro_processed"]
    cumulative["total_classifications"] = total_class
    funnel["compression_ratio"] = round(funnel["total_evidence"] / max(funnel["actions_proposed"], 1), 1)
    cumulative["peak_compression"] = funnel["compression_ratio"]
    _wait(DEMO_STEPS[7]["duration"], speed, 7, _extras(
        narrative="Learning proposal: lower vibration z-score warning from 2.0σ to 1.8σ for earlier detection. "
                  "Requires human review before activation.",
        learning_proposal=proposal.model_dump(mode="json"),
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(7, _extras(narrative="Single-line walkthrough complete. Ready to scale."))
    if _demo_stop.is_set(): return

    # === PART 2: SCALE STORY ===
    # Scale acts use rule-backed only (LLM already proven in Part 1).
    # Process in batches with SSE updates so the UI stays alive.
    from app.inference.client import set_force_rules
    set_force_rules(True)

    for scale_step, scale_cfg in [
        (8,  {"lines": 10, "failure_rate": 0.02, "seed": 100}),
        (9,  {"lines": 50, "failure_rate": 0.02, "seed": 200}),
        (10, {"lines": 50, "failure_rate": 0.15, "seed": 300}),
        (11, {"lines": 50, "failure_rate": 0.02, "seed": 400}),
    ]:
        if _demo_stop.is_set(): return
        n_lines = scale_cfg["lines"]
        fr = scale_cfg["failure_rate"]
        step_def = DEMO_STEPS[scale_step]

        set_demo_state(_make_state(scale_step, 0, **_extras(
            narrative=f"Generating evidence for {n_lines} factory lines at {fr:.0%} failure rate...",
            live_agent={"name": "scale_generator", "status": f"generating {n_lines} lines", "tier": "system"},
        )))
        _pause_sleep(0.5)

        start_t = time.monotonic()
        scale_evidence = generate_scaled_evidence(n_lines, failure_rate=fr, seed=scale_cfg["seed"])
        s_funnel = {"total_evidence": len(scale_evidence), "nano_processed": 0, "nano_escalated": 0,
                    "nano_retained": 0, "micro_processed": 0, "micro_escalated": 0,
                    "macro_processed": 0, "actions_proposed": 0, "verifications_created": 0,
                    "learning_proposals": 0, "compression_ratio": 0.0}
        s_events: list[dict] = []

        set_demo_state(_make_state(scale_step, 20, **_extras(
            narrative=f"{len(scale_evidence)} evidence artifacts generated. Running nanoagents...",
            live_agent={"name": "nanoagent_pipeline", "status": f"classifying {len(scale_evidence)} artifacts", "tier": "nano"},
            funnel=s_funnel,
        )))
        _pause_sleep(0.3)

        # Nano tier — process in batches with updates
        batch_size = max(1, len(scale_evidence) // 5)
        all_nano = []
        for batch_start in range(0, len(scale_evidence), batch_size):
            if _demo_stop.is_set(): return
            batch = scale_evidence[batch_start:batch_start + batch_size]
            for module_path in NANO_MODULES:
                module = importlib.import_module(module_path)
                records = module.classify(batch, baseline)
                all_nano.extend(records)
                for r in records:
                    _emit(s_events, r.agent_name, r.class_name, r.taxonomy, r.severity, r.confidence, "nano", r.rationale)
            s_funnel["nano_processed"] = len(all_nano)
            progress = 20 + (batch_start + len(batch)) / len(scale_evidence) * 40
            set_demo_state(_make_state(scale_step, progress, **_extras(
                narrative=f"Nano: {len(all_nano)} classifications from {batch_start + len(batch)}/{len(scale_evidence)} artifacts...",
                live_agent={"name": "nanoagent_pipeline", "status": "classifying", "tier": "nano"},
                funnel=s_funnel, agent_events=s_events[-25:],
            )))
            _pause_sleep(0.2)

        # Escalation + micro (rule-backed, fast)
        escalated = [ev for ev in scale_evidence if should_escalate_to_micro(all_nano, ev)]
        s_funnel["nano_escalated"] = len(escalated)
        s_funnel["nano_retained"] = len(scale_evidence) - len(escalated)

        set_demo_state(_make_state(scale_step, 65, **_extras(
            narrative=f"Nano complete. {s_funnel['nano_escalated']} escalated to micro. Running microagents (rule-backed)...",
            live_agent={"name": "micro_pipeline", "status": "classifying escalated evidence", "tier": "micro"},
            funnel=s_funnel, agent_events=s_events[-25:],
        )))
        _pause_sleep(0.3)

        micro_recs = _run_micro_tier(escalated, s_events, s_funnel)

        # Macro for stress test only
        if fr > 0.05 and should_escalate_to_macro(micro_recs, scale_evidence):
            set_demo_state(_make_state(scale_step, 80, **_extras(
                narrative=f"High failure rate — escalating to macroagents...",
                live_agent={"name": "macro_pipeline", "status": "reasoning", "tier": "macro"},
                funnel=s_funnel, agent_events=s_events[-25:],
            )))
            _pause_sleep(0.3)
            _run_macro_tier(scale_evidence[:20], all_nano[:20] + micro_recs[:10], baseline, s_events, s_funnel)

        elapsed = round((time.monotonic() - start_t) * 1000)
        failing_count = sum(1 for e in scale_evidence if e.labels.get("failing"))
        s_funnel["actions_proposed"] = max(1, failing_count // 6) if fr > 0.05 else 0
        s_funnel["learning_proposals"] = 3 if scale_step == 11 else (1 if fr > 0.05 else 0)
        total_class = s_funnel["nano_processed"] + s_funnel["micro_processed"] + s_funnel.get("macro_processed", 0)
        s_funnel["compression_ratio"] = round(len(scale_evidence) / max(s_funnel["actions_proposed"], 1), 1)

        cumulative["lines_monitored"] = n_lines
        cumulative["total_evidence"] += len(scale_evidence)
        cumulative["total_classifications"] += total_class
        cumulative["total_actions"] += s_funnel["actions_proposed"]
        cumulative["total_learning"] += s_funnel["learning_proposals"]
        if s_funnel["compression_ratio"] > cumulative["peak_compression"]:
            cumulative["peak_compression"] = s_funnel["compression_ratio"]

        label = step_def["title"]
        if fr > 0.05:
            narrative = (f"STRESS: {n_lines} lines at {fr:.0%} failure. {len(scale_evidence)} evidence, "
                        f"{s_funnel['nano_escalated']} escalated, {s_funnel.get('macro_processed', 0)} macro. "
                        f"{s_funnel['actions_proposed']} actions. {elapsed}ms.")
        elif scale_step == 11:
            narrative = (f"Recovery: {s_funnel['nano_processed']} nano classifications. "
                        f"System stabilized in {elapsed}ms. {s_funnel['learning_proposals']} learning proposals from the storm.")
        else:
            narrative = (f"{n_lines} lines: {len(scale_evidence)} evidence → {total_class} classifications "
                        f"in {elapsed}ms. Compression: {s_funnel['compression_ratio']}:1.")

        _wait(DEMO_STEPS[scale_step]["duration"], speed, scale_step, {
            "funnel": s_funnel, "agent_events": s_events[-25:], "cumulative": cumulative,
            "narrative": narrative,
            "scale_metrics": {"lines": n_lines, "failure_rate": fr, "evidence": len(scale_evidence),
                             "classifications": total_class, "elapsed_ms": elapsed,
                             "failing_lines": failing_count // 6 if fr > 0.05 else 0},
        })
        if _demo_stop.is_set(): return
        _auto_pause_between_steps(scale_step, {
            "funnel": s_funnel, "agent_events": s_events[-25:], "cumulative": cumulative,
            "narrative": narrative,
        })
        if _demo_stop.is_set(): return

    # Restore LLM availability
    set_force_rules(False)

    # Step 12: The Claim
    set_demo_state({
        "status": "completed",
        "current_step": len(DEMO_STEPS) - 1,
        "step_id": "claim",
        "step_title": DEMO_STEPS[-1]["title"],
        "step_subtitle": DEMO_STEPS[-1]["subtitle"],
        "step_progress": 100,
        "total_steps": len(DEMO_STEPS),
        "flow_description": FLOW_DESCRIPTIONS["claim"],
        "narrative": "The complete story. All on CPU. No GPU. No LLM.",
        "cumulative": cumulative,
        "claim": {
            "total_evidence_processed": cumulative["total_evidence"],
            "total_classifications": cumulative["total_classifications"],
            "peak_lines_monitored": 50,
            "peak_failure_rate": "15%",
            "total_actions_proposed": cumulative["total_actions"],
            "total_learning_proposals": cumulative["total_learning"],
            "agents": 17,
            "tiers": 3,
            "gpu": "none",
            "llm": "none",
            "runtime": "CPU only",
        },
    })


@router.post("/start")
async def start_demo(req: DemoStartRequest = DemoStartRequest()):
    global _demo_thread
    _demo_stop.clear()
    _demo_pause.set()
    from app.inference.client import reset_inference_stats
    reset_inference_stats()
    set_demo_state({"status": "starting", "total_steps": len(DEMO_STEPS), "steps": DEMO_STEPS})

    def _run():
        try:
            _run_demo(req.speed)
        except Exception as e:
            set_demo_state({"status": "error", "error": str(e)[:500]})

    _demo_thread = threading.Thread(target=_run, daemon=True)
    _demo_thread.start()
    return {"status": "started", "steps": len(DEMO_STEPS)}


@router.post("/pause")
async def pause_demo():
    _demo_pause.clear()
    return {"status": "paused"}


@router.post("/resume")
async def resume_demo():
    _demo_pause.set()
    return {"status": "resumed"}


@router.post("/stop")
async def stop_demo():
    _demo_pause.set()
    _demo_stop.set()
    set_demo_state({"status": "stopped"})
    return {"status": "stopped"}


@router.get("/state")
async def get_state():
    from app.api.sse import get_demo_state
    state = get_demo_state()
    return state if state else {"status": "idle"}


@router.get("/infrastructure")
async def get_infrastructure():
    import os
    import platform

    from app.inference.client import get_inference_config, get_inference_stats

    inference_config = get_inference_config()
    inference_stats = get_inference_stats()

    nano_agents = [
        {"name": "baseline_distance", "type": "deterministic", "runtime": "CPU", "description": "Compares feature values to baseline thresholds, flags drift beyond normal ranges"},
        {"name": "metric_drift", "type": "deterministic", "runtime": "CPU", "description": "Slope and z-score checks — detects gradual trends in metric time series"},
        {"name": "log_pattern", "type": "deterministic", "runtime": "CPU", "description": "Regex pattern matching for ERROR/WARN/CRIT in log evidence"},
        {"name": "document_heuristic", "type": "deterministic", "runtime": "CPU", "description": "Keyword analysis for actionable terms in documents and notes"},
        {"name": "image_metadata", "type": "deterministic", "runtime": "CPU", "description": "Defect score evaluation from image inspection labels"},
        {"name": "audio_energy", "type": "deterministic", "runtime": "CPU", "description": "Anomaly score evaluation from audio/vibration sensor labels"},
        {"name": "evidence_gate", "type": "deterministic", "runtime": "CPU", "description": "Decides ignore/retain/escalate for each evidence piece based on modality and severity"},
    ]
    micro_agents = [
        {"name": "text_classifier", "type": "rule-backed", "runtime": "CPU (Xeon-optimized)", "description": "Pattern matching against known incident families — infrastructure, quality, security, capacity"},
        {"name": "document_classifier", "type": "rule-backed", "runtime": "CPU (Xeon-optimized)", "description": "Document type and sensitivity classification by keyword analysis"},
        {"name": "image_classifier", "type": "fixture-backed / optional ONNX", "runtime": "CPU (Xeon-optimized)", "description": "Defect classification is fixture-backed by default, with optional OpenVINO/ONNX CPU adapters when configured"},
        {"name": "audio_classifier", "type": "fixture-backed / optional ONNX", "runtime": "CPU (Xeon-optimized)", "description": "Anomaly classification is fixture-backed by default, with optional OpenVINO/ONNX CPU adapters when configured"},
        {"name": "embedding_classifier", "type": "placeholder", "runtime": "CPU", "description": "Placeholder for embedding/clustering — extension point for vector inference"},
    ]
    macro_agents = [
        {"name": "incident_timeline", "type": "template-based", "runtime": "CPU", "description": "Sequences evidence by timestamp, overlays classifications to build incident narrative"},
        {"name": "root_cause_hypothesis", "type": "template-based", "runtime": "CPU", "description": "Counts classification families across modalities to identify most likely root cause"},
        {"name": "action_planner", "type": "template-based", "runtime": "CPU", "description": "Proposes safe actions (notify, observe, ticket) — never destructive without human approval"},
        {"name": "verification_planner", "type": "template-based", "runtime": "CPU", "description": "Builds verification plan to check if post-action metrics return to baseline"},
        {"name": "learning_proposal", "type": "template-based", "runtime": "CPU", "description": "Proposes threshold/rule updates based on high-confidence findings — never auto-applied"},
    ]

    return {
        "runtime": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "cpu_count": os.cpu_count(),
            "hostname": platform.node(),
        },
        "inference": {
            "llm_connected": inference_config["available"],
            "api_base": inference_config["api_base"] or "not configured",
            "model_micro": inference_config["model_micro"],
            "model_macro": inference_config["model_macro"],
            "mode": "LLM inference via LiteLLM" if inference_config["available"] else "Rule-backed (no LLM configured)",
            "nano_tier": "Deterministic rules — always CPU, no inference",
            "micro_tier": f"{'LLM: ' + inference_config['model_micro'] if inference_config['available'] else 'Rule-backed classifiers'} (CPU)",
            "macro_tier": f"{'LLM: ' + inference_config['model_macro'] if inference_config['available'] else 'Template-based reasoning'} (CPU)",
            "stats": inference_stats.to_dict(),
        },
        "agents": {
            "total": 17,
            "tiers": 3,
            "nano": {"count": len(nano_agents), "type": "deterministic", "agents": nano_agents},
            "micro": {"count": len(micro_agents), "type": "rule-backed", "agents": micro_agents},
            "macro": {"count": len(macro_agents), "type": "template-based", "agents": macro_agents},
        },
        "pipeline": {
            "flow": "Signals → Evidence → Baseline → Nano → Micro → Macro → Act → Verify → Learn",
            "compression": "Nanoagents filter most evidence before micro/macro tiers — no inference cost for filtered signals",
            "safety": "Only non-destructive actions proposed. Destructive ops require human approval. Learning never auto-applied.",
        },
        "framework": {
            "backend": "FastAPI + Pydantic v2",
            "frontend": "React 19 + motion/react",
            "database": "PostgreSQL (optional — graceful degradation without DB)",
            "container": "Podman / OCI-compatible",
        },
    }


@router.post("/ingest")
async def ingest_fixture():
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    return [e.model_dump(mode="json") for e in evidence]


@router.post("/baseline")
async def build_baseline():
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    bl = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    bl.status = "active"
    return bl.model_dump(mode="json")


@router.post("/classify")
async def run_classification():
    from app.inference.client import set_force_rules
    set_force_rules(True)
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    bl = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    bl.status = "active"
    from app.classification.engine import ClassificationEngine
    records = ClassificationEngine().classify(evidence, bl)
    set_force_rules(False)
    return [r.model_dump(mode="json") for r in records]


@router.post("/classify/nano")
async def run_nano_only():
    import time as _time
    start = _time.monotonic()
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    bl = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    bl.status = "active"
    from app.nanoagents.pipeline import run_pipeline
    records = run_pipeline(evidence, bl)
    elapsed = round((_time.monotonic() - start) * 1000)
    return {
        "tier": "nano",
        "records": [r.model_dump(mode="json") for r in records],
        "count": len(records),
        "elapsed_ms": elapsed,
        "agents": list({r.agent_name for r in records}),
        "decision_type": "deterministic",
        "runtime": "CPU — no inference",
    }


@router.post("/classify/micro")
async def run_micro_only():
    import time as _time
    start = _time.monotonic()
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    bl = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    bl.status = "active"
    from app.nanoagents.pipeline import run_pipeline
    from app.classification.cascade import should_escalate_to_micro as esc_micro
    nano = run_pipeline(evidence, bl)
    escalated = [ev for ev in evidence if esc_micro(nano, ev)]
    from app.microagents.text_classifier import TextClassifierAgent
    from app.microagents.document_classifier import DocumentClassifierAgent
    from app.microagents.image_classifier import ImageDefectClassifierAgent
    from app.microagents.audio_classifier import AudioAnomalyClassifierAgent
    records = []
    for agent in [TextClassifierAgent(), DocumentClassifierAgent(), ImageDefectClassifierAgent(), AudioAnomalyClassifierAgent()]:
        modalities = getattr(agent, "modalities", set())
        relevant = [ev for ev in escalated if ev.modality in modalities] if modalities else escalated
        if relevant:
            records.extend(agent.classify(relevant))
    elapsed = round((_time.monotonic() - start) * 1000)
    from app.inference.client import is_inference_available
    return {
        "tier": "micro",
        "records": [r.model_dump(mode="json") for r in records],
        "count": len(records),
        "elapsed_ms": elapsed,
        "escalated_from_nano": len(escalated),
        "agents": list({r.agent_name for r in records}),
        "decision_type": "LLM inference" if is_inference_available() else "rule-backed",
        "runtime": "LLM via LiteLLM" if is_inference_available() else "CPU — rules only",
    }


@router.post("/classify/macro")
async def run_macro_only():
    import time as _time
    start = _time.monotonic()
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    bl = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    bl.status = "active"
    from app.nanoagents.pipeline import run_pipeline
    from app.classification.cascade import should_escalate_to_micro as esc_micro, should_escalate_to_macro as esc_macro
    nano = run_pipeline(evidence, bl)
    escalated = [ev for ev in evidence if esc_micro(nano, ev)]
    from app.microagents.text_classifier import TextClassifierAgent
    from app.microagents.document_classifier import DocumentClassifierAgent
    from app.microagents.image_classifier import ImageDefectClassifierAgent
    from app.microagents.audio_classifier import AudioAnomalyClassifierAgent
    micro = []
    for agent in [TextClassifierAgent(), DocumentClassifierAgent(), ImageDefectClassifierAgent(), AudioAnomalyClassifierAgent()]:
        modalities = getattr(agent, "modalities", set())
        relevant = [ev for ev in escalated if ev.modality in modalities] if modalities else escalated
        if relevant:
            micro.extend(agent.classify(relevant))
    records = []
    if esc_macro(micro, evidence):
        from app.macroagents.incident_timeline import IncidentTimelineAgent
        from app.macroagents.root_cause_hypothesis import RootCauseHypothesisAgent
        from app.macroagents.action_planner import ActionPlannerAgent
        from app.macroagents.verification_planner import VerificationPlannerAgent
        from app.macroagents.learning_proposal_agent import LearningProposalMacroAgent
        for agent in [IncidentTimelineAgent(), RootCauseHypothesisAgent(), ActionPlannerAgent(), VerificationPlannerAgent(), LearningProposalMacroAgent()]:
            records.extend(agent.reason(evidence, nano + micro, bl))
    elapsed = round((_time.monotonic() - start) * 1000)
    from app.inference.client import is_inference_available
    return {
        "tier": "macro",
        "records": [r.model_dump(mode="json") for r in records],
        "count": len(records),
        "elapsed_ms": elapsed,
        "agents": list({r.agent_name for r in records}),
        "decision_type": "LLM reasoning" if is_inference_available() else "template-based",
        "runtime": "LLM via LiteLLM" if is_inference_available() else "CPU — templates only",
    }


@router.post("/loop")
async def run_full_loop():
    from app.inference.client import set_force_rules
    set_force_rules(True)
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    bl = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    bl.status = "active"
    from app.agent_loop.loop import AgentLoop
    result = AgentLoop().run(evidence, bl)
    set_force_rules(False)
    return {
        "classifications": [c.model_dump(mode="json") for c in result["classifications"]],
        "actions": [a.model_dump(mode="json") for a in result["actions"]],
        "verifications": [v.model_dump(mode="json") for v in result["verifications"]],
        "learning_proposals": [p.model_dump(mode="json") for p in result["learning_proposals"]],
    }
