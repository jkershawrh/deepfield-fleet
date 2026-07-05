"""Optional CPU media inference adapters with fixture fallback."""

import os
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.domain.models import EvidenceArtifact


@dataclass
class MediaInference:
    modality: str
    backend: str
    class_name: str
    score: float
    label: str
    used_model: bool = False
    fallback_reason: Optional[str] = None
    metrics: dict = field(default_factory=dict)


@dataclass
class MediaStats:
    onnx_calls: int = 0
    fixture_fallbacks: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "onnx_calls": self.onnx_calls,
            "fixture_fallbacks": self.fixture_fallbacks,
            "errors": self.errors,
        }


_stats = MediaStats()


def reset_media_stats() -> None:
    global _stats
    _stats = MediaStats()


def get_media_stats() -> MediaStats:
    return _stats


def classify_image(ev: EvidenceArtifact) -> MediaInference:
    if os.getenv("DEEPFIELD_MEDIA_BACKEND", "fixture").lower() == "onnx":
        model_path = os.getenv("DEEPFIELD_IMAGE_ONNX_MODEL", "")
        if model_path:
            result = _try_image_onnx(ev, Path(model_path))
            if result is not None:
                return result
        return _fixture_image(ev, "onnx backend configured but image model is unavailable")
    return _fixture_image(ev, None)


def classify_audio(ev: EvidenceArtifact) -> MediaInference:
    if os.getenv("DEEPFIELD_MEDIA_BACKEND", "fixture").lower() == "onnx":
        model_path = os.getenv("DEEPFIELD_AUDIO_ONNX_MODEL", "")
        if model_path:
            result = _try_audio_onnx(ev, Path(model_path))
            if result is not None:
                return result
        return _fixture_audio(ev, "onnx backend configured but audio model is unavailable")
    return _fixture_audio(ev, None)


def _fixture_image(ev: EvidenceArtifact, fallback_reason: Optional[str]) -> MediaInference:
    if fallback_reason:
        _stats.fixture_fallbacks += 1
    score = float(ev.labels.get("surface_defect_score", 0.0) or 0.0)
    label = str(ev.labels.get("defect_type", "unknown"))
    return MediaInference(
        modality="image",
        backend="fixture",
        class_name="quality" if score > 0.5 else "unclassified",
        score=min(max(score, 0.0), 1.0) if score else 0.5,
        label=label,
        fallback_reason=fallback_reason,
        metrics={"model": "fixture_backed", "runtime": "cpu", "defect_type": label},
    )


def _fixture_audio(ev: EvidenceArtifact, fallback_reason: Optional[str]) -> MediaInference:
    if fallback_reason:
        _stats.fixture_fallbacks += 1
    score = float(ev.labels.get("vibration_anomaly_score", 0.0) or 0.0)
    label = str(ev.labels.get("anomaly_type", "unknown"))
    return MediaInference(
        modality="audio",
        backend="fixture",
        class_name="quality" if score > 0.5 else "unclassified",
        score=min(max(score, 0.0), 1.0) if score else 0.5,
        label=label,
        fallback_reason=fallback_reason,
        metrics={"model": "fixture_backed", "runtime": "cpu", "anomaly_type": label},
    )


def _try_image_onnx(ev: EvidenceArtifact, model_path: Path) -> Optional[MediaInference]:
    if not model_path.is_file() or not ev.content_ref:
        return None
    try:
        import numpy as np
        import onnxruntime as ort
        from PIL import Image

        session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        input_meta = session.get_inputs()[0]
        shape = list(input_meta.shape)
        channels_first = True
        height = width = 224
        if len(shape) == 4:
            if shape[1] in (1, 3):
                channels_first = True
                height = shape[2] if isinstance(shape[2], int) else 224
                width = shape[3] if isinstance(shape[3], int) else 224
            else:
                channels_first = False
                height = shape[1] if isinstance(shape[1], int) else 224
                width = shape[2] if isinstance(shape[2], int) else 224

        image = Image.open(ev.content_ref).convert("RGB").resize((int(width), int(height)))
        arr = np.asarray(image, dtype=np.float32) / 255.0
        if channels_first:
            arr = np.transpose(arr, (2, 0, 1))
        arr = np.expand_dims(arr, axis=0)

        outputs = session.run(None, {input_meta.name: arr})
        _stats.onnx_calls += 1
        flat = np.asarray(outputs[0], dtype=np.float32).ravel()
        score = float(flat.max()) if flat.size else 0.0
        return MediaInference(
            modality="image",
            backend="onnx",
            class_name="quality" if score > 0.5 else "unclassified",
            score=min(max(score, 0.0), 1.0),
            label="onnx_image_class",
            used_model=True,
            metrics={"model": str(model_path), "runtime": "onnxruntime-cpu", "backend": "onnx"},
        )
    except Exception as exc:
        _stats.errors += 1
        return _fixture_image(ev, f"onnx image inference failed: {str(exc)[:120]}")


def _try_audio_onnx(ev: EvidenceArtifact, model_path: Path) -> Optional[MediaInference]:
    if not model_path.is_file() or not ev.content_ref:
        return None
    if Path(ev.content_ref).suffix.lower() != ".wav":
        return _fixture_audio(ev, "audio ONNX adapter requires WAV PCM input")
    try:
        import numpy as np
        import onnxruntime as ort

        with wave.open(ev.content_ref, "rb") as wav:
            frames = wav.readframes(wav.getnframes())
            channels = wav.getnchannels()
            samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
            if channels > 1:
                samples = samples.reshape(-1, channels).mean(axis=1)

        session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        input_meta = session.get_inputs()[0]
        shape = list(input_meta.shape)
        target_len = shape[-1] if shape and isinstance(shape[-1], int) and shape[-1] > 0 else len(samples)
        if len(samples) < target_len:
            samples = np.pad(samples, (0, target_len - len(samples)))
        elif len(samples) > target_len:
            samples = samples[:target_len]

        arr = samples.astype(np.float32)
        if len(shape) == 2:
            arr = np.expand_dims(arr, axis=0)
        elif len(shape) == 3:
            arr = np.expand_dims(np.expand_dims(arr, axis=0), axis=0)

        outputs = session.run(None, {input_meta.name: arr})
        _stats.onnx_calls += 1
        flat = np.asarray(outputs[0], dtype=np.float32).ravel()
        score = float(flat.max()) if flat.size else 0.0
        return MediaInference(
            modality="audio",
            backend="onnx",
            class_name="quality" if score > 0.5 else "unclassified",
            score=min(max(score, 0.0), 1.0),
            label="onnx_audio_class",
            used_model=True,
            metrics={"model": str(model_path), "runtime": "onnxruntime-cpu", "backend": "onnx"},
        )
    except Exception as exc:
        _stats.errors += 1
        return _fixture_audio(ev, f"onnx audio inference failed: {str(exc)[:120]}")
