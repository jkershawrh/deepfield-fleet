"""Tests for event profiles and pre-warm logic."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from app.domain.event_profile import EventProfile, LoadProfile, SLOTargets, EventSchedule, PreWarmAction
from app.domain.fleet_intents import PreWarmIntent, AlertIntent, IntentType


class TestEventProfile:
    def test_basic_profile(self):
        profile = EventProfile(
            name="test-event",
            description="Test event",
            load_profile=LoadProfile(concurrent_users=50, models=["model-a"]),
            slo_targets=SLOTargets(p95_latency_ms=5000),
        )
        assert profile.name == "test-event"
        assert profile.required_rps() == pytest.approx(50 * 2.0 / 60.0, rel=0.01)

    def test_burst_rps(self):
        profile = EventProfile(
            name="burst-test",
            load_profile=LoadProfile(concurrent_users=100, peak_burst_multiplier=5.0),
        )
        base = 100 * 2.0 / 60.0
        assert profile.burst_rps() == pytest.approx(base * 5.0, rel=0.01)

    def test_load_from_yaml(self, tmp_path):
        from app.intents.event_scheduler import load_event_profile

        yaml_content = """
name: yaml-test
description: From YAML
schedule:
  pre_warm_minutes: 20
load_profile:
  concurrent_users: 30
  models: [model-x]
slo_targets:
  p95_latency_ms: 3000
pre_warm_action:
  replicas: 2
  models: [model-x]
"""
        f = tmp_path / "test.yaml"
        f.write_text(yaml_content)

        profile = load_event_profile(str(f))
        assert profile.name == "yaml-test"
        assert profile.schedule.pre_warm_minutes == 20
        assert profile.load_profile.concurrent_users == 30
        assert profile.pre_warm_action.replicas == 2


class TestEventScheduler:
    def _make_profile(self):
        return EventProfile(
            name="test-event",
            schedule=EventSchedule(pre_warm_minutes=30),
            load_profile=LoadProfile(models=["model-a", "model-b"]),
            pre_warm_action=PreWarmAction(replicas=4, models=["model-a", "model-b"]),
        )

    def test_pre_warm_emitted(self):
        from app.intents.event_scheduler import evaluate_event

        profile = self._make_profile()
        now = datetime(2026, 7, 10, 9, 0)
        event_start = datetime(2026, 7, 10, 9, 20)  # 20 min away

        intents = evaluate_event(profile, event_start, now)
        pre_warms = [i for i in intents if isinstance(i, PreWarmIntent)]
        assert len(pre_warms) == 2  # one per model
        assert pre_warms[0].model == "model-a"
        assert pre_warms[0].target_replicas == 4

    def test_no_intent_when_far(self):
        from app.intents.event_scheduler import evaluate_event

        profile = self._make_profile()
        now = datetime(2026, 7, 10, 7, 0)
        event_start = datetime(2026, 7, 10, 10, 0)  # 3 hours away

        intents = evaluate_event(profile, event_start, now)
        assert len(intents) == 0

    def test_event_live_alert(self):
        from app.intents.event_scheduler import evaluate_event

        profile = self._make_profile()
        now = datetime(2026, 7, 10, 9, 30)
        event_start = datetime(2026, 7, 10, 9, 0)  # started 30 min ago

        intents = evaluate_event(profile, event_start, now)
        alerts = [i for i in intents if isinstance(i, AlertIntent)]
        assert len(alerts) == 1
        assert "live" in alerts[0].justification.lower() or "in progress" in alerts[0].message.lower()

    def test_early_warning(self):
        from app.intents.event_scheduler import evaluate_event

        profile = self._make_profile()
        now = datetime(2026, 7, 10, 8, 15)
        event_start = datetime(2026, 7, 10, 9, 0)  # 45 min away (within 30+30=60 window)

        intents = evaluate_event(profile, event_start, now)
        alerts = [i for i in intents if isinstance(i, AlertIntent)]
        assert len(alerts) == 1
        assert "approaching" in alerts[0].message.lower()

    def test_summit_connect_profile_loads(self):
        from app.intents.event_scheduler import load_event_profile

        profile_path = Path(__file__).parent.parent.parent / "config" / "defaults" / "event_profiles" / "summit_connect.yaml"
        if not profile_path.exists():
            pytest.skip("Summit Connect profile not found")

        profile = load_event_profile(str(profile_path))
        assert profile.name == "summit-connect"
        assert profile.load_profile.concurrent_users == 50
        assert len(profile.load_profile.models) >= 3
