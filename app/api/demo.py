"""Synthetic fleet presentation story; never runtime or promotion evidence."""

import importlib
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter
from pydantic import BaseModel

from app.api.sse import set_demo_state
from app.baseline.compiler import BaselineCompiler
from app.classification.cascade import should_escalate_to_macro, should_escalate_to_micro
from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact
from app.multimodal.normalizer import normalize_fixture
from app.multimodal.scale_generator import generate_scaled_evidence

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])
DEMO_EVIDENCE_STATE = "synthetic-presentation-only"

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

_demo_thread: Optional[threading.Thread] = None
_demo_stop = threading.Event()
_demo_pause = threading.Event()
_demo_pause.set()  # starts unpaused (set = not paused)

# Flow descriptions per step: the technical story
FLOW_DESCRIPTIONS = {
    "cost": (
        "GPU inference costs $32/hr per instance. Intel Xeon CPU inference via llm-d "
        "runs at $0.60/hr. A 53x cost reduction. The fleet controller monitors both "
        "cost curves and routes traffic to the cheapest tier that meets SLO targets."
    ),
    "event": (
        "An event profile defines the blast parameters: expected concurrency, models requested, "
        "burst multiplier, and SLO targets. fleet-llm-d loads these profiles to pre-position "
        "resources before the first user arrives."
    ),
    "fleet_deploy": (
        "fleet-llm-d deploys across clusters, placing models where GPU or CPU capacity exists. "
        "The fleet agent on each cluster reports health, capacity, and latency back to the "
        "control plane. Model placement follows affinity, cost, and SLO constraints."
    ),
    "platform": (
        "Seven CRDs define the fleet's desired state: FleetInferencePool, PlacementPolicy, "
        "TenantProfile, ModelProfile, SLOTarget, EventProfile, and FleetGateway. The controller "
        "reconciles actual state toward desired state continuously."
    ),
    "forecast": (
        "The SLO forecaster agent runs linear regression on P95 latency time series. When the "
        "projected breach time falls within the forecast horizon, it emits a classification with "
        "confidence proportional to R-squared fit. This is predictive, not reactive."
    ),
    "blast_radius": (
        "The consequence scoper assesses impact: how many models affected, how many tenants, "
        "how many users. It computes a severity score (users x violation x model_count) and "
        "determines whether human approval is required before action."
    ),
    "intent": (
        "This synthetic storyline illustrates the proposed intent lifecycle. It does not submit "
        "a FleetIntent, authorize execution, or observe an infrastructure change."
    ),
    "proof": (
        "This presentation renders illustrative ledger rows only. Live immutable-ledger receipts "
        "and cross-repository execution evidence must be collected separately."
    ),
    "scale_10": (
        "Twenty concurrent users across five models. The SLO forecaster processes latency evidence "
        "in real time. Nanoagent-level filtering compresses the signal, and only actionable deviations "
        "reach the forecaster. All classification on CPU."
    ),
    "scale_50": (
        "One hundred users. HPA scales replicas from 1 to 4 based on queue depth and P95 latency. "
        "The fleet controller coordinates scaling across clusters, respecting placement policies "
        "and cost constraints. Scale events are ledger-recorded."
    ),
    "stress": (
        "Two hundred concurrent users saturate capacity. Load shedding activates. A ShedLoadIntent "
        "caps inflight requests per model. 503 responses are absorbed gracefully. The system "
        "degrades predictably rather than failing catastrophically."
    ),
    "recovery": (
        "Load drops below capacity. P95 latency returns to SLO targets within minutes. The fleet "
        "controller captures learning: updated event profiles, refined SLO thresholds, improved "
        "pre-warm timing. Each incident makes the fleet smarter."
    ),
    "claim": (
        "Synthetic scenario complete. Cost, scale, execution, and ledger outcomes shown here are "
        "illustrative and cannot support a maturity or production-readiness claim."
    ),
}

