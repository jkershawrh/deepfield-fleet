"""Transport and ownership tests for the GCL producer boundary."""

import json
import os
from datetime import datetime, timezone
from unittest.mock import patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.events_v1 import ForecastV1, ResourceRefV1
from app.domain.fleet_intents import AlertIntent, ScaleIntent
from app.domain.models import EvidenceArtifact
from app.intents.ecosystem_emitter import (
    EcosystemEventFactory,
    EcosystemEventPublisher,
    ProducerContext,
    evidence_reference,
)
from app.intents.emitter import IntentEmitter
from app.main import app


def _context() -> ProducerContext:
    return ProducerContext(
        source="urn:srex:deepfield-fleet:test",
        tenant="tenant-a",
        zone="us-central-1",
        cluster="spoke-a",
        namespace="tenant-a",
        requested_by="deepfield-test",
        model_version="capacity/1.0.0",
    )


def _forecast_event():
    now = datetime(2026, 7, 13, 12, 0, tzinfo=timezone.utc)
    evidence = evidence_reference(
        {"latency": 5400},
        uri="urn:srex:evidence:latency",
    )
    data = ForecastV1(
        forecast_id="forecast-1",
        generated_at=now,
        valid_until=now.replace(minute=30),
        horizon_seconds=1800,
        forecast_type="replica_demand",
        target=ResourceRefV1(
            cluster="spoke-a",
            namespace="tenant-a",
            kind="FleetInferencePool",
            name="pool-a",
        ),
        predicted_value=8,
        unit="replicas",
        confidence=0.9,
        recommended_actions=["fleet.scale"],
        model_version="capacity/1.0.0",
        input_digest=evidence.sha256,
        evidence=[evidence],
    )
    return EcosystemEventFactory(_context()).forecast(
        data,
        correlation_id="corr-1",
        causation_id="obs-1",
        idempotency_key="forecast-1",
    )


@pytest.mark.asyncio
async def test_publisher_posts_structured_cloudevent_and_reports_transport_only():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(202, json={"proposal_id": "gcl-1"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    publisher = EcosystemEventPublisher(
        sink_url="https://gcl.example/api/v1/events/deepfield",
        token="test-token",
        client=client,
    )
    result = await publisher.publish(_forecast_event())
    await client.aclose()

    assert result.status == "accepted"
    assert result.execution_verified is False
    assert result.ledger_receipt_id is None
    assert captured["url"] == "https://gcl.example/api/v1/events/deepfield"
    assert captured["headers"]["content-type"] == "application/cloudevents+json"
    assert captured["headers"]["idempotency-key"] == "forecast-1"
    assert captured["headers"]["authorization"] == "Bearer test-token"
    assert captured["body"]["type"] == "io.srex.deepfield.forecast.v1"


@pytest.mark.asyncio
async def test_missing_or_failed_sink_defers_without_execution_claim():
    publisher = EcosystemEventPublisher(sink_url="")
    missing = await publisher.publish(_forecast_event())
    await publisher.close()
    assert missing.status == "deferred"
    assert missing.execution_verified is False

    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    publisher = EcosystemEventPublisher(
        sink_url="https://gcl.example/api/v1/events/deepfield",
        client=client,
    )
    failed = await publisher.publish(_forecast_event())
    await client.aclose()
    assert failed.status == "deferred"
    assert "failed" in failed.reason


@pytest.mark.asyncio
async def test_sink_rejection_is_not_recast_as_success():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(403))
    )
    publisher = EcosystemEventPublisher(
        sink_url="https://gcl.example/api/v1/events/deepfield",
        client=client,
    )
    result = await publisher.publish(_forecast_event())
    await client.aclose()
    assert result.status == "rejected"
    assert result.downstream_status == 403
    assert result.execution_verified is False


