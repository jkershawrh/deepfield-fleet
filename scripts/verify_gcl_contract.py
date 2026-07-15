"""Verify actual DeepField producer events against GCL's pinned consumer."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.contracts.events_v1 import (
    EvidenceRefV1,
    FindingV1,
    ForecastV1,
    GovernedRemediationProposalV1,
    ObservationV1,
    ResourceRefV1,
)
from app.intents.ecosystem_emitter import EcosystemEventFactory, ProducerContext
from gcl.adapter.deepfield_event_adapter import (
    DeepFieldCloudEventV1,
    deepfield_event_to_evidence,
)


now = datetime.now(timezone.utc)
digest = "a" * 64
resource = ResourceRefV1(
    cluster="spoke-a",
    namespace="tenant-a",
    kind="FleetInferencePool",
    name="pool-a",
)
evidence = [EvidenceRefV1(uri="urn:srex:evidence:one", sha256=digest)]
factory = EcosystemEventFactory(
    ProducerContext(
        source="urn:srex:deepfield-fleet:contract",
        tenant="tenant-a",
        zone="us-central-1",
        cluster="spoke-a",
        namespace="tenant-a",
        requested_by="deepfield-contract",
        model_version="deepfield-fleet/0.1.0",
    )
)

observation = factory.observation(
    ObservationV1(
        observation_id="obs-1",
        observed_at=now,
        resource=resource,
        signal_type="replica_pressure",
        severity="high",
        value=0.94,
        evidence=evidence,
    ),
    correlation_id="corr-1",
    causation_id="source-1",
    idempotency_key="obs-1",
)
finding = factory.finding(
    FindingV1(
        finding_id="finding-1",
        created_at=now,
        finding_type="sustained_pressure",
        severity="high",
        summary="Replica pressure remained above threshold.",
        confidence=0.95,
        resources=[resource],
        observation_ids=["obs-1"],
        evidence=evidence,
    ),
    correlation_id="corr-1",
    causation_id=observation.id,
    idempotency_key="finding-1",
)
forecast = factory.forecast(
    ForecastV1(
        forecast_id="forecast-1",
        generated_at=now,
        valid_until=now + timedelta(minutes=30),
        horizon_seconds=1800,
        forecast_type="replica_demand",
        target=resource,
        predicted_value=8,
        unit="replicas",
        confidence=0.83,
        recommended_actions=["fleet.scale"],
        model_version="deepfield-fleet/0.1.0",
        input_digest=digest,
        rejected_alternatives=["fleet.shed_load"],
        evidence=evidence,
    ),
    correlation_id="corr-1",
    causation_id=finding.id,
    idempotency_key="forecast-1",
)
proposal = factory.remediation_proposal(
    GovernedRemediationProposalV1(
        proposal_id="proposal-1",
        requested_at=now,
        target=resource,
        action_class="fleet.scale",
        parameters={"desired_replicas": 8},
        reason="Forecast demand exceeds observed capacity.",
        requested_by="deepfield-contract",
        request_digest=digest,
        confidence=0.83,
        evidence=evidence,
    ),
    correlation_id="corr-1",
    causation_id=forecast.id,
    idempotency_key="proposal-1",
)

for event in (observation, finding, forecast, proposal):
    consumed = DeepFieldCloudEventV1.model_validate_json(event.model_dump_json())
    converted = deepfield_event_to_evidence(consumed)
    assert len(converted) == 1
    assert converted[0].metadata["producer_event_id"] == event.id
    print(f"{event.type}: compatible")
