"""Action manager — propose, approve, execute, reject safe actions."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.db import enqueue_write
from app.domain.models import AgentAction

SAFE_ACTION_TYPES = frozenset({
    "notify", "observe", "ticket", "human_approval", "no_action",
})


class ActionManager:
    def __init__(self):
        self._actions: dict[UUID, AgentAction] = {}

    def propose(
        self,
        action_type: str,
        payload: dict,
        created_by_agent: str,
        incident_id: Optional[UUID] = None,
        finding_id: Optional[UUID] = None,
    ) -> AgentAction:
        action = AgentAction(
            action_type=action_type,
            payload=payload,
            created_by_agent=created_by_agent,
            incident_id=incident_id,
            finding_id=finding_id,
            requires_human_approval=action_type not in ("observe", "no_action"),
        )
        self._actions[action.action_id] = action
        enqueue_write("agent_actions", action.model_dump(mode="json"))
        return action

    def approve(self, action_id: UUID) -> AgentAction:
        action = self._actions.get(action_id)
        if action and action.status == "proposed":
            action.status = "approved"
        return action

    def reject(self, action_id: UUID) -> AgentAction:
        action = self._actions.get(action_id)
        if action and action.status in ("proposed", "approved"):
            action.status = "rejected"
        return action

    def execute(self, action_id: UUID) -> AgentAction:
        action = self._actions.get(action_id)
        if action is None:
            return action
        if action.status != "approved":
            return action
        action.status = "executed"
        action.executed_at = datetime.now(timezone.utc)
        return action

    def get(self, action_id: UUID) -> Optional[AgentAction]:
        return self._actions.get(action_id)

    def list_actions(self, status: Optional[str] = None) -> list[AgentAction]:
        result = list(self._actions.values())
        if status:
            result = [a for a in result if a.status == status]
        return result
