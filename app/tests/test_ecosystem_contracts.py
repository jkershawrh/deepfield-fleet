"""Conformance tests for DeepField-owned CloudEvents v1."""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.contracts.events_v1 import (
    EvidenceRefV1,
    FindingEventV1,
    FindingV1,
    ForecastEventV1,
    ForecastV1,
    GovernedRemediationProposalEventV1,
    GovernedRemediationProposalV1,
    ObservationEventV1,
    ObservationV1,
    ResourceRefV1,
)
from app.intents.ecosystem_emitter import (
    EcosystemEventFactory,
    ProducerContext,
)
from app.main import app

NOW = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
DIGEST = "a" * 64


def _context() -> ProducerContext:
    return ProducerContext(
        source="urn:srex:deepfield-fleet:test",
        tenant="tenant-a",
        zone="us-central-1",
        cluster="spoke-a",
        namespace="tenant-a",
        requested_by="deepfield-test",
        model_version="forecast/1.0.0",
    )


def _resource() -> ResourceRefV1:
    return ResourceRefV1(
        cluster="spoke-a",
        namespace="tenant-a",
        kind="FleetInferencePool",
        name="pool-a",
    )


def _evidence() -> list[EvidenceRefV1]:
    return [
        EvidenceRefV1(
            uri="urn:srex:evidence:one",
            sha256=DIGEST,
        )
    ]


def test_factory_builds_all_owned_event_types_and_schemas():
    factory = EcosystemEventFactory(_context())
    observation = factory.observation(
        ObservationV1(
            observation_id="obs-1",
            observed_at=NOW,
            resource=_resource(),
            signal_type="replica_pressure",
            severity="high",
            value=0.94,
            evidence=_evidence(),
        ),
        correlation_id="corr-1",
        causation_id="source-1",
        idempotency_key="obs-1",
    )
    finding = factory.finding(
        FindingV1(
            finding_id="finding-1",
            created_at=NOW,
            finding_type="sustained_pressure",
            severity="high",
            summary="Replica pressure remained above threshold.",
            confidence=0.95,
            resources=[_resource()],
            observation_ids=["obs-1"],
            evidence=_evidence(),
        ),
        correlation_id="corr-1",
        causation_id=observation.id,
        idempotency_key="finding-1",
    )
    forecast = factory.forecast(
        ForecastV1(
            forecast_id="forecast-1",
            generated_at=NOW,
            valid_until=NOW + timedelta(minutes=30),
            horizon_seconds=1800,
            forecast_type="replica_demand",
            target=_resource(),
            predicted_value=8,
            unit="replicas",
            confidence=0.83,
            recommended_actions=["fleet.scale"],
            model_version="forecast/1.0.0",
            input_digest=DIGEST,
            rejected_alternatives=["fleet.shed_load"],
            evidence=_evidence(),
        ),
        correlation_id="corr-1",
        causation_id=finding.id,
        idempotency_key="forecast-1",
    )
    proposal = factory.remediation_proposal(
        GovernedRemediationProposalV1(
            proposal_id="proposal-1",
            requested_at=NOW,
            target=_resource(),
            action_class="fleet.scale",
            parameters={"desired_replicas": 8},
            reason="Forecast demand exceeds observed capacity.",
            requested_by="deepfield-test",
            request_digest=DIGEST,
            confidence=0.83,
            evidence=_evidence(),
        ),
        correlation_id="corr-1",
        causation_id=forecast.id,
        idempotency_key="proposal-1",
    )

    assert isinstance(observation, ObservationEventV1)
    assert isinstance(finding, FindingEventV1)
    assert isinstance(forecast, ForecastEventV1)
    assert isinstance(proposal, GovernedRemediationProposalEventV1)
    assert forecast.data.advisory_only is True
    assert proposal.data.advisory_only is True
    for event in (observation, finding, forecast, proposal):
        assert event.specversion == "1.0"
        assert event.causationid
        assert event.expiresat > event.time
        assert event.model_json_schema()["properties"]["specversion"]["const"] == "1.0"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("traceparent", "not-a-traceparent"),
        ("expiresat", NOW - timedelta(seconds=1)),
        ("causationid", ""),
    ],
)
def test_invalid_envelope_is_rejected(field, value):
    factory = EcosystemEventFactory(_context())
    event = factory.observation(
        ObservationV1(
            observation_id="obs-1",
            observed_at=NOW,
            resource=_resource(),
            signal_type="pressure",
            severity="high",
            evidence=_evidence(),
        ),
        correlation_id="corr-1",
        causation_id="source-1",
        idempotency_key="obs-1",
    ).model_dump(mode="python")
    event[field] = value
    with pytest.raises(ValidationError):
        ObservationEventV1.model_validate(event)


def test_forecast_and_remediation_cannot_claim_authority():
    forecast = {
        "forecast_id": "forecast-1",
        "generated_at": NOW,
        "valid_until": NOW + timedelta(minutes=5),
        "horizon_seconds": 300,
        "forecast_type": "replica_demand",
        "target": _resource().model_dump(),
        "predicted_value": 4,
        "confidence": 0.8,
        "recommended_actions": ["fleet.scale"],
        "advisory_only": False,
        "model_version": "forecast/1",
        "input_digest": DIGEST,
        "evidence": [item.model_dump() for item in _evidence()],
    }
    with pytest.raises(ValidationError):
        ForecastV1.model_validate(forecast)

    proposal = {
        "proposal_id": "proposal-1",
        "requested_at": NOW,
        "target": _resource().model_dump(),
        "action_class": "fleet.scale",
        "reason": "Scale recommendation",
        "requested_by": "deepfield-test",
        "request_digest": DIGEST,
        "confidence": 0.8,
        "advisory_only": False,
        "evidence": [item.model_dump() for item in _evidence()],
    }
    with pytest.raises(ValidationError):
        GovernedRemediationProposalV1.model_validate(proposal)


@pytest.mark.asyncio
async def test_contract_schemas_are_published():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/ecosystem/contracts/schemas")
        missing = await client.get("/api/v1/ecosystem/contracts/schemas/not-owned")

    assert response.status_code == 200
    assert set(response.json()) == {
        "observation",
        "finding",
        "forecast",
        "remediation-proposal",
    }
    assert missing.status_code == 404
