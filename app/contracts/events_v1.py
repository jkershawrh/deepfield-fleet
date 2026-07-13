"""DeepField ecosystem producer contracts, version 1.

DeepField owns observations, findings, forecasts, and advisory remediation
proposals. These structured CloudEvents never represent an execution grant,
infrastructure actuation, or immutable-ledger acknowledgement.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

OBSERVATION_SCHEMA_V1 = "urn:srex:deepfield:schema:observation:v1"
FINDING_SCHEMA_V1 = "urn:srex:deepfield:schema:finding:v1"
FORECAST_SCHEMA_V1 = "urn:srex:deepfield:schema:forecast:v1"
REMEDIATION_PROPOSAL_SCHEMA_V1 = "urn:srex:deepfield:schema:remediation-proposal:v1"

OBSERVATION_EVENT_TYPE_V1 = "io.srex.deepfield.observation.v1"
FINDING_EVENT_TYPE_V1 = "io.srex.deepfield.finding.v1"
FORECAST_EVENT_TYPE_V1 = "io.srex.deepfield.forecast.v1"
REMEDIATION_PROPOSAL_EVENT_TYPE_V1 = "io.srex.deepfield.remediation.proposal.v1"

_SHA256_PATTERN = r"^[0-9a-f]{64}$"
_TRACEPARENT_PATTERN = r"^[0-9a-f]{2}-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}$"


def _require_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return value


def _require_uri(value: str) -> str:
    if ":" not in value or value.startswith(":"):
        raise ValueError("value must be an absolute URI or URN")
    return value


def _validate_traceparent(value: str) -> str:
    version, trace_id, parent_id, _flags = value.split("-")
    if version == "ff":
        raise ValueError("traceparent version ff is forbidden")
    if trace_id == "0" * 32 or parent_id == "0" * 16:
        raise ValueError("traceparent identifiers must be nonzero")
    return value


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRefV1(ContractModel):
    uri: str = Field(min_length=1)
    sha256: str = Field(pattern=_SHA256_PATTERN)
    media_type: str = "application/json"

    _uri_is_absolute = field_validator("uri")(_require_uri)


class ResourceRefV1(ContractModel):
    cluster: str = Field(min_length=1)
    namespace: str | None = None
    kind: str = Field(min_length=1)
    name: str = Field(min_length=1)
    uid: str | None = None


SeverityV1 = Literal["info", "low", "medium", "high", "critical"]
CanonicalFleetActionClassV1 = Literal[
    "fleet.deploy",
    "fleet.scale",
    "fleet.route",
    "fleet.prewarm",
    "fleet.shed_load",
    "fleet.migrate",
    "fleet.kv_transfer",
]


class ObservationV1(ContractModel):
    observation_id: str = Field(min_length=1)
    observed_at: datetime
    resource: ResourceRefV1
    signal_type: str = Field(min_length=1)
    severity: SeverityV1
    value: JsonValue | None = None
    unit: str | None = None
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    evidence: list[EvidenceRefV1] = Field(min_length=1)

    _observed_at_is_aware = field_validator("observed_at")(_require_aware)


class FindingV1(ContractModel):
    finding_id: str = Field(min_length=1)
    created_at: datetime
    finding_type: str = Field(min_length=1)
    severity: SeverityV1
    summary: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    resources: list[ResourceRefV1] = Field(min_length=1)
    observation_ids: list[str] = Field(min_length=1)
    attributes: dict[str, JsonValue] = Field(default_factory=dict)
    evidence: list[EvidenceRefV1] = Field(min_length=1)

    _created_at_is_aware = field_validator("created_at")(_require_aware)


class ForecastV1(ContractModel):
    forecast_id: str = Field(min_length=1)
    generated_at: datetime
    valid_until: datetime
    horizon_seconds: int = Field(gt=0)
    forecast_type: str = Field(min_length=1)
    target: ResourceRefV1
    predicted_value: JsonValue
    unit: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_actions: list[CanonicalFleetActionClassV1] = Field(default_factory=list)
    advisory_only: Literal[True] = True
    model_version: str = Field(min_length=1)
    input_digest: str = Field(pattern=_SHA256_PATTERN)
    rejected_alternatives: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRefV1] = Field(min_length=1)

    _times_are_aware = field_validator("generated_at", "valid_until")(_require_aware)

    @model_validator(mode="after")
    def valid_window(self) -> "ForecastV1":
        if self.valid_until <= self.generated_at:
            raise ValueError("valid_until must be later than generated_at")
        return self


class GovernedRemediationProposalV1(ContractModel):
    """Advisory input for GCL decision synthesis, never an execution grant."""

    proposal_id: str = Field(min_length=1)
    requested_at: datetime
    target: ResourceRefV1
    action_class: CanonicalFleetActionClassV1
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    reason: str = Field(min_length=1)
    requested_by: str = Field(min_length=1)
    request_digest: str = Field(pattern=_SHA256_PATTERN)
    confidence: float = Field(ge=0.0, le=1.0)
    advisory_only: Literal[True] = True
    evidence: list[EvidenceRefV1] = Field(min_length=1)

    _requested_at_is_aware = field_validator("requested_at")(_require_aware)


class CloudEventV1(ContractModel):
    specversion: Literal["1.0"] = "1.0"
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    type: str
    subject: str = Field(min_length=1)
    time: datetime
    datacontenttype: Literal["application/json"] = "application/json"
    dataschema: str
    correlationid: str = Field(min_length=1)
    causationid: str = Field(min_length=1)
    idempotencykey: str = Field(min_length=1)
    tenant: str = Field(min_length=1)
    zone: str = Field(min_length=1)
    traceparent: str = Field(pattern=_TRACEPARENT_PATTERN)
    expiresat: datetime

    _time_is_aware = field_validator("time", "expiresat")(_require_aware)
    _source_is_absolute = field_validator("source")(_require_uri)
    _traceparent_is_valid = field_validator("traceparent")(_validate_traceparent)

    @model_validator(mode="after")
    def expiry_follows_event_time(self) -> "CloudEventV1":
        if self.expiresat <= self.time:
            raise ValueError("expiresat must be later than event time")
        return self


class ObservationEventV1(CloudEventV1):
    type: Literal[OBSERVATION_EVENT_TYPE_V1] = OBSERVATION_EVENT_TYPE_V1
    dataschema: Literal[OBSERVATION_SCHEMA_V1] = OBSERVATION_SCHEMA_V1
    data: ObservationV1


class FindingEventV1(CloudEventV1):
    type: Literal[FINDING_EVENT_TYPE_V1] = FINDING_EVENT_TYPE_V1
    dataschema: Literal[FINDING_SCHEMA_V1] = FINDING_SCHEMA_V1
    data: FindingV1


class ForecastEventV1(CloudEventV1):
    type: Literal[FORECAST_EVENT_TYPE_V1] = FORECAST_EVENT_TYPE_V1
    dataschema: Literal[FORECAST_SCHEMA_V1] = FORECAST_SCHEMA_V1
    data: ForecastV1


class GovernedRemediationProposalEventV1(CloudEventV1):
    type: Literal[REMEDIATION_PROPOSAL_EVENT_TYPE_V1] = (
        REMEDIATION_PROPOSAL_EVENT_TYPE_V1
    )
    dataschema: Literal[REMEDIATION_PROPOSAL_SCHEMA_V1] = REMEDIATION_PROPOSAL_SCHEMA_V1
    data: GovernedRemediationProposalV1


ContractEventV1 = Annotated[
    Union[
        ObservationEventV1,
        FindingEventV1,
        ForecastEventV1,
        GovernedRemediationProposalEventV1,
    ],
    Field(discriminator="type"),
]


CONTRACT_MODELS_V1: dict[str, type[CloudEventV1]] = {
    "observation": ObservationEventV1,
    "finding": FindingEventV1,
    "forecast": ForecastEventV1,
    "remediation-proposal": GovernedRemediationProposalEventV1,
}
