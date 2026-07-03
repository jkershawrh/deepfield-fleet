"""File connector — reads CSV, JSON, or log files."""

import csv
import json
import logging
from pathlib import Path
from typing import Iterator

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class FileConnector(BaseConnector):
    name = "file"

    def __init__(self):
        self._path: Path | None = None
        self._records: list[dict] = []

    def connect(self, config: dict) -> bool:
        path = Path(config.get("path", ""))
        if not path.exists():
            logger.warning("File not found: %s", path)
            return False
        self._path = path
        return True

    def sample(self, count: int = 200) -> list[dict]:
        if not self._path:
            return []
        suffix = self._path.suffix.lower()
        if suffix == ".csv":
            return self._read_csv(count)
        elif suffix == ".json":
            return self._read_json(count)
        elif suffix in (".log", ".txt"):
            return self._read_log(count)
        elif suffix in (".yaml", ".yml"):
            return self._read_yaml(count)
        else:
            return self._read_log(count)

    def stream(self) -> Iterator[dict]:
        yield from self.sample(count=10000)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "connected": self._path is not None,
            "path": str(self._path) if self._path else None,
            "format": self._path.suffix if self._path else None,
            "records_sampled": len(self._records),
        }

    def _read_csv(self, count: int) -> list[dict]:
        records = []
        with open(self._path) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= count:
                    break
                records.append(dict(row))
        self._records = records
        return records

    def _read_json(self, count: int) -> list[dict]:
        with open(self._path) as f:
            data = json.load(f)
        if isinstance(data, list):
            self._records = data[:count]
        elif isinstance(data, dict):
            self._records = [data]
        else:
            self._records = []
        return self._records

    def _read_log(self, count: int) -> list[dict]:
        records = []
        with open(self._path) as f:
            for i, line in enumerate(f):
                if i >= count:
                    break
                line = line.strip()
                if line:
                    records.append({"line_number": i + 1, "text": line})
        self._records = records
        return records

    def _read_yaml(self, count: int) -> list[dict]:
        import yaml
        with open(self._path) as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            self._records = data[:count]
        elif isinstance(data, dict):
            self._records = [data]
        else:
            self._records = []
        return self._records
