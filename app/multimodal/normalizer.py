"""Evidence normalizer — converts signals and raw artifacts into EvidenceArtifact."""

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

import yaml

from app.domain.models import EvidenceArtifact, NormalizedSignal
from app.multimodal.feature_extractors import (
    extract_audio_features,
    extract_document_features,
    extract_log_features,
    extract_metric_features,
    extract_text_features,
)


def normalize_signal(signal: NormalizedSignal) -> EvidenceArtifact:
    return EvidenceArtifact(
        signal_id=signal.signal_id,
        cluster_id=signal.cluster_id,
        namespace=signal.namespace,
        resource_kind=signal.resource_kind,
        resource_name=signal.resource_name,
        source="deepfield_signal",
        modality="event",
        artifact_type=signal.signal_type,
        content_text=str(signal.evidence) if signal.evidence else None,
        features=extract_text_features(str(signal.evidence)) if signal.evidence else {},
        labels=signal.labels,
        timestamp=signal.timestamp,
    )


def normalize_raw(source: str, modality: str, content: dict) -> EvidenceArtifact:
    features = {}
    content_text = None

    if modality == "text":
        content_text = content.get("text", "")
        features = extract_text_features(content_text)
    elif modality == "log":
        content_text = content.get("text", "")
        features = extract_log_features(content_text)
    elif modality == "metric":
        features = extract_metric_features(content.get("values", []))
    elif modality == "image":
        features = content.get("features", {})
    elif modality == "audio":
        features = content.get("features", {})
    elif modality == "document":
        content_text = content.get("text", "")
        features = extract_document_features(content_text, content.get("extension", ""))

    return EvidenceArtifact(
        source=source,
        modality=modality,
        artifact_type=content.get("name", content.get("artifact_type", modality)),
        content_text=content_text,
        content_ref=content.get("ref"),
        features=features,
        labels=content.get("labels", {}),
    )


def normalize_fixture(manifest_path: Union[str, Path]) -> list[EvidenceArtifact]:
    manifest_path = Path(manifest_path)
    fixture_dir = manifest_path.parent
    manifest = yaml.safe_load(manifest_path.read_text())

    artifacts = []
    for entry in manifest.get("artifacts", []):
        file_path = fixture_dir / entry["file"]
        modality = entry["modality"]
        artifact_type = entry["artifact_type"]
        mock_labels = entry.get("mock_labels", {})

        if modality == "metric" and file_path.suffix == ".csv":
            artifacts.append(_load_metric_csv(file_path, artifact_type, mock_labels))
        elif modality == "log":
            artifacts.append(_load_log(file_path, artifact_type, mock_labels))
        elif modality == "document":
            artifacts.append(_load_document(file_path, artifact_type, mock_labels))
        elif modality == "image":
            artifacts.append(_load_placeholder(file_path, "image", artifact_type, mock_labels))
        elif modality == "audio":
            artifacts.append(_load_placeholder(file_path, "audio", artifact_type, mock_labels))

    return artifacts


def _load_metric_csv(path: Path, artifact_type: str, labels: dict) -> EvidenceArtifact:
    values = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            for k, v in row.items():
                if k != "timestamp":
                    try:
                        values.append(float(v))
                    except ValueError:
                        pass

    features = extract_metric_features(values)
    return EvidenceArtifact(
        source="fixture",
        modality="metric",
        artifact_type=artifact_type,
        content_ref=str(path),
        features=features,
        labels=labels,
    )


def _load_log(path: Path, artifact_type: str, labels: dict) -> EvidenceArtifact:
    text = path.read_text()
    features = extract_log_features(text)
    return EvidenceArtifact(
        source="fixture",
        modality="log",
        artifact_type=artifact_type,
        content_text=text,
        content_ref=str(path),
        features=features,
        labels=labels,
    )


def _load_document(path: Path, artifact_type: str, labels: dict) -> EvidenceArtifact:
    text = path.read_text()
    features = extract_document_features(text, path.suffix)
    return EvidenceArtifact(
        source="fixture",
        modality="document",
        artifact_type=artifact_type,
        content_text=text,
        content_ref=str(path),
        features=features,
        labels=labels,
    )


def _load_placeholder(path: Path, modality: str, artifact_type: str, labels: dict) -> EvidenceArtifact:
    return EvidenceArtifact(
        source="fixture",
        modality=modality,
        artifact_type=artifact_type,
        content_ref=str(path),
        features={},
        labels=labels,
    )
