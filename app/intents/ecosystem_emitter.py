"""Strict DeepField CloudEvent construction and delivery to GCL.

Delivery acknowledgement is transport evidence only. It never means that GCL
selected an action, execution was authorized, fleet actuated it, or an
immutable-ledger receipt was recorded.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from app.contracts.events_v1 import (
    ContractEventV1,
    EvidenceRefV1,
    FindingEventV1,
    FindingV1,
    ForecastEventV1,
    ForecastV1,
    GovernedRemediationProposalEventV1,
    GovernedRemediationProposalV1,
    ObservationEventV1,
    ObservationV1,
)

logger = logging.getLogger(__name__)

_contract_event_adapter = TypeAdapter(ContractEventV1)


def canonical_sha256(value: BaseModel | dict[str, Any] | bytes | str) -> str:
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        data = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
        payload = json.dumps(
            data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def deterministic_traceparent(seed: str) -> str:
    trace_id = hashlib.sha256(f"trace:{seed}".encode()).hexdigest()[:32]
    span_id = hashlib.sha256(f"span:{seed}".encode()).hexdigest()[:16]
    return f"00-{trace_id}-{span_id}-01"


class ProducerContext(BaseModel):
    """Explicit scope required before DeepField can publish an ecosystem event."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(min_length=1)
    tenant: str = Field(min_length=1)
    zone: str = Field(min_length=1)
    cluster: str = Field(min_length=1)
    namespace: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    model_version: str = Field(min_length=1)

    @classmethod
    def from_environment(cls) -> "ProducerContext | None":
        values = {
            "source": os.getenv("DEEPFIELD_EVENT_SOURCE", "urn:srex:deepfield-fleet"),
            "tenant": os.getenv("DEEPFIELD_TENANT", ""),
            "zone": os.getenv("DEEPFIELD_ZONE", ""),
            "cluster": os.getenv("DEEPFIELD_CLUSTER", ""),
            "namespace": os.getenv("DEEPFIELD_NAMESPACE", ""),
            "requested_by": os.getenv("DEEPFIELD_PRODUCER_ID", "deepfield-fleet"),
            "model_version": os.getenv(
                "DEEPFIELD_MODEL_VERSION", "deepfield-fleet/0.1.0"
            ),
        }
        if any(not values[key] for key in ("tenant", "zone", "cluster", "namespace")):
            return None
        return cls(**values)


