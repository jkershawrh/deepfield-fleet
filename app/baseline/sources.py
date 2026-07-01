"""Source adapters for the baseline compiler."""

from pathlib import Path
from typing import Union

from app.domain.models import EvidenceArtifact
from app.multimodal.normalizer import normalize_fixture


class FixtureSource:
    def __init__(self, fixture_path: Union[str, Path]):
        self.fixture_path = Path(fixture_path)

    def load(self) -> list[EvidenceArtifact]:
        manifest = self.fixture_path / "manifest.yaml" if self.fixture_path.is_dir() else self.fixture_path
        return normalize_fixture(manifest)


class EvidenceStoreSource:
    def __init__(self, store):
        self.store = store

    def load(self) -> list[EvidenceArtifact]:
        return self.store.list_all()
