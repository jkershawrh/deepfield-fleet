"""Baseline profile store — in-memory with optional DB persistence."""

from typing import Optional
from uuid import UUID

from app.db import enqueue_write
from app.domain.models import BaselineProfile


class BaselineProfileStore:
    def __init__(self):
        self._profiles: dict[UUID, BaselineProfile] = {}

    def save(self, profile: BaselineProfile) -> None:
        self._profiles[profile.baseline_id] = profile
        enqueue_write("baseline_profiles", profile.model_dump(mode="json"))

    def get(self, baseline_id: UUID) -> Optional[BaselineProfile]:
        return self._profiles.get(baseline_id)

    def list_profiles(
        self,
        scope_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list[BaselineProfile]:
        result = list(self._profiles.values())
        if scope_type:
            result = [p for p in result if p.scope_type == scope_type]
        if status:
            result = [p for p in result if p.status == status]
        return result

    def activate(self, baseline_id: UUID) -> None:
        profile = self._profiles.get(baseline_id)
        if profile is None:
            return
        for p in self._profiles.values():
            if (
                p.baseline_id != baseline_id
                and p.scope_type == profile.scope_type
                and p.scope_id == profile.scope_id
                and p.modality == profile.modality
                and p.status == "active"
            ):
                p.status = "archived"
        profile.status = "active"

    def get_active(
        self, scope_type: str, scope_id: str, modality: str,
    ) -> Optional[BaselineProfile]:
        for p in self._profiles.values():
            if (
                p.scope_type == scope_type
                and p.scope_id == scope_id
                and p.modality == modality
                and p.status == "active"
            ):
                return p
        return None