class DeliveryResult(BaseModel):
    """One CloudEvent delivery result, explicitly not an execution result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    event_type: str
    status: Literal["accepted", "deferred", "rejected"]
    reason: str
    downstream_status: int | None = None
    execution_verified: Literal[False] = False
    ledger_receipt_id: None = None


class EcosystemEventFactory:
    """Construct deterministic CloudEvents around producer-owned payloads."""

    def __init__(self, context: ProducerContext):
        self.context = context

    def _envelope(
        self,
        *,
        event_type: str,
        subject: str,
        event_time: datetime,
        correlation_id: str,
        causation_id: str,
        idempotency_key: str,
        ttl: timedelta,
    ) -> dict[str, Any]:
        if event_time.tzinfo is None or event_time.utcoffset() is None:
            raise ValueError("event_time must include a timezone")
        fingerprint = canonical_sha256(f"{event_type}:{idempotency_key}")
        event_id = f"urn:sha256:{fingerprint}"
        return {
            "id": event_id,
            "source": self.context.source,
            "subject": subject,
            "time": event_time,
            "correlationid": correlation_id,
            "causationid": causation_id,
            "idempotencykey": idempotency_key,
            "tenant": self.context.tenant,
            "zone": self.context.zone,
            "traceparent": deterministic_traceparent(event_id),
            "expiresat": event_time + ttl,
        }

    def observation(
        self,
        data: ObservationV1,
        *,
        correlation_id: str,
        causation_id: str,
        idempotency_key: str,
        ttl: timedelta = timedelta(hours=24),
    ) -> ObservationEventV1:
        return ObservationEventV1(
            **self._envelope(
                event_type="io.srex.deepfield.observation.v1",
                subject=f"{data.resource.kind}/{data.resource.name}",
                event_time=data.observed_at,
                correlation_id=correlation_id,
                causation_id=causation_id,
                idempotency_key=idempotency_key,
                ttl=ttl,
            ),
            data=data,
        )

    def finding(
        self,
        data: FindingV1,
        *,
        correlation_id: str,
        causation_id: str,
        idempotency_key: str,
        ttl: timedelta = timedelta(hours=24),
    ) -> FindingEventV1:
        target = data.resources[0]
        return FindingEventV1(
            **self._envelope(
                event_type="io.srex.deepfield.finding.v1",
                subject=f"{target.kind}/{target.name}",
                event_time=data.created_at,
                correlation_id=correlation_id,
                causation_id=causation_id,
                idempotency_key=idempotency_key,
                ttl=ttl,
            ),
            data=data,
        )

    def forecast(
        self,
        data: ForecastV1,
        *,
        correlation_id: str,
        causation_id: str,
        idempotency_key: str,
    ) -> ForecastEventV1:
        return ForecastEventV1(
            **self._envelope(
                event_type="io.srex.deepfield.forecast.v1",
                subject=f"{data.target.kind}/{data.target.name}",
                event_time=data.generated_at,
                correlation_id=correlation_id,
                causation_id=causation_id,
                idempotency_key=idempotency_key,
                ttl=data.valid_until - data.generated_at,
            ),
            data=data,
        )

    def remediation_proposal(
        self,
        data: GovernedRemediationProposalV1,
        *,
        correlation_id: str,
        causation_id: str,
        idempotency_key: str,
        ttl: timedelta = timedelta(minutes=15),
    ) -> GovernedRemediationProposalEventV1:
        return GovernedRemediationProposalEventV1(
            **self._envelope(
                event_type="io.srex.deepfield.remediation.proposal.v1",
                subject=f"{data.target.kind}/{data.target.name}",
                event_time=data.requested_at,
                correlation_id=correlation_id,
                causation_id=causation_id,
                idempotency_key=idempotency_key,
                ttl=ttl,
            ),
            data=data,
        )


class EcosystemEventPublisher:
    """Publish validated DeepField CloudEvents to an exact configured GCL URL."""

    def __init__(
        self,
        sink_url: str | None = None,
        token: str | None = None,
        *,
        client: httpx.AsyncClient | None = None,
        timeout_seconds: float = 10.0,
    ):
        configured_sink = (
            os.getenv("GCL_EVENT_SINK_URL", "") if sink_url is None else sink_url
        )
        self.sink_url = configured_sink.strip()
        self.token = os.getenv("GCL_EVENT_SINK_TOKEN", "") if token is None else token
        self._owns_client = client is None
        self.client = client or httpx.AsyncClient(timeout=timeout_seconds)

    async def publish(self, event: ContractEventV1 | dict[str, Any]) -> DeliveryResult:
        validated = _contract_event_adapter.validate_python(event)
        if not self.sink_url:
            return DeliveryResult(
                event_id=validated.id,
                event_type=validated.type,
                status="deferred",
                reason="GCL_EVENT_SINK_URL is not configured; no action was requested",
            )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/cloudevents+json",
            "Idempotency-Key": validated.idempotencykey,
            "X-Correlation-ID": validated.correlationid,
            "traceparent": validated.traceparent,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = await self.client.post(
                self.sink_url,
                content=validated.model_dump_json(),
                headers=headers,
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "DeepField event delivery deferred: type=%s id=%s error=%s",
                validated.type,
                validated.id,
                exc,
            )
            return DeliveryResult(
                event_id=validated.id,
                event_type=validated.type,
                status="deferred",
                reason=f"GCL event delivery failed: {exc}",
            )

        if response.status_code == 202:
            return DeliveryResult(
                event_id=validated.id,
                event_type=validated.type,
                status="accepted",
                reason="GCL sink accepted the event for asynchronous processing",
                downstream_status=response.status_code,
            )

        contract_reason = f"GCL sink returned HTTP {response.status_code}"
        if 200 <= response.status_code < 300:
            contract_reason += "; expected asynchronous admission status 202"
        return DeliveryResult(
            event_id=validated.id,
            event_type=validated.type,
            status="rejected",
            reason=contract_reason,
            downstream_status=response.status_code,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()


def evidence_reference(
    value: BaseModel | dict[str, Any],
    *,
    uri: str,
    media_type: str = "application/json",
) -> EvidenceRefV1:
    return EvidenceRefV1(
        uri=uri,
        sha256=canonical_sha256(value),
        media_type=media_type,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
