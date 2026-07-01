"""Baseline compiler — builds BaselineProfile from historical evidence."""

import math
from collections import defaultdict

from app.domain.models import BaselineProfile, EvidenceArtifact


class BaselineCompiler:
    def compile(
        self,
        evidence: list[EvidenceArtifact],
        scope: dict,
    ) -> BaselineProfile:
        if not evidence:
            return BaselineProfile(
                scope_type=scope.get("scope_type", "global"),
                scope_id=scope.get("scope_id", "unknown"),
                modality="unknown",
                confidence=0.0,
            )

        modalities = {e.modality for e in evidence}
        primary_modality = max(modalities, key=lambda m: sum(1 for e in evidence if e.modality == m))

        feature_stats = self._compute_feature_stats(evidence)
        normal_ranges = self._compute_normal_ranges(feature_stats)
        thresholds = self._compute_thresholds(feature_stats)
        confidence = self._compute_confidence(evidence, feature_stats)

        return BaselineProfile(
            scope_type=scope.get("scope_type", "global"),
            scope_id=scope.get("scope_id", "unknown"),
            modality=primary_modality,
            normal_ranges=normal_ranges,
            feature_stats=feature_stats,
            thresholds=thresholds,
            class_priors=self._compute_class_priors(evidence),
            confidence=min(confidence, 1.0),
            status="draft",
        )

    def _compute_feature_stats(self, evidence: list[EvidenceArtifact]) -> dict:
        stats = {}
        by_type = defaultdict(list)
        for e in evidence:
            by_type[e.artifact_type].append(e.features)

        for artifact_type, feature_dicts in by_type.items():
            type_stats = {}
            all_keys = set()
            for fd in feature_dicts:
                all_keys.update(fd.keys())
            for key in all_keys:
                values = [fd[key] for fd in feature_dicts if key in fd and isinstance(fd[key], (int, float))]
                if values:
                    n = len(values)
                    mean = sum(values) / n
                    variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
                    std = math.sqrt(variance)
                    type_stats[key] = {
                        "mean": round(mean, 6),
                        "std": round(std, 6),
                        "min": min(values),
                        "max": max(values),
                        "count": n,
                    }
            stats[artifact_type] = type_stats
        return stats

    def _compute_normal_ranges(self, feature_stats: dict) -> dict:
        ranges = {}
        for artifact_type, type_stats in feature_stats.items():
            type_ranges = {}
            for key, s in type_stats.items():
                low = s["mean"] - 2 * s["std"]
                high = s["mean"] + 2 * s["std"]
                type_ranges[key] = {"low": round(low, 6), "high": round(high, 6)}
            ranges[artifact_type] = type_ranges
        return ranges

    def _compute_thresholds(self, feature_stats: dict) -> dict:
        thresholds = {}
        for artifact_type, type_stats in feature_stats.items():
            type_thresholds = {}
            for key, s in type_stats.items():
                type_thresholds[f"{key}_z_warning"] = 2.0
                type_thresholds[f"{key}_z_critical"] = 3.0
                type_thresholds[f"{key}_upper"] = round(s["mean"] + 3 * s["std"], 6)
            thresholds[artifact_type] = type_thresholds
        return thresholds

    def _compute_class_priors(self, evidence: list[EvidenceArtifact]) -> dict:
        modality_counts = defaultdict(int)
        for e in evidence:
            modality_counts[e.modality] += 1
        total = len(evidence)
        return {k: round(v / total, 4) for k, v in modality_counts.items()}

    def _compute_confidence(self, evidence: list[EvidenceArtifact], feature_stats: dict) -> float:
        evidence_score = min(len(evidence) / 10.0, 1.0)
        stats_score = min(len(feature_stats) / 3.0, 1.0)
        return round((evidence_score + stats_score) / 2.0, 4)
