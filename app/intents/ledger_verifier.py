"""Verifies the prediction → action → outcome chain in the ARE Ledger."""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class LedgerChainVerifier:
    """Verifies that the ARE Ledger contains the full causal chain:
    prediction → action → outcome.
    """

    def __init__(self, ledger_url: str):
        self.ledger_url = ledger_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=10.0)

    async def verify_chain(self, correlation_id: str) -> dict:
        """Verify that a prediction → action → outcome chain exists."""
        try:
            resp = await self.client.get(
                f"{self.ledger_url}/api/entries",
                params={"correlation_id": correlation_id},
            )
            if resp.status_code != 200:
                return {"valid": False, "error": f"Ledger returned {resp.status_code}"}

            entries = resp.json()
            if not isinstance(entries, list):
                entries = entries.get("entries", [])

            chain = {
                "prediction": None,
                "action": None,
                "outcome": None,
            }

            for entry in entries:
                entry_type = entry.get("entry_type", "")
                if "prediction" in entry_type:
                    chain["prediction"] = entry
                elif "intent" in entry_type:
                    chain["action"] = entry
                elif "outcome" in entry_type:
                    chain["outcome"] = entry

            has_prediction = chain["prediction"] is not None
            has_action = chain["action"] is not None

            return {
                "valid": has_prediction and has_action,
                "correlation_id": correlation_id,
                "chain": chain,
                "entries_found": len(entries),
                "has_prediction": has_prediction,
                "has_action": has_action,
                "has_outcome": chain["outcome"] is not None,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    async def close(self):
        await self.client.aclose()
