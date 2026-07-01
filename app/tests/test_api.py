"""API endpoint tests — FastAPI test client, no DB required."""

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestEvidenceAPI:
    @pytest.mark.asyncio
    async def test_list_evidence_empty(self, client):
        resp = await client.get("/api/v1/multimodal/evidence")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_submit_and_get_evidence(self, client):
        eid = str(uuid4())
        payload = {
            "evidence_id": eid,
            "source": "test",
            "modality": "metric",
            "artifact_type": "vibration",
            "features": {"mean": 0.22},
            "labels": {},
            "sensitivity": "internal",
        }
        resp = await client.post("/api/v1/multimodal/evidence", json=payload)
        assert resp.status_code == 200
        assert resp.json()["evidence_id"] == eid

        resp = await client.get(f"/api/v1/multimodal/evidence/{eid}")
        assert resp.status_code == 200


class TestBaselineAPI:
    @pytest.mark.asyncio
    async def test_create_job(self, client):
        resp = await client.post("/api/v1/baseline/jobs", json={
            "source_specs": [],
            "scope": {"scope_type": "site", "scope_id": "test"},
            "time_range": {},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_jobs(self, client):
        resp = await client.get("/api/v1/baseline/jobs")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_job_404(self, client):
        resp = await client.get(f"/api/v1/baseline/jobs/{uuid4()}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_list_profiles(self, client):
        resp = await client.get("/api/v1/baseline/profiles")
        assert resp.status_code == 200
