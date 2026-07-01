"""Base class for microagents."""

from abc import ABC, abstractmethod

from app.domain.models import ClassificationRecord, EvidenceArtifact


class BaseMicroagent(ABC):
    name: str = "base"

    @abstractmethod
    def classify(self, evidence: list[EvidenceArtifact], **kwargs) -> list[ClassificationRecord]:
        ...
