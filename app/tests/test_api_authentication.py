"""Authentication and CORS behaviour for the DeepField API surface.

DeepField originates the observations, findings and forecasts that the rest
of the governance chain reasons about, so its ingestion surface must not be
open. These tests pin the three behaviours that matter: routes reject bad
credentials when a token is configured, production refuses to serve at all
when no token is configured, and probe/UI paths stay reachable either way.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

TOKEN = "deepfield-test-token-not-a-real-secret"


def _client(monkeypatch, *, token: str | None, mode: str) -> TestClient:
    """Rebuild the app so module-level CORS and auth config are re-read."""
    if token is None:
        monkeypatch.delenv("DEEPFIELD_API_TOKEN", raising=False)
    else:
        monkeypatch.setenv("DEEPFIELD_API_TOKEN", token)
    monkeypatch.setenv("DEEPFIELD_RUNTIME_MODE", mode)

    import app.main

    importlib.reload(app.main)
    return TestClient(app.main.app)


def test_api_route_rejects_missing_token(monkeypatch):
    with _client(monkeypatch, token=TOKEN, mode="production") as client:
        response = client.get("/api/v1/demo/infrastructure")
    assert response.status_code == 401, response.text


def test_api_route_rejects_wrong_token(monkeypatch):
    with _client(monkeypatch, token=TOKEN, mode="production") as client:
        response = client.get(
            "/api/v1/demo/infrastructure",
            headers={"Authorization": "Bearer wrong-token-entirely"},
        )
    assert response.status_code == 401, response.text


def test_api_route_accepts_correct_token(monkeypatch):
    with _client(monkeypatch, token=TOKEN, mode="production") as client:
        response = client.get(
            "/api/v1/demo/infrastructure",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert response.status_code != 401, response.text


def test_production_without_token_refuses_to_serve(monkeypatch):
    """A missing token in production must fail closed, not serve openly."""
    with _client(monkeypatch, token=None, mode="production") as client:
        response = client.get("/api/v1/demo/infrastructure")
    assert response.status_code == 503, response.text
    assert "DEEPFIELD_API_TOKEN" in response.text


def test_development_without_token_still_works(monkeypatch):
    """Local development and the existing test suite must stay usable."""
    with _client(monkeypatch, token=None, mode="development") as client:
        response = client.get("/api/v1/demo/infrastructure")
    assert response.status_code != 401, response.text
    assert response.status_code != 503, response.text


@pytest.mark.parametrize("mode", ["production", "development"])
def test_health_is_always_reachable(monkeypatch, mode):
    """Liveness probes must never depend on credentials."""
    with _client(monkeypatch, token=TOKEN, mode=mode) as client:
        response = client.get("/health")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"


def test_cors_does_not_grant_credentials_to_arbitrary_origins(monkeypatch):
    """allow_origins=["*"] with allow_credentials=True made Starlette echo the
    caller's own Origin back, letting any site read authenticated responses."""
    with _client(monkeypatch, token=TOKEN, mode="production") as client:
        response = client.get(
            "/health", headers={"Origin": "https://attacker.example"}
        )
    assert response.headers.get("access-control-allow-credentials") != "true"
    assert (
        response.headers.get("access-control-allow-origin")
        != "https://attacker.example"
    )


def test_cors_allows_configured_origin(monkeypatch):
    monkeypatch.setenv("DEEPFIELD_CORS_ORIGINS", "https://dashboard.example")
    with _client(monkeypatch, token=TOKEN, mode="production") as client:
        response = client.get(
            "/health", headers={"Origin": "https://dashboard.example"}
        )
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://dashboard.example"
    )
