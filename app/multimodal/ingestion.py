"""Ingestion coordinator — orchestrates normalizer and feature extractors."""

from pathlib import Path
from typing import Union

from app.domain.models import EvidenceArtifact, NormalizedSignal
from app.multimodal.normalizer import normalize_fixture, normalize_signal


def ingest_fixture_scenario(fixture_path: Union[str, Path]) -> list[EvidenceArtifact]:
    fixture_path = Path(fixture_path)
    manifest_path = fixture_path / "manifest.yaml" if fixture_path.is_dir() else fixture_path
    return normalize_fixture(manifest_path)


def ingest_historical_signals(signals: list[NormalizedSignal]) -> list[EvidenceArtifact]:
    return [normalize_signal(s) for s in signals]
