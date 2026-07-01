"""TDD tests for classification engine and cascade. RED first."""

from pathlib import Path

from app.baseline.compiler import BaselineCompiler
from app.classification.engine import ClassificationEngine
from app.domain.models import BaselineProfile, ClassificationRecord, EvidenceArtifact
from app.classification.taxonomy import is_valid_classification
from app.multimodal.normalizer import normalize_fixture

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


class TestClassificationEngine:
    def _get_evidence_and_baseline(self):
        evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        compiler = BaselineCompiler()
        baseline = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        baseline.status = "active"
        return evidence, baseline

    def test_cascade_produces_records(self):
        evidence, baseline = self._get_evidence_and_baseline()
        engine = ClassificationEngine()
        records = engine.classify(evidence, baseline)
        assert len(records) > 0
        assert all(isinstance(r, ClassificationRecord) for r in records)

    def test_produces_nano_records(self):
        evidence, baseline = self._get_evidence_and_baseline()
        engine = ClassificationEngine()
        records = engine.classify(evidence, baseline)
        nano = [r for r in records if r.agent_tier == "nano"]
        assert len(nano) > 0

    def test_produces_micro_records(self):
        evidence, baseline = self._get_evidence_and_baseline()
        engine = ClassificationEngine()
        records = engine.classify(evidence, baseline)
        micro = [r for r in records if r.agent_tier == "micro"]
        assert len(micro) > 0

    def test_produces_macro_records(self):
        evidence, baseline = self._get_evidence_and_baseline()
        engine = ClassificationEngine()
        records = engine.classify(evidence, baseline)
        macro = [r for r in records if r.agent_tier == "macro"]
        assert len(macro) > 0

    def test_taxonomy_values_valid(self):
        evidence, baseline = self._get_evidence_and_baseline()
        engine = ClassificationEngine()
        records = engine.classify(evidence, baseline)
        for r in records:
            assert is_valid_classification(r.taxonomy, r.class_name), \
                f"Invalid: {r.taxonomy}/{r.class_name} from {r.agent_name}"

    def test_all_tiers_represented(self):
        evidence, baseline = self._get_evidence_and_baseline()
        engine = ClassificationEngine()
        records = engine.classify(evidence, baseline)
        tiers = {r.agent_tier for r in records}
        assert tiers == {"nano", "micro", "macro"}

    def test_normal_evidence_no_macro_escalation(self):
        normal_evidence = [EvidenceArtifact(
            source="test", modality="metric", artifact_type="vibration_rms",
            features={"mean": 0.22, "std": 0.01, "slope": 0.001, "z_score_last": 0.3},
        )]
        baseline = BaselineProfile(
            scope_type="site", scope_id="test", modality="metric",
            thresholds={"vibration_rms": {"mean_z_warning": 2.0, "mean_z_critical": 3.0, "mean_upper": 0.35}},
            normal_ranges={"vibration_rms": {"mean": {"low": 0.18, "high": 0.26}}},
            feature_stats={"vibration_rms": {"mean": {"mean": 0.22, "std": 0.012}}},
            confidence=0.8, status="active",
        )
        engine = ClassificationEngine()
        records = engine.classify(normal_evidence, baseline)
        macro = [r for r in records if r.agent_tier == "macro"]
        assert len(macro) == 0
