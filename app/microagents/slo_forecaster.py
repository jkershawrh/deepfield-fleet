"""Microagent: SLO forecaster — predicts SLO breach using linear regression on latency metrics."""

import math
from typing import Optional

from app.domain.models import ClassificationRecord, EvidenceArtifact
from app.microagents.base import BaseMicroagent


class SLOForecasterAgent(BaseMicroagent):
    name = "slo_forecaster"
    modalities = {"metric"}

    def __init__(self, forecast_horizon_minutes: int = 30, default_slo_target: float = 5000.0):
        self.forecast_horizon = forecast_horizon_minutes
        self.default_slo_target = default_slo_target

    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        records = []
        # Collect latency time series from evidence
        latency_series = []
        slo_target = self.default_slo_target

        for ev in evidence:
            if ev.modality != "metric":
                continue
            atype = ev.artifact_type.lower()
            if not any(k in atype for k in ("latency", "ttft", "p95", "p99")):
                continue

            value = ev.features.get("value")
            timestamp_offset = ev.features.get("timestamp_offset_minutes", len(latency_series))
            if ev.features.get("slo_target"):
                slo_target = float(ev.features["slo_target"])

            if value is not None and isinstance(value, (int, float)):
                latency_series.append((float(timestamp_offset), float(value)))

        if len(latency_series) < 3:
            return records  # Not enough data to forecast

        # Linear regression: y = slope * x + intercept
        slope, intercept, r_squared = self._linear_regression(latency_series)

        # Forecast at T + horizon
        last_x = latency_series[-1][0]
        forecast_x = last_x + self.forecast_horizon
        forecast_value = slope * forecast_x + intercept

        # Confidence based on R² and sample count
        n = len(latency_series)
        confidence = min(0.95, r_squared * min(1.0, n / 10.0))
        confidence = max(0.1, confidence)

        # Current value
        current_value = latency_series[-1][1]

        # Classify based on forecast
        if forecast_value >= slo_target:
            # SLO breach predicted
            minutes_to_breach = self._estimate_breach_time(slope, intercept, slo_target, last_x)
            records.append(self._make_record(
                evidence[0],
                class_name="slo_breach_predicted",
                severity="critical" if minutes_to_breach <= 10 else "high",
                confidence=confidence,
                rationale=f"P95 forecast to reach {forecast_value:.0f}ms in {self.forecast_horizon}min "
                          f"(SLO target: {slo_target:.0f}ms). Breach in ~{minutes_to_breach:.0f}min. "
                          f"Trend: +{slope:.1f}ms/min over {n} samples (R²={r_squared:.2f}).",
                metrics={
                    "current_value": current_value,
                    "forecast_value": forecast_value,
                    "slo_target": slo_target,
                    "slope_per_minute": slope,
                    "r_squared": r_squared,
                    "minutes_to_breach": minutes_to_breach,
                    "sample_count": n,
                    "forecast_horizon_minutes": self.forecast_horizon,
                },
            ))
        elif forecast_value >= slo_target * 0.8:
            # Approaching SLO
            records.append(self._make_record(
                evidence[0],
                class_name="slo_approaching",
                severity="medium",
                confidence=confidence,
                rationale=f"P95 forecast to reach {forecast_value:.0f}ms in {self.forecast_horizon}min "
                          f"({forecast_value/slo_target*100:.0f}% of SLO target {slo_target:.0f}ms). "
                          f"Trend: +{slope:.1f}ms/min.",
                metrics={
                    "current_value": current_value,
                    "forecast_value": forecast_value,
                    "slo_target": slo_target,
                    "slope_per_minute": slope,
                    "r_squared": r_squared,
                },
            ))
        else:
            # SLO safe
            records.append(self._make_record(
                evidence[0],
                class_name="slo_forecast_safe",
                severity="info",
                confidence=confidence,
                rationale=f"P95 forecast {forecast_value:.0f}ms in {self.forecast_horizon}min "
                          f"(SLO target: {slo_target:.0f}ms). System healthy.",
                metrics={
                    "current_value": current_value,
                    "forecast_value": forecast_value,
                    "slo_target": slo_target,
                    "slope_per_minute": slope,
                    "r_squared": r_squared,
                },
            ))

        return records

    def _linear_regression(self, points: list[tuple[float, float]]) -> tuple[float, float, float]:
        """Simple linear regression. Returns (slope, intercept, r_squared)."""
        n = len(points)
        sum_x = sum(p[0] for p in points)
        sum_y = sum(p[1] for p in points)
        sum_xy = sum(p[0] * p[1] for p in points)
        sum_x2 = sum(p[0] ** 2 for p in points)
        sum_y2 = sum(p[1] ** 2 for p in points)

        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-10:
            return 0.0, sum_y / n if n > 0 else 0.0, 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R²
        ss_res = sum((y - (slope * x + intercept)) ** 2 for x, y in points)
        mean_y = sum_y / n
        ss_tot = sum((y - mean_y) ** 2 for _, y in points)
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        r_squared = max(0.0, r_squared)

        return slope, intercept, r_squared

    def _estimate_breach_time(self, slope: float, intercept: float, target: float, current_x: float) -> float:
        """Estimate minutes until the trend line crosses the SLO target."""
        if slope <= 0:
            return float('inf')
        breach_x = (target - intercept) / slope
        return max(0, breach_x - current_x)

    def _make_record(self, ev, class_name, severity, confidence, rationale, metrics=None):
        return ClassificationRecord(
            target_type="evidence",
            target_id=ev.evidence_id,
            agent_tier="micro",
            agent_name=self.name,
            taxonomy="fleet.slo",
            class_name=class_name,
            severity=severity,
            confidence=confidence,
            rationale=rationale,
            evidence_ids=[ev.evidence_id],
            metrics=metrics or {},
        )
