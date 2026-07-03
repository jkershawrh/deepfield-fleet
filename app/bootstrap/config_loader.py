"""Config loader — reads YAML configs with fallback to defaults, then hardcoded.

Looks for configs in this order:
1. config/{path}          — user/bootstrap-generated config
2. config/defaults/{path} — built-in defaults
3. Hardcoded fallback     — original values (always works, no files needed)
"""

import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_DEFAULTS_DIR = _CONFIG_DIR / "defaults"


def _find_config(relative_path: str) -> Optional[Path]:
    user_path = _CONFIG_DIR / relative_path
    if user_path.exists():
        return user_path
    default_path = _DEFAULTS_DIR / relative_path
    if default_path.exists():
        return default_path
    return None


def load_yaml(relative_path: str) -> Optional[dict]:
    path = _find_config(relative_path)
    if path is None:
        return None
    try:
        return yaml.safe_load(path.read_text())
    except Exception as e:
        logger.warning("Failed to load config %s: %s", relative_path, str(e)[:100])
        return None


def load_taxonomies() -> dict:
    data = load_yaml("taxonomies/general.yaml")
    if data:
        return {k: v for k, v in data.items() if isinstance(v, list)}
    from app.classification.taxonomy import ALL_TAXONOMIES
    return dict(ALL_TAXONOMIES)


def load_pipeline_config() -> dict:
    data = load_yaml("pipeline.yaml")
    if data:
        return data
    return {
        "nano_agents": [
            "app.nanoagents.baseline_distance",
            "app.nanoagents.metric_drift",
            "app.nanoagents.log_pattern",
            "app.nanoagents.document_heuristic",
            "app.nanoagents.image_metadata",
            "app.nanoagents.audio_energy",
            "app.nanoagents.evidence_gate",
        ],
        "micro_agents": [],
        "macro_agents": [],
    }


def load_nano_agent_list() -> list[str]:
    config = load_pipeline_config()
    return config.get("nano_agents", [])


def save_config(relative_path: str, data: dict):
    path = _CONFIG_DIR / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    logger.info("Config saved: %s", path)
