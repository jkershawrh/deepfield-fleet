"""Fleet-llm-d demo endpoints — live proxy or simulated responses for offline demos."""

import hashlib
import logging
import os
import random
import time
from pathlib import Path
from typing import Optional
from uuid import uuid4

import httpx
import yaml
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain.event_profile import EventProfile
from app.domain.fleet_intents import IntentStatus, IntentType
from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.macroagents import consequence_scoper
from app.microagents.slo_forecaster import SLOForecasterAgent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fleet", tags=["fleet-demo"])

EVENT_PROFILES_DIR = Path(__file__).resolve().parents[2] / "config" / "defaults" / "event_profiles"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fleet_url() -> str:
    return os.environ.get("FLEET_URL", "")


def _fleet_token() -> str:
    return os.environ.get("FLEET_TOKEN", "")


def _is_fleet_available() -> bool:
    return bool(_fleet_url()) and bool(_fleet_token())


def _fleet_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    token = _fleet_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fake_hash(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ForecastResponse(BaseModel):
    current_p95_ms: float
    forecast_p95_ms: float
    slo_target_ms: float = 5000.0
    breach_in_minutes: Optional[float] = None
    confidence: float
    status: str  # "safe" | "approaching" | "breach_predicted"


class BlastRadiusResponse(BaseModel):
    affected_models: int
    estimated_users: int
    severity_score: float
    requires_human_gate: bool
    severity: str
    rationale: str


class EmitIntentRequest(BaseModel):
    intent_type: str = Field(description="pre_warm | scale | shed_load | alert")
    model: str = "granite-350m"
    target_replicas: int = 4
    confidence: float = Field(ge=0.0, le=1.0, default=0.85)
    justification: str = "Predictive brain recommendation"


class EmitIntentResponse(BaseModel):
    intent_id: str
    status: str  # "executed" | "refused" | "deferred"
    reason: str
    ledger_entry_id: Optional[str] = None


class ChainEntry(BaseModel):
    type: str
    valid: bool
    entries: int
    latest_hash: str


class VerifyChainResponse(BaseModel):
    chains: list[ChainEntry]


class EventProfileSummary(BaseModel):
    name: str
    expected_users: int
    pre_warm_minutes: int
    models: list[str]


# ---------------------------------------------------------------------------
# 1. GET /health
# ---------------------------------------------------------------------------

@router.get("/health")
async def fleet_health():
    """Check fleet-llm-d health. Proxies /healthz if FLEET_URL is set."""
    if _is_fleet_available():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{_fleet_url()}/healthz",
                    headers=_fleet_headers(),
                )
                data = resp.json() if resp.status_code == 200 else {}
                return {
                    "status": "ok" if resp.status_code == 200 else "degraded",
                    "fleet_url": _fleet_url(),
                    "mode": "live",
                    "clusters": data.get("clusters", []),
                    "models": data.get("models", []),
                }
        except Exception as e:
            logger.warning(f"Fleet health check failed: {e}")
            return {
                "status": "unreachable",
                "fleet_url": _fleet_url(),
                "mode": "live",
                "error": str(e)[:200],
                "clusters": [],
                "models": [],
            }

    # Simulated response
    return {
        "status": "ok",
        "fleet_url": "simulated",
        "mode": "simulated",
        "clusters": [
            {"name": "us-east-1", "status": "ready", "gpu_type": "cpu-only", "nodes": 3},
            {"name": "us-west-2", "status": "ready", "gpu_type": "cpu-only", "nodes": 2},
            {"name": "eu-central-1", "status": "ready", "gpu_type": "cpu-only", "nodes": 2},
        ],
        "models": [
            {"name": "granite-350m", "replicas": 4, "status": "serving"},
            {"name": "granite-2b-int8", "replicas": 2, "status": "serving"},
            {"name": "granite-4.1-3b", "replicas": 2, "status": "serving"},
            {"name": "phi3-mini-cpu", "replicas": 1, "status": "idle"},
            {"name": "qwen25-3b-cpu", "replicas": 1, "status": "idle"},
        ],
    }


# ---------------------------------------------------------------------------
# 2. POST /forecast
# ---------------------------------------------------------------------------

