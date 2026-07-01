"""Baseline compiler and profiles API routes."""

import threading
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.baseline.compiler import BaselineCompiler
from app.baseline.profiles import BaselineProfileStore
from app.domain.models import BaselineBuildJob, BaselineProfile

router = APIRouter(prefix="/api/v1/baseline", tags=["baseline"])

_profile_store: Optional[BaselineProfileStore] = None
_jobs: dict[UUID, BaselineBuildJob] = {}


def _get_profile_store() -> BaselineProfileStore:
    global _profile_store
    if _profile_store is None:
        _profile_store = BaselineProfileStore()
    return _profile_store


class JobCreateRequest(BaseModel):
    source_specs: list[dict] = []
    scope: dict = {}
    time_range: dict = {}


@router.post("/jobs", response_model=BaselineBuildJob)
async def create_job(request: JobCreateRequest):
    job = BaselineBuildJob(
        source_specs=request.source_specs,
        scope=request.scope,
        time_range=request.time_range,
    )
    _jobs[job.job_id] = job
    return job


@router.get("/jobs", response_model=list[BaselineBuildJob])
async def list_jobs():
    return list(_jobs.values())


@router.get("/jobs/{job_id}", response_model=BaselineBuildJob)
async def get_job(job_id: UUID):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=BaselineBuildJob)
async def cancel_job(job_id: UUID):
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in ("pending", "running"):
        job.status = "cancelled"
    return job


@router.get("/profiles", response_model=list[BaselineProfile])
async def list_profiles(
    scope_type: Optional[str] = None,
    status: Optional[str] = None,
):
    return _get_profile_store().list_profiles(scope_type=scope_type, status=status)


@router.get("/profiles/{baseline_id}", response_model=BaselineProfile)
async def get_profile(baseline_id: UUID):
    profile = _get_profile_store().get(baseline_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/profiles/{baseline_id}/activate", response_model=BaselineProfile)
async def activate_profile(baseline_id: UUID):
    store = _get_profile_store()
    profile = store.get(baseline_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    store.activate(baseline_id)
    return store.get(baseline_id)
