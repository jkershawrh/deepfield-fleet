"""Multimodal evidence API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter

from app.domain.models import EvidenceArtifact
from app.multimodal.storage import get_evidence_store

router = APIRouter(prefix="/api/v1/multimodal", tags=["multimodal"])


@router.post("/evidence", response_model=EvidenceArtifact)
async def submit_evidence(artifact: EvidenceArtifact):
    store = get_evidence_store()
    store.store(artifact)
    return artifact


@router.get("/evidence", response_model=list[EvidenceArtifact])
async def list_evidence(
    modality: Optional[str] = None,
    cluster_id: Optional[UUID] = None,
):
    store = get_evidence_store()
    return store.list_by_scope(cluster_id=cluster_id, modality=modality)


@router.get("/evidence/{evidence_id}", response_model=Optional[EvidenceArtifact])
async def get_evidence(evidence_id: UUID):
    store = get_evidence_store()
    return store.get(evidence_id)
