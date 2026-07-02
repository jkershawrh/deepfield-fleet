"""Auto-orchestrated demo — Hero's Journey story arc with live streaming."""

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

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"

_demo_thread: Optional[threading.Thread] = None
_demo_stop = threading.Event()

DEMO_STEPS = [
    {"id": "ordinary",       "title": "The Ordinary World",          "subtitle": "Everything is normal. The factory hums.",                    "duration": 8},
    {"id": "call",           "title": "The Call to Adventure",       "subtitle": "Signals arrive. Something is different.",                   "duration": 10},
    {"id": "threshold",      "title": "Crossing the Threshold",      "subtitle": "The baseline reveals the shape of normal.",                 "duration": 10},
    {"id": "ordeal_nano",    "title": "The Ordeal — Nano Tier",      "subtitle": "Deterministic agents detect what humans can't yet see.",    "duration": 12},
    {"id": "ordeal_micro",   "title": "The Ordeal — Micro Tier",     "subtitle": "Classifiers converge on defects and anomalies.",            "duration": 10},
    {"id": "ordeal_macro",   "title": "The Ordeal — Macro Tier",     "subtitle": "Higher reasoning builds the incident timeline.",            "duration": 10},
    {"id": "reward",         "title": "The Reward",                  "subtitle": "A safe, governed action is proposed.",                      "duration": 8},
    {"id": "return",         "title": "The Return",                  "subtitle": "What was learned will protect the future.",                 "duration": 6},
]

NANO_MODULES = [
    "app.nanoagents.baseline_distance",
    "app.nanoagents.metric_drift",
    "app.nanoagents.log_pattern",
    "app.nanoagents.document_heuristic",
    "app.nanoagents.image_metadata",
    "app.nanoagents.audio_energy",
    "app.nanoagents.evidence_gate",
]


class DemoStartRequest(BaseModel):
    speed: float = 1.0


