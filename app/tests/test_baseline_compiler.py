"""TDD tests for baseline compiler.

Written RED first — these must fail before implementation exists.
"""

from pathlib import Path
from uuid import uuid4

from app.baseline.compiler import BaselineCompiler
from app.baseline.profiles import BaselineProfileStore
from app.domain.models import BaselineProfile, EvidenceArtifact

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


# ---------------------------------------------------------------------------
# Baseline compiler
# ---------------------------------------------------------------------------

class TestBaselineCompiler:
    def test_compile_from_evidence(self):
        evidence = [
            EvidenceArtifact(
                source="fixture", modality="metric", artifact_type="vibration_rms",
                features={"mean": 0.22, "std": 0.012, "min": 0.20, "max": 0.24},
            ),
            EvidenceArtifact(
                source="fixture", modality="metric", artifact_type="temperature",
                features={"mean": 38.2, "std": 0.15, "min": 37.8, "max": 38.5},
            ),
        ]
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        assert isinstance(profile, BaselineProfile)
        assert profile.status == "draft"
        assert profile.scope_type == "site"
        assert profile.scope_id == "factory-line-01"

    def test_profile_has_normal_ranges(self):
        evidence = [
            EvidenceArtifact(
                source="fixture", modality="metric", artifact_type="vibration_rms",
                features={"mean": 0.22, "std": 0.012, "min": 0.20, "max": 0.24},
            ),
        ]
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        assert len(profile.normal_ranges) > 0

    def test_profile_has_thresholds(self):
        evidence = [
            EvidenceArtifact(
                source="fixture", modality="metric", artifact_type="vibration_rms",
                features={"mean": 0.22, "std": 0.012, "min": 0.20, "max": 0.24},
            ),
        ]
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        assert len(profile.thresholds) > 0

    def test_profile_has_feature_stats(self):
        evidence = [
            EvidenceArtifact(
                source="fixture", modality="metric", artifact_type="vibration_rms",
                features={"mean": 0.22, "std": 0.012, "min": 0.20, "max": 0.24},
            ),
        ]
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        assert len(profile.feature_stats) > 0

    def test_confidence_above_zero(self):
        evidence = [
            EvidenceArtifact(
                source="fixture", modality="metric", artifact_type="vibration_rms",
                features={"mean": 0.22, "std": 0.012, "min": 0.20, "max": 0.24},
            ),
        ]
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        assert profile.confidence > 0.0

    def test_empty_evidence_produces_low_confidence(self):
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=[],
            scope={"scope_type": "site", "scope_id": "empty"},
        )
        assert profile.confidence <= 0.1


# ---------------------------------------------------------------------------
# Baseline profile store
# ---------------------------------------------------------------------------

class TestBaselineProfileStore:
    def test_save_and_get(self):
        store = BaselineProfileStore()
        profile = BaselineProfile(
            scope_type="site", scope_id="test", modality="metric",
            confidence=0.8,
        )
        store.save(profile)
        retrieved = store.get(profile.baseline_id)
        assert retrieved is not None
        assert retrieved.baseline_id == profile.baseline_id

    def test_list_profiles(self):
        store = BaselineProfileStore()
        p1 = BaselineProfile(scope_type="site", scope_id="a", modality="metric")
        p2 = BaselineProfile(scope_type="cluster", scope_id="b", modality="log")
        store.save(p1)
        store.save(p2)
        all_profiles = store.list_profiles()
        assert len(all_profiles) == 2

    def test_activate_sets_status(self):
        store = BaselineProfileStore()
        profile = BaselineProfile(
            scope_type="site", scope_id="test", modality="metric",
        )
        store.save(profile)
        store.activate(profile.baseline_id)
        activated = store.get(profile.baseline_id)
        assert activated.status == "active"

    def test_activate_archives_previous(self):
        store = BaselineProfileStore()
        p1 = BaselineProfile(scope_type="site", scope_id="test", modality="metric", status="active")
        p2 = BaselineProfile(scope_type="site", scope_id="test", modality="metric")
        store.save(p1)
        store.save(p2)
        store.activate(p2.baseline_id)
        old = store.get(p1.baseline_id)
        assert old.status == "archived"

    def test_get_active(self):
        store = BaselineProfileStore()
        profile = BaselineProfile(
            scope_type="site", scope_id="test", modality="metric",
        )
        store.save(profile)
        store.activate(profile.baseline_id)
        active = store.get_active("site", "test", "metric")
        assert active is not None
        assert active.baseline_id == profile.baseline_id
