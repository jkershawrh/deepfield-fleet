"""BDD scenario tests — Given/When/Then for end-to-end flows."""

from pathlib import Path

from app.baseline.compiler import BaselineCompiler
from app.classification.engine import ClassificationEngine
from app.classification.taxonomy import is_valid_classification
from app.domain.models import BaselineProfile, EvidenceArtifact
from app.multimodal.normalizer import normalize_fixture

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


# ---------------------------------------------------------------------------
# M2 Scenario: Ingest fixture and build baseline
# ---------------------------------------------------------------------------

class TestScenarioIngestFixture:
    """
    Scenario: Ingest factory-line-bearing-failure fixture
      Given the factory-line-bearing-failure fixture directory
      When the fixture is ingested through the normalizer
      Then evidence artifacts are produced for metric, log, document, image, and audio modalities
      And each artifact has extracted features
      And feature values are within expected ranges
    """

    def test_given_fixture_exists(self):
        assert (FIXTURE_DIR / "manifest.yaml").exists()

    def test_when_ingested_then_produces_artifacts(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        assert len(artifacts) >= 5

    def test_then_covers_expected_modalities(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        modalities = {a.modality for a in artifacts}
        expected = {"metric", "log", "document", "image", "audio"}
        assert expected.issubset(modalities)

    def test_and_metric_features_present(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        metric_arts = [a for a in artifacts if a.modality == "metric"]
        for a in metric_arts:
            assert "mean" in a.features
            assert "std" in a.features
            assert "slope" in a.features

    def test_and_vibration_drift_detectable(self):
        artifacts = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        vibration = [a for a in artifacts if a.artifact_type == "vibration_rms"]
        assert len(vibration) == 1
        assert vibration[0].features["slope"] > 0


class TestScenarioBaselineCompilation:
    """
    Scenario: Build baseline from historical fixture data
      Given evidence artifacts from the normal baseline period
      When the baseline compiler runs
      Then a BaselineProfile is produced with status "draft"
      And the profile contains normal ranges for vibration
      And the profile confidence is above 0.5
    """

    def _get_evidence(self):
        return normalize_fixture(FIXTURE_DIR / "manifest.yaml")

    def test_when_compiled_then_produces_profile(self):
        evidence = self._get_evidence()
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        assert isinstance(profile, BaselineProfile)
        assert profile.status == "draft"

    def test_then_has_normal_ranges(self):
        evidence = self._get_evidence()
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        assert len(profile.normal_ranges) > 0
        assert "vibration_rms" in profile.normal_ranges or any(
            "vibration" in k for k in str(profile.normal_ranges)
        )

    def test_then_confidence_above_threshold(self):
        evidence = self._get_evidence()
        compiler = BaselineCompiler()
        profile = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        assert profile.confidence >= 0.5


# ---------------------------------------------------------------------------
# M3 Scenario: Full classification cascade on bearing failure
# ---------------------------------------------------------------------------

class TestScenarioBearingFailureCascade:
    """
    Scenario: Full classification cascade on bearing failure
      Given evidence from the factory-line-bearing-failure scenario
      And an active baseline profile built from the normal period
      When the classification engine runs the cascade
      Then nanoagents detect drift in vibration metrics
      And nanoagents flag error patterns in maintenance logs
      And microagents classify the surface defect image
      And microagents classify the audio vibration anomaly
      And a macroagent builds an incident timeline
      And a macroagent proposes bearing failure as root cause
      And the proposed action is non-destructive
    """

    def _run_cascade(self):
        evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
        compiler = BaselineCompiler()
        baseline = compiler.compile(
            evidence=evidence,
            scope={"scope_type": "site", "scope_id": "factory-line-01"},
        )
        baseline.status = "active"
        engine = ClassificationEngine()
        records = engine.classify(evidence, baseline)
        return evidence, records

    def test_then_nano_detects_metric_drift(self):
        _, records = self._run_cascade()
        nano_metric = [r for r in records if r.agent_tier == "nano" and r.agent_name == "metric_drift"]
        degraded = [r for r in nano_metric if r.class_name in ("degraded", "watch")]
        assert len(degraded) > 0

    def test_then_nano_flags_log_errors(self):
        _, records = self._run_cascade()
        nano_log = [r for r in records if r.agent_tier == "nano" and r.agent_name == "log_pattern"]
        actionable = [r for r in nano_log if r.class_name == "actionable"]
        assert len(actionable) > 0

    def test_then_micro_classifies_image(self):
        _, records = self._run_cascade()
        micro_image = [r for r in records if r.agent_tier == "micro" and r.agent_name == "image_classifier"]
        assert len(micro_image) > 0

    def test_then_micro_classifies_audio(self):
        _, records = self._run_cascade()
        micro_audio = [r for r in records if r.agent_tier == "micro" and r.agent_name == "audio_classifier"]
        assert len(micro_audio) > 0

    def test_then_macro_builds_timeline(self):
        _, records = self._run_cascade()
        timeline = [r for r in records if r.agent_tier == "macro" and r.agent_name == "incident_timeline"]
        assert len(timeline) > 0
        assert timeline[0].rationale != ""

    def test_then_macro_proposes_root_cause(self):
        _, records = self._run_cascade()
        rca = [r for r in records if r.agent_tier == "macro" and r.agent_name == "root_cause_hypothesis"]
        assert len(rca) > 0

    def test_then_action_is_safe(self):
        _, records = self._run_cascade()
        actions = [r for r in records if r.agent_tier == "macro" and r.agent_name == "action_planner"]
        assert len(actions) > 0
        safe_actions = {"observe", "notify", "ticket", "human_approval", "no_action"}
        assert actions[0].class_name in safe_actions

    def test_all_classifications_have_valid_taxonomy(self):
        _, records = self._run_cascade()
        for r in records:
            assert is_valid_classification(r.taxonomy, r.class_name), \
                f"Invalid: {r.taxonomy}/{r.class_name} from {r.agent_name}"

    def test_all_three_tiers_present(self):
        _, records = self._run_cascade()
        tiers = {r.agent_tier for r in records}
        assert tiers == {"nano", "micro", "macro"}


class TestScenarioNormalEvidence:
    """
    Scenario: Classification cascade with no anomalies
      Given normal-range metric evidence only
      And the active baseline profile
      When the classification engine runs
      Then nanoagents classify evidence as normal
      And no evidence escalates to macro tier
    """

    def test_normal_no_macro(self):
        evidence = [EvidenceArtifact(
            source="test", modality="metric", artifact_type="vibration_rms",
            features={"mean": 0.22, "std": 0.01, "slope": 0.001, "z_score_last": 0.3},
        )]
        baseline = BaselineProfile(
            scope_type="site", scope_id="test", modality="metric",
            thresholds={"vibration_rms": {"mean_z_warning": 2.0, "mean_z_critical": 3.0}},
            normal_ranges={"vibration_rms": {"mean": {"low": 0.18, "high": 0.26}}},
            feature_stats={"vibration_rms": {"mean": {"mean": 0.22, "std": 0.012}}},
            confidence=0.8, status="active",
        )
        engine = ClassificationEngine()
        records = engine.classify(evidence, baseline)
        macro = [r for r in records if r.agent_tier == "macro"]
        assert len(macro) == 0
