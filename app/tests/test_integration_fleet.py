"""Integration tests: deepfield-fleet → fleet-llm-d intent round-trip.

Requires a live fleet-llm-d instance. Set FLEET_URL and FLEET_TOKEN env vars,
or tests will be skipped.

Run: FLEET_URL=http://localhost:18080 FLEET_TOKEN=<token> python3 -m pytest app/tests/test_integration_fleet.py -v
"""

import os
import pytest
import httpx
from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.fleet_intents import (
    PreWarmIntent, ScaleIntent, ShedLoadIntent, AlertIntent,
    IntentStatus,
)
from app.domain.event_profile import EventProfile, LoadProfile, EventSchedule, PreWarmAction
from app.domain.models import EvidenceArtifact, ClassificationRecord
from app.intents.emitter import IntentEmitter
from app.intents.predictor import FleetPredictor
from app.intents.event_scheduler import evaluate_event
from app.macroagents import consequence_scoper

FLEET_URL = os.environ.get("FLEET_URL", "")
FLEET_TOKEN = os.environ.get("FLEET_TOKEN", "")

skip_no_fleet = pytest.mark.skipif(
    not FLEET_URL, reason="FLEET_URL not set — skipping integration tests"
)


def _check_fleet_reachable():
    """Verify fleet-llm-d is reachable before running tests."""
    if not FLEET_URL:
        return False
    try:
        resp = httpx.get(f"{FLEET_URL}/healthz", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


@skip_no_fleet
class TestIntentRoundTrip:
    """Test intent emission to live fleet-llm-d."""

    def _post_intent(self, intent_data: dict) -> dict:
        # Go expects RFC3339 timestamps with timezone suffix
        if "created_at" in intent_data and not str(intent_data["created_at"]).endswith("Z"):
            intent_data["created_at"] = str(intent_data["created_at"]) + "Z"

        headers = {"Content-Type": "application/json"}
        if FLEET_TOKEN:
            headers["Authorization"] = f"Bearer {FLEET_TOKEN}"
        resp = httpx.post(
            f"{FLEET_URL}/api/v1/intents",
            json=intent_data,
            headers=headers,
            timeout=10,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        return resp.json()

    def test_pre_warm_accepted(self):
        """CDD: Valid PreWarm intent is accepted by fleet-llm-d."""
        intent = PreWarmIntent(
            confidence=0.85,
            horizon_seconds=1800,
            justification="Integration test: event pre-warming",
            model="granite-2b-int8",
            target_replicas=4,
            reason="Integration test",
        )
        result = self._post_intent(intent.model_dump(mode="json"))
        assert result["status"] == "executed"
        assert result["intent_id"] == str(intent.id)

    def test_low_confidence_deferred(self):
        """TDD: Low confidence intent is deferred."""
        intent = PreWarmIntent(
            confidence=0.3,
            horizon_seconds=600,
            justification="Weak signal — should be deferred",
            model="test-model",
            target_replicas=2,
        )
        result = self._post_intent(intent.model_dump(mode="json"))
        assert result["status"] == "deferred"
        assert "confidence" in result["reason"].lower() or "threshold" in result["reason"].lower()

    def test_excessive_replicas_refused(self):
        """TDD: Requesting too many replicas is refused."""
        intent = PreWarmIntent(
            confidence=0.9,
            horizon_seconds=1800,
            justification="Aggressive scale — should be refused",
            model="test-model",
            target_replicas=20,
        )
        result = self._post_intent(intent.model_dump(mode="json"))
        assert result["status"] == "refused"
        assert "replica" in result["reason"].lower() or "max" in result["reason"].lower()

    def test_critical_alert_human_gate(self):
        """BDD: Critical alert with human gate is deferred."""
        intent = AlertIntent(
            confidence=0.95,
            horizon_seconds=300,
            justification="SLO breach imminent — requires human approval",
            severity="critical",
            message="P95 latency forecast to exceed 5s SLO in 5 minutes",
            recommended_action="Scale granite-2b-int8 to 4 replicas",
        )
        result = self._post_intent(intent.model_dump(mode="json"))
        assert result["status"] == "deferred"
        assert "human" in result["reason"].lower() or "critical" in result["reason"].lower()

    def test_scale_intent_accepted(self):
        """CDD: Valid ScaleIntent is accepted."""
        intent = ScaleIntent(
            confidence=0.78,
            horizon_seconds=600,
            justification="CPU utilization trending toward saturation",
            pool="cpu-inference",
            current_replicas=1,
            desired_replicas=4,
            metric="cpu_utilization_p95",
        )
        result = self._post_intent(intent.model_dump(mode="json"))
        assert result["status"] == "executed"

    def test_shed_load_accepted(self):
        """CDD: Valid ShedLoadIntent is accepted."""
        intent = ShedLoadIntent(
            confidence=0.92,
            horizon_seconds=60,
            justification="Queue depth exceeds capacity",
            model="granite-4.1-3b",
            max_inflight=10,
            duration_seconds=300,
            reason="Protect SLO during peak",
        )
        result = self._post_intent(intent.model_dump(mode="json"))
        assert result["status"] == "executed"

    def test_ledger_entry_returned(self):
        """CDD: Executed intent returns a ledger entry ID."""
        intent = PreWarmIntent(
            confidence=0.88,
            horizon_seconds=900,
            justification="Ledger chain test",
            model="test-model",
            target_replicas=2,
        )
        result = self._post_intent(intent.model_dump(mode="json"))
        assert result["status"] == "executed"
        assert result.get("ledger_entry_id"), "Expected ledger_entry_id in response"


@skip_no_fleet
class TestFullPipeline:
    """Test the complete predictive brain pipeline against live fleet-llm-d."""

    @pytest.mark.asyncio
    async def test_slo_forecast_to_scale_intent(self):
        """CDD: Latency ramp → SLO forecast → ScaleIntent emitted to fleet-llm-d."""
        emitter = IntentEmitter(fleet_url=FLEET_URL, token=FLEET_TOKEN)
        predictor = FleetPredictor(emitter=emitter, enabled=True)

        # Create ramping latency evidence that will trigger SLO breach prediction
        evidence = []
        for i in range(30):
            evidence.append(EvidenceArtifact(
                source="fleet-metrics",
                modality="metric",
                artifact_type="latency_p95",
                features={"value": 3000 + 50 * i, "timestamp_offset_minutes": i, "slo_target": 5000},
            ))

        intents = await predictor.process_signals(evidence)
        await emitter.close()

        scale_intents = [i for i in intents if isinstance(i, ScaleIntent)]
        assert len(scale_intents) >= 1, "Expected at least one ScaleIntent from SLO forecast"
        assert scale_intents[0].metric == "slo_forecast"

    @pytest.mark.asyncio
    async def test_event_profile_pre_warm(self):
        """CDD: Event profile triggers PreWarmIntent for each model."""
        profile = EventProfile(
            name="integration-test-event",
            schedule=EventSchedule(pre_warm_minutes=30),
            load_profile=LoadProfile(models=["model-a", "model-b"]),
            pre_warm_action=PreWarmAction(replicas=4, models=["model-a", "model-b"]),
        )

        emitter = IntentEmitter(fleet_url=FLEET_URL, token=FLEET_TOKEN)
        predictor = FleetPredictor(emitter=emitter, enabled=True, event_profiles=[profile])

        event_start = datetime.utcnow() + timedelta(minutes=20)
        evidence = [EvidenceArtifact(
            source="calendar",
            modality="event",
            artifact_type="calendar_event",
            features={"event_start": event_start.isoformat(), "event_start_minutes": 20},
        )]

        intents = await predictor.process_signals(evidence, now=datetime.utcnow())
        await emitter.close()

        pre_warms = [i for i in intents if isinstance(i, PreWarmIntent)]
        assert len(pre_warms) >= 2, f"Expected PreWarmIntent per model, got {len(pre_warms)}"

    @pytest.mark.asyncio
    async def test_consequence_scoper_blast_radius(self):
        """CDD: Consequence scoper adds blast radius data."""
        evidence = [EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type="latency_p95",
            features={"models": ["granite-2b", "granite-4.1-3b"], "active_users": 50},
        )]

        # Create a critical classification as if from the SLO forecaster
        classification = ClassificationRecord(
            target_type="evidence",
            target_id=uuid4(),
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
        assert len(scoped) >= 1
        assert scoped[0].metrics["affected_models"] >= 2
        assert scoped[0].metrics["estimated_users"] == 50
        assert scoped[0].metrics["requires_human_gate"] in (True, False)
