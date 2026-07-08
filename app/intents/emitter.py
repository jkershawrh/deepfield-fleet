"""Emits FleetIntents to fleet-llm-d and records predictions in the ARE Ledger."""

import httpx
import logging
from typing import Optional

from app.domain.fleet_intents import FleetIntent, IntentResponse

logger = logging.getLogger(__name__)


class IntentEmitter:
    """Sends typed intents to fleet-llm-d's /api/v1/intents endpoint."""

    def __init__(self, fleet_url: str, token: str = "", ledger_url: str = ""):
        self.fleet_url = fleet_url.rstrip("/")
        self.token = token
        self.ledger_url = ledger_url.rstrip("/") if ledger_url else ""
        self.client = httpx.AsyncClient(timeout=10.0)

    async def emit(self, intent: FleetIntent) -> Optional[IntentResponse]:
        """Send an intent to fleet-llm-d and optionally record in ledger."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Record prediction in ledger first
        if self.ledger_url:
            await self._record_prediction(intent)

        try:
            resp = await self.client.post(
                f"{self.fleet_url}/api/v1/intents",
                content=intent.model_dump_json(),
                headers=headers,
            )
            if resp.status_code == 200:
                return IntentResponse(**resp.json())
            else:
                logger.warning(f"Intent {intent.id} rejected: {resp.status_code} {resp.text}")
                return IntentResponse(
                    intent_id=intent.id,
                    status="refused",
                    reason=f"HTTP {resp.status_code}: {resp.text[:200]}",
                )
        except Exception as e:
            logger.error(f"Failed to emit intent {intent.id}: {e}")
            return None

    async def _record_prediction(self, intent: FleetIntent) -> None:
        """Write prediction entry to ARE Ledger."""
        if not self.ledger_url:
            return
        try:
            entry = {
                "entry_type": f"fleet.prediction.{intent.type.value}",
                "agent_id": "deepfield-fleet",
                "content": intent.model_dump_json(),
                "content_type": "application/json",
                "source_id": "deepfield-fleet",
                "correlation_id": str(intent.id),
            }
            await self.client.post(
                f"{self.ledger_url}/api/entries",
                json=entry,
                timeout=5.0,
            )
        except Exception as e:
            logger.warning(f"Failed to record prediction in ledger: {e}")

    async def close(self):
        await self.client.aclose()
