"""Event profile definitions for calendar-driven predictive scaling."""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field


class LoadProfile(BaseModel):
    concurrent_users: int = 50
    requests_per_user_per_minute: float = 2.0
    peak_burst_multiplier: float = 4.0
    models: list[str] = Field(default_factory=list)


class SLOTargets(BaseModel):
    p50_latency_ms: float = 2000.0
    p95_latency_ms: float = 5000.0
    error_rate_percent: float = 1.0


class EventSchedule(BaseModel):
    pre_warm_minutes: int = 30
    session_duration_minutes: int = 90
    cool_down_minutes: int = 15


class PreWarmAction(BaseModel):
    replicas: int = 4
    models: list[str] = Field(default_factory=list)


class EventProfile(BaseModel):
    """A named event profile that drives predictive scaling."""
    name: str
    description: str = ""
    schedule: EventSchedule = Field(default_factory=EventSchedule)
    load_profile: LoadProfile = Field(default_factory=LoadProfile)
    slo_targets: SLOTargets = Field(default_factory=SLOTargets)
    pre_warm_action: PreWarmAction = Field(default_factory=PreWarmAction)

    def required_rps(self) -> float:
        """Calculate required requests per second from load profile."""
        return self.load_profile.concurrent_users * self.load_profile.requests_per_user_per_minute / 60.0

    def burst_rps(self) -> float:
        """Calculate peak burst RPS."""
        return self.required_rps() * self.load_profile.peak_burst_multiplier
