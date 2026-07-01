"""TDD tests for multimodal normalizer and feature extractors.

Written RED first — these must fail before implementation exists.
"""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.domain.models import EvidenceArtifact, NormalizedSignal
from app.multimodal.normalizer import normalize_fixture, normalize_raw, normalize_signal
from app.multimodal.feature_extractors import (
    extract_audio_features,
    extract_document_features,
    extract_image_features,
    extract_log_features,
    extract_metric_features,
    extract_text_features,
)

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


# ---------------------------------------------------------------------------
# normalize_signal
# ---------------------------------------------------------------------------

class TestNormalizeSignal:
    def test_produces_evidence_artifact(self):
        sig = NormalizedSignal(
            signal_id=uuid4(), cluster_id=uuid4(), namespace="ns",
            resource_kind="Pod", resource_name="web-1",
            signal_type="pod_restart", severity="medium",
            confidence=0.8, timestamp=datetime.now(timezone.utc),
        )
        ev = normalize_signal(sig)
        assert isinstance(ev, EvidenceArtifact)
        assert ev.signal_id == sig.signal_id
        assert ev.modality == "event"
        assert ev.source == "deepfield_signal"

    def test_preserves_cluster_id(self):
        cid = uuid4()
        sig = NormalizedSignal(
            signal_id=uuid4(), cluster_id=cid, namespace="ns",
            resource_kind="Pod", resource_name="web-1",
            signal_type="metric", severity="info",
            confidence=0.5, timestamp=datetime.now(timezone.utc),
        )
        ev = normalize_signal(sig)
        assert ev.cluster_id == cid


# ---------------------------------------------------------------------------
# normalize_raw
# ---------------------------------------------------------------------------

class TestNormalizeRaw:
    def test_produces_evidence_artifact(self):
        ev = normalize_raw(
            source="test", modality="metric",
            content={"values": [1.0, 2.0, 3.0], "name": "vibration"},
        )
        assert isinstance(ev, EvidenceArtifact)
        assert ev.modality == "metric"
        assert ev.source == "test"

    def test_stores_content_text_for_text(self):
        ev = normalize_raw(
            source="test", modality="text",
            content={"text": "hello world"},
        )
        assert ev.content_text == "hello world"


# ---------------------------------------------------------------------------
# normalize_fixture
# ---------------------------------------------------------------------------

class TestNormalizeFixture:
    def test_loads_fixture_scenario(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        assert len(artifacts) > 0
        assert all(isinstance(a, EvidenceArtifact) for a in artifacts)

    def test_covers_all_modalities(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        modalities = {a.modality for a in artifacts}
        assert "metric" in modalities
        assert "log" in modalities
        assert "document" in modalities
        assert "image" in modalities
        assert "audio" in modalities

    def test_metric_artifacts_have_features(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        metric_artifacts = [a for a in artifacts if a.modality == "metric"]
        assert len(metric_artifacts) >= 2
        for a in metric_artifacts:
            assert "mean" in a.features
            assert "std" in a.features

    def test_log_artifact_has_features(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        log_artifacts = [a for a in artifacts if a.modality == "log"]
        assert len(log_artifacts) >= 1
        assert "error_count" in log_artifacts[0].features

    def test_image_artifact_has_mock_labels(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        image_artifacts = [a for a in artifacts if a.modality == "image"]
        assert len(image_artifacts) >= 1
        assert "surface_defect_score" in image_artifacts[0].labels

    def test_audio_artifact_has_mock_labels(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        audio_artifacts = [a for a in artifacts if a.modality == "audio"]
        assert len(audio_artifacts) >= 1
        assert "vibration_anomaly_score" in audio_artifacts[0].labels


# ---------------------------------------------------------------------------
# Feature extractors
# ---------------------------------------------------------------------------

class TestFeatureExtractors:
    def test_text_features(self):
        features = extract_text_features("This is an error message from the system")
        assert "length" in features
        assert "word_count" in features
        assert features["length"] > 0

    def test_log_features(self):
        log = "ERROR Vibration threshold exceeded\nWARN Temperature rising\nINFO Normal operation"
        features = extract_log_features(log)
        assert "error_count" in features
        assert "warn_count" in features
        assert features["error_count"] >= 1
        assert features["warn_count"] >= 1

    def test_metric_features(self):
        values = [0.22, 0.21, 0.23, 0.22, 0.20, 0.40, 0.50, 0.60, 0.70, 0.80]
        features = extract_metric_features(values)
        assert "min" in features
        assert "max" in features
        assert "mean" in features
        assert "std" in features
        assert "slope" in features
        assert "z_score_last" in features
        assert features["min"] < features["max"]

    def test_metric_features_slope_positive_for_drift(self):
        values = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        features = extract_metric_features(values)
        assert features["slope"] > 0

    def test_image_features(self):
        metadata = {"width": 640, "height": 480, "format": "png"}
        features = extract_image_features(metadata)
        assert "width" in features
        assert "height" in features

    def test_audio_features(self):
        metadata = {"duration_seconds": 5.0, "sample_rate": 44100}
        features = extract_audio_features(metadata)
        assert "duration_seconds" in features

    def test_document_features(self):
        text = "Maintenance Observation\n\nUnit: Bearing Assembly\n\nThe bearing is worn."
        features = extract_document_features(text, ".txt")
        assert "extension" in features
        assert "line_count" in features
        assert "word_count" in features
