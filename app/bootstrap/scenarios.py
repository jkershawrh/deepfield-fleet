"""Scenario loader — reads synthetic fixture scenarios for the lab."""

import logging
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

_SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "scenarios"
_FACTORY_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"


def list_scenarios() -> list[dict]:
    scenarios = []

    if _FACTORY_DIR.exists():
        scenarios.append({
            "id": "factory-bearing",
            "name": "Factory Floor Monitoring",
            "domain": "manufacturing",
            "description": "Vibration drift, thermal increase, surface defect, and maintenance notes from a factory bearing failure.",
            "signal_count": 6,
            "modalities": ["metric", "log", "document", "image", "audio"],
        })

    if not _SCENARIOS_DIR.exists():
        return scenarios

    for manifest_path in sorted(_SCENARIOS_DIR.glob("*/manifest.yaml")):
        try:
            data = yaml.safe_load(manifest_path.read_text())
            scenarios.append({
                "id": data.get("id", manifest_path.parent.name),
                "name": data.get("name", manifest_path.parent.name),
                "domain": data.get("domain", "unknown"),
                "description": data.get("description", ""),
                "signal_count": data.get("signal_count", 0),
                "modalities": data.get("modalities", []),
                "profile": data.get("profile"),
            })
        except Exception as e:
            logger.warning("Failed to load scenario %s: %s", manifest_path, str(e)[:100])

    return scenarios


def load_scenario(scenario_id: str) -> tuple[list[dict], Optional[str]]:
    if scenario_id == "factory-bearing":
        from app.connectors.file import FileConnector
        samples = []
        for csv_file in sorted(_FACTORY_DIR.glob("metrics/*.csv")):
            c = FileConnector()
            c.connect({"path": str(csv_file)})
            samples.extend(c.sample(100))
        log_file = _FACTORY_DIR / "logs" / "maintenance.log"
        if log_file.exists():
            c = FileConnector()
            c.connect({"path": str(log_file)})
            samples.extend(c.sample(50))
        return samples, None

    scenario_dir = _SCENARIOS_DIR / scenario_id
    if not scenario_dir.exists():
        for d in _SCENARIOS_DIR.iterdir():
            manifest = d / "manifest.yaml"
            if manifest.exists():
                data = yaml.safe_load(manifest.read_text())
                if data.get("id") == scenario_id:
                    scenario_dir = d
                    break

    if not scenario_dir.exists():
        return [], None

    manifest_path = scenario_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text()) if manifest_path.exists() else {}
    profile_id = manifest.get("profile")

    from app.connectors.file import FileConnector
    samples = []
    for data_file in sorted(scenario_dir.glob("*.csv")):
        c = FileConnector()
        c.connect({"path": str(data_file)})
        samples.extend(c.sample(200))
    for log_file in sorted(scenario_dir.glob("*.log")):
        c = FileConnector()
        c.connect({"path": str(log_file)})
        samples.extend(c.sample(50))

    return samples, profile_id
