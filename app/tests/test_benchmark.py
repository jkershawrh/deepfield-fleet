"""Benchmark and measured-proof tests."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.benchmark import run_benchmark, run_project_validation, save_report
from app.domain.models import EvidenceArtifact
from app.main import app
from app.microagents.audio_classifier import AudioAnomalyClassifierAgent
from app.microagents.image_classifier import ImageDefectClassifierAgent
from app.multimodal.media_adapter import get_media_stats, reset_media_stats


class TestBenchmarkRunner:
    def test_enterprise_profile_reports_cpu_compression(self):
        report = run_benchmark(profile="enterprise-signal-volume", iterations=1)

        assert report["profile"] == "enterprise-signal-volume"
        assert report["totals"]["evidence_count"] > 0
        assert report["totals"]["records_by_tier"]["nano"] > 0
        assert report["compression"]["cpu_pre_expensive_ratio"] >= 0.98
        assert report["compression"]["meets_98_cpu_claim"] is True

    def test_unknown_profile_rejected(self):
        with pytest.raises(ValueError):
            run_benchmark(profile="missing-profile", iterations=1)

    def test_report_serialization_writes_json_and_markdown(self, tmp_path):
        report = run_benchmark(profile="factory-demo", iterations=1)
        paths = save_report(report, tmp_path / "latest.json")

        assert Path(paths["json"]).is_file()
        assert Path(paths["markdown"]).is_file()
        assert "DeepField Benchmark Report" in Path(paths["markdown"]).read_text()

    def test_report_serialization_includes_project_validation(self, tmp_path):
        report = run_benchmark(profile="factory-demo", iterations=1)
        report["project_validation"] = {
            "status": "passed",
            "checks": [
                {"name": "backend_pytest", "passed": True, "elapsed_ms": 10.0},
                {"name": "frontend_vitest", "passed": True, "elapsed_ms": 20.0},
            ],
            "summary": {"total": 2, "passed": 2, "failed": 0, "total_elapsed_ms": 30.0},
        }
        paths = save_report(report, tmp_path / "latest.json")

        markdown = Path(paths["markdown"]).read_text()
        assert "Project Validation" in markdown
        assert "backend_pytest" in markdown

    def test_project_validation_uses_all_project_checks(self, monkeypatch):
        calls = []

        def fake_run(check):
            calls.append(check["name"])
            return {
                "name": check["name"],
                "description": check["description"],
                "command": "fake",
                "passed": True,
                "exit_code": 0,
                "elapsed_ms": 1.0,
                "output_tail": "",
            }

        monkeypatch.setattr("app.benchmark._run_check", fake_run)
        result = run_project_validation()

        assert result["status"] == "passed"
        assert calls == ["backend_pytest", "frontend_vitest", "frontend_build"]


class TestBenchmarkAPI:
    @pytest.mark.asyncio
    async def test_run_benchmark_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/benchmark/run", json={
                "profile": "factory-demo",
                "iterations": 1,
                "save": False,
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["report"]["totals"]["evidence_count"] == 6

    @pytest.mark.asyncio
    async def test_latest_benchmark_endpoint(self):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/benchmark/latest")
        assert resp.status_code == 200
        assert resp.json()["status"] in {"ok", "missing"}


class TestMediaAdapterFallbacks:
    def test_image_fixture_fallback_default(self, monkeypatch):
        monkeypatch.delenv("DEEPFIELD_MEDIA_BACKEND", raising=False)
        reset_media_stats()
        ev = EvidenceArtifact(
            source="test",
            modality="image",
            artifact_type="surface_inspection",
            labels={"surface_defect_score": 0.72, "defect_type": "bearing_wear"},
        )

        records = ImageDefectClassifierAgent().classify([ev])

        assert records[0].class_name == "quality"
        assert records[0].metrics["model"] == "fixture_backed"
        assert get_media_stats().onnx_calls == 0

    def test_unavailable_onnx_falls_back_with_reason(self, monkeypatch):
        monkeypatch.setenv("DEEPFIELD_MEDIA_BACKEND", "onnx")
        monkeypatch.setenv("DEEPFIELD_IMAGE_ONNX_MODEL", "missing-image-model.onnx")
        reset_media_stats()
        ev = EvidenceArtifact(
            source="test",
            modality="image",
            artifact_type="surface_inspection",
            labels={"surface_defect_score": 0.72, "defect_type": "bearing_wear"},
        )

        records = ImageDefectClassifierAgent().classify([ev])

        assert records[0].class_name == "quality"
        assert records[0].metrics["model"] == "fixture_backed"
        assert "fallback_reason" in records[0].metrics
        assert get_media_stats().fixture_fallbacks == 1

    def test_audio_fixture_fallback_default(self, monkeypatch):
        monkeypatch.delenv("DEEPFIELD_MEDIA_BACKEND", raising=False)
        reset_media_stats()
        ev = EvidenceArtifact(
            source="test",
            modality="audio",
            artifact_type="vibration_audio",
            labels={"vibration_anomaly_score": 0.81, "anomaly_type": "bearing_resonance"},
        )

        records = AudioAnomalyClassifierAgent().classify([ev])

        assert records[0].class_name == "quality"
        assert records[0].metrics["model"] == "fixture_backed"
        assert get_media_stats().onnx_calls == 0
