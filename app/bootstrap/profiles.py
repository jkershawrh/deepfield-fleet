"""Pre-built profiles — load YAML profile configs for common use cases."""

import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

_PROFILES_DIR = Path(__file__).resolve().parents[2] / "config" / "profiles"


def list_profiles() -> list[dict]:
    profiles = []
    if not _PROFILES_DIR.exists():
        return profiles
    for yaml_file in sorted(_PROFILES_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(yaml_file.read_text())
            profiles.append({
                "id": yaml_file.stem,
                "name": data.get("name", yaml_file.stem),
                "domain": data.get("domain", "unknown"),
                "description": data.get("description", ""),
                "connectors": data.get("connectors", []),
            })
        except Exception as e:
            logger.warning("Failed to load profile %s: %s", yaml_file.name, str(e)[:100])
    return profiles


def load_profile(profile_id: str) -> Optional[dict]:
    path = _PROFILES_DIR / f"{profile_id}.yaml"
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text())
    except Exception as e:
        logger.warning("Failed to load profile %s: %s", profile_id, str(e)[:100])
        return None