def _make_state(step_index: int, progress: float, **extra) -> dict:
    step = DEMO_STEPS[step_index]
    state = {
        "status": "running",
        "current_step": step_index,
        "step_id": step["id"],
        "step_title": step["title"],
        "step_subtitle": step["subtitle"],
        "step_progress": min(100, int(progress)),
        "total_steps": len(DEMO_STEPS),
        "steps": DEMO_STEPS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state.update(extra)
    return state


def _wait(duration: float, speed: float, step_index: int, state_extras: dict):
    actual = duration / speed
    start = time.monotonic()
    while not _demo_stop.is_set():
        elapsed = time.monotonic() - start
        progress = (elapsed / actual) * 100
        set_demo_state(_make_state(step_index, progress, **state_extras))
        if elapsed >= actual:
            break
        time.sleep(0.4)


def _emit_agent_event(events: list, agent_name: str, modality: str, class_name: str,
                       taxonomy: str, severity: str, confidence: float, tier: str):
    events.append({
        "agent_name": agent_name,
        "modality": modality,
        "class_name": class_name,
        "taxonomy": taxonomy,
        "severity": severity,
        "confidence": confidence,
        "tier": tier,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _run_demo(speed: float):
    evidence: list[EvidenceArtifact] = []
    baseline: Optional[BaselineProfile] = None
    nano_records: list[ClassificationRecord] = []
    micro_records: list[ClassificationRecord] = []
    macro_records: list[ClassificationRecord] = []
    agent_events: list[dict] = []
    funnel: dict = {
        "total_evidence": 0,
        "nano_processed": 0, "nano_escalated": 0, "nano_retained": 0,
        "micro_processed": 0, "micro_escalated": 0,
        "macro_processed": 0,
        "actions_proposed": 0, "verifications_created": 0, "learning_proposals": 0,
    }

    # --- Step 0: The Ordinary World ---
    set_demo_state(_make_state(0, 0, funnel=funnel, agent_events=[],
                               narrative="A factory production line hums with precision machinery..."))
    _wait(DEMO_STEPS[0]["duration"], speed, 0, {
        "funnel": funnel, "agent_events": [],
        "narrative": "Bearings spin, temperatures hold steady. Every signal says: normal.",
        "baseline_metrics": {"vibration_rms": 0.22, "temperature_c": 38.2, "defect_rate": 0.001},
    })
    if _demo_stop.is_set(): return

    # --- Step 1: The Call to Adventure — Ingest evidence ---
    evidence_all = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    for i, ev in enumerate(evidence_all):
        if _demo_stop.is_set(): return
        evidence.append(ev)
        funnel["total_evidence"] = len(evidence)
        progress = ((i + 1) / len(evidence_all)) * 100
        set_demo_state(_make_state(1, progress, funnel=funnel, agent_events=agent_events,
                                    narrative=f"Ingesting {ev.modality}/{ev.artifact_type}...",
                                    live_agent={"name": "normalizer", "status": "ingesting",
                                               "modality": ev.modality, "artifact_type": ev.artifact_type},
                                    evidence=[e.model_dump(mode="json") for e in evidence]))
        time.sleep(max(0.5, DEMO_STEPS[1]["duration"] / len(evidence_all) / speed))
    if _demo_stop.is_set(): return

    # --- Step 2: Crossing the Threshold — Build baseline ---
    set_demo_state(_make_state(2, 0, funnel=funnel, agent_events=agent_events,
                                narrative="Compiling the shape of normal from historical evidence..."))
    compiler = BaselineCompiler()
    baseline = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    baseline.status = "active"
    _wait(DEMO_STEPS[2]["duration"], speed, 2, {
        "funnel": funnel, "agent_events": agent_events,
        "narrative": f"Baseline compiled: {baseline.confidence:.0%} confidence, "
                     f"{len(baseline.thresholds)} threshold groups.",
        "baseline": baseline.model_dump(mode="json"),
    })
    if _demo_stop.is_set(): return

    # --- Step 3: The Ordeal — Nano Tier ---
    for j, module_path in enumerate(NANO_MODULES):
        if _demo_stop.is_set(): return
        module = importlib.import_module(module_path)
        agent_name = getattr(module, "name", module_path.split(".")[-1])
        records = module.classify(evidence, baseline)
        nano_records.extend(records)
        funnel["nano_processed"] = len(nano_records)

        for r in records:
            _emit_agent_event(agent_events, r.agent_name, "—", r.class_name,
                              r.taxonomy, r.severity, r.confidence, "nano")

        progress = ((j + 1) / len(NANO_MODULES)) * 100
        set_demo_state(_make_state(3, progress, funnel=funnel,
                                    agent_events=agent_events[-20:],
                                    narrative=f"Nanoagent '{agent_name}' found {len(records)} classifications.",
                                    live_agent={"name": agent_name, "status": "classifying",
                                               "tier": "nano", "records_found": len(records)},
                                    nano_records=[r.model_dump(mode="json") for r in nano_records]))
        time.sleep(max(0.3, DEMO_STEPS[3]["duration"] / len(NANO_MODULES) / speed))

    escalated_evidence = [ev for ev in evidence if should_escalate_to_micro(nano_records, ev)]
    funnel["nano_escalated"] = len(escalated_evidence)
    funnel["nano_retained"] = len(evidence) - len(escalated_evidence)
    if _demo_stop.is_set(): return

    # --- Step 4: The Ordeal — Micro Tier ---
    from app.microagents.text_classifier import TextClassifierAgent
    from app.microagents.document_classifier import DocumentClassifierAgent
    from app.microagents.image_classifier import ImageDefectClassifierAgent
    from app.microagents.audio_classifier import AudioAnomalyClassifierAgent

    micro_agents = [
        TextClassifierAgent(), DocumentClassifierAgent(),
        ImageDefectClassifierAgent(), AudioAnomalyClassifierAgent(),
    ]

    for k, agent in enumerate(micro_agents):
        if _demo_stop.is_set(): return
        modalities = getattr(agent, "modalities", set())
        relevant = [ev for ev in escalated_evidence if ev.modality in modalities] if modalities else escalated_evidence
        if relevant:
            records = agent.classify(relevant)
            micro_records.extend(records)
            funnel["micro_processed"] = len(micro_records)
            for r in records:
                _emit_agent_event(agent_events, r.agent_name, relevant[0].modality if relevant else "—",
                                  r.class_name, r.taxonomy, r.severity, r.confidence, "micro")

        progress = ((k + 1) / len(micro_agents)) * 100
        set_demo_state(_make_state(4, progress, funnel=funnel,
                                    agent_events=agent_events[-20:],
                                    narrative=f"Microagent '{agent.name}' classified {len(records) if relevant else 0} artifacts.",
                                    live_agent={"name": agent.name, "status": "classifying", "tier": "micro"},
                                    micro_records=[r.model_dump(mode="json") for r in micro_records]))
        time.sleep(max(0.5, DEMO_STEPS[4]["duration"] / len(micro_agents) / speed))

    do_macro = should_escalate_to_macro(micro_records, evidence)
    funnel["micro_escalated"] = len(evidence) if do_macro else 0
    if _demo_stop.is_set(): return

    # --- Step 5: The Ordeal — Macro Tier ---
    if do_macro:
        from app.macroagents.incident_timeline import IncidentTimelineAgent
        from app.macroagents.root_cause_hypothesis import RootCauseHypothesisAgent
        from app.macroagents.action_planner import ActionPlannerAgent
        from app.macroagents.verification_planner import VerificationPlannerAgent
        from app.macroagents.learning_proposal_agent import LearningProposalMacroAgent

        macro_agents = [
            IncidentTimelineAgent(), RootCauseHypothesisAgent(),
            ActionPlannerAgent(), VerificationPlannerAgent(), LearningProposalMacroAgent(),
        ]
        all_prior = nano_records + micro_records
        for m, agent in enumerate(macro_agents):
            if _demo_stop.is_set(): return
            records = agent.reason(evidence, all_prior, baseline)
            macro_records.extend(records)
            funnel["macro_processed"] = len(macro_records)
            for r in records:
                _emit_agent_event(agent_events, r.agent_name, "multi",
                                  r.class_name, r.taxonomy, r.severity, r.confidence, "macro")

            progress = ((m + 1) / len(macro_agents)) * 100
            set_demo_state(_make_state(5, progress, funnel=funnel,
                                        agent_events=agent_events[-20:],
                                        narrative=f"Macroagent '{agent.name}': {records[0].rationale[:80]}..." if records else "Processing...",
                                        live_agent={"name": agent.name, "status": "reasoning", "tier": "macro"},
                                        macro_records=[r.model_dump(mode="json") for r in macro_records]))
            time.sleep(max(0.5, DEMO_STEPS[5]["duration"] / len(macro_agents) / speed))
    else:
        set_demo_state(_make_state(5, 100, funnel=funnel, agent_events=agent_events[-20:],
                                    narrative="No macro escalation needed — evidence within normal bounds."))
        _wait(3, speed, 5, {"funnel": funnel, "agent_events": agent_events[-20:]})
    if _demo_stop.is_set(): return

    # --- Step 6: The Reward — Action + Verification ---
    from app.agent_loop.actions import ActionManager
    from app.agent_loop.verification import VerificationService

    action_mgr = ActionManager()
    verif_svc = VerificationService()

    action_plans = [r for r in macro_records if r.agent_name == "action_planner"]
    action_type = action_plans[0].class_name if action_plans else "observe"
    action = action_mgr.propose(action_type=action_type, payload={"source": "demo"},
                                 created_by_agent="action_planner")
    funnel["actions_proposed"] = 1

    verification = verif_svc.create(action_id=action.action_id,
                                     verification_type="metric_return_to_baseline",
                                     expected_outcome={"vibration_rms_below": 0.35})
    funnel["verifications_created"] = 1

    _wait(DEMO_STEPS[6]["duration"], speed, 6, {
        "funnel": funnel, "agent_events": agent_events[-20:],
        "narrative": f"Action proposed: {action.action_type} (requires human approval). Verification pending.",
        "action": action.model_dump(mode="json"),
        "verification": verification.model_dump(mode="json"),
    })
    if _demo_stop.is_set(): return

    # --- Step 7: The Return — Learning ---
    from app.agent_loop.learning import LearningService

    learn_svc = LearningService()
    high_conf = [c for c in nano_records + micro_records + macro_records
                 if c.confidence >= 0.7 and c.severity in ("high", "critical")]
    proposal = learn_svc.propose(
        source_type="incident", source_id=high_conf[0].classification_id if high_conf else evidence[0].evidence_id,
        proposal_type="threshold_update",
        target_scope={"scope_type": "site", "scope_id": "factory-line-01"},
        before={"thresholds": baseline.thresholds if baseline else {}},
        after={"recommendation": "tighten thresholds for earlier detection"},
        rationale=f"Based on {len(high_conf)} high-confidence findings across {len(set(c.agent_name for c in high_conf))} agents",
        confidence=0.65,
    )
    funnel["learning_proposals"] = 1
    funnel["compression_ratio"] = round(funnel["total_evidence"] / max(funnel["actions_proposed"], 1), 1)

    all_records = nano_records + micro_records + macro_records
    _wait(DEMO_STEPS[7]["duration"], speed, 7, {
        "funnel": funnel, "agent_events": agent_events[-20:],
        "narrative": "The hero returns. What was learned will protect the future.",
        "learning_proposal": proposal.model_dump(mode="json"),
        "journey_summary": {
            "total_evidence": len(evidence),
            "modalities": len(set(e.modality for e in evidence)),
            "total_classifications": len(all_records),
            "tiers": {"nano": len(nano_records), "micro": len(micro_records), "macro": len(macro_records)},
            "agents_used": len(set(r.agent_name for r in all_records)),
            "high_confidence_findings": len(high_conf),
            "action": action.action_type,
            "verification_status": verification.status,
        },
    })

    set_demo_state({
        "status": "completed",
        "current_step": len(DEMO_STEPS) - 1,
        "step_progress": 100,
        "total_steps": len(DEMO_STEPS),
        "steps": DEMO_STEPS,
        "funnel": funnel,
        "agent_events": agent_events[-30:],
        "journey_summary": {
            "total_evidence": len(evidence),
            "modalities": len(set(e.modality for e in evidence)),
            "total_classifications": len(all_records),
            "tiers": {"nano": len(nano_records), "micro": len(micro_records), "macro": len(macro_records)},
            "agents_used": len(set(r.agent_name for r in all_records)),
            "high_confidence_findings": len(high_conf),
            "action": action.action_type,
            "verification_status": verification.status,
            "learning_proposal": proposal.proposal_type,
        },
    })


@router.post("/start")
async def start_demo(req: DemoStartRequest = DemoStartRequest()):
    global _demo_thread
    _demo_stop.clear()
    set_demo_state({"status": "starting", "total_steps": len(DEMO_STEPS), "steps": DEMO_STEPS})

    def _run():
        try:
            _run_demo(req.speed)
        except Exception as e:
            set_demo_state({"status": "error", "error": str(e)[:200]})

    _demo_thread = threading.Thread(target=_run, daemon=True)
    _demo_thread.start()
    return {"status": "started", "steps": len(DEMO_STEPS)}


@router.post("/stop")
async def stop_demo():
    _demo_stop.set()
    set_demo_state({"status": "stopped"})
    return {"status": "stopped"}


@router.get("/state")
async def get_state():
    from app.api.sse import get_demo_state
    state = get_demo_state()
    return state if state else {"status": "idle"}


@router.post("/ingest")
async def ingest_fixture():
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    return [e.model_dump(mode="json") for e in evidence]


@router.post("/baseline")
async def build_baseline():
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    baseline = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    baseline.status = "active"
    return baseline.model_dump(mode="json")


@router.post("/classify")
async def run_classification():
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    baseline = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    baseline.status = "active"
    from app.classification.engine import ClassificationEngine
    engine = ClassificationEngine()
    records = engine.classify(evidence, baseline)
    return [r.model_dump(mode="json") for r in records]


@router.post("/loop")
async def run_full_loop():
    evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    compiler = BaselineCompiler()
    baseline = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": "factory-line-01"})
    baseline.status = "active"
    from app.agent_loop.loop import AgentLoop
    loop = AgentLoop()
    result = loop.run(evidence, baseline)
    return {
        "classifications": [c.model_dump(mode="json") for c in result["classifications"]],
        "actions": [a.model_dump(mode="json") for a in result["actions"]],
        "verifications": [v.model_dump(mode="json") for v in result["verifications"]],
        "learning_proposals": [p.model_dump(mode="json") for p in result["learning_proposals"]],
    }
