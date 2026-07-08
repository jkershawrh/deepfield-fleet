"""Fleet intent types for the predictive brain -> fleet-llm-d contract.

These are the typed recommendations that the predictive brain emits.
fleet-llm-d consumes them, evaluates against policy, and executes or refuses.
"""

from datetime import datetime
from enum import Enum
from typing import Literal, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    PRE_WARM = "pre_warm"
    SCALE = "scale"
    SHED_LOAD = "shed_load"
    ALERT = "alert"
    MIGRATE = "migrate"
    NO_ACTION = "no_action"


class IntentStatus(str, Enum):
    PROPOSED = "proposed"
    EXECUTED = "executed"
    REFUSED = "refused"
    DEFERRED = "deferred"


class FleetIntent(BaseModel):
    """Base intent emitted by the predictive brain."""
    id: UUID = Field(default_factory=uuid4)
    type: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    horizon_seconds: int = Field(ge=0, description="How far ahead this predicts")
    justification: str
    state_snapshot: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: IntentStatus = IntentStatus.PROPOSED
    response_reason: Optional[str] = None


class PreWarmIntent(FleetIntent):
    type: Literal[IntentType.PRE_WARM] = IntentType.PRE_WARM
    model: str
    target_replicas: int = Field(ge=1)
    target_clusters: list[str] = Field(default_factory=list)
    reason: str = ""


class ScaleIntent(FleetIntent):
    type: Literal[IntentType.SCALE] = IntentType.SCALE
    pool: str
    current_replicas: int = Field(ge=0)
    desired_replicas: int = Field(ge=0)
    metric: str = ""


class ShedLoadIntent(FleetIntent):
    type: Literal[IntentType.SHED_LOAD] = IntentType.SHED_LOAD
    model: str
    max_inflight: int = Field(ge=1)
    duration_seconds: int = Field(ge=0)
    reason: str = ""


class AlertIntent(FleetIntent):
    type: Literal[IntentType.ALERT] = IntentType.ALERT
    severity: Literal["info", "warning", "critical"]
    message: str
    recommended_action: str = ""


class IntentResponse(BaseModel):
    """Response from fleet-llm-d after evaluating an intent."""
    intent_id: UUID
    status: IntentStatus
    reason: str = ""
    ledger_entry_id: Optional[str] = None
