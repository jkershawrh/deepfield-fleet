"""Tests for SLO forecaster microagent."""

import pytest
from uuid import uuid4
from app.domain.models import EvidenceArtifact
from app.microagents.slo_forecaster import SLOForecasterAgent


class TestSLOForecaster:
    def _make_ramp_evidence(self, start_value, slope_per_minute, count, slo_target=5000):
        """Create a series of evidence artifacts simulating a latency ramp."""
        evidence = []
        for i in range(count):
            evidence.append(EvidenceArtifact(
                source="fleet-metrics",
                modality="metric",
                artifact_type="latency_p95",
                features={
                    "value": start_value + slope_per_minute * i,
                    "timestamp_offset_minutes": i,
                    "slo_target": slo_target,
                    "sample_count": 100,
                },
            ))
        return evidence

    def test_predicts_breach(self):
        # Ramp from 3000 to 4500 over 30 min at 50ms/min
        # At T+30 forecast = 4500 + 50*30 = 6000 > 5000 SLO
        evidence = self._make_ramp_evidence(3000, 50, 30, slo_target=5000)
        forecaster = SLOForecasterAgent(forecast_horizon_minutes=30)
        records = forecaster.classify(evidence)

        assert len(records) == 1
        assert records[0].class_name == "slo_breach_predicted"
        assert records[0].severity in ("high", "critical")
        assert records[0].metrics["forecast_value"] > 5000

    def test_predicts_safe(self):
        # Flat at 1000, SLO is 5000: safe
        evidence = self._make_ramp_evidence(1000, 0, 30, slo_target=5000)
        forecaster = SLOForecasterAgent(forecast_horizon_minutes=30)
        records = forecaster.classify(evidence)

        assert len(records) == 1
        assert records[0].class_name == "slo_forecast_safe"
        assert records[0].severity == "info"

    def test_predicts_approaching(self):
        # Ramp from 2000 at 35ms/min over 30 samples, forecast ~4065 (81% of 5000)
        evidence = self._make_ramp_evidence(2000, 35, 30, slo_target=5000)
        forecaster = SLOForecasterAgent(forecast_horizon_minutes=30)
        records = forecaster.classify(evidence)

        assert len(records) == 1
        assert records[0].class_name == "slo_approaching"
        assert records[0].severity == "medium"

    def test_not_enough_data(self):
        # Only 2 data points: not enough to forecast
        evidence = self._make_ramp_evidence(1000, 10, 2, slo_target=5000)
        forecaster = SLOForecasterAgent(forecast_horizon_minutes=30)
        records = forecaster.classify(evidence)
        assert len(records) == 0

    def test_minutes_to_breach(self):
        # Steep ramp: breach should be soon
        evidence = self._make_ramp_evidence(4000, 100, 10, slo_target=5000)
        forecaster = SLOForecasterAgent(forecast_horizon_minutes=30)
        records = forecaster.classify(evidence)

        assert records[0].class_name == "slo_breach_predicted"
        assert records[0].metrics["minutes_to_breach"] < 15
        assert records[0].severity == "critical"  # breach in <10 min

    def test_declining_trend_safe(self):
        # Declining from 4000 to 3000, getting better, not worse
        evidence = self._make_ramp_evidence(4000, -33, 30, slo_target=5000)
        forecaster = SLOForecasterAgent(forecast_horizon_minutes=30)
        records = forecaster.classify(evidence)

        assert records[0].class_name == "slo_forecast_safe"

    def test_linear_regression_accuracy(self):
        # Perfect linear data: R² should be ~1.0
        evidence = self._make_ramp_evidence(1000, 10, 20, slo_target=5000)
        forecaster = SLOForecasterAgent()
        records = forecaster.classify(evidence)

        assert records[0].metrics.get("r_squared", 0) > 0.95

    def test_ignores_non_latency_metrics(self):
        evidence = [EvidenceArtifact(
            source="test", modality="metric", artifact_type="cpu_utilization",
            features={"value": 85},
        )]
        forecaster = SLOForecasterAgent()
        records = forecaster.classify(evidence)
        assert len(records) == 0

    def test_custom_horizon(self):
        evidence = self._make_ramp_evidence(3000, 50, 30, slo_target=5000)
        # 10-min horizon: 4500 + 50*10 = 5000, right at threshold
        forecaster = SLOForecasterAgent(forecast_horizon_minutes=10)
        records = forecaster.classify(evidence)
        assert len(records) == 1
