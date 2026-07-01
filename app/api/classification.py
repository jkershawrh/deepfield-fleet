"""Classification cascade API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.baseline.profiles import BaselineProfileStore
from app.classification.engine import ClassificationEngine
from app.domain.models import ClassificationRecord, EvidenceArtifact

router = APIRouter(prefix="/api/v1/classification", tags=["classification"])

_records: dict[UUID, ClassificationRecord] = {}
_engine = ClassificationEngine()
_profile_store: Optional[BaselineProfileStore] = None


def _get_profile_store() -> BaselineProfileStore:
    global _profile_store
    if _profile_store is None:
        _profile_store = BaselineProfileStore()
    return _profile_store


class RunRequest(BaseModel):
    evidence: list[EvidenceArtifact]
    baseline_id: Optional[UUID] = None
    scope_type: Optional[str] = None
    scope_id: Optional[str] = None
    modality: Optional[str] = None


@router.post("/run", response_model=list[ClassificationRecord])
async def run_classification(request: RunRequest):
    baseline = None
    if request.baseline_id:
        baseline = _get_profile_store().get(request.baseline_id)
    elif request.scope_type and request.scope_id and request.modality:
        baseline = _get_profile_store().get_active(
            request.scope_type, request.scope_id, request.modality,
        )

    records = _engine.classify(request.evidence, baseline)
    for r in records:
        _records[r.classification_id] = r
    return records


@router.get("/records", response_model=list[ClassificationRecord])
async def list_records(
    target_type: Optional[str] = None,
    agent_tier: Optional[str] = None,
):
    result = list(_records.values())
    if target_type:
        result = [r for r in result if r.target_type == target_type]
    if agent_tier:
        result = [r for r in result if r.agent_tier == agent_tier]
    return result


@router.get("/records/{classification_id}", response_model=ClassificationRecord)
async def get_record(classification_id: UUID):
    record = _records.get(classification_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return record
