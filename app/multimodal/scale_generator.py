"""Scale generator — multiplies the fixture scenario across N factory lines."""

import math
import random
from pathlib import Path

from app.domain.models import EvidenceArtifact
from app.multimodal.feature_extractors import (
    extract_log_features,
    extract_metric_features,
)

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


def generate_scaled_evidence(
    num_lines: int,
    failure_rate: float = 0.02,
    seed: int = 42,
) -> list[EvidenceArtifact]:
    rng = random.Random(seed)
    artifacts = []

    for line_idx in range(num_lines):
        scope_id = f"factory-line-{line_idx + 1:02d}"
        is_failing = rng.random() < failure_rate

        base_vibration = 0.22 + rng.gauss(0, 0.01)
        base_temp = 38.2 + rng.gauss(0, 0.3)

        if is_failing:
            drift = 0.3 + rng.random() * 0.4
            temp_rise = 10 + rng.random() * 12
        else:
            drift = rng.gauss(0, 0.02)
            temp_rise = rng.gauss(0, 0.5)

        vib_values = [base_vibration + (drift * i / 72) for i in range(73)]
        vib_features = extract_metric_features(vib_values)

        artifacts.append(EvidenceArtifact(
            source="scale_generator", modality="metric", artifact_type="vibration_rms",
            features=vib_features, labels={"line": scope_id, "failing": is_failing},
            namespace=scope_id,
        ))

        temp_values = [base_temp + (temp_rise * i / 72) for i in range(73)]
        temp_features = extract_metric_features(temp_values)

        artifacts.append(EvidenceArtifact(
            source="scale_generator", modality="metric", artifact_type="temperature_celsius",
            features=temp_features, labels={"line": scope_id, "failing": is_failing},
            namespace=scope_id,
        ))

        if is_failing:
            error_count = rng.randint(2, 6)
            warn_count = rng.randint(1, 4)
        else:
            error_count = 0
            warn_count = rng.randint(0, 1)

        log_features = {
            "line_count": 14, "error_count": error_count,
            "warn_count": warn_count, "crit_count": 1 if error_count > 4 else 0,
            "info_count": 14 - error_count - warn_count,
            "severity_max": "critical" if error_count > 4 else "high" if error_count > 0 else "info",
        }
        artifacts.append(EvidenceArtifact(
            source="scale_generator", modality="log", artifact_type="maintenance_log",
            features=log_features, labels={"line": scope_id, "failing": is_failing},
            content_text=f"{'ERROR ' * error_count}{'WARN ' * warn_count}maintenance log for {scope_id}",
            namespace=scope_id,
        ))

        if is_failing:
            defect_score = 0.5 + rng.random() * 0.4
            anomaly_score = 0.5 + rng.random() * 0.4
        else:
            defect_score = rng.random() * 0.2
            anomaly_score = rng.random() * 0.2

        artifacts.append(EvidenceArtifact(
            source="scale_generator", modality="image", artifact_type="surface_inspection",
            labels={"surface_defect_score": round(defect_score, 2), "defect_type": "bearing_wear" if is_failing else "none", "line": scope_id},
            namespace=scope_id,
        ))

        artifacts.append(EvidenceArtifact(
            source="scale_generator", modality="audio", artifact_type="vibration_audio",
            labels={"vibration_anomaly_score": round(anomaly_score, 2), "anomaly_type": "bearing_resonance" if is_failing else "none", "line": scope_id},
            namespace=scope_id,
        ))

        artifacts.append(EvidenceArtifact(
            source="scale_generator", modality="document", artifact_type="operator_note",
            content_text=f"Line {scope_id}: {'unusual noise reported' if is_failing else 'normal operations'}",
            features={"word_count": 5, "extension": ".txt"},
            labels={"line": scope_id, "failing": is_failing},
            namespace=scope_id,
        ))

    return artifacts
