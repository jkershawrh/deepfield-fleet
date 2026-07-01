"""Verification service — compare post-action observations to expected outcomes."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.db import enqueue_write
from app.domain.models import VerificationRecord


class VerificationService:
    def __init__(self):
        self._records: dict[UUID, VerificationRecord] = {}

    def create(
        self,
        action_id: UUID,
        verification_type: str,
        expected_outcome: dict,
    ) -> VerificationRecord:
        record = VerificationRecord(
            action_id=action_id,
            verification_type=verification_type,
            expected_outcome=expected_outcome,
        )
        self._records[record.verification_id] = record
        enqueue_write("verification_records", record.model_dump(mode="json"))
        return record

    def run(
        self,
        verification_id: UUID,
        observed_outcome: dict,
    ) -> VerificationRecord:
        record = self._records.get(verification_id)
        if record is None:
            return record
        record.observed_outcome = observed_outcome
        record.completed_at = datetime.now(timezone.utc)

        passed = self._evaluate(record.expected_outcome, observed_outcome)
        record.status = "passed" if passed else "failed"
        record.confidence = 0.85 if passed else 0.3
        return record

    def get(self, verification_id: UUID) -> Optional[VerificationRecord]:
        return self._records.get(verification_id)

    def list_all(self) -> list[VerificationRecord]:
        return list(self._records.values())

    def _evaluate(self, expected: dict, observed: dict) -> bool:
        for key, threshold in expected.items():
            if key.endswith("_below"):
                metric_name = key[:-6]
                observed_val = observed.get(metric_name)
                if observed_val is not None and observed_val > threshold:
                    return False
            elif key.endswith("_above"):
                metric_name = key[:-6]
                observed_val = observed.get(metric_name)
                if observed_val is not None and observed_val < threshold:
                    return False
            else:
                observed_val = observed.get(key)
                if observed_val is not None and observed_val != threshold:
                    return False
        return True
