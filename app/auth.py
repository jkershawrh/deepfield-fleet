"""Bearer-token authentication for the DeepField API.

DeepField is the producer at the head of the governance chain
(deepfield-fleet -> governed-cognitive-loop -> fleet-llm-d -> ledger).
Everything downstream reasons about the observations, findings and
forecasts that originate here, so the ingestion surface needs the same
protection the emission path already has: `app.intents.ecosystem_emitter`
authenticates outbound events to GCL with a bearer token, and GCL's
`/events/deepfield` endpoint verifies it.

Behaviour mirrors that GCL endpoint deliberately:

  - when DEEPFIELD_API_TOKEN is set, every API route requires it;
  - when DEEPFIELD_RUNTIME_MODE is "production" and no token is set,
    requests are refused rather than served unauthenticated;
  - otherwise (local development, tests) requests pass through.

Health checks, static assets and the SPA fallback are mounted directly on
the application rather than on a router, so they are never covered by
this dependency and stay reachable for probes and the dashboard shell.
"""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status


def _configured_token() -> str:
    return os.environ.get("DEEPFIELD_API_TOKEN", "").strip()


def _runtime_mode() -> str:
    return os.environ.get("DEEPFIELD_RUNTIME_MODE", "development").strip().lower()


async def require_api_token(authorization: str = Header(default="")) -> None:
    """FastAPI dependency enforcing bearer-token auth on API routes."""
    token = _configured_token()

    if not token:
        if _runtime_mode() == "production":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "DEEPFIELD_API_TOKEN is not configured; refusing to serve "
                    "API requests unauthenticated in production"
                ),
            )
        return

    expected = f"Bearer {token}"
    if not hmac.compare_digest(authorization, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing or invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
