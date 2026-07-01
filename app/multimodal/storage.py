"""Evidence storage — in-memory with optional DB persistence."""

from typing import Optional
from uuid import UUID

from app.db import enqueue_write
from app.domain.models import EvidenceArtifact

_store: Optional["EvidenceStore"] = None


def get_evidence_store() -> "EvidenceStore":
    global _store
    if _store is None:
        _store = EvidenceStore()
    return _store


class EvidenceStore:
    def __init__(self):
        self._artifacts: dict[UUID, EvidenceArtifact] = {}

    def store(self, artifact: EvidenceArtifact) -> None:
        self._artifacts[artifact.evidence_id] = artifact
        enqueue_write("evidence_artifacts", artifact.model_dump(mode="json"))

    def get(self, evidence_id: UUID) -> Optional[EvidenceArtifact]:
        return self._artifacts.get(evidence_id)

    def list_by_scope(
        self,
        cluster_id: Optional[UUID] = None,
        modality: Optional[str] = None,
    ) -> list[EvidenceArtifact]:
        result = list(self._artifacts.values())
        if cluster_id is not None:
            result = [a for a in result if a.cluster_id == cluster_id]
        if modality is not None:
            result = [a for a in result if a.modality == modality]
        return result

    def list_all(self) -> list[EvidenceArtifact]:
        return list(self._artifacts.values())

    def count(self) -> int:
        return len(self._artifacts)
