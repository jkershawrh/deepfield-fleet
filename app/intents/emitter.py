"""Emit DeepField forecasts and advisory proposals to a configured GCL sink.

The historical class name remains for callers, but ordinary emission no longer
posts directly to fleet-llm-d and never writes to an immutable-ledger endpoint.
"""

from __future__ import annotations

import logging
from datetime import timedelta, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.events_v1 import (
    EvidenceRefV1,
    FindingV1,
    ForecastV1,
    GovernedRemediationProposalV1,
    ResourceRefV1,
)
from app.domain.fleet_intents import (
    AlertIntent,
    FleetIntent,
    PreWarmIntent,
    ScaleIntent,
    ShedLoadIntent,
)
from app.domain.models import EvidenceArtifact
from app.intents.ecosystem_emitter import (
    DeliveryResult,
    EcosystemEventFactory,
    EcosystemEventPublisher,
    ProducerContext,
    canonical_sha256,
    evidence_reference,
)

logger = logging.getLogger(__name__)


class IntentEmissionResult(BaseModel):
    """Aggregate transport result, never evidence of execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    intent_id: str
    status: Literal["accepted", "deferred", "rejected"]
    reason: str
    event_ids: list[str] = Field(default_factory=list)
    deliveries: list[DeliveryResult] = Field(default_factory=list)
    execution_verified: Literal[False] = False
    ledger_receipt_id: None = None


class IntentEmitter:
    """Compatibility facade for the governed DeepField producer boundary.

    ``fleet_url`` and ``ledger_url`` are accepted only so older constructors do
    not crash during migration. They are never contacted.
    """

    def __init__(
        self,
        gcl_sink_url: str = "",
        token: str = "",
        *,
        context: ProducerContext | None = None,
        publisher: EcosystemEventPublisher | None = None,
        fleet_url: str = "",
        ledger_url: str = "",
    ):
        self.context = context or ProducerContext.from_environment()
        self.publisher = publisher or EcosystemEventPublisher(
            sink_url=gcl_sink_url or None,
            token=token or None,
        )
        self.gcl_sink_url = self.publisher.sink_url
        self.fleet_url = fleet_url.rstrip("/") if fleet_url else ""
        self.ledger_url = ledger_url.rstrip("/") if ledger_url else ""
        if self.fleet_url or self.ledger_url:
            logger.warning(
                "fleet_url/ledger_url compatibility arguments are ignored; "
                "DeepField publishes advisory CloudEvents only"
            )

    async def emit(
        self,
        intent: FleetIntent,
        *,
        evidence: list[EvidenceArtifact] | None = None,
    ) -> IntentEmissionResult:
        if self.context is None:
            return IntentEmissionResult(
                intent_id=str(intent.id),
                status="deferred",
                reason=(
                    "DeepField producer scope is incomplete; configure tenant, "
                    "zone, cluster, and namespace before publishing"
                ),
            )

        refs = self._evidence_refs(intent, evidence or [])
        factory = EcosystemEventFactory(self.context)
        generated_at = intent.created_at
        if generated_at.tzinfo is None or generated_at.utcoffset() is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        horizon_seconds = max(1, intent.horizon_seconds)
        valid_until = generated_at + timedelta(seconds=horizon_seconds)
        correlation_id = str(intent.id)
        causation_id = refs[0].uri
        events = []

        if isinstance(intent, AlertIntent):
            finding = FindingV1(
                finding_id=str(intent.id),
                created_at=generated_at,
                finding_type="fleet_advisory_alert",
                severity=self._alert_severity(intent),
                summary=intent.message or intent.justification,
                confidence=intent.confidence,
                resources=[self._target(intent)],
                observation_ids=[ref.uri for ref in refs],
                attributes={
                    "recommended_action": intent.recommended_action,
                    "horizon_seconds": intent.horizon_seconds,
                },
                evidence=refs,
            )
            events.append(
                factory.finding(
                    finding,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                    idempotency_key=f"deepfield:{intent.id}:finding:v1",
                )
            )
        else:
            action_class, predicted_value, unit, parameters = self._recommendation(
                intent
            )
            input_digest = canonical_sha256(
                [artifact.model_dump(mode="json") for artifact in evidence]
                or intent.model_dump(mode="json")
            )
            forecast = ForecastV1(
                forecast_id=str(intent.id),
                generated_at=generated_at,
                valid_until=valid_until,
                horizon_seconds=horizon_seconds,
                forecast_type=f"{intent.type.value}_recommendation",
                target=self._target(intent),
                predicted_value=predicted_value,
                unit=unit,
                confidence=intent.confidence,
                recommended_actions=[action_class],
                model_version=self.context.model_version,
                input_digest=input_digest,
                rejected_alternatives=[],
                evidence=refs,
            )
            events.append(
                factory.forecast(
                    forecast,
                    correlation_id=correlation_id,
                    causation_id=causation_id,
                    idempotency_key=f"deepfield:{intent.id}:forecast:v1",
                )
            )
            proposal_parameters = {
                **parameters,
                "forecast_id": forecast.forecast_id,
                "forecast_valid_until": forecast.valid_until.isoformat(),
            }
            proposal = GovernedRemediationProposalV1(
                proposal_id=str(intent.id),
                requested_at=generated_at,
                target=forecast.target,
                action_class=action_class,
                parameters=proposal_parameters,
                reason=intent.justification,
                requested_by=self.context.requested_by,
                request_digest=canonical_sha256(proposal_parameters),
                confidence=intent.confidence,
                evidence=refs,
            )
            events.append(
                factory.remediation_proposal(
                    proposal,
                    correlation_id=correlation_id,
                    causation_id=events[0].id,
                    idempotency_key=f"deepfield:{intent.id}:proposal:v1",
                    ttl=timedelta(seconds=min(horizon_seconds, 900)),
                )
            )

        deliveries = [await self.publisher.publish(event) for event in events]
        return self._aggregate(intent, deliveries)

    def _evidence_refs(
        self,
        intent: FleetIntent,
        evidence: list[EvidenceArtifact],
    ) -> list[EvidenceRefV1]:
        refs = []
        for artifact in evidence:
            uri = artifact.source_uri or artifact.content_ref
            if not uri or ":" not in uri:
                uri = f"urn:srex:deepfield:evidence:{artifact.evidence_id}"
            refs.append(
                evidence_reference(
                    artifact,
                    uri=uri,
                    media_type=self._evidence_media_type(artifact),
                )
            )
        if refs:
            return refs
        return [
            evidence_reference(
                intent,
                uri=f"urn:srex:deepfield:recommendation:{intent.id}",
            )
        ]

    @staticmethod
    def _evidence_media_type(artifact: EvidenceArtifact) -> str:
        if artifact.modality == "image":
            return "image/*"
        if artifact.modality == "audio":
            return "audio/*"
        if artifact.modality == "video":
            return "video/*"
        if artifact.modality in ("text", "log", "human_note"):
            return "text/plain"
        return "application/json"

    def _target(self, intent: FleetIntent) -> ResourceRefV1:
        assert self.context is not None
        if isinstance(intent, ScaleIntent):
            kind, name = "FleetInferencePool", intent.pool
        elif isinstance(intent, (PreWarmIntent, ShedLoadIntent)):
            kind, name = "ModelService", intent.model
        else:
            kind = str(intent.state_snapshot.get("resource_kind") or "Fleet")
            name = str(intent.state_snapshot.get("resource_name") or "advisory")
        return ResourceRefV1(
            cluster=self.context.cluster,
            namespace=self.context.namespace,
            kind=kind,
            name=name,
        )

    @staticmethod
    def _recommendation(
        intent: FleetIntent,
    ) -> tuple[str, Any, str, dict[str, Any]]:
        if isinstance(intent, PreWarmIntent):
            return (
                "fleet.prewarm",
                intent.target_replicas,
                "replicas",
                {
                    "model": intent.model,
                    "target_replicas": intent.target_replicas,
                    "target_clusters": intent.target_clusters,
                },
            )
        if isinstance(intent, ScaleIntent):
            return (
                "fleet.scale",
                intent.desired_replicas,
                "replicas",
                {
                    "pool": intent.pool,
                    "current_replicas": intent.current_replicas,
                    "desired_replicas": intent.desired_replicas,
                    "metric": intent.metric,
                },
            )
        if isinstance(intent, ShedLoadIntent):
            return (
                "fleet.shed_load",
                intent.max_inflight,
                "requests",
                {
                    "model": intent.model,
                    "max_inflight": intent.max_inflight,
                    "duration_seconds": intent.duration_seconds,
                },
            )
        raise ValueError(
            f"intent type {intent.type.value} has no governed action mapping"
        )

    @staticmethod
    def _alert_severity(intent: AlertIntent) -> str:
        return {
            "info": "info",
            "warning": "medium",
            "critical": "critical",
        }[intent.severity]

    @staticmethod
    def _aggregate(
        intent: FleetIntent,
        deliveries: list[DeliveryResult],
    ) -> IntentEmissionResult:
        statuses = {delivery.status for delivery in deliveries}
        if "rejected" in statuses:
            status = "rejected"
            reason = "GCL rejected at least one advisory event; nothing executed"
        elif "deferred" in statuses:
            status = "deferred"
            reason = "At least one advisory event is undelivered; nothing executed"
        else:
            status = "accepted"
            reason = (
                "GCL accepted advisory events for asynchronous processing; "
                "execution remains unverified"
            )
        return IntentEmissionResult(
            intent_id=str(intent.id),
            status=status,
            reason=reason,
            event_ids=[delivery.event_id for delivery in deliveries],
            deliveries=deliveries,
        )

    async def close(self) -> None:
        await self.publisher.close()
