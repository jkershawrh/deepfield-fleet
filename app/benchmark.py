"""Benchmark runner for measured CPU-compression proof."""

import argparse
import json
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.baseline.compiler import BaselineCompiler
from app.classification.engine import ClassificationEngine
from app.domain.models import EvidenceArtifact
from app.inference.client import get_inference_stats, reset_inference_stats
from app.multimodal.media_adapter import get_media_stats, reset_media_stats
from app.multimodal.normalizer import normalize_fixture
from app.multimodal.scale_generator import generate_scaled_evidence

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "multimodal" / "factory-line-bearing-failure"
BENCHMARK_DIR = Path(__file__).resolve().parents[1] / "benchmark-results"
LATEST_REPORT = BENCHMARK_DIR / "latest.json"
CLAIM_THRESHOLD = 0.98
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def run_benchmark(
    profile: str = "enterprise-signal-volume",
    iterations: int = 5,
    include_project_tests: bool = False,
) -> dict:
    if iterations < 1:
        raise ValueError("iterations must be >= 1")

    reset_inference_stats()
    reset_media_stats()

    elapsed_ms: list[float] = []
    totals: dict[str, int] = {
        "evidence": 0,
        "classifications": 0,
        "nano": 0,
        "micro": 0,
        "macro": 0,
    }

    for idx in range(iterations):
        evidence = _load_profile(profile, idx)
        compiler = BaselineCompiler()
        baseline = compiler.compile(evidence=evidence, scope={"scope_type": "site", "scope_id": profile})
        baseline.status = "active"

        start = time.monotonic()
        records = ClassificationEngine().classify(evidence, baseline)
        elapsed_ms.append((time.monotonic() - start) * 1000)

        totals["evidence"] += len(evidence)
        totals["classifications"] += len(records)
        for tier in ("nano", "micro", "macro"):
            totals[tier] += sum(1 for r in records if r.agent_tier == tier)

    inference_stats = get_inference_stats().to_dict()
    media_stats = get_media_stats().to_dict()
    expensive_calls = inference_stats["total_calls"] + media_stats["onnx_calls"]
    ratio = (totals["evidence"] - expensive_calls) / max(totals["evidence"], 1)
    ratio = max(0.0, min(1.0, ratio))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "iterations": iterations,
        "hardware": {
            "cpu_model": _cpu_model(),
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "machine": platform.machine(),
            "target": "Intel Xeon 6 lab, local fallback",
        },
        "totals": {
            "evidence_count": totals["evidence"],
            "classification_count": totals["classifications"],
            "records_by_tier": {
                "nano": totals["nano"],
                "micro": totals["micro"],
                "macro": totals["macro"],
            },
            "llm_calls": inference_stats["total_calls"],
            "onnx_openvino_calls": media_stats["onnx_calls"],
            "evidence_sent_to_llm_or_media_model": expensive_calls,
        },
        "runtime": {
            "elapsed_ms": [round(v, 2) for v in elapsed_ms],
            "p50_elapsed_ms": round(statistics.median(elapsed_ms), 2),
            "p95_elapsed_ms": round(_percentile(elapsed_ms, 95), 2),
        },
        "compression": {
            "cpu_pre_expensive_ratio": round(ratio, 4),
            "cpu_pre_expensive_percent": round(ratio * 100, 2),
            "threshold_percent": CLAIM_THRESHOLD * 100,
            "meets_98_cpu_claim": ratio >= CLAIM_THRESHOLD,
        },
        "inference": inference_stats,
        "media": media_stats,
    }
    if include_project_tests:
        report["project_validation"] = run_project_validation()
    return report


def run_project_validation() -> dict:
    checks = [
        {
            "name": "backend_pytest",
            "description": "Backend FastAPI, agent, bootstrap, benchmark, and contract tests",
            "command": [sys.executable, "-m", "pytest", "app/tests", "-q"],
            "cwd": PROJECT_ROOT,
        },
        {
            "name": "frontend_vitest",
            "description": "Frontend component tests",
            "command": ["npm", "test"],
            "cwd": PROJECT_ROOT / "frontend",
        },
        {
            "name": "frontend_build",
            "description": "TypeScript and Vite production build",
            "command": ["npm", "run", "build"],
            "cwd": PROJECT_ROOT / "frontend",
        },
    ]

    results = [_run_check(check) for check in checks]
    return {
        "status": "passed" if all(r["passed"] for r in results) else "failed",
        "checks": results,
        "summary": {
            "total": len(results),
            "passed": sum(1 for r in results if r["passed"]),
            "failed": sum(1 for r in results if not r["passed"]),
            "total_elapsed_ms": round(sum(r["elapsed_ms"] for r in results), 2),
        },
    }


def save_report(report: dict, out_path: Path = LATEST_REPORT) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str))
    md_path = out_path.with_suffix(".md")
    md_path.write_text(_markdown_report(report))
    return {"json": str(out_path), "markdown": str(md_path)}


def load_latest_report() -> Optional[dict]:
    if not LATEST_REPORT.is_file():
        return None
    return json.loads(LATEST_REPORT.read_text())


def _load_profile(profile: str, iteration: int) -> list[EvidenceArtifact]:
    if profile == "factory-demo":
        return normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    if profile == "enterprise-signal-volume":
        return _mostly_cpu_evidence(iteration)
    if profile == "incident-storm":
        return generate_scaled_evidence(num_lines=50, failure_rate=0.15, seed=100 + iteration)
    raise ValueError(f"Unknown benchmark profile: {profile}")


