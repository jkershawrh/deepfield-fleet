# DeepField ecosystem producer contracts v1

DeepField Fleet is the canonical producer of observations, findings, and
forecasts in the governed fleet ecosystem. It may also publish an advisory
remediation proposal, but that proposal is only input to GCL decision
synthesis. It is never a `FleetIntent`, execution authorization, an
infrastructure operation, or an immutable-ledger receipt.

## Owned events

| Event type | Purpose |
|---|---|
| `io.srex.deepfield.observation.v1` | Timestamped source signal with resource scope and evidence digest |
| `io.srex.deepfield.finding.v1` | Correlated assessment derived from one or more observations |
| `io.srex.deepfield.forecast.v1` | Expiry-bounded, model-versioned advisory forecast |
| `io.srex.deepfield.remediation.proposal.v1` | Non-authoritative recommendation for GCL evaluation |

Every event is structured CloudEvents 1.0 JSON and requires event,
correlation, causation, and idempotency identifiers; source, subject, tenant,
zone, trace context, expiry, schema identity, and SHA-256 evidence references.
Unknown fields are rejected. Forecasts and remediation proposals require
`advisory_only=true`.

Schemas are published by the service:

```text
GET /api/v1/ecosystem/contracts/schemas
GET /api/v1/ecosystem/contracts/schemas/{observation|finding|forecast|remediation-proposal}
```

## Delivery

Set `GCL_EVENT_SINK_URL` to GCL's DeepField admission endpoint. No path is
appended by the publisher:

```text
GCL_EVENT_SINK_URL=https://gcl.example/api/v1/events/deepfield
```

GCL returns HTTP 202 after it validates and admits the event into decision
synthesis. Optional bearer credentials come from `GCL_EVENT_SINK_TOKEN`.

Producer scope is mandatory:

```text
DEEPFIELD_TENANT=tenant-a
DEEPFIELD_ZONE=us-central-1
DEEPFIELD_CLUSTER=spoke-a
DEEPFIELD_NAMESPACE=tenant-a
```

Optional identity metadata:

```text
DEEPFIELD_EVENT_SOURCE=urn:srex:deepfield-fleet
DEEPFIELD_PRODUCER_ID=deepfield-fleet
DEEPFIELD_MODEL_VERSION=deepfield-fleet/0.1.0
```

Only HTTP 202 produces `status=accepted` and `execution_verified=false`.
Missing configuration or a transport error produces `status=deferred`. Any
other response, including a different 2xx, produces `status=rejected` as a
contract mismatch. None of these states asserts that GCL selected the
recommendation or that a downstream component authorized, actuated, observed,
or recorded it.

## Compatibility API

`POST /api/v1/fleet/emit-intent` remains for the presentation client. It now
adapts the legacy request into owned advisory events. It never calls
fleet-llm-d, never writes an immutable-ledger endpoint, never fabricates a
receipt, and never returns `executed`.

The `/api/v1/fleet/verify-chain` presentation endpoint likewise returns no
synthetic chains. It can display externally supplied fleet evidence when
available, but that evidence is not authorization.

## Evidence boundary

The producer and GCL repositories implement matching contracts and the
`POST /api/v1/events/deepfield` consumer boundary. Local tests demonstrate
schema validation, deterministic envelopes, admission semantics, transport
behavior, and absence of a direct fleet/ledger write path from ordinary
emission. They do not by themselves demonstrate a deployed cross-repository
request, signed DecisionPackage, execution-authorization handoff, fleet
actuation, multi-cluster operation, immutable-ledger receipt, or promotion
maturity.
