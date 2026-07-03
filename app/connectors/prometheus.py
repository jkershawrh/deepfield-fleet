"""Prometheus connector — queries metrics from OpenShift monitoring stack.

Supports in-cluster Thanos (https://thanos-querier.openshift-monitoring.svc:9091)
or external Prometheus endpoints. Uses service account token when available.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Iterator
from urllib.request import Request, urlopen
from urllib.error import URLError

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class PrometheusConnector(BaseConnector):
    name = "prometheus"

    def __init__(self):
        self._endpoint = ""
        self._token = ""
        self._queries: list[str] = []
        self._connected = False

    def connect(self, config: dict) -> bool:
        self._endpoint = config.get("endpoint", "").rstrip("/")
        self._token = config.get("token", "") or self._load_sa_token()
        self._queries = config.get("queries", [
            'up',
            'kube_pod_status_phase{phase!="Running"}',
            'kube_pod_container_status_restarts_total',
            'node_cpu_seconds_total',
        ])

        try:
            data = self._get("/api/v1/status/config")
            self._connected = data is not None
            if self._connected:
                logger.info("Prometheus connected: %s", self._endpoint)
            return self._connected
        except Exception as e:
            logger.warning("Prometheus connect failed: %s", str(e)[:100])
            return False

    def sample(self, count: int = 200) -> list[dict]:
        records = []
        for query in self._queries:
            data = self._get("/api/v1/query", {"query": query})
            if not data:
                continue
            for result in data.get("data", {}).get("result", []):
                metric = result.get("metric", {})
                value = result.get("value", [None, None])
                record = {
                    "__name__": metric.get("__name__", query.split("{")[0]),
                    "namespace": metric.get("namespace", ""),
                    "pod": metric.get("pod", ""),
                    "instance": metric.get("instance", ""),
                    "job": metric.get("job", ""),
                    "timestamp": value[0] if value[0] else "",
                    "value": value[1] if len(value) > 1 else "",
                }
                record.update({k: v for k, v in metric.items()
                              if k not in ("__name__", "namespace", "pod", "instance", "job")})
                records.append(record)
                if len(records) >= count:
                    return records
        return records

    def stream(self) -> Iterator[dict]:
        yield from self.sample(count=500)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "connected": self._connected,
            "endpoint": self._endpoint,
            "queries": self._queries,
        }

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self._endpoint}{path}"
        if params:
            query_string = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{url}?{query_string}"
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.debug("Prometheus GET %s: %s", path, str(e)[:100])
            return None

    @staticmethod
    def _load_sa_token() -> str:
        try:
            with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
                return f.read().strip()
        except Exception:
            return ""
