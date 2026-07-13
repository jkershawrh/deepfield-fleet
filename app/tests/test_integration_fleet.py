"""Optional live integration tests for deepfield-fleet -> GCL delivery.

Set GCL_EVENT_SINK_URL and the explicit DeepField scope variables to exercise
the producer boundary. These tests verify event delivery only; they do not
claim a DecisionPackage, execution authorization, fleet execution, or an
immutable-ledger receipt.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

from app.domain.event_profile import (
    EventProfile,
    EventSchedule,
    LoadProfile,
    PreWarmAction,
)
from app.domain.fleet_intents import PreWarmIntent, ScaleIntent
from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.intents.ecosystem_emitter import ProducerContext
from app.intents.emitter import IntentEmitter
from app.intents.predictor import FleetPredictor
from app.macroagents import consequence_scoper

GCL_EVENT_SINK_URL = os.environ.get("GCL_EVENT_SINK_URL", "")
GCL_EVENT_SINK_TOKEN = os.environ.get("GCL_EVENT_SINK_TOKEN", "")


def _context() -> ProducerContext | None:
    return ProducerContext.from_environment()


skip_no_gcl = pytest.mark.skipif(
    not GCL_EVENT_SINK_URL or _context() is None,
    reason="GCL sink or required DeepField producer scope is not configured",
)


@skip_no_gcl
class TestGovernedProducerDelivery:
    @pytest.mark.asyncio
    async def test_scale_recommendation_delivers_owned_events(self):
        emitter = IntentEmitter(
            gcl_sink_url=GCL_EVENT_SINK_URL,
            token=GCL_EVENT_SINK_TOKEN,
            context=_context(),
        )
        try:
            result = await emitter.emit(
                ScaleIntent(
                    confidence=0.82,
                    horizon_seconds=600,
                    justification="SLO forecast exceeds the safe capacity window.",
                    pool="cpu-inference",
                    current_replicas=1,
                    desired_replicas=4,
                    metric="slo_forecast",
                ),
                evidence=[
                    EvidenceArtifact(
                        source="prometheus",
                        source_uri="urn:srex:evidence:live-prometheus-window",
                        modality="metric",
                        artifact_type="latency_p95",
                        features={"value": 5400, "slo_target": 5000},
                    )
                ],
            )
        finally:
            await emitter.close()

        assert result.status == "accepted"
        assert len(result.event_ids) == 2
        assert result.execution_verified is False
        assert result.ledger_receipt_id is None

    @pytest.mark.asyncio
    async def test_slo_forecast_pipeline_publishes_without_direct_actuation(self):
        emitter = IntentEmitter(
            gcl_sink_url=GCL_EVENT_SINK_URL,
            token=GCL_EVENT_SINK_TOKEN,
            context=_context(),
        )
        predictor = FleetPredictor(emitter=emitter, enabled=True)
        evidence = [
            EvidenceArtifact(
                source="fleet-metrics",
                source_uri=f"urn:srex:evidence:latency-{index}",
                modality="metric",
                artifact_type="latency_p95",
                features={
                    "value": 3000 + 50 * index,
                    "timestamp_offset_minutes": index,
                    "slo_target": 5000,
                },
            )
            for index in range(30)
        ]
        try:
            recommendations = await predictor.process_signals(evidence)
        finally:
            await emitter.close()

        assert any(isinstance(item, ScaleIntent) for item in recommendations)

    @pytest.mark.asyncio
    async def test_event_profile_publishes_prewarm_recommendations(self):
        profile = EventProfile(
            name="integration-test-event",
            schedule=EventSchedule(pre_warm_minutes=30),
            load_profile=LoadProfile(models=["model-a", "model-b"]),
            pre_warm_action=PreWarmAction(
                replicas=4,
                models=["model-a", "model-b"],
            ),
        )
        emitter = IntentEmitter(
            gcl_sink_url=GCL_EVENT_SINK_URL,
            token=GCL_EVENT_SINK_TOKEN,
            context=_context(),
        )
        predictor = FleetPredictor(
            emitter=emitter,
            enabled=True,
            event_profiles=[profile],
        )
        event_start = datetime.now(timezone.utc) + timedelta(minutes=20)
        evidence = [
            EvidenceArtifact(
                source="calendar",
                source_uri="urn:srex:evidence:event-calendar",
                modality="event",
                artifact_type="calendar_event",
                features={"event_start": event_start.isoformat()},
            )
        ]
        try:
            recommendations = await predictor.process_signals(
                evidence,
                now=datetime.now(timezone.utc),
            )
        finally:
            await emitter.close()

        prewarms = [item for item in recommendations if isinstance(item, PreWarmIntent)]
        assert len(prewarms) >= 2


def test_consequence_scoper_remains_advisory():
    evidence = [
        EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type="latency_p95",
            features={"models": ["model-a", "model-b"], "active_users": 50},
        )
    ]
    classification = ClassificationRecord(
        target_type="evidence",
        target_id=evidence[0].evidence_id,
        agent_tier="micro",
        agent_name="slo_forecaster",
        taxonomy="fleet.slo",
        class_name="slo_breach_predicted",
        severity="critical",
        confidence=0.85,
        rationale="P95 forecast exceeds SLO",
        metrics={"forecast_value": 7000, "slo_target": 5000},
    )

    scoped = consequence_scoper.reason(evidence, [classification])

    assert scoped
    assert scoped[0].metrics["affected_models"] >= 2
    assert scoped[0].metrics["estimated_users"] == 50