DEMO_STEPS = [
    {"id": "cost",           "title": "The Cost of Inference",        "subtitle": "GPU inference: $32/hr. Intel Xeon: $0.60/hr.",                    "duration": 10},
    {"id": "event",          "title": "The Event Arrives",            "subtitle": "Summit Connect: 200 users in 30 minutes.",                       "duration": 12},
    {"id": "fleet_deploy",   "title": "The Fleet Deploys",           "subtitle": "fleet-llm-d orchestrates clusters and models.",                   "duration": 12},
    {"id": "platform",       "title": "The Platform",                "subtitle": "7 CRDs define the fleet's desired state.",                        "duration": 12},
    {"id": "forecast",       "title": "The Brain Predicts",          "subtitle": "SLO forecaster: P95 will breach in 22 minutes.",                  "duration": 15},
    {"id": "blast_radius",   "title": "The Blast Radius",            "subtitle": "200 users x 5 models. Severity: critical.",                       "duration": 12},
    {"id": "intent",         "title": "The Intent",                  "subtitle": "Synthetic lifecycle illustration; no execution.",                 "duration": 12},
    {"id": "proof",          "title": "The Proof",                   "subtitle": "Illustrative rows; live receipts required.",                       "duration": 10},
    {"id": "scale_10",       "title": "Scale: 10x Load",           "subtitle": "20 concurrent users across 5 models.",                            "duration": 12},
    {"id": "scale_50",       "title": "Scale: 50x Load",           "subtitle": "100 users. HPA scales 1 to 4 replicas.",                          "duration": 12},
    {"id": "stress",         "title": "Stress Test",                 "subtitle": "200 users. Load shedding activates. 503s absorbed.",              "duration": 15},
    {"id": "recovery",       "title": "Recovery",                    "subtitle": "Load drops. Metrics stabilize. Learning captured.",                "duration": 10},
    {"id": "claim",          "title": "Scenario Boundary",           "subtitle": "Synthetic presentation only; not promotion evidence.",             "duration": 8},
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


def _run_demo(speed: float):
    agent_events: list[dict] = []
    models = ["granite-350m", "granite-2b-int8", "granite-4.1-3b",
              "granite-3.2-sovereign", "granite-3.2-8b"]
    cumulative = {"total_evidence": 0, "total_classifications": 0,
                  "models_served": len(models), "clusters_active": 2,
                  "peak_users": 0, "intents_emitted": 0}
    funnel: dict = {"total_evidence": 0, "forecasts": 0, "breach_predicted": 0,
                    "intents_emitted": 0, "intents_executed": 0}
    def _extras(**kw):
        return {"funnel": funnel, "agent_events": agent_events[-25:],
                "cumulative": cumulative, "evidence_state": DEMO_EVIDENCE_STATE, **kw}

    # === PART 1: FLEET WALKTHROUGH (steps 0-7) ===
    # Step 0: The Cost of Inference
    fleet_metrics = {"gpu_per_hour": 32.00, "cpu_per_hour": 0.60, "savings_factor": 53}
    _wait(DEMO_STEPS[0]["duration"], speed, 0, _extras(
        narrative="GPU inference costs $32/hr per instance. Intel Xeon CPU inference via "
                  "llm-d runs at $0.60/hr. That is a 53x cost reduction. The foundation "
                  "of the fleet-llm-d value proposition.",
        fleet_metrics=fleet_metrics, cost_data=fleet_metrics,
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(0, _extras(
        narrative="Cost baseline established: 53x savings with CPU inference.",
        fleet_metrics=fleet_metrics, cost_data=fleet_metrics))
    if _demo_stop.is_set(): return

    # Step 1: The Event Arrives
    event_profile = {}
    profile_path = CONFIG_DIR / "defaults" / "event_profiles" / "summit_connect.yaml"
    try:
        with open(profile_path) as f:
            event_profile = yaml.safe_load(f)
    except Exception:
        event_profile = {"name": "summit-connect", "load_profile": {
            "concurrent_users": 200, "models": models}}
    ep_load = event_profile.get("load_profile", {})
    ep_slo = event_profile.get("slo_targets", {})
    event_data = {
        "event_name": event_profile.get("name", "summit-connect"),
        "expected_users": ep_load.get("concurrent_users", 200),
        "models": ep_load.get("models", models),
        "peak_burst": ep_load.get("peak_burst_multiplier", 4),
        "p95_slo_ms": ep_slo.get("p95_latency_ms", 5000),
        "pre_warm_minutes": event_profile.get("schedule", {}).get("pre_warm_minutes", 30),
    }
    _wait(DEMO_STEPS[1]["duration"], speed, 1, _extras(
        narrative=f"Event profile loaded: {event_data['event_name']}. "
                  f"{event_data['expected_users']} concurrent users, "
                  f"{len(event_data['models'])} models, "
                  f"{event_data['peak_burst']}x peak burst. "
                  f"P95 SLO target: {event_data['p95_slo_ms']}ms.",
        event_profile=event_data,
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(1, _extras(
        narrative=f"Event profile '{event_data['event_name']}' loaded. "
                  f"Pre-warming starts {event_data['pre_warm_minutes']}min before session.",
        event_profile=event_data))
    if _demo_stop.is_set(): return

    # Step 2: The Fleet Deploys
    clusters = [
        {"name": "dev-cluster-1", "status": "healthy", "gpu": False, "cpu_nodes": 4},
        {"name": "prod-cluster-1", "status": "healthy", "gpu": False, "cpu_nodes": 8},
    ]
    model_deployments = [{"model": m, "cluster": clusters[i % 2]["name"],
                          "replicas": 1, "status": "running"} for i, m in enumerate(models)]
    _wait(DEMO_STEPS[2]["duration"], speed, 2, _extras(
        narrative=f"{len(clusters)} clusters active. {len(models)} models deployed. "
                  f"Fleet health: all green. CPU inference on Intel Xeon, no GPU required.",
        fleet_clusters=clusters, model_deployments=model_deployments,
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(2, _extras(
        narrative="Fleet deployed and healthy. All models serving on CPU.",
        fleet_clusters=clusters, model_deployments=model_deployments))
    if _demo_stop.is_set(): return

    # Step 3: The Platform
    crds = [
        {"name": "FleetInferencePool", "purpose": "Defines a pool of inference endpoints across clusters"},
        {"name": "PlacementPolicy", "purpose": "Rules for where models can be placed (affinity, cost, SLO)"},
        {"name": "TenantProfile", "purpose": "Per-tenant resource quotas and priority"},
        {"name": "ModelProfile", "purpose": "Model metadata: size, precision, GPU/CPU requirements"},
        {"name": "SLOTarget", "purpose": "Latency and error rate targets per model per tenant"},
        {"name": "EventProfile", "purpose": "Scheduled event load parameters and pre-warm config"},
        {"name": "FleetGateway", "purpose": "Cross-cluster traffic routing and load balancing"},
    ]
    _wait(DEMO_STEPS[3]["duration"], speed, 3, _extras(
        narrative=f"{len(crds)} CRDs define the fleet's desired state. The controller "
                  f"reconciles actual state toward desired state continuously.",
        crds=crds,
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(3, _extras(
        narrative="Platform CRDs established. Ready for predictive scaling.", crds=crds))
    if _demo_stop.is_set(): return

    # Step 4: The Brain Predicts (SLO Forecaster)
    from app.microagents.slo_forecaster import SLOForecasterAgent

    evidence = []
    for i in range(30):
        evidence.append(EvidenceArtifact(
            source="fleet-metrics", modality="metric", artifact_type="latency_p95",
            features={"value": 800 + 123 * i, "timestamp_offset_minutes": i,
                      "slo_target": 5000, "model": "granite-4.1-3b",
                      "active_users": 200, "models": models},
        ))

    forecaster = SLOForecasterAgent()
    forecast_records = forecaster.classify(evidence)

    slo_gauge = {"current_p95": 800, "forecast_p95": 0, "slo_target": 5000,
                 "minutes_to_breach": 0, "confidence": 0, "slope": 0}
    for r in forecast_records:
        m = r.metrics or {}
        slo_gauge.update({"forecast_p95": m.get("forecast_value", 0),
                          "minutes_to_breach": m.get("minutes_to_breach", 0),
                          "confidence": r.confidence, "slope": m.get("slope_per_minute", 0)})
        _emit(agent_events, r.agent_name, r.class_name, r.taxonomy,
              r.severity, r.confidence, "micro", r.rationale)

    cumulative["total_evidence"] += len(evidence)
    cumulative["total_classifications"] += len(forecast_records)
    funnel.update({"total_evidence": len(evidence), "forecasts": len(forecast_records),
                   "breach_predicted": sum(1 for r in forecast_records if r.class_name == "slo_breach_predicted")})

    _wait(DEMO_STEPS[4]["duration"], speed, 4, _extras(
        narrative=f"SLO forecaster: P95 latency forecast to reach "
                  f"{slo_gauge['forecast_p95']:.0f}ms. "
                  f"Breach predicted in ~{slo_gauge['minutes_to_breach']:.0f} minutes. "
                  f"Confidence: {slo_gauge['confidence']:.0%}.",
        slo_gauge=slo_gauge,
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(4, _extras(
        narrative=f"SLO breach predicted in ~{slo_gauge['minutes_to_breach']:.0f} minutes. "
                  f"Ready to assess blast radius.",
        slo_gauge=slo_gauge))
    if _demo_stop.is_set(): return

    # Step 5: The Blast Radius
    from app.macroagents import consequence_scoper

    blast_evidence = [EvidenceArtifact(
        source="fleet-metrics", modality="metric", artifact_type="latency_p95",
        features={"models": models, "active_users": 200},
    )]
    blast_classification = ClassificationRecord(
        target_type="evidence", target_id=blast_evidence[0].evidence_id,
        agent_tier="micro", agent_name="slo_forecaster",
        taxonomy="fleet.slo", class_name="slo_breach_predicted",
        severity="critical", confidence=0.85, rationale="P95 forecast exceeds SLO",
        metrics={"forecast_value": 6200, "slo_target": 5000},
    )
    scoped = consequence_scoper.reason(blast_evidence, [blast_classification])

    blast_data = {"affected_models": len(models), "affected_users": 200,
                  "severity": "critical", "requires_human_gate": True, "severity_score": 0}
    for r in scoped:
        blast_data["severity_score"] = (r.metrics or {}).get("severity_score", 0)
        blast_data["requires_human_gate"] = (r.metrics or {}).get("requires_human_gate", True)
        _emit(agent_events, r.agent_name, r.class_name, r.taxonomy,
              r.severity, r.confidence, "macro", r.rationale)
    cumulative["total_classifications"] += len(scoped)

    _wait(DEMO_STEPS[5]["duration"], speed, 5, _extras(
        narrative=f"Blast radius: {blast_data['affected_models']} models, "
                  f"{blast_data['affected_users']} users affected. "
                  f"Severity score: {blast_data['severity_score']:.0f}. "
                  f"{'Requires human approval.' if blast_data['requires_human_gate'] else 'Auto-action permitted.'}",
        blast_radius=blast_data,
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(5, _extras(
        narrative="Blast radius assessed. Consequence scoper recommends human gate.",
        blast_radius=blast_data))
    if _demo_stop.is_set(): return

    # Step 6: The Intent
    from app.domain.fleet_intents import PreWarmIntent

    intent = PreWarmIntent(
        confidence=0.85, horizon_seconds=1320,
        justification="SLO breach predicted at T+22min",
        model="granite-4.1-3b", target_replicas=4,
        reason="Summit Connect pre-warming",
    )

    intent_phases = ["predict", "emit", "evaluate", "illustrate"]
    for phase_idx, phase in enumerate(intent_phases):
        if _demo_stop.is_set(): return
        progress = ((phase_idx + 1) / len(intent_phases)) * 100
        set_demo_state(_make_state(6, progress, **_extras(
            narrative=f"Intent lifecycle: {phase}. "
                      f"PreWarmIntent for {intent.model} to {intent.target_replicas} replicas.",
            intent_flow={
                "intent_type": "PreWarmIntent",
                "model": intent.model,
                "target_replicas": intent.target_replicas,
                "confidence": intent.confidence,
                "horizon_seconds": intent.horizon_seconds,
                "justification": intent.justification,
                "current_phase": phase,
                "phases": intent_phases,
                "phase_index": phase_idx,
                "stages": [
                    {"name": p, "status": "complete" if i < phase_idx
                     else "active" if i == phase_idx else "pending"}
                    for i, p in enumerate(intent_phases)
                ],
            },
        )))
        _pause_sleep(max(0.5, DEMO_STEPS[6]["duration"] / len(intent_phases) / speed))

    cumulative["intents_emitted"] += 1
    funnel.update({"intents_emitted": funnel["intents_emitted"] + 1})
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(6, _extras(
        narrative=f"Synthetic PreWarmIntent illustration for {intent.model}; no replicas were changed.",
        intent_flow={"intent_type": "PreWarmIntent", "model": intent.model,
                     "target_replicas": intent.target_replicas, "status": "simulated",
                     "current_phase": "illustrate", "phases": intent_phases,
                     "stages": [{"name": p, "status": "complete"} for p in intent_phases]}))
    if _demo_stop.is_set(): return

    # Step 7: The Proof
    ledger_chains = [
        {"chain": "evidence-ingestion", "entries": 30, "status": "illustrative", "hash_verified": False},
        {"chain": "slo-forecast", "entries": len(forecast_records), "status": "illustrative", "hash_verified": False},
        {"chain": "blast-radius", "entries": len(scoped), "status": "illustrative", "hash_verified": False},
        {"chain": "intent-lifecycle", "entries": 4, "status": "illustrative", "hash_verified": False},
        {"chain": "execution-audit", "entries": 1, "status": "illustrative", "hash_verified": False},
    ]
    test_matrix = {"unit": 0, "bdd": 0, "contract": 0, "e2e": 0,
                   "integration": 0, "total": 0, "passing": 0,
                   "evidence_state": DEMO_EVIDENCE_STATE}

    _wait(DEMO_STEPS[7]["duration"], speed, 7, _extras(
        narrative="Illustrative ledger rows only; no live receipt or chain verification was performed.",
        ledger_chains=ledger_chains, test_matrix=test_matrix,
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(7, _extras(
        narrative="Synthetic proof step complete. Live external evidence remains required.",
        ledger_chains=ledger_chains, test_matrix=test_matrix))
    if _demo_stop.is_set(): return

    # === PART 2: SCALE RUN (steps 8-12) ===
    # Step 8: Scale: 10x Load (20 users)
    scale_ev_10 = [EvidenceArtifact(
        source="fleet-metrics", modality="metric", artifact_type="latency_p95",
        features={"value": 900 + 80 * i, "timestamp_offset_minutes": i,
                  "slo_target": 5000, "model": models[i % len(models)],
                  "active_users": 20, "models": models},
    ) for i in range(20)]

    sr_10 = forecaster.classify(scale_ev_10)
    for r in sr_10:
        _emit(agent_events, r.agent_name, r.class_name, r.taxonomy,
              r.severity, r.confidence, "micro", r.rationale)

    s10_funnel = {"total_evidence": 20, "forecasts": len(sr_10),
                  "breach_predicted": sum(1 for r in sr_10 if "breach" in r.class_name),
                  "safe": sum(1 for r in sr_10 if "safe" in r.class_name)}
    cumulative["total_evidence"] += 20
    cumulative["total_classifications"] += len(sr_10)
    cumulative["peak_users"] = 20

    _wait(DEMO_STEPS[8]["duration"], speed, 8, _extras(
        narrative=f"20 users across 5 models. {len(sr_10)} SLO forecasts generated. "
                  f"System healthy, all latencies within SLO targets.",
        funnel=s10_funnel,
        scale_metrics={"users": 20, "models": 5, "evidence": 20,
                       "classifications": len(sr_10), "replicas": 1},
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(8, _extras(
        narrative="10x load absorbed. All SLOs met. Ready to push to 50x.",
        funnel=s10_funnel))
    if _demo_stop.is_set(): return

    # Step 9: Scale: 50x Load (100 users, HPA scaling)
    scale_ev_50 = [EvidenceArtifact(
        source="fleet-metrics", modality="metric", artifact_type="latency_p95",
        features={"value": 1200 + 35 * i, "timestamp_offset_minutes": i,
                  "slo_target": 5000, "model": models[i % len(models)],
                  "active_users": 100, "models": models},
    ) for i in range(100)]

    sr_50 = forecaster.classify(scale_ev_50)
    for r in sr_50:
        _emit(agent_events, r.agent_name, r.class_name, r.taxonomy,
              r.severity, r.confidence, "micro", r.rationale)

    replica_events = [
        {"time": "T+0", "replicas": 1, "trigger": "baseline"},
        {"time": "T+5min", "replicas": 2, "trigger": "queue_depth > 10"},
        {"time": "T+12min", "replicas": 4, "trigger": "p95_latency > 3500ms"},
    ]
    s50_funnel = {"total_evidence": 100, "forecasts": len(sr_50),
                  "breach_predicted": sum(1 for r in sr_50 if "breach" in r.class_name),
                  "safe": sum(1 for r in sr_50 if "safe" in r.class_name)}
    cumulative["total_evidence"] += 100
    cumulative["total_classifications"] += len(sr_50)
    cumulative["peak_users"] = 100

    _wait(DEMO_STEPS[9]["duration"], speed, 9, _extras(
        narrative=f"100 users. HPA scaling: 1 to 2 to 4 replicas. "
                  f"{len(sr_50)} forecasts generated. Latencies rising but within SLO.",
        funnel=s50_funnel, replica_events=replica_events,
        scale_metrics={"users": 100, "models": 5, "evidence": 100,
                       "classifications": len(sr_50), "replicas": 4},
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(9, _extras(
        narrative="50x load absorbed. HPA scaled to 4 replicas. Ready for stress test.",
        funnel=s50_funnel, replica_events=replica_events))
    if _demo_stop.is_set(): return

    # Step 10: Stress Test (200 users, load shedding)
    from app.domain.fleet_intents import ShedLoadIntent

    scale_ev_200 = [EvidenceArtifact(
        source="fleet-metrics", modality="metric", artifact_type="latency_p95",
        features={"value": 2000 + 25 * i + (500 if i > 150 else 0),
                  "timestamp_offset_minutes": i, "slo_target": 5000,
                  "model": models[i % len(models)],
                  "active_users": 200, "models": models},
    ) for i in range(200)]

    sr_200 = forecaster.classify(scale_ev_200)
    for r in sr_200:
        _emit(agent_events, r.agent_name, r.class_name, r.taxonomy,
              r.severity, r.confidence, "micro", r.rationale)

    shed_intent = ShedLoadIntent(
        confidence=0.90, horizon_seconds=300,
        justification="Capacity saturated at 200 concurrent users",
        model="granite-4.1-3b", max_inflight=50,
        duration_seconds=300, reason="Stress test load shedding",
    )
    n_503 = 23
    stress_funnel = {"total_evidence": 200, "forecasts": len(sr_200),
                     "breach_predicted": sum(1 for r in sr_200 if "breach" in r.class_name),
                     "load_shed": True, "http_503_count": n_503}
    cumulative["total_evidence"] += 200
    cumulative["total_classifications"] += len(sr_200)
    cumulative["peak_users"] = 200
    cumulative["intents_emitted"] += 1

    _wait(DEMO_STEPS[10]["duration"], speed, 10, _extras(
        narrative=f"200 users. Load shedding activated via ShedLoadIntent: max "
                  f"{shed_intent.max_inflight} inflight per model. "
                  f"{n_503} 503s absorbed gracefully. System degrades predictably.",
        funnel=stress_funnel,
        intent_flow={"intent_type": "ShedLoadIntent", "model": shed_intent.model,
                     "max_inflight": shed_intent.max_inflight, "status": "simulated",
                     "current_phase": "illustrate"},
        scale_metrics={"users": 200, "models": 5, "evidence": 200,
                       "classifications": len(sr_200), "replicas": 4, "http_503": n_503},
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(10, _extras(
        narrative=f"Stress test complete. {n_503} 503s absorbed. System held.",
        funnel=stress_funnel))
    if _demo_stop.is_set(): return

    # Step 11: Recovery
    recovery_ev = [EvidenceArtifact(
        source="fleet-metrics", modality="metric", artifact_type="latency_p95",
        features={"value": max(400, 3000 - 60 * i), "timestamp_offset_minutes": i,
                  "slo_target": 5000, "model": models[i % len(models)],
                  "active_users": max(10, 200 - 6 * i), "models": models},
    ) for i in range(30)]

    recovery_records = forecaster.classify(recovery_ev)
    cumulative["total_evidence"] += len(recovery_ev)
    cumulative["total_classifications"] += len(recovery_records)

    learning = [
        {"type": "event_profile_update", "detail": "Peak burst multiplier updated: 4x to 6x"},
        {"type": "slo_threshold_refinement", "detail": "Pre-warm trigger latency: 3500ms to 3000ms"},
        {"type": "capacity_model_update", "detail": "Users-per-replica ceiling: 50 to 40"},
    ]

    _wait(DEMO_STEPS[11]["duration"], speed, 11, _extras(
        narrative="Load drops. P95 latency returns to baseline within 8 minutes. "
                  "3 learning proposals generated. Each incident makes the fleet smarter.",
        scale_metrics={"users": 10, "models": 5, "replicas": 4,
                       "p95_current": 450, "status": "stabilized"},
        learning_proposals=learning,
    ))
    if _demo_stop.is_set(): return
    _auto_pause_between_steps(11, _extras(
        narrative="Recovery complete. Learning captured. Ready for the claim.",
        learning_proposals=learning))
    if _demo_stop.is_set(): return

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
        "narrative": "Synthetic scenario complete; live cost, execution, and ledger evidence remains required.",
        "evidence_state": DEMO_EVIDENCE_STATE,
        "cumulative": cumulative,
        "claim": {
            "cost_reduction": "illustrative 53x",
            "models_served": 5,
            "peak_users": 200,
            "replicas_scaled": 4,
            "total_evidence": cumulative["total_evidence"],
            "total_classifications": cumulative["total_classifications"],
            "intents_emitted": cumulative["intents_emitted"],
            "tests_passing": 0,
            "ledger_chains": 0,
            "http_503_absorbed": n_503,
            "learning_proposals": len(learning),
            "clusters": 2,
            "inference": "CPU only (Intel Xeon)",
            "gpu": "none",
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
        {"name": "metric_drift", "type": "deterministic", "runtime": "CPU", "description": "Slope and z-score checks, detects gradual trends in metric time series"},
        {"name": "log_pattern", "type": "deterministic", "runtime": "CPU", "description": "Regex pattern matching for ERROR/WARN/CRIT in log evidence"},
        {"name": "document_heuristic", "type": "deterministic", "runtime": "CPU", "description": "Keyword analysis for actionable terms in documents and notes"},
        {"name": "image_metadata", "type": "deterministic", "runtime": "CPU", "description": "Defect score evaluation from image inspection labels"},
        {"name": "audio_energy", "type": "deterministic", "runtime": "CPU", "description": "Anomaly score evaluation from audio/vibration sensor labels"},
        {"name": "evidence_gate", "type": "deterministic", "runtime": "CPU", "description": "Decides ignore/retain/escalate for each evidence piece based on modality and severity"},
    ]
    micro_agents = [
        {"name": "text_classifier", "type": "rule-backed", "runtime": "CPU (Xeon-optimized)", "description": "Pattern matching against known incident families: infrastructure, quality, security, capacity"},
        {"name": "document_classifier", "type": "rule-backed", "runtime": "CPU (Xeon-optimized)", "description": "Document type and sensitivity classification by keyword analysis"},
        {"name": "image_classifier", "type": "fixture-backed / optional ONNX", "runtime": "CPU (Xeon-optimized)", "description": "Defect classification is fixture-backed by default, with optional OpenVINO/ONNX CPU adapters when configured"},
        {"name": "audio_classifier", "type": "fixture-backed / optional ONNX", "runtime": "CPU (Xeon-optimized)", "description": "Anomaly classification is fixture-backed by default, with optional OpenVINO/ONNX CPU adapters when configured"},
        {"name": "embedding_classifier", "type": "placeholder", "runtime": "CPU", "description": "Placeholder for embedding/clustering, extension point for vector inference"},
    ]
    macro_agents = [
        {"name": "incident_timeline", "type": "template-based", "runtime": "CPU", "description": "Sequences evidence by timestamp, overlays classifications to build incident narrative"},
        {"name": "root_cause_hypothesis", "type": "template-based", "runtime": "CPU", "description": "Counts classification families across modalities to identify most likely root cause"},
        {"name": "action_planner", "type": "template-based", "runtime": "CPU", "description": "Proposes safe actions (notify, observe, ticket), never destructive without human approval"},
        {"name": "verification_planner", "type": "template-based", "runtime": "CPU", "description": "Builds verification plan to check if post-action metrics return to baseline"},
        {"name": "learning_proposal", "type": "template-based", "runtime": "CPU", "description": "Proposes threshold/rule updates based on high-confidence findings, never auto-applied"},
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
            "nano_tier": "Deterministic rules, always CPU, no inference",
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
            "compression": "Nanoagents filter most evidence before micro/macro tiers, no inference cost for filtered signals",
            "safety": "Only non-destructive actions proposed. Destructive ops require human approval. Learning never auto-applied.",
        },
        "framework": {
            "backend": "FastAPI + Pydantic v2",
            "frontend": "React 19 + motion/react",
            "database": "PostgreSQL (optional, graceful degradation without DB)",
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
        "runtime": "CPU, no inference",
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
        "runtime": "LLM via LiteLLM" if is_inference_available() else "CPU, rules only",
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
        "runtime": "LLM via LiteLLM" if is_inference_available() else "CPU, templates only",
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
