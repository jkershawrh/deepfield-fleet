"""Learning service — propose, accept, reject learning proposals. Never silent apply."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.db import enqueue_write
from app.domain.models import LearningProposal


class LearningService:
    def __init__(self):
        self._proposals: dict[UUID, LearningProposal] = {}

    def propose(
        self,
        source_type: str,
        source_id: UUID,
        proposal_type: str,
        target_scope: dict,
        before: dict,
        after: dict,
        rationale: str,
        confidence: float,
    ) -> LearningProposal:
        proposal = LearningProposal(
            source_type=source_type,
            source_id=source_id,
            proposal_type=proposal_type,
            target_scope=target_scope,
            before=before,
            after=after,
            rationale=rationale,
            confidence=confidence,
        )
        self._proposals[proposal.proposal_id] = proposal
        enqueue_write("learning_proposals", proposal.model_dump(mode="json"))
        return proposal

    def accept(self, proposal_id: UUID) -> LearningProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal and proposal.status == "proposed":
            proposal.status = "accepted"
            proposal.reviewed_at = datetime.now(timezone.utc)
        return proposal

    def reject(self, proposal_id: UUID) -> LearningProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal and proposal.status == "proposed":
            proposal.status = "rejected"
            proposal.reviewed_at = datetime.now(timezone.utc)
        return proposal

    def get(self, proposal_id: UUID) -> Optional[LearningProposal]:
        return self._proposals.get(proposal_id)

    def list_all(self, status: Optional[str] = None) -> list[LearningProposal]:
        result = list(self._proposals.values())
        if status:
            result = [p for p in result if p.status == status]
        return result
