"""Bootstrap API — connect, analyze, approve, deploy."""

import logging
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.bootstrap.semantic_classifier import SourceAnalysis
from app.domain.models import AgentMaturity, EvidenceArtifact

router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])

logger = logging.getLogger(__name__)

_state: dict = {"status": "idle"}
_samples: list[dict] = []
_analysis: Optional[SourceAnalysis] = None
_configs: dict = {}
_agents: list[AgentMaturity] = []


class ConnectRequest(BaseModel):
    source_type: str = "file"
    config: dict = {}


class AnalyzeRequest(BaseModel):
    hints: str = ""


class ApproveRequest(BaseModel):
    edits: dict = {}


@router.get("/scenarios")
async def get_scenarios():
    from app.bootstrap.scenarios import list_scenarios
    return {"scenarios": list_scenarios()}


@router.post("/scenarios/{scenario_id}/load")
async def load_scenario_data(scenario_id: str):
    global _samples, _state
    from app.bootstrap.scenarios import load_scenario
    samples, profile_id = load_scenario(scenario_id)
    if not samples:
        raise HTTPException(404, f"Scenario not found or empty: {scenario_id}")
    _samples = samples
    _state = {
        "status": "scenario_loaded",
        "scenario_id": scenario_id,
        "sample_count": len(samples),
        "sample_preview": samples[:5],
        "suggested_profile": profile_id,
    }
    return _state


@router.get("/profiles")
async def get_profiles():
    from app.bootstrap.profiles import list_profiles
    return {"profiles": list_profiles()}


@router.post("/profiles/{profile_id}/apply")
async def apply_profile(profile_id: str):
    global _analysis, _state, _agents
    from app.bootstrap.profiles import load_profile
    from app.bootstrap.semantic_classifier import SourceAnalysis

    profile = load_profile(profile_id)
    if profile is None:
        raise HTTPException(404, f"Profile not found: {profile_id}")

    _analysis = SourceAnalysis(
        modality=profile.get("modality", "mixed"),
        domain=profile.get("domain", "unknown"),
        domain_description=profile.get("description", ""),
        taxonomy=profile.get("taxonomy", {}),
        nano_rules=profile.get("nano_rules", []),
        micro_prompt=profile.get("micro_prompt", ""),
        macro_prompt=profile.get("macro_prompt", ""),
        confidence=1.0,
        reasoning=f"Loaded from pre-built profile: {profile.get('name', profile_id)}",
    )

    _agents = []
    for rule in _analysis.nano_rules:
        _agents.append(AgentMaturity(
            name=rule.get("name", "rule"),
            tier="draft", source="builtin",
            config={
                "name": rule.get("name", "rule"),
                "modality": rule.get("modality", _analysis.modality),
                "condition": rule.get("condition", {}),
                "classification": rule.get("classification", {}),
            },
        ))

    _state = {
        "status": "profile_applied",
        "profile_id": profile_id,
        "profile_name": profile.get("name", profile_id),
        "domain": _analysis.domain,
        "agents_created": len(_agents),
        "analysis": {
            "modality": _analysis.modality,
            "domain": _analysis.domain,
            "domain_description": _analysis.domain_description,
            "confidence": _analysis.confidence,
            "taxonomy": _analysis.taxonomy,
            "nano_rules": _analysis.nano_rules,
        },
    }
    return _state


