"""Tests for FleetIntent models and IntentEmitter."""

import pytest
from uuid import UUID
from datetime import datetime

from app.domain.fleet_intents import (
    FleetIntent, PreWarmIntent, ScaleIntent, ShedLoadIntent, AlertIntent,
    IntentType, IntentStatus, IntentResponse,
)


class TestFleetIntentModels:
    def test_pre_warm_intent(self):
        intent = PreWarmIntent(
            confidence=0.85,
            horizon_seconds=1800,
            justification="Summit Connect session starts in 30 min",
            model="granite-2b-int8",
            target_replicas=4,
            target_clusters=["cluster-a"],
            reason="Event pre-warming",
        )
        assert intent.type == IntentType.PRE_WARM
        assert isinstance(intent.id, UUID)
        assert intent.confidence == 0.85
        assert intent.model == "granite-2b-int8"
        assert intent.target_replicas == 4

    def test_scale_intent(self):
        intent = ScaleIntent(
            confidence=0.72,
            horizon_seconds=300,
            justification="CPU utilization trending toward saturation",
            pool="cpu-inference",
            current_replicas=1,
            desired_replicas=4,
            metric="cpu_utilization_p95",
        )
        assert intent.type == IntentType.SCALE
        assert intent.desired_replicas == 4

    def test_shed_load_intent(self):
        intent = ShedLoadIntent(
            confidence=0.95,
            horizon_seconds=60,
            justification="Queue depth exceeds capacity",
            model="granite-4.1-3b",
            max_inflight=10,
            duration_seconds=300,
            reason="Protect SLO during peak",
        )
        assert intent.type == IntentType.SHED_LOAD
        assert intent.max_inflight == 10

    def test_alert_intent(self):
        intent = AlertIntent(
            confidence=0.88,
            horizon_seconds=900,
            justification="SLO breach predicted in 15 minutes",
            severity="warning",
            message="P95 latency forecast to exceed 5s SLO",
            recommended_action="Scale granite-2b-int8 to 4 replicas",
        )
        assert intent.type == IntentType.ALERT
        assert intent.severity == "warning"

    def test_intent_serialization(self):
        intent = PreWarmIntent(
            confidence=0.9,
            horizon_seconds=600,
            justification="test",
            model="test-model",
            target_replicas=2,
        )
        json_str = intent.model_dump_json()
        assert "pre_warm" in json_str
        assert "test-model" in json_str

        # Deserialize
        loaded = PreWarmIntent.model_validate_json(json_str)
        assert loaded.id == intent.id
        assert loaded.model == "test-model"

    def test_intent_response(self):
        resp = IntentResponse(
            intent_id=UUID("12345678-1234-1234-1234-123456789012"),
            status=IntentStatus.EXECUTED,
            reason="Policy checks passed",
            ledger_entry_id="entry-42",
        )
        assert resp.status == IntentStatus.EXECUTED

    def test_confidence_validation(self):
        with pytest.raises(Exception):
            FleetIntent(
                type=IntentType.NO_ACTION,
                confidence=1.5,  # invalid
                horizon_seconds=0,
                justification="test",
            )


class TestIntentEmitter:
    @pytest.mark.asyncio
    async def test_emitter_creation(self):
        from app.intents.emitter import IntentEmitter
        emitter = IntentEmitter(
            fleet_url="http://localhost:8080",
            token="test-token",
        )
        assert emitter.fleet_url == "http://localhost:8080"
        await emitter.close()