def _mostly_cpu_evidence(iteration: int) -> list[EvidenceArtifact]:
    evidence = []
    rng_seed = 1000 + iteration
    scale = generate_scaled_evidence(num_lines=120, failure_rate=0.015, seed=rng_seed)
    for ev in scale:
        if ev.modality in {"metric", "log", "event"}:
            evidence.append(ev)
    for i in range(10):
        evidence.append(EvidenceArtifact(
            source="benchmark",
            modality="event",
            artifact_type="cluster_event",
            namespace=f"namespace-{i % 5}",
            resource_name=f"deployment-{i}",
            content_text="Normal rollout event" if i % 9 else "Warning BackOff observed",
            features={"warning_count": 1 if i % 9 == 0 else 0, "event_count": 1},
        ))
    rich_media = [ev for ev in scale if ev.modality in {"image", "audio", "document"}]
    evidence.extend(rich_media[:6])
    return evidence


def _cpu_model() -> str:
    try:
        if platform.system().lower() == "windows":
            import subprocess
            output = subprocess.check_output(
                ["wmic", "cpu", "get", "Name"], text=True, stderr=subprocess.DEVNULL
            )
            lines = [line.strip() for line in output.splitlines() if line.strip() and line.strip() != "Name"]
            if lines:
                return lines[0]
        cpuinfo = Path("/proc/cpuinfo")
        if cpuinfo.is_file():
            for line in cpuinfo.read_text(errors="ignore").splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or "unknown"


def _percentile(values: list[float], percentile: int) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    k = (len(ordered) - 1) * (percentile / 100)
    lower = int(k)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (k - lower)


def _markdown_report(report: dict) -> str:
    compression = report["compression"]
    runtime = report["runtime"]
    totals = report["totals"]
    status = "PASS" if compression["meets_98_cpu_claim"] else "MEASURED BELOW TARGET"
    lines = [
        "# DeepField Benchmark Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Profile: `{report['profile']}`",
        f"- Iterations: {report['iterations']}",
        f"- CPU: {report['hardware']['cpu_model']}",
        f"- Evidence: {totals['evidence_count']}",
        f"- Classifications: {totals['classification_count']}",
        f"- Expensive calls: {totals['evidence_sent_to_llm_or_media_model']}",
        f"- CPU pre-expensive ratio: {compression['cpu_pre_expensive_percent']}%",
        f"- 98% claim: {status}",
        f"- p50 elapsed: {runtime['p50_elapsed_ms']}ms",
        f"- p95 elapsed: {runtime['p95_elapsed_ms']}ms",
        "",
    ]
    validation = report.get("project_validation")
    if validation:
        summary = validation["summary"]
        lines.extend([
            "## Project Validation",
            "",
            f"- Status: {validation['status'].upper()}",
            f"- Checks: {summary['passed']}/{summary['total']} passed",
            f"- Total validation time: {summary['total_elapsed_ms']}ms",
            "",
            "| Check | Result | Time |",
            "| --- | --- | ---: |",
        ])
        for check in validation["checks"]:
            result = "PASS" if check["passed"] else "FAIL"
            lines.append(f"| {check['name']} | {result} | {check['elapsed_ms']}ms |")
        lines.append("")
    return "\n".join(lines)


def _run_check(check: dict) -> dict:
    start = time.monotonic()
    command = _resolve_command(check["command"])
    try:
        proc = subprocess.run(
            command,
            cwd=check["cwd"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
        )
        elapsed = (time.monotonic() - start) * 1000
        output = _strip_ansi(((proc.stdout or "") + "\n" + (proc.stderr or "")).strip())
        return {
            "name": check["name"],
            "description": check["description"],
            "command": " ".join(str(part) for part in command),
            "passed": proc.returncode == 0,
            "exit_code": proc.returncode,
            "elapsed_ms": round(elapsed, 2),
            "output_tail": output[-2000:],
        }
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        return {
            "name": check["name"],
            "description": check["description"],
            "command": " ".join(str(part) for part in command),
            "passed": False,
            "exit_code": None,
            "elapsed_ms": round(elapsed, 2),
            "output_tail": str(exc)[:2000],
        }


def _resolve_command(command: list) -> list:
    if not command:
        return command
    executable = str(command[0])
    resolved = shutil.which(executable)
    if resolved:
        return [resolved, *command[1:]]
    if platform.system().lower() == "windows" and not executable.lower().endswith((".exe", ".cmd", ".bat")):
        resolved = shutil.which(f"{executable}.cmd") or shutil.which(f"{executable}.exe")
        if resolved:
            return [resolved, *command[1:]]
    return command


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run DeepField benchmark profiles")
    parser.add_argument("--profile", default="enterprise-signal-volume",
                        choices=["factory-demo", "enterprise-signal-volume", "incident-storm"])
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--out", default=str(LATEST_REPORT))
    parser.add_argument("--include-project-tests", action="store_true",
                        help="Run backend tests, frontend tests, and frontend production build as part of the report")
    args = parser.parse_args()

    report = run_benchmark(
        profile=args.profile,
        iterations=args.iterations,
        include_project_tests=args.include_project_tests,
    )
    paths = save_report(report, Path(args.out))
    print(json.dumps({"report": report, "paths": paths}, indent=2))


if __name__ == "__main__":
    main()
