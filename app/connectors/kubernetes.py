"""Kubernetes API connector — reads pod status, events, and node health.

READ-ONLY. Watch/Get only. Never apply/delete/patch/create.
Uses service account token when running in-cluster.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Iterator, Optional
from urllib.request import Request, urlopen

from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class KubernetesConnector(BaseConnector):
    name = "kubernetes"

    def __init__(self):
        self._api_url = ""
        self._token = ""
        self._namespaces: list[str] = []
        self._exclude_ns: list[str] = []
        self._connected = False

    def connect(self, config: dict) -> bool:
        self._api_url = config.get("api_url", "").rstrip("/")
        if not self._api_url:
            self._api_url = self._detect_in_cluster()
        self._token = config.get("token", "") or self._load_sa_token()
        self._namespaces = config.get("namespaces", [])
        self._exclude_ns = config.get("exclude_namespaces", [
            "openshift-*", "kube-*", "openshift",
        ])

        try:
            data = self._get("/api/v1/namespaces?limit=1")
            self._connected = data is not None
            if self._connected:
                logger.info("Kubernetes connected: %s", self._api_url)
            return self._connected
        except Exception as e:
            logger.warning("Kubernetes connect failed: %s", str(e)[:100])
            return False

    def sample(self, count: int = 200) -> list[dict]:
        records = []
        records.extend(self._sample_pods(count // 3))
        records.extend(self._sample_events(count // 3))
        records.extend(self._sample_nodes(count // 3))
        return records[:count]

    def stream(self) -> Iterator[dict]:
        yield from self.sample(count=500)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "connected": self._connected,
            "api_url": self._api_url,
            "namespaces": self._namespaces or ["all (filtered)"],
        }

    def _sample_pods(self, count: int) -> list[dict]:
        records = []
        data = self._get("/api/v1/pods?limit=500")
        if not data:
            return records
        for item in data.get("items", []):
            ns = item.get("metadata", {}).get("namespace", "")
            if not self._ns_allowed(ns):
                continue
            name = item.get("metadata", {}).get("name", "")
            status = item.get("status", {})
            phase = status.get("phase", "Unknown")
            restarts = 0
            reason = ""
            for cs in status.get("containerStatuses", []):
                restarts += cs.get("restartCount", 0)
                waiting = cs.get("state", {}).get("waiting", {})
                if waiting.get("reason"):
                    reason = waiting["reason"]
            records.append({
                "type": "pod",
                "namespace": ns,
                "name": name,
                "phase": phase,
                "restarts": restarts,
                "reason": reason,
                "node": item.get("spec", {}).get("nodeName", ""),
                "timestamp": item.get("metadata", {}).get("creationTimestamp", ""),
            })
            if len(records) >= count:
                break
        return records

    def _sample_events(self, count: int) -> list[dict]:
        records = []
        data = self._get("/api/v1/events?fieldSelector=type=Warning&limit=200")
        if not data:
            return records
        for item in data.get("items", []):
            ns = item.get("metadata", {}).get("namespace", "")
            if not self._ns_allowed(ns):
                continue
            involved = item.get("involvedObject", {})
            records.append({
                "type": "event",
                "namespace": ns,
                "name": involved.get("name", ""),
                "kind": involved.get("kind", ""),
                "reason": item.get("reason", ""),
                "message": item.get("message", "")[:200],
                "count": item.get("count", 1),
                "timestamp": item.get("lastTimestamp", item.get("metadata", {}).get("creationTimestamp", "")),
            })
            if len(records) >= count:
                break
        return records

    def _sample_nodes(self, count: int) -> list[dict]:
        records = []
        data = self._get("/api/v1/nodes")
        if not data:
            return records
        for item in data.get("items", []):
            name = item.get("metadata", {}).get("name", "")
            conditions = {c["type"]: c for c in item.get("status", {}).get("conditions", [])}
            ready = conditions.get("Ready", {}).get("status", "Unknown")
            memory_pressure = conditions.get("MemoryPressure", {}).get("status", "False")
            disk_pressure = conditions.get("DiskPressure", {}).get("status", "False")
            records.append({
                "type": "node",
                "name": name,
                "ready": ready,
                "memory_pressure": memory_pressure,
                "disk_pressure": disk_pressure,
                "os": item.get("status", {}).get("nodeInfo", {}).get("osImage", ""),
                "kubelet": item.get("status", {}).get("nodeInfo", {}).get("kubeletVersion", ""),
            })
            if len(records) >= count:
                break
        return records

    def _ns_allowed(self, ns: str) -> bool:
        from fnmatch import fnmatch
        if any(fnmatch(ns, pat) for pat in self._exclude_ns):
            return False
        if not self._namespaces:
            return True
        return any(fnmatch(ns, pat) for pat in self._namespaces)

    def _get(self, path: str) -> Optional[dict]:
        url = f"{self._api_url}{path}"
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            req = Request(url, headers=headers)
            # In-cluster certs
            import ssl
            ctx = ssl.create_default_context()
            ca_path = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"
            if os.path.exists(ca_path):
                ctx.load_verify_locations(ca_path)
            else:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
            with urlopen(req, timeout=15, context=ctx) as resp:
                return json.loads(resp.read())
        except Exception as e:
            logger.debug("K8s GET %s: %s", path, str(e)[:100])
            return None

    @staticmethod
    def _load_sa_token() -> str:
        try:
            with open("/var/run/secrets/kubernetes.io/serviceaccount/token") as f:
                return f.read().strip()
        except Exception:
            return ""

    @staticmethod
    def _detect_in_cluster() -> str:
        host = os.getenv("KUBERNETES_SERVICE_HOST", "")
        port = os.getenv("KUBERNETES_SERVICE_PORT", "443")
        if host:
            return f"https://{host}:{port}"
        return ""
