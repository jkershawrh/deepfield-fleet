"""Persistence for fleet intents and A/B runs using the enqueue_write pattern."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from app.db import enqueue_write
from app.domain.fleet_intents import FleetIntent, IntentResponse


def save_intent(intent: FleetIntent, predictor_mode: str = "predictive", ab_run_id: Optional[UUID] = None) -> None:
    """Persist an intent to the fleet_intents table."""
    data = {
        "intent_id": str(intent.id),
        "intent_type": intent.type.value if hasattr(intent.type, 'value') else str(intent.type),
        "confidence": intent.confidence,
        "horizon_seconds": intent.horizon_seconds,
        "justification": intent.justification,
        "state_snapshot": intent.state_snapshot,
        "status": intent.status.value if hasattr(intent.status, 'value') else str(intent.status),
        "predictor_mode": predictor_mode,
        "created_at": intent.created_at.isoformat() if isinstance(intent.created_at, datetime) else str(intent.created_at),
    }

    # Type-specific fields
    for field in ("model", "pool", "target_replicas", "desired_replicas", "current_replicas",
                  "max_inflight", "duration_seconds", "severity", "message"):
        val = getattr(intent, field, None)
        if val is not None:
            data[field] = val

    if ab_run_id:
        data["ab_run_id"] = str(ab_run_id)

    enqueue_write("fleet_intents", data)


def save_intent_response(intent_id: UUID, response: IntentResponse) -> None:
    """Update an intent with the response from fleet-llm-d."""
    # enqueue_write doesn't support updates, so we write a new entry
    # with the response data. In production, this would be an UPDATE.
    data = {
        "intent_id": str(intent_id),
        "status": response.status.value if hasattr(response.status, 'value') else str(response.status),
        "response_reason": response.reason,
        "ledger_entry_id": response.ledger_entry_id,
    }
    enqueue_write("fleet_intents", data)


def start_ab_run(
    name: str,
    predictor_mode: str,
    event_profile: str = "",
    description: str = "",
) -> UUID:
    """Start a new A/B run and return its ID."""
    run_id = uuid4()
    data = {
        "run_id": str(run_id),
        "name": name,
        "description": description,
        "event_profile": event_profile,
        "predictor_mode": predictor_mode,
        "started_at": datetime.utcnow().isoformat(),
    }
    enqueue_write("ab_runs", data)
    return run_id


def end_ab_run(
    run_id: UUID,
    stats: dict,
    slo_metrics: Optional[dict] = None,
    baseline_run_id: Optional[UUID] = None,
) -> None:
    """End an A/B run with results."""
    data = {
        "run_id": str(run_id),
        "ended_at": datetime.utcnow().isoformat(),
        "total_intents": stats.get("total_intents", 0),
        "intents_by_type": stats.get("intents_by_type", {}),
        "classifications_count": stats.get("total_classifications", 0),
    }
    if slo_metrics:
        for key in ("p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "error_rate", "throughput_rps"):
            if key in slo_metrics:
                data[key] = slo_metrics[key]
    if baseline_run_id:
        data["baseline_run_id"] = str(baseline_run_id)

    enqueue_write("ab_runs", data)


def save_prediction_outcome(
    intent_id: UUID,
    predicted_metric: str,
    predicted_value: float,
    predicted_at: datetime,
    horizon_seconds: int,
    actual_value: Optional[float] = None,
    ab_run_id: Optional[UUID] = None,
) -> None:
    """Record a prediction outcome for accuracy tracking."""
    data = {
        "outcome_id": str(uuid4()),
        "intent_id": str(intent_id),
        "predicted_metric": predicted_metric,
        "predicted_value": predicted_value,
        "predicted_at": predicted_at.isoformat(),
        "prediction_horizon_seconds": horizon_seconds,
    }
    if actual_value is not None:
        data["actual_value"] = actual_value
        data["observed_at"] = datetime.utcnow().isoformat()
        data["absolute_error"] = abs(predicted_value - actual_value)
        if actual_value > 0:
            data["relative_error"] = abs(predicted_value - actual_value) / actual_value
        data["prediction_correct"] = predicted_value > 0 and actual_value > 0
    if ab_run_id:
        data["ab_run_id"] = str(ab_run_id)

    enqueue_write("prediction_outcomes", data)
