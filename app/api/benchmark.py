"""Benchmark API routes for measured proof."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.benchmark import load_latest_report, run_benchmark, save_report

router = APIRouter(prefix="/api/v1/benchmark", tags=["benchmark"])


class BenchmarkRunRequest(BaseModel):
    profile: str = "enterprise-signal-volume"
    iterations: int = Field(default=5, ge=1, le=20)
    save: bool = True
    include_project_tests: bool = False


@router.get("/latest")
async def latest_benchmark():
    report = load_latest_report()
    if report is None:
        return {"status": "missing", "message": "No benchmark report found. Run a benchmark to verify CPU compression."}
    return {"status": "ok", "report": report}


@router.post("/run")
async def run_benchmark_endpoint(req: BenchmarkRunRequest = BenchmarkRunRequest()):
    try:
        report = run_benchmark(
            profile=req.profile,
            iterations=req.iterations,
            include_project_tests=req.include_project_tests,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    paths = save_report(report) if req.save else {}
    return {"status": "ok", "report": report, "paths": paths}
