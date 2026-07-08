"""Tests for intent persistence and A/B run tracking."""

import pytest
from datetime import datetime
from uuid import uuid4

from app.domain.fleet_intents import PreWarmIntent, IntentResponse, IntentStatus


class TestIntentPersistence:
    def test_save_intent(self):
        from app.intents.persistence import save_intent
        intent = PreWarmIntent(
            confidence=0.85,
            horizon_seconds=1800,
            justification="Event pre-warming",
            model="granite-2b",
            target_replicas=4,
        )
        # Should not raise (graceful degradation when no DB)
        save_intent(intent, predictor_mode="predictive")

    def test_save_intent_with_ab_run(self):
        from app.intents.persistence import save_intent
        run_id = uuid4()
        intent = PreWarmIntent(
            confidence=0.9,
            horizon_seconds=600,
            justification="Test",
            model="test",
            target_replicas=2,
        )
        save_intent(intent, predictor_mode="predictive", ab_run_id=run_id)

    def test_start_ab_run(self):
        from app.intents.persistence import start_ab_run
        run_id = start_ab_run(
            name="test-run",
            predictor_mode="predictive",
            event_profile="summit-connect",
        )
        assert run_id is not None

    def test_end_ab_run(self):
        from app.intents.persistence import start_ab_run, end_ab_run
        run_id = start_ab_run("end-test", "reactive")
        end_ab_run(
            run_id,
            stats={"total_intents": 5, "intents_by_type": {"pre_warm": 3, "scale": 2}},
            slo_metrics={"p95_latency_ms": 2300, "error_rate": 0.0},
        )

    def test_save_prediction_outcome(self):
        from app.intents.persistence import save_prediction_outcome
        save_prediction_outcome(
            intent_id=uuid4(),
            predicted_metric="p95_latency_ms",
            predicted_value=6000.0,
            predicted_at=datetime.utcnow(),
            horizon_seconds=1800,
            actual_value=5500.0,
        )

    def test_prediction_accuracy_calc(self):
        from app.intents.persistence import save_prediction_outcome
        # Should compute error metrics without raising
        save_prediction_outcome(
            intent_id=uuid4(),
            predicted_metric="p95_latency_ms",
            predicted_value=7000.0,
            predicted_at=datetime.utcnow(),
            horizon_seconds=600,
            actual_value=6500.0,
            ab_run_id=uuid4(),
        )


class TestFleetPredictorABIntegration:
    @pytest.mark.asyncio
    async def test_predictor_ab_run_lifecycle(self):
        from app.intents.predictor import FleetPredictor

        p = FleetPredictor(enabled=True)

        # Start A/B run
        run_id = p.start_ab_run("integration-test", event_profile="summit-connect")
        assert run_id is not None
        assert p.mode == "predictive"

        # End A/B run
        p.end_ab_run(slo_metrics={"p95_latency_ms": 1500, "error_rate": 0.0})