@router.post("/forecast", response_model=ForecastResponse)
async def fleet_forecast():
    """Run SLO forecaster on ramping latency evidence."""
    # Generate 30 data points of ramping latency: 800ms -> 4500ms
    evidence: list[EvidenceArtifact] = []
    for i in range(30):
        # Ramp from ~800 to ~4500 with some noise
        base = 800 + (4500 - 800) * (i / 29)
        noise = random.uniform(-80, 80)
        value = max(100, base + noise)
        ev = EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type="latency_p95",
            features={
                "value": round(value, 1),
                "timestamp_offset_minutes": i,
                "slo_target": 5000,
            },
        )
        evidence.append(ev)

    # Run the SLO forecaster
    forecaster = SLOForecasterAgent(forecast_horizon_minutes=30, default_slo_target=5000.0)
    records = forecaster.classify(evidence)

    if not records:
        return ForecastResponse(
            current_p95_ms=evidence[-1].features["value"],
            forecast_p95_ms=evidence[-1].features["value"],
            slo_target_ms=5000.0,
            confidence=0.0,
            status="safe",
        )

    record = records[0]
    metrics = record.metrics

    # Determine status from class_name
    if record.class_name == "slo_breach_predicted":
        status = "breach_predicted"
    elif record.class_name == "slo_approaching":
        status = "approaching"
    else:
        status = "safe"

    return ForecastResponse(
        current_p95_ms=round(metrics.get("current_value", evidence[-1].features["value"])),
        forecast_p95_ms=round(metrics.get("forecast_value", 0)),
        slo_target_ms=round(metrics.get("slo_target", 5000.0)),
        breach_in_minutes=round(metrics.get("minutes_to_breach") or 0, 1) or None,
        confidence=round(record.confidence, 2),
        status=status,
    )


# ---------------------------------------------------------------------------
# 3. POST /blast-radius
# ---------------------------------------------------------------------------

@router.post("/blast-radius", response_model=BlastRadiusResponse)
async def fleet_blast_radius():
    """Run consequence scoper on fleet evidence representing an SLO breach prediction."""
    # Build evidence representing a fleet under load
    evidence = [
        EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type="latency_p95",
            features={
                "value": 4800,
                "slo_target": 5000,
                "model": "granite-350m",
                "models": ["granite-350m", "granite-2b-int8", "granite-4.1-3b"],
                "expected_users": 200,
                "tenant_id": "summit-connect",
            },
        ),
    ]

    # Build a classification representing the SLO breach prediction
    classification = ClassificationRecord(
        target_type="evidence",
        target_id=evidence[0].evidence_id,
        agent_tier="micro",
        agent_name="slo_forecaster",
        taxonomy="fleet.slo",
        class_name="slo_breach_predicted",
        severity="critical",
        confidence=0.87,
        rationale="P95 forecast to breach 5000ms SLO in 12 minutes",
        evidence_ids=[evidence[0].evidence_id],
        metrics={
            "current_value": 4800,
            "forecast_value": 6200,
            "slo_target": 5000,
            "minutes_to_breach": 12,
        },
    )

    # Run consequence scoper
    results = consequence_scoper.reason(
        evidence=evidence,
        classifications=[classification],
    )

    if not results:
        return BlastRadiusResponse(
            affected_models=3,
            estimated_users=200,
            severity_score=120.0,
            requires_human_gate=True,
            severity="critical",
            rationale="Blast radius assessment unavailable — no critical classifications matched.",
        )

    result = results[0]
    metrics = result.metrics

    return BlastRadiusResponse(
        affected_models=metrics.get("affected_models", 1),
        estimated_users=metrics.get("estimated_users", 10),
        severity_score=metrics.get("severity_score", 0),
        requires_human_gate=metrics.get("requires_human_gate", False),
        severity=result.severity,
        rationale=result.rationale,
    )


# ---------------------------------------------------------------------------
# 4. POST /emit-intent
# ---------------------------------------------------------------------------

@router.post("/emit-intent", response_model=EmitIntentResponse)
async def fleet_emit_intent(req: EmitIntentRequest):
    """Emit an intent to fleet-llm-d or simulate policy evaluation."""
    intent_id = str(uuid4())
    ledger_entry_id = str(uuid4())

    if _is_fleet_available():
        try:
            payload = {
                "type": req.intent_type,
                "model": req.model,
                "target_replicas": req.target_replicas,
                "confidence": req.confidence,
                "justification": req.justification,
                "horizon_seconds": 1800,
            }
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{_fleet_url()}/api/v1/intents",
                    json=payload,
                    headers=_fleet_headers(),
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return EmitIntentResponse(
                        intent_id=data.get("intent_id", intent_id),
                        status=data.get("status", "executed"),
                        reason=data.get("reason", "Accepted by fleet controller"),
                        ledger_entry_id=data.get("ledger_entry_id", ledger_entry_id),
                    )
                else:
                    return EmitIntentResponse(
                        intent_id=intent_id,
                        status="refused",
                        reason=f"Fleet returned HTTP {resp.status_code}: {resp.text[:200]}",
                        ledger_entry_id=None,
                    )
        except Exception as e:
            logger.warning(f"Failed to emit intent to fleet: {e}")
            return EmitIntentResponse(
                intent_id=intent_id,
                status="refused",
                reason=f"Fleet unreachable: {e}",
                ledger_entry_id=None,
            )

    # Simulated policy evaluation
    if req.confidence < 0.5:
        return EmitIntentResponse(
            intent_id=intent_id,
            status="deferred",
            reason=f"Confidence {req.confidence:.2f} below policy threshold (0.50). "
                   f"Queued for human review.",
            ledger_entry_id=ledger_entry_id,
        )

    if req.target_replicas > 8:
        return EmitIntentResponse(
            intent_id=intent_id,
            status="refused",
            reason=f"Requested {req.target_replicas} replicas exceeds policy maximum (8). "
                   f"Submit capacity exception request.",
            ledger_entry_id=ledger_entry_id,
        )

    if req.intent_type in ("shed_load", "alert") and req.confidence >= 0.5:
        # Critical intents with human gate
        return EmitIntentResponse(
            intent_id=intent_id,
            status="deferred",
            reason=f"Intent type '{req.intent_type}' requires human approval per policy. "
                   f"Notification sent to fleet operator.",
            ledger_entry_id=ledger_entry_id,
        )

    return EmitIntentResponse(
        intent_id=intent_id,
        status="executed",
        reason=f"{req.intent_type.replace('_', '-')} intent executed: {req.model} scaled to "
               f"{req.target_replicas} replicas (confidence {req.confidence:.2f}).",
        ledger_entry_id=ledger_entry_id,
    )