@pytest.mark.asyncio
async def test_only_202_is_treated_as_gcl_admission():
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _request: httpx.Response(200))
    )
    publisher = EcosystemEventPublisher(
        sink_url="https://gcl.example/api/v1/events/deepfield",
        client=client,
    )
    result = await publisher.publish(_forecast_event())
    await client.aclose()
    assert result.status == "rejected"
    assert result.downstream_status == 200
    assert "expected asynchronous admission status 202" in result.reason


@pytest.mark.asyncio
async def test_intent_facade_emits_forecast_and_advisory_proposal_only():
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(202)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    publisher = EcosystemEventPublisher(
        sink_url="https://gcl.example/api/v1/events/deepfield",
        client=client,
    )
    emitter = IntentEmitter(context=_context(), publisher=publisher)
    intent = ScaleIntent(
        confidence=0.88,
        horizon_seconds=600,
        justification="Capacity forecast exceeds the safe range.",
        pool="pool-a",
        current_replicas=2,
        desired_replicas=4,
        metric="latency_p95",
    )
    evidence = EvidenceArtifact(
        source="prometheus",
        source_uri="urn:srex:evidence:prometheus-window-1",
        modality="metric",
        artifact_type="latency_p95",
        features={"value": 5400},
    )
    result = await emitter.emit(intent, evidence=[evidence])
    await client.aclose()

    assert result.status == "accepted"
    assert result.execution_verified is False
    assert result.ledger_receipt_id is None
    assert [body["type"] for body in bodies] == [
        "io.srex.deepfield.forecast.v1",
        "io.srex.deepfield.remediation.proposal.v1",
    ]
    assert all(body["data"]["advisory_only"] is True for body in bodies)


@pytest.mark.asyncio
async def test_alert_is_a_finding_not_an_execution_request():
    bodies = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(202)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    publisher = EcosystemEventPublisher(
        sink_url="https://gcl.example/api/v1/events/deepfield",
        client=client,
    )
    emitter = IntentEmitter(context=_context(), publisher=publisher)
    result = await emitter.emit(
        AlertIntent(
            confidence=0.9,
            horizon_seconds=300,
            justification="Review the forecast.",
            severity="warning",
            message="SLO pressure is rising.",
            recommended_action="Operator review",
        )
    )
    await client.aclose()

    assert result.status == "accepted"
    assert len(bodies) == 1
    assert bodies[0]["type"] == "io.srex.deepfield.finding.v1"


@pytest.mark.asyncio
async def test_incomplete_scope_defers_before_delivery():
    with patch.dict(os.environ, {}, clear=True):
        emitter = IntentEmitter()
        result = await emitter.emit(
            ScaleIntent(
                confidence=0.8,
                horizon_seconds=300,
                justification="test",
                pool="pool-a",
                current_replicas=1,
                desired_replicas=2,
            )
        )
        await emitter.close()
    assert result.status == "deferred"
    assert result.event_ids == []
    assert result.execution_verified is False


def test_ordinary_emission_sources_have_no_direct_fleet_or_ledger_write_path():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sources = [
        (root / "intents" / "emitter.py").read_text(),
        (root / "api" / "fleet_demo.py").read_text(),
    ]
    assert all("/api/v1/intents" not in source for source in sources)
    assert all("/api/entries" not in source for source in sources)


@pytest.mark.asyncio
async def test_compatibility_api_defers_and_does_not_fabricate_evidence():
    with patch.dict(os.environ, {}, clear=True):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            emitted = await client.post(
                "/api/v1/fleet/emit-intent",
                json={
                    "intent_type": "pre_warm",
                    "model": "model-a",
                    "target_replicas": 4,
                    "confidence": 0.9,
                    "justification": "Calendar forecast",
                },
            )
            chain = await client.post("/api/v1/fleet/verify-chain")

    assert emitted.status_code == 200
    assert emitted.json()["status"] == "deferred"
    assert emitted.json()["execution_verified"] is False
    assert emitted.json()["ledger_entry_id"] is None
    assert chain.status_code == 200
    assert chain.json()["verified"] is False
    assert chain.json()["chains"] == []
    assert chain.json()["evidence_only"] is True
