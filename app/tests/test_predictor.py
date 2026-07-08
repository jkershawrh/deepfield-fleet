"""Tests for FleetPredictor A/B toggle and event-driven intents."""

import pytest
from datetime import datetime, timedelta

from app.domain.event_profile import EventProfile, LoadProfile, EventSchedule, PreWarmAction
from app.domain.fleet_intents import PreWarmIntent, ScaleIntent, IntentType
from app.domain.models import EvidenceArtifact
from app.intents.predictor import FleetPredictor


class TestFleetPredictor:
    def _make_predictor(self, enabled=True):
        profile = EventProfile(
            name="test-event",
            schedule=EventSchedule(pre_warm_minutes=30),
            load_profile=LoadProfile(models=["model-a"]),
            pre_warm_action=PreWarmAction(replicas=4, models=["model-a"]),
        )
        return FleetPredictor(enabled=enabled, event_profiles=[profile])

    def test_mode_toggle(self):
        p = self._make_predictor(enabled=True)
        assert p.mode == "predictive"
        p.toggle(False)
        assert p.mode == "reactive"
        p.toggle(True)
        assert p.mode == "predictive"

    @pytest.mark.asyncio
    async def test_emits_pre_warm_when_enabled(self):
        p = self._make_predictor(enabled=True)

        event_start = datetime(2026, 7, 10, 10, 0)
        now = datetime(2026, 7, 10, 9, 40)  # 20 min before

        evidence = [EvidenceArtifact(
            source="calendar",
            modality="event",
            artifact_type="calendar_event",
            features={"event_start": event_start.isoformat(), "event_start_minutes": 20},
        )]

        intents = await p.process_signals(evidence, now=now)
        pre_warms = [i for i in intents if isinstance(i, PreWarmIntent)]
        assert len(pre_warms) >= 1
        assert pre_warms[0].target_replicas == 4

    @pytest.mark.asyncio
    async def test_computes_but_does_not_emit_when_disabled(self):
        p = self._make_predictor(enabled=False)

        event_start = datetime(2026, 7, 10, 10, 0)
        now = datetime(2026, 7, 10, 9, 40)

        evidence = [EvidenceArtifact(
            source="calendar",
            modality="event",
            artifact_type="calendar_event",
            features={"event_start": event_start.isoformat(), "event_start_minutes": 20},
        )]

        intents = await p.process_signals(evidence, now=now)
        # Intents are computed (returned) but not emitted (no emitter configured)
        assert len(intents) >= 1
        # Stats still track them
        stats = p.get_stats()
        assert stats["mode"] == "reactive"
        assert stats["total_intents"] >= 1

    @pytest.mark.asyncio
    async def test_slo_forecast_triggers_scale(self):
        p = FleetPredictor(enabled=True)

        # Create ramping latency evidence
        evidence = []
        for i in range(30):
            evidence.append(EvidenceArtifact(
                source="fleet-metrics",
                modality="metric",
                artifact_type="latency_p95",
                features={"value": 3000 + 50 * i, "timestamp_offset_minutes": i, "slo_target": 5000},
            ))

        intents = await p.process_signals(evidence)
        scale_intents = [i for i in intents if isinstance(i, ScaleIntent)]
        assert len(scale_intents) >= 1
        assert scale_intents[0].metric == "slo_forecast"

    @pytest.mark.asyncio
    async def test_no_intents_on_healthy_signals(self):
        p = FleetPredictor(enabled=True)

        evidence = [EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type="cpu_utilization",
            features={"utilization": 0.3},
        )]

        intents = await p.process_signals(evidence)
        # Healthy signals should not produce scale/pre-warm intents
        scale_or_warm = [i for i in intents if isinstance(i, (ScaleIntent, PreWarmIntent))]
        assert len(scale_or_warm) == 0

    def test_stats_tracking(self):
        p = self._make_predictor()
        stats = p.get_stats()
        assert stats["mode"] == "predictive"
        assert stats["total_intents"] == 0

        p.reset_stats()
        assert p.get_stats()["total_intents"] == 0


class TestLedgerChainVerifier:
    def test_verifier_creation(self):
        from app.intents.ledger_verifier import LedgerChainVerifier
        v = LedgerChainVerifier(ledger_url="http://localhost:28099")
        assert v.ledger_url == "http://localhost:28099"
