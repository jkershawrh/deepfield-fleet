"""Inference client — OpenAI-compatible calls to LiteLLM or local models.

Configured via environment variables:
  LITELLM_API_BASE  — e.g., https://litellm.example.com
  LITELLM_API_KEY   — API key for the LiteLLM proxy
  LITELLM_MODEL_MICRO — model name for micro tier (default: granite-3-2-8b-instruct-cpu)
  LITELLM_MODEL_MACRO — model name for macro tier (default: granite-3-2-8b-instruct-cpu)

When LITELLM_API_BASE is not set, returns None (agents fall back to rule-based).
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)


@dataclass
class InferenceResult:
    model: str
    output: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    error: Optional[str] = None


@dataclass
class InferenceStats:
    total_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_latency_ms: float = 0.0
    errors: int = 0
    calls: list = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_calls, 1)

    @property
    def avg_tokens_per_sec(self) -> float:
        if self.total_latency_ms == 0:
            return 0.0
        return self.total_tokens_out / (self.total_latency_ms / 1000)

    def record(self, result: InferenceResult):
        self.total_calls += 1
        self.total_tokens_in += result.tokens_in
        self.total_tokens_out += result.tokens_out
        self.total_latency_ms += result.latency_ms
        if result.error:
            self.errors += 1
        self.calls.append({
            "model": result.model,
            "tokens_in": result.tokens_in,
            "tokens_out": result.tokens_out,
            "latency_ms": round(result.latency_ms, 1),
            "error": result.error,
        })

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_latency_ms": round(self.total_latency_ms, 1),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "avg_tokens_per_sec": round(self.avg_tokens_per_sec, 1),
            "errors": self.errors,
            "recent_calls": self.calls[-10:],
        }


_stats = InferenceStats()


def get_inference_stats() -> InferenceStats:
    return _stats


def reset_inference_stats():
    global _stats
    _stats = InferenceStats()


def is_inference_available() -> bool:
    return bool(os.getenv("LITELLM_API_BASE"))


def get_inference_config() -> dict:
    base = os.getenv("LITELLM_API_BASE", "")
    return {
        "available": bool(base),
        "api_base": base,
        "model_micro": os.getenv("LITELLM_MODEL_MICRO", "granite-3-2-8b-instruct-cpu"),
        "model_macro": os.getenv("LITELLM_MODEL_MACRO", "granite-3-2-8b-instruct-cpu"),
        "has_key": bool(os.getenv("LITELLM_API_KEY")),
    }


def infer(
    prompt: str,
    system_prompt: str = "You are a classification agent. Respond concisely.",
    tier: str = "micro",
    max_tokens: int = 200,
) -> Optional[InferenceResult]:
    base = os.getenv("LITELLM_API_BASE")
    if not base:
        return None

    key = os.getenv("LITELLM_API_KEY", "")
    model_env = "LITELLM_MODEL_MICRO" if tier == "micro" else "LITELLM_MODEL_MACRO"
    model = os.getenv(model_env, "granite-3-2-8b-instruct-cpu")

    url = f"{base.rstrip('/')}/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    start = time.monotonic()
    try:
        req = Request(url, data=payload, headers=headers, method="POST")
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())

        latency = (time.monotonic() - start) * 1000
        output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})
        tokens_in = usage.get("prompt_tokens", 0)
        tokens_out = usage.get("completion_tokens", 0)

        result = InferenceResult(
            model=model, output=output,
            tokens_in=tokens_in, tokens_out=tokens_out,
            latency_ms=latency,
        )
        _stats.record(result)
        return result

    except (URLError, OSError, json.JSONDecodeError, KeyError) as e:
        latency = (time.monotonic() - start) * 1000
        result = InferenceResult(
            model=model, output="", tokens_in=0, tokens_out=0,
            latency_ms=latency, error=str(e)[:200],
        )
        _stats.record(result)
        logger.warning("Inference failed (%s): %s", model, str(e)[:200])
        return result
