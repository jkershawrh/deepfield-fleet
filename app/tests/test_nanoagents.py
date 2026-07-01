"""TDD tests for multimodal nanoagents. RED first."""

from uuid import uuid4

from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact
from app.nanoagents.baseline_distance import classify as baseline_distance_classify
from app.nanoagents.metric_drift import classify as metric_drift_classify
from app.nanoagents.log_pattern import classify as log_pattern_classify
from app.nanoagents.evidence_gate import classify as evidence_gate_classify
from app.nanoagents.document_heuristic import classify as document_heuristic_classify
from app.nanoagents.image_metadata import classify as image_metadata_classify
from app.nanoagents.audio_energy import classify as audio_energy_classify


def _metric_evidence(**kw):
    defaults = dict(source="test", modality="metric", artifact_type="vibration_rms",
                    features={"mean": 0.65, "std": 0.15, "slope": 0.08, "z_score_last": 3.5})
    return EvidenceArtifact(**(defaults | kw))


def _log_evidence(**kw):
    defaults = dict(source="test", modality="log", artifact_type="maintenance_log",
                    content_text="ERROR Vibration threshold exceeded\nWARN Temperature rising",
                    features={"error_count": 1, "warn_count": 1, "severity_max": "high"})
    return EvidenceArtifact(**(defaults | kw))


def _baseline(**kw):
    defaults = dict(scope_type="site", scope_id="test", modality="metric",
                    thresholds={"vibration_rms": {"mean_z_warning": 2.0, "mean_z_critical": 3.0, "mean_upper": 0.35}},
                    normal_ranges={"vibration_rms": {"mean": {"low": 0.18, "high": 0.26}}},
                    feature_stats={"vibration_rms": {"mean": {"mean": 0.22, "std": 0.012}}},
                    confidence=0.8, status="active")
    return BaselineProfile(**(defaults | kw))


class TestBaselineDistance:
    def test_detects_drift(self):
        evidence = [_metric_evidence()]
        baseline = _baseline()
        records = baseline_distance_classify(evidence, baseline)
        assert len(records) > 0
        assert all(isinstance(r, ClassificationRecord) for r in records)
        assert all(r.agent_tier == "nano" for r in records)

    def test_normal_passes(self):
        evidence = [_metric_evidence(features={"mean": 0.22, "std": 0.01, "slope": 0.001, "z_score_last": 0.5})]
        baseline = _baseline()
        records = baseline_distance_classify(evidence, baseline)
        normal = [r for r in records if r.class_name == "normal"]
        assert len(normal) > 0


class TestMetricDrift:
    def test_detects_positive_slope(self):
        evidence = [_metric_evidence(features={"slope": 0.08, "z_score_last": 3.5, "mean": 0.65})]
        records = metric_drift_classify(evidence, None)
        assert len(records) > 0
        assert records[0].agent_tier == "nano"

    def test_flat_metric_normal(self):
        evidence = [_metric_evidence(features={"slope": 0.001, "z_score_last": 0.3, "mean": 0.22})]
        records = metric_drift_classify(evidence, None)
        normal = [r for r in records if r.class_name == "normal"]
        assert len(normal) > 0


class TestLogPattern:
    def test_detects_errors(self):
        evidence = [_log_evidence()]
        records = log_pattern_classify(evidence, None)
        assert len(records) > 0
        actionable = [r for r in records if r.class_name == "actionable"]
        assert len(actionable) > 0

    def test_info_only_is_noise(self):
        evidence = [_log_evidence(
            content_text="INFO Normal operation",
            features={"error_count": 0, "warn_count": 0, "severity_max": "info"},
        )]
        records = log_pattern_classify(evidence, None)
        noise = [r for r in records if r.class_name in ("noise", "normal")]
        assert len(noise) > 0


class TestEvidenceGate:
    def test_escalates_high_severity(self):
        evidence = [_metric_evidence(features={"mean": 0.65, "slope": 0.08, "z_score_last": 3.5})]
        records = evidence_gate_classify(evidence, _baseline())
        escalated = [r for r in records if r.class_name in ("actionable", "escalate")]
        assert len(escalated) > 0

    def test_retains_normal(self):
        evidence = [_metric_evidence(features={"mean": 0.22, "slope": 0.001, "z_score_last": 0.3})]
        records = evidence_gate_classify(evidence, _baseline())
        assert len(records) > 0


class TestDocumentHeuristic:
    def test_classifies_document(self):
        evidence = [EvidenceArtifact(
            source="test", modality="document", artifact_type="operator_note",
            content_text="Maintenance note about bearing noise",
            features={"word_count": 5, "extension": ".txt"},
        )]
        records = document_heuristic_classify(evidence, None)
        assert len(records) > 0
        assert records[0].agent_tier == "nano"


class TestImageMetadata:
    def test_classifies_with_labels(self):
        evidence = [EvidenceArtifact(
            source="test", modality="image", artifact_type="surface_inspection",
            labels={"surface_defect_score": 0.72, "defect_type": "bearing_wear"},
        )]
        records = image_metadata_classify(evidence, None)
        assert len(records) > 0
        assert records[0].agent_tier == "nano"


class TestAudioEnergy:
    def test_classifies_with_labels(self):
        evidence = [EvidenceArtifact(
            source="test", modality="audio", artifact_type="vibration_audio",
            labels={"vibration_anomaly_score": 0.81, "anomaly_type": "bearing_resonance"},
        )]
        records = audio_energy_classify(evidence, None)
        assert len(records) > 0
        assert records[0].agent_tier == "nano"