# ---------------------------------------------------------------------------
# 5. GET /cost
# ---------------------------------------------------------------------------

@router.get("/cost")
async def fleet_cost():
    """Return GPU vs CPU cost comparison data."""
    gpu_per_hour = 32.00
    cpu_per_hour = 0.60
    hours_per_month = 720  # 30 days
    gpu_monthly = gpu_per_hour * hours_per_month
    cpu_monthly = cpu_per_hour * hours_per_month
    savings_multiplier = round(gpu_per_hour / cpu_per_hour)
    annual_savings = (gpu_monthly - cpu_monthly) * 12

    return {
        "gpu": {
            "type": "H100",
            "per_hour": gpu_per_hour,
            "monthly": gpu_monthly,
        },
        "cpu": {
            "type": "Intel Xeon 6",
            "per_hour": cpu_per_hour,
            "monthly": cpu_monthly,
        },
        "savings_multiplier": savings_multiplier,
        "annual_savings": annual_savings,
    }


# ---------------------------------------------------------------------------
# 6. POST /verify-chain
# ---------------------------------------------------------------------------

@router.post("/verify-chain", response_model=VerifyChainResponse)
async def fleet_verify_chain():
    """Simulate or proxy ledger chain verification."""
    if _is_fleet_available():
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{_fleet_url()}/api/v1/ledger/verify",
                    headers=_fleet_headers(),
                )
                if resp.status_code == 200:
                    return VerifyChainResponse(**resp.json())
        except Exception as e:
            logger.warning(f"Chain verification proxy failed: {e}")

    # Simulated chain verification
    chain_types = ["placement", "scaling", "routing", "lifecycle", "tenant"]
    ts = str(time.time())
    chains = [
        ChainEntry(
            type=ct,
            valid=True,
            entries=random.randint(42, 380),
            latest_hash=_fake_hash(f"{ct}-{ts}"),
        )
        for ct in chain_types
    ]

    return VerifyChainResponse(chains=chains)


# ---------------------------------------------------------------------------
# 7. GET /event-profiles
# ---------------------------------------------------------------------------

@router.get("/event-profiles")
async def fleet_event_profiles():
    """List available event profiles from YAML config or inline defaults."""
    profiles: list[dict] = []

    # Try to read from config directory
    if EVENT_PROFILES_DIR.exists():
        for yaml_file in sorted(EVENT_PROFILES_DIR.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                if data:
                    profile = EventProfile(**data)
                    profiles.append({
                        "name": profile.name,
                        "description": profile.description,
                        "expected_users": profile.load_profile.concurrent_users,
                        "pre_warm_minutes": profile.schedule.pre_warm_minutes,
                        "models": profile.load_profile.models,
                        "session_duration_minutes": profile.schedule.session_duration_minutes,
                        "slo_p95_ms": profile.slo_targets.p95_latency_ms,
                        "pre_warm_replicas": profile.pre_warm_action.replicas,
                    })
            except Exception as e:
                logger.warning(f"Failed to load event profile {yaml_file}: {e}")

    # Fallback: inline Summit Connect profile if no files found
    if not profiles:
        profiles.append({
            "name": "summit-connect",
            "description": "Red Hat Summit Connect lab session with CPU inference",
            "expected_users": 50,
            "pre_warm_minutes": 30,
            "models": [
                "granite-350m",
                "granite-2b-int8",
                "granite-4.1-3b",
                "phi3-mini-cpu",
                "qwen25-3b-cpu",
            ],
            "session_duration_minutes": 90,
            "slo_p95_ms": 5000,
            "pre_warm_replicas": 4,
        })

    return {"profiles": profiles}
