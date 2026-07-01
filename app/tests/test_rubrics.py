"""EDD rubric evaluation tests.

Verifies the red/green matrix state at each milestone.
M1: contract_compliance=green, fixture_scenarios=green, db_degradation=green,
    evidence_normalization=red, classification_accuracy=red (expected).
"""

from pathlib import Path

import yaml

from app.analysis.evaluator import (
    evaluate_pipeline,
    score_agent_coverage,
    score_baseline_quality,
    score_cascade_efficiency,
    score_classification_accuracy,
    score_contract_compliance,
    score_db_degradation,
    score_evidence_normalization,
    score_fixture_scenarios,
    score_safety,
)

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


# ---------------------------------------------------------------------------
# M1: Contract compliance — GREEN
# ---------------------------------------------------------------------------

class TestM1ContractCompliance:
    def test_models_importable(self):
        from app.domain.models import (
            AgentAction,
            BaselineBuildJob,
            BaselineProfile,
            ClassificationRecord,
            EvidenceArtifact,
            FilterDecision,
            LearningProposal,
            NormalizedSignal,
            RawSignal,
            VerificationRecord,
        )
        assert all([
            RawSignal, NormalizedSignal, FilterDecision,
            EvidenceArtifact, ClassificationRecord, BaselineProfile,
            BaselineBuildJob, AgentAction, VerificationRecord, LearningProposal,
        ])

    def test_rubric_scores_green(self):
        result = score_contract_compliance(
            models_importable=True,
            all_literals_enforced=True,
            confidence_ranges_enforced=True,
            serialization_roundtrips=True,
        )
        assert result["score"] == "healthy"


# ---------------------------------------------------------------------------
# M1: Fixture scenarios — GREEN
# ---------------------------------------------------------------------------

class TestM1FixtureScenarios:
    def test_manifest_exists_and_loads(self):
        manifest_path = FIXTURE_DIR / "manifest.yaml"
        assert manifest_path.exists()
        manifest = yaml.safe_load(manifest_path.read_text())
        assert manifest["scenario_id"] == "factory-line-bearing-failure"

    def test_all_modalities_have_files(self):
        assert (FIXTURE_DIR / "metrics" / "vibration.csv").exists()
        assert (FIXTURE_DIR / "metrics" / "temperature.csv").exists()
        assert (FIXTURE_DIR / "logs" / "maintenance.log").exists()
        assert (FIXTURE_DIR / "documents" / "maintenance-note.txt").exists()
        assert (FIXTURE_DIR / "images" / "README.md").exists()
        assert (FIXTURE_DIR / "audio" / "README.md").exists()

    def test_manifest_has_expected_classifications(self):
        manifest = yaml.safe_load((FIXTURE_DIR / "manifest.yaml").read_text())
        assert "expected_classifications" in manifest
        assert "nano" in manifest["expected_classifications"]
        assert "micro" in manifest["expected_classifications"]
        assert "macro" in manifest["expected_classifications"]

    def test_rubric_scores_green(self):
        result = score_fixture_scenarios(
            manifest_loadable=True,
            all_modalities_present=True,
            expected_classifications_defined=True,
        )
        assert result["score"] == "healthy"


# ---------------------------------------------------------------------------
# M1: DB graceful degradation — GREEN
# ---------------------------------------------------------------------------

class TestM1DBDegradation:
    def test_db_module_importable(self):
        from app.db import enqueue_write, query
        assert callable(enqueue_write)
        assert callable(query)

    def test_enqueue_write_no_crash_without_db(self):
        from app.db import enqueue_write
        enqueue_write("evidence_artifacts", {"test": True})

    def test_rubric_scores_green(self):
        result = score_db_degradation(
            works_without_db=True,
            writes_silently_skipped=True,
            queries_return_empty=True,
        )
        assert result["score"] == "healthy"


# ---------------------------------------------------------------------------
# M1: Evidence normalization — RED (expected, M2 target)
# ---------------------------------------------------------------------------

class TestM1EvidenceNormalization:
    def test_rubric_scores_failing(self):
        result = score_evidence_normalization()
        assert result["score"] == "failing"


# ---------------------------------------------------------------------------
# M1: Classification accuracy — RED (expected, M3 target)
# ---------------------------------------------------------------------------

class TestM1ClassificationAccuracy:
    def test_rubric_scores_failing(self):
        result = score_classification_accuracy()
        assert result["score"] == "failing"


# ---------------------------------------------------------------------------
# M1: Cascade efficiency — RED (expected, M3 target)
# ---------------------------------------------------------------------------

class TestM1CascadeEfficiency:
    def test_rubric_scores_failing(self):
        result = score_cascade_efficiency()
        assert result["score"] == "failing"


# ---------------------------------------------------------------------------
# M1: Agent coverage — RED (expected, M3 target)
# ---------------------------------------------------------------------------

class TestM1AgentCoverage:
    def test_rubric_scores_failing(self):
        result = score_agent_coverage()
        assert result["score"] == "failing"


# ---------------------------------------------------------------------------
# M1: Full pipeline evaluation — overall failing (expected)
# ---------------------------------------------------------------------------

