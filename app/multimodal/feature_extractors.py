"""Lightweight per-modality feature extractors. No heavy ML dependencies."""

import hashlib
import math
import re


def extract_text_features(text: str) -> dict:
    words = text.split()
    return {
        "length": len(text),
        "word_count": len(words),
        "hash": hashlib.md5(text.encode()).hexdigest()[:12],
    }


def extract_log_features(log_text: str) -> dict:
    lines = log_text.strip().split("\n")
    error_count = sum(1 for l in lines if re.search(r'\bERROR\b', l))
    warn_count = sum(1 for l in lines if re.search(r'\bWARN\b', l))
    crit_count = sum(1 for l in lines if re.search(r'\bCRIT\b', l))
    info_count = sum(1 for l in lines if re.search(r'\bINFO\b', l))
    return {
        "line_count": len(lines),
        "error_count": error_count,
        "warn_count": warn_count,
        "crit_count": crit_count,
        "info_count": info_count,
        "severity_max": "critical" if crit_count else "high" if error_count else "medium" if warn_count else "info",
    }


def extract_metric_features(values: list) -> dict:
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "slope": 0.0, "z_score_last": 0.0}
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
    std = math.sqrt(variance)
    slope = 0.0
    if n >= 2:
        x_mean = (n - 1) / 2.0
        numerator = sum((i - x_mean) * (v - mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator else 0.0
    z_score_last = (values[-1] - mean) / std if std > 0 else 0.0
    return {
        "min": min(values),
        "max": max(values),
        "mean": round(mean, 6),
        "std": round(std, 6),
        "slope": round(slope, 6),
        "z_score_last": round(z_score_last, 4),
        "count": n,
    }


def extract_image_features(metadata: dict) -> dict:
    return {
        "width": metadata.get("width", 0),
        "height": metadata.get("height", 0),
        "format": metadata.get("format", "unknown"),
        "perceptual_hash": "placeholder",
    }


def extract_audio_features(metadata: dict) -> dict:
    return {
        "duration_seconds": metadata.get("duration_seconds", 0.0),
        "sample_rate": metadata.get("sample_rate", 0),
        "rms_level": metadata.get("rms_level", 0.0),
        "spectral_summary": "placeholder",
    }


def extract_document_features(text: str, extension: str) -> dict:
    lines = text.strip().split("\n")
    words = text.split()
    title = lines[0].strip() if lines else ""
    sections = [l.strip() for l in lines if l.strip() and not l.startswith(" ")]
    return {
        "extension": extension,
        "line_count": len(lines),
        "word_count": len(words),
        "char_count": len(text),
        "title": title[:100],
        "section_count": len(sections),
    }
