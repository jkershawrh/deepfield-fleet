"""Agent loop API routes — actions, verifications, learning proposals."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent_loop.actions import ActionManager
from app.agent_loop.learning import LearningService
from app.agent_loop.verification import VerificationService
from app.domain.models import AgentAction, LearningProposal, VerificationRecord

router = APIRouter(prefix="/api/v1/agent-loop", tags=["agent-loop"])

_action_mgr: Optional[ActionManager] = None
_verification_svc: Optional[VerificationService] = None
_learning_svc: Optional[LearningService] = None


def _get_actions() -> ActionManager:
    global _action_mgr
    if _action_mgr is None:
        _action_mgr = ActionManager()
    return _action_mgr


def _get_verification() -> VerificationService:
    global _verification_svc
    if _verification_svc is None:
        _verification_svc = VerificationService()
    return _verification_svc


def _get_learning() -> LearningService:
    global _learning_svc
    if _learning_svc is None:
        _learning_svc = LearningService()
    return _learning_svc


class ActionRequest(BaseModel):
    action_type: str
    payload: dict = {}
    created_by_agent: str = "api"
    incident_id: Optional[UUID] = None
    finding_id: Optional[UUID] = None


class VerifyRequest(BaseModel):
    verification_type: str
    expected_outcome: dict = {}


class ObservedRequest(BaseModel):
    observed_outcome: dict = {}


class LearnRequest(BaseModel):
    source_type: str
    source_id: UUID
    proposal_type: str
    target_scope: dict = {}
    before: dict = {}
    after: dict = {}
    rationale: str = ""
    confidence: float = 0.5


# --- Actions ---

@router.post("/actions", response_model=AgentAction)
async def propose_action(request: ActionRequest):
    return _get_actions().propose(
        action_type=request.action_type,
        payload=request.payload,
        created_by_agent=request.created_by_agent,
        incident_id=request.incident_id,
        finding_id=request.finding_id,
    )


@router.get("/actions", response_model=list[AgentAction])
async def list_actions(status: Optional[str] = None):
    return _get_actions().list_actions(status=status)


@router.post("/actions/{action_id}/approve", response_model=AgentAction)
async def approve_action(action_id: UUID):
    action = _get_actions().approve(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/actions/{action_id}/execute", response_model=AgentAction)
async def execute_action(action_id: UUID):
    action = _get_actions().execute(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.post("/actions/{action_id}/verify", response_model=VerificationRecord)
async def create_verification(action_id: UUID, request: VerifyRequest):
    return _get_verification().create(
        action_id=action_id,
        verification_type=request.verification_type,
        expected_outcome=request.expected_outcome,
    )


# --- Verifications ---

@router.get("/verifications", response_model=list[VerificationRecord])
async def list_verifications():
    return _get_verification().list_all()


# --- Learning proposals ---

@router.get("/learning-proposals", response_model=list[LearningProposal])
async def list_proposals(status: Optional[str] = None):
    return _get_learning().list_all(status=status)


@router.post("/learning-proposals", response_model=LearningProposal)
async def create_proposal(request: LearnRequest):
    return _get_learning().propose(
        source_type=request.source_type,
        source_id=request.source_id,
        proposal_type=request.proposal_type,
        target_scope=request.target_scope,
        before=request.before,
        after=request.after,
        rationale=request.rationale,
        confidence=request.confidence,
    )


@router.post("/learning-proposals/{proposal_id}/accept", response_model=LearningProposal)
async def accept_proposal(proposal_id: UUID):
    proposal = _get_learning().accept(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.post("/learning-proposals/{proposal_id}/reject", response_model=LearningProposal)
async def reject_proposal(proposal_id: UUID):
    proposal = _get_learning().reject(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal
