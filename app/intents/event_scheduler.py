"""Event scheduler: reads event profiles and emits pre-warm intents on schedule."""

import logging
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.domain.event_profile import EventProfile
from app.domain.fleet_intents import PreWarmIntent, ScaleIntent, AlertIntent

logger = logging.getLogger(__name__)


def load_event_profile(path: str) -> EventProfile:
    """Load an event profile from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)
    return EventProfile(**data)


def load_profiles_from_directory(directory: str) -> list[EventProfile]:
    """Load all event profiles from a directory."""
    profiles = []
    dir_path = Path(directory)
    if not dir_path.exists():
        return profiles
    for f in dir_path.glob("*.yaml"):
        try:
            profiles.append(load_event_profile(str(f)))
        except Exception as e:
            logger.warning(f"Failed to load profile {f}: {e}")
    return profiles


def evaluate_event(
    profile: EventProfile,
    event_start: datetime,
    now: Optional[datetime] = None,
) -> list:
    """Evaluate an event profile and return any intents that should be emitted now."""
    if now is None:
        now = datetime.utcnow()

    minutes_until = (event_start - now).total_seconds() / 60.0
    intents = []

    models = profile.pre_warm_action.models or profile.load_profile.models

    if minutes_until <= 0 and minutes_until > -profile.schedule.session_duration_minutes:
        # Event is live -- monitor SLO
        intents.append(AlertIntent(
            confidence=1.0,
            horizon_seconds=0,
            justification=f"Event '{profile.name}' is live. Monitoring SLOs.",
            severity="info",
            message=f"Event '{profile.name}' in progress",
            recommended_action="Monitor SLO compliance",
        ))
    elif minutes_until <= profile.schedule.pre_warm_minutes and minutes_until > 0:
        # Pre-warm window -- emit pre-warm intents
        for model in models:
            intents.append(PreWarmIntent(
                confidence=0.95,
                horizon_seconds=int(minutes_until * 60),
                justification=(
                    f"Event '{profile.name}' starts in {minutes_until:.0f} min. "
                    f"Expected {profile.load_profile.concurrent_users} users. "
                    f"Pre-warming {model} to {profile.pre_warm_action.replicas} replicas."
                ),
                model=model,
                target_replicas=profile.pre_warm_action.replicas,
                reason=f"Calendar-driven pre-warm for {profile.name}",
            ))
    elif minutes_until <= profile.schedule.pre_warm_minutes + 30 and minutes_until > profile.schedule.pre_warm_minutes:
        # Early warning -- event approaching
        intents.append(AlertIntent(
            confidence=0.9,
            horizon_seconds=int(minutes_until * 60),
            justification=f"Event '{profile.name}' starts in {minutes_until:.0f} min.",
            severity="info",
            message=f"Event '{profile.name}' approaching, pre-warm will begin in {minutes_until - profile.schedule.pre_warm_minutes:.0f} min",
            recommended_action="Verify backend health",
        ))

    return intents