class TestM1FullEvaluation:
    def test_overall_failing_at_m1(self):
        result = evaluate_pipeline(
            models_importable=True,
            all_literals_enforced=True,
            confidence_ranges_enforced=True,
            serialization_roundtrips=True,
            manifest_loadable=True,
            all_modalities_present=True,
            expected_classifications_defined=True,
            works_without_db=True,
            writes_silently_skipped=True,
            queries_return_empty=True,
        )
        assert result["rubrics"]["contract_compliance"]["score"] == "healthy"
        assert result["rubrics"]["fixture_scenarios"]["score"] == "healthy"
        assert result["rubrics"]["db_graceful_degradation"]["score"] == "healthy"
        assert result["rubrics"]["evidence_normalization"]["score"] == "failing"
        assert result["rubrics"]["classification_accuracy"]["score"] == "failing"
        assert result["overall"] == "failing"

    def test_red_green_matrix_m1(self):
        """The M1 red/green matrix: 3 green, 6 red."""
        result = evaluate_pipeline(
            models_importable=True,
            all_literals_enforced=True,
            confidence_ranges_enforced=True,
            serialization_roundtrips=True,
            manifest_loadable=True,
            all_modalities_present=True,
            expected_classifications_defined=True,
            works_without_db=True,
            writes_silently_skipped=True,
            queries_return_empty=True,
        )
        green = [k for k, v in result["rubrics"].items() if v["score"] == "healthy"]
        red = [k for k, v in result["rubrics"].items() if v["score"] == "failing"]
        assert set(green) == {"contract_compliance", "fixture_scenarios", "db_graceful_degradation"}
        assert len(red) == 6


# ---------------------------------------------------------------------------
# M3: Full rubric matrix — ALL GREEN
# ---------------------------------------------------------------------------

class TestM3FullEvaluation:
    def test_m3_has_safety_red(self):
        """At M3: 8 green, 1 red (safety — not yet implemented)."""
        result = evaluate_pipeline(
            models_importable=True, all_literals_enforced=True,
            confidence_ranges_enforced=True, serialization_roundtrips=True,
            manifest_loadable=True, all_modalities_present=True,
            expected_classifications_defined=True,
            modality_coverage=1.0, feature_extraction_complete=True,
            artifact_validity_rate=1.0,
            history_coverage=0.8, scope_coverage=1.0, confidence=0.7,
            has_thresholds=True,
            taxonomy_compliance=1.0, confidence_calibration=0.85,
            evidence_linkage=1.0,
            nano_retention_rate=0.6, micro_escalation_rate=0.3,
            macro_escalation_rate=0.15,
            nano_agent_count=7, micro_agent_count=5,
            macro_agent_count=5, modalities_covered=6,
            works_without_db=True, writes_silently_skipped=True,
            queries_return_empty=True,
        )
        green = [k for k, v in result["rubrics"].items() if v["score"] == "healthy"]
        red = [k for k, v in result["rubrics"].items() if v["score"] == "failing"]
        assert len(green) == 8
        assert red == ["safety"]


# ---------------------------------------------------------------------------
# M4: ALL rubrics GREEN (including safety)
# ---------------------------------------------------------------------------

class TestM4FullEvaluation:
    def test_all_rubrics_green_at_m4(self):
        result = evaluate_pipeline(
            models_importable=True, all_literals_enforced=True,
            confidence_ranges_enforced=True, serialization_roundtrips=True,
            manifest_loadable=True, all_modalities_present=True,
            expected_classifications_defined=True,
            modality_coverage=1.0, feature_extraction_complete=True,
            artifact_validity_rate=1.0,
            history_coverage=0.8, scope_coverage=1.0, confidence=0.7,
            has_thresholds=True,
            taxonomy_compliance=1.0, confidence_calibration=0.85,
            evidence_linkage=1.0,
            nano_retention_rate=0.6, micro_escalation_rate=0.3,
            macro_escalation_rate=0.15,
            nano_agent_count=7, micro_agent_count=5,
            macro_agent_count=5, modalities_covered=6,
            works_without_db=True, writes_silently_skipped=True,
            queries_return_empty=True,
            non_destructive_actions=True, human_approval_gates=True,
            no_silent_learning=True, action_loop_functional=True,
        )
        for name, rubric in result["rubrics"].items():
            assert rubric["score"] == "healthy", f"Rubric {name} is {rubric['score']}"
        assert result["overall"] == "healthy"

    def test_red_green_matrix_m4(self):
        """At M4 completion: all 9 rubric dimensions green."""
        result = evaluate_pipeline(
            models_importable=True, all_literals_enforced=True,
            confidence_ranges_enforced=True, serialization_roundtrips=True,
            manifest_loadable=True, all_modalities_present=True,
            expected_classifications_defined=True,
            modality_coverage=1.0, feature_extraction_complete=True,
            artifact_validity_rate=1.0,
            history_coverage=0.8, scope_coverage=1.0, confidence=0.7,
            has_thresholds=True,
            taxonomy_compliance=1.0, confidence_calibration=0.85,
            evidence_linkage=1.0,
            nano_retention_rate=0.6, micro_escalation_rate=0.3,
            macro_escalation_rate=0.15,
            nano_agent_count=7, micro_agent_count=5,
            macro_agent_count=5, modalities_covered=6,
            works_without_db=True, writes_silently_skipped=True,
            queries_return_empty=True,
            non_destructive_actions=True, human_approval_gates=True,
            no_silent_learning=True, action_loop_functional=True,
        )
        green = [k for k, v in result["rubrics"].items() if v["score"] == "healthy"]
        assert len(green) == 9