@router.get("/models")
async def get_bootstrap_models():
    from app.inference.client import get_inference_config
    config = get_inference_config()
    return {
        "bootstrap_available": config.get("bootstrap_available", False),
        "bootstrap_model": config.get("bootstrap_model", ""),
        "available_models": [
            {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "type": "frontier", "provider": "Anthropic"},
            {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "type": "frontier", "provider": "Anthropic"},
            {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5", "type": "frontier", "provider": "Anthropic"},
            {"id": "qwen3-235b", "name": "Qwen 3 235B", "type": "open-weight", "provider": "Alibaba/Intel"},
        ],
    }


@router.post("/connect")
async def connect_source(req: ConnectRequest):
    global _samples, _state
    _state = {"status": "connecting", "source_type": req.source_type}

    if req.source_type == "file":
        from app.connectors.file import FileConnector
        connector = FileConnector()
    elif req.source_type == "prometheus":
        from app.connectors.prometheus import PrometheusConnector
        connector = PrometheusConnector()
    elif req.source_type == "kubernetes":
        from app.connectors.kubernetes import KubernetesConnector
        connector = KubernetesConnector()
    else:
        raise HTTPException(400, f"Unsupported source type: {req.source_type}. Supported: file, prometheus, kubernetes")

    if not connector.connect(req.config):
        raise HTTPException(400, "Failed to connect to source")

    _samples = connector.sample(200)
    _state = {
        "status": "connected",
        "source_type": req.source_type,
        "source_info": connector.describe(),
        "sample_count": len(_samples),
        "sample_preview": _samples[:5],
    }
    return _state


@router.post("/analyze")
async def analyze_source(req: AnalyzeRequest = AnalyzeRequest()):
    global _analysis, _state
    if not _samples:
        raise HTTPException(400, "No samples — connect to a source first")

    _state["status"] = "analyzing"

    from app.bootstrap.semantic_classifier import analyze_samples
    _analysis = analyze_samples(_samples, hints=req.hints)

    if _analysis.error:
        _state["status"] = "analysis_error"
        _state["error"] = _analysis.error
        return {"status": "error", "error": _analysis.error, "analysis": asdict(_analysis)}

    _state["status"] = "analyzed"
    _state["analysis"] = {
        "modality": _analysis.modality,
        "domain": _analysis.domain,
        "domain_description": _analysis.domain_description,
        "confidence": _analysis.confidence,
        "reasoning": _analysis.reasoning,
        "features": _analysis.features,
        "taxonomy": _analysis.taxonomy,
        "thresholds": _analysis.thresholds,
        "nano_rules": _analysis.nano_rules,
        "schema_mapping": _analysis.schema_mapping,
        "micro_prompt": _analysis.micro_prompt,
        "macro_prompt": _analysis.macro_prompt,
        "inference_latency_ms": _analysis.inference_latency_ms,
    }
    return _state


@router.get("/config")
async def get_config():
    if _analysis is None:
        return {"status": "no_analysis", "configs": {}}
    return {"status": _state.get("status", "idle"), "analysis": asdict(_analysis), "configs": _configs}


@router.put("/config")
async def edit_config(edits: dict):
    global _analysis
    if _analysis is None:
        raise HTTPException(400, "No analysis to edit")
    if "taxonomy" in edits and _analysis:
        _analysis.taxonomy = edits["taxonomy"]
    if "thresholds" in edits and _analysis:
        _analysis.thresholds = edits["thresholds"]
    if "nano_rules" in edits and _analysis:
        _analysis.nano_rules = edits["nano_rules"]
    if "micro_prompt" in edits and _analysis:
        _analysis.micro_prompt = edits["micro_prompt"]
    if "macro_prompt" in edits and _analysis:
        _analysis.macro_prompt = edits["macro_prompt"]
    _state["status"] = "edited"
    return {"status": "edited", "analysis": asdict(_analysis)}


@router.post("/approve")
async def approve_config(req: ApproveRequest = ApproveRequest()):
    global _configs, _state
    if _analysis is None:
        raise HTTPException(400, "No analysis to approve")

    if req.edits:
        await edit_config(req.edits)

    from app.bootstrap.config_generator import generate_configs
    source_name = _analysis.domain.replace(" ", "_").lower()
    _configs = generate_configs(_analysis, source_name=source_name)

    from app.classification.taxonomy import reload
    reload()

    _state["status"] = "approved"
    _state["configs_generated"] = list(_configs.keys())
    return {"status": "approved", "configs": list(_configs.keys()), "message": "Configuration approved and deployed"}


@router.post("/test")
async def test_pipeline():
    if not _samples:
        raise HTTPException(400, "No samples — connect first")
    if _analysis is None:
        raise HTTPException(400, "No analysis — analyze first")

    from app.multimodal.normalizer import normalize_raw
    from app.baseline.compiler import BaselineCompiler
    from app.nanoagents.pipeline import run_pipeline

    evidence = []
    for sample in _samples[:20]:
        ev = normalize_raw(
            source="bootstrap_test",
            modality=_analysis.modality,
            content={"values": [float(v) for v in sample.values() if _is_numeric(v)], **sample},
        )
        evidence.append(ev)

    compiler = BaselineCompiler()
    baseline = compiler.compile(evidence=evidence, scope={"scope_type": "domain", "scope_id": _analysis.domain})

    records = run_pipeline(evidence, baseline)

    return {
        "status": "tested",
        "evidence_count": len(evidence),
        "classification_count": len(records),
        "records": [r.model_dump(mode="json") for r in records[:20]],
        "baseline_confidence": baseline.confidence,
    }


@router.post("/validate")
async def validate_agents():
    if not _samples:
        raise HTTPException(400, "No samples — connect first")
    if _analysis is None:
        raise HTTPException(400, "No analysis — analyze first")

    from app.bootstrap.promotion import run_validation_round, get_rubric_matrix
    from app.bootstrap.rule_engine import RuleBasedNanoagent
    from app.multimodal.normalizer import normalize_raw
    from app.baseline.compiler import BaselineCompiler

    valid_modalities = {"metric", "log", "event", "text", "document", "image", "audio", "trace", "human_note", "unknown"}
    modality = _analysis.modality if _analysis.modality in valid_modalities else "event"

    evidence = []
    for sample in _samples:
        features = {}
        for k, v in sample.items():
            if _is_numeric(v):
                features[k] = float(v)
            else:
                features[k] = v
        ev = EvidenceArtifact(
            source="bootstrap_validate",
            modality=modality,
            artifact_type=sample.get("type", modality),
            namespace=sample.get("namespace", ""),
            resource_name=sample.get("name", ""),
            features=features,
            content_text=str(sample),
        )
        evidence.append(ev)

    compiler = BaselineCompiler()
    baseline = compiler.compile(evidence=evidence, scope={"scope_type": "domain", "scope_id": _analysis.domain})

    global _agents
    if not _agents:
        for rule in _analysis.nano_rules:
            _agents.append(AgentMaturity(
                name=rule.get("name", "rule"),
                tier="draft", source="bootstrap",
                config={
                    "name": rule.get("name", "rule"),
                    "modality": _analysis.modality,
                    "condition": {"field": rule.get("field", ""), "operator": rule.get("operator", "gt"), "value": rule.get("value", 0)},
                    "classification": {"taxonomy": rule.get("taxonomy", "operational_state"), "class_name": rule.get("class_name", "degraded"), "severity": rule.get("severity", "high"), "confidence": 0.8},
                },
            ))

    _agents = run_validation_round(_agents, evidence, baseline)
    matrix = get_rubric_matrix(_agents)
    _state["status"] = "validated"
    _state["rubric"] = matrix
    return matrix


@router.get("/rubric")
async def get_rubric():
    from app.bootstrap.promotion import get_rubric_matrix
    return get_rubric_matrix(_agents)


@router.post("/promote/{agent_id}")
async def promote_agent(agent_id: str):
    from app.bootstrap.promotion import PromotionEngine
    engine = PromotionEngine()
    for i, agent in enumerate(_agents):
        if str(agent.agent_id) == agent_id:
            agent.human_reviewed = True
            _agents[i] = engine.check_promotion(agent)
            return {"status": "promoted", "agent": _agents[i].model_dump(mode="json")}
    raise HTTPException(404, "Agent not found")


@router.post("/demote/{agent_id}")
async def demote_agent(agent_id: str):
    for i, agent in enumerate(_agents):
        if str(agent.agent_id) == agent_id:
            prev = agent.tier
            agent.tier = "draft"
            agent.rubric_status = "red"
            agent.promotion_history.append({"from": prev, "to": "draft", "reason": "manual_demotion"})
            return {"status": "demoted", "agent": agent.model_dump(mode="json")}
    raise HTTPException(404, "Agent not found")


@router.get("/status")
async def get_status():
    return _state


@router.post("/reset")
async def reset():
    global _samples, _analysis, _configs, _state, _agents
    _samples = []
    _analysis = None
    _configs = {}
    _agents = []
    _state = {"status": "idle"}
    return {"status": "reset"}


def _is_numeric(val) -> bool:
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False
