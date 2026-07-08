"""Tests for fleet-specific nanoagents."""

import pytest
from uuid import uuid4
from app.domain.models import EvidenceArtifact, BaselineProfile
from app.nanoagents import slo_drift, capacity_pressure, queue_depth, event_calendar


class TestSLODrift:
    def _make_evidence(self, value, slo_target, artifact_type="latency_p95"):
        return [EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type=artifact_type,
            features={"value": value, "slo_target": slo_target, "sample_count": 100},
        )]

    def test_healthy(self):
        records = slo_drift.classify(self._make_evidence(1000, 5000), None)
        assert len(records) >= 1
        assert records[0].class_name == "slo_healthy"
        assert records[0].severity == "info"

    def test_warning(self):
        records = slo_drift.classify(self._make_evidence(3500, 5000), None)
        assert records[0].class_name == "slo_warning"
        assert records[0].severity == "medium"

    def test_degraded(self):
        records = slo_drift.classify(self._make_evidence(4200, 5000), None)
        assert records[0].class_name == "slo_degraded"
        assert records[0].severity == "high"

    def test_breach_imminent(self):
        records = slo_drift.classify(self._make_evidence(4800, 5000), None)
        assert records[0].class_name == "slo_breach_imminent"
        assert records[0].severity == "critical"

    def test_ignores_non_metric(self):
        ev = [EvidenceArtifact(source="test", modality="log", artifact_type="app_log")]
        records = slo_drift.classify(ev, None)
        assert len(records) == 0


class TestCapacityPressure:
    def _make_evidence(self, utilization):
        return [EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type="cpu_utilization",
            features={"utilization": utilization},
        )]

    def test_normal(self):
        records = capacity_pressure.classify(self._make_evidence(0.3), None)
        assert records[0].class_name == "capacity_normal"

    def test_pressure(self):
        records = capacity_pressure.classify(self._make_evidence(0.8), None)
        assert records[0].class_name == "capacity_pressure"
        assert records[0].severity == "high"

    def test_saturated(self):
        records = capacity_pressure.classify(self._make_evidence(0.95), None)
        assert records[0].class_name == "capacity_saturated"
        assert records[0].severity == "critical"


class TestQueueDepth:
    def _make_evidence(self, depth, capacity=20):
        return [EvidenceArtifact(
            source="fleet-metrics",
            modality="metric",
            artifact_type="queue_depth",
            features={"depth": depth, "capacity": capacity},
        )]

    def test_normal(self):
        records = queue_depth.classify(self._make_evidence(3, 20), None)
        assert records[0].class_name == "queue_normal"

    def test_overflow(self):
        records = queue_depth.classify(self._make_evidence(19, 20), None)
        assert records[0].class_name == "queue_overflow"
        assert records[0].severity == "critical"


class TestEventCalendar:
    def _make_evidence(self, minutes_until):
        return [EvidenceArtifact(
            source="event-calendar",
            modality="event",
            artifact_type="calendar_event",
            features={"event_start_minutes": minutes_until, "expected_users": 50, "models": ["granite-2b"]},
        )]

    def test_scheduled_far(self):
        records = event_calendar.classify(self._make_evidence(120), None)
        assert records[0].class_name == "event_scheduled"
        assert records[0].severity == "info"

    def test_pre_warm_needed(self):
        records = event_calendar.classify(self._make_evidence(25), None)
        assert records[0].class_name == "pre_warm_needed"
        assert records[0].severity == "high"

    def test_event_starting(self):
        records = event_calendar.classify(self._make_evidence(3), None)
        assert records[0].class_name == "event_starting"
        assert records[0].severity == "critical"


class TestPipelineIntegration:
    def test_fleet_agents_in_pipeline(self):
        from app.nanoagents.pipeline import _DEFAULT_MODULES
        fleet_agents = [
            "app.nanoagents.slo_drift",
            "app.nanoagents.capacity_pressure",
            "app.nanoagents.queue_depth",
            "app.nanoagents.event_calendar",
        ]
        for agent in fleet_agents:
            assert agent in _DEFAULT_MODULES, f"{agent} not in pipeline"
