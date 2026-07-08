"""Predictive brain orchestrator with A/B toggle.

When ON: runs fleet nanoagents + SLO forecaster, emits intents to fleet-llm-d.
When OFF: passthrough, no intents emitted (reactive-only mode via fleet-llm-d HPA).
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.domain.event_profile import EventProfile
from app.domain.fleet_intents import FleetIntent
from app.domain.models import EvidenceArtifact, ClassificationRecord
from app.intents.emitter import IntentEmitter
from app.intents.event_scheduler import evaluate_event
from app.nanoagents.pipeline import run_pipeline

logger = logging.getLogger(__name__)


class FleetPredictor:
    """Composable predictive brain that sits above fleet-llm-d.

    Toggle on/off for A/B comparison:
    - ON: classifies fleet signals, forecasts SLOs, emits intents
    - OFF: no predictions, fleet-llm-d runs reactive-only
    """

    def __init__(
        self,
        emitter: Optional[IntentEmitter] = None,
        enabled: bool = True,
        event_profiles: Optional[list[EventProfile]] = None,
    ):
        self.emitter = emitter
        self.enabled = enabled
        self.event_profiles = event_profiles or []
        self._intents_emitted: list[FleetIntent] = []
        self._classifications: list[ClassificationRecord] = []

    @property
    def mode(self) -> str:
        return "predictive" if self.enabled else "reactive"

    def toggle(self, enabled: bool) -> None:
        """Toggle predictor on/off."""
        old = self.mode
        self.enabled = enabled
        logger.info(f"Predictor toggled: {old} → {self.mode}")

    async def process_signals(
        self,
        evidence: list[EvidenceArtifact],
        now: Optional[datetime] = None,
    ) -> list[FleetIntent]:
        """Process fleet signals and optionally emit intents.

        Returns list of intents (emitted if enabled, computed but not emitted if disabled).
        """
        if now is None:
            now = datetime.utcnow()

        intents: list[FleetIntent] = []

        # Step 1: Run nanoagent pipeline for classification
        classifications = run_pipeline(evidence, baseline=None)
        self._classifications.extend(classifications)

        # Step 2: Check event profiles
        for profile in self.event_profiles:
            # Event start time would come from a scheduler — for now, check features
            for ev in evidence:
                if ev.modality == "event" and ev.features.get("event_start"):
                    event_start = datetime.fromisoformat(ev.features["event_start"])
                    event_intents = evaluate_event(profile, event_start, now)
                    intents.extend(event_intents)

        # Step 3: Run SLO forecaster on latency metrics
        latency_evidence = [e for e in evidence if e.modality == "metric"
                           and any(k in e.artifact_type.lower() for k in ("latency", "ttft", "p95"))]
        if len(latency_evidence) >= 3:
            from app.microagents.slo_forecaster import SLOForecasterAgent
            forecaster = SLOForecasterAgent()
            forecast_records = forecaster.classify(latency_evidence)
            for rec in forecast_records:
                if rec.class_name == "slo_breach_predicted":
                    from app.domain.fleet_intents import ScaleIntent
                    intents.append(ScaleIntent(
                        confidence=rec.confidence,
                        horizon_seconds=int(rec.metrics.get("minutes_to_breach", 30) * 60),
                        justification=rec.rationale,
                        pool="cpu-inference",
                        current_replicas=1,
                        desired_replicas=4,
                        metric="slo_forecast",
                    ))

        # Step 4: Emit if enabled
        if self.enabled and self.emitter:
            for intent in intents:
                await self.emitter.emit(intent)

        self._intents_emitted.extend(intents)

        # Persist intents
        from app.intents.persistence import save_intent
        for intent in intents:
            save_intent(intent, predictor_mode=self.mode, ab_run_id=getattr(self, '_ab_run_id', None))

        return intents

    def get_stats(self) -> dict:
        """Return predictor statistics for A/B comparison."""
        return {
            "mode": self.mode,
            "total_intents": len(self._intents_emitted),
            "total_classifications": len(self._classifications),
            "intents_by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> dict:
        counts = {}
        for intent in self._intents_emitted:
            t = intent.type.value if hasattr(intent.type, 'value') else str(intent.type)
            counts[t] = counts.get(t, 0) + 1
        return counts

    def reset_stats(self) -> None:
        """Reset stats for a new A/B run."""
        self._intents_emitted.clear()
        self._classifications.clear()

    def start_ab_run(self, name: str, event_profile: str = "") -> UUID:
        """Start tracking an A/B run."""
        from app.intents.persistence import start_ab_run
        self._ab_run_id = start_ab_run(name, self.mode, event_profile)
        self.reset_stats()
        return self._ab_run_id

    def end_ab_run(self, slo_metrics: Optional[dict] = None, baseline_run_id: Optional[UUID] = None) -> None:
        """End the current A/B run with results."""
        from app.intents.persistence import end_ab_run
        if hasattr(self, '_ab_run_id') and self._ab_run_id:
            end_ab_run(self._ab_run_id, self.get_stats(), slo_metrics, baseline_run_id)
            self._ab_run_id = None
