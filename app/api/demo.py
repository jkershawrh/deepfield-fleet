"""Demo API — powers the Hero's Journey frontend story."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter

from app.agent_loop.loop import AgentLoop
from app.baseline.compiler import BaselineCompiler
from app.domain.models import BaselineProfile, EvidenceArtifact
from app.multimodal.normalizer import normalize_fixture
from app.multimodal.storage import get_evidence_store

router = APIRouter(prefix="/api/v1/demo", tags=["demo"])

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "multimodal" / "factory-line-bearing-failure"

_evidence: list[EvidenceArtifact] = []
_baseline: Optional[BaselineProfile] = None


@router.post("/ingest")
async def ingest_fixture():
    global _evidence
    _evidence = normalize_fixture(FIXTURE_DIR / "manifest.yaml")
    store = get_evidence_store()
    for e in _evidence:
        store.store(e)
    return [e.model_dump(mode="json") for e in _evidence]


@router.post("/baseline")
async def build_baseline():
    global _baseline
    if not _evidence:
        await ingest_fixture()
    compiler = BaselineCompiler()
    _baseline = compiler.compile(
        evidence=_evidence,
        scope={"scope_type": "site", "scope_id": "factory-line-01"},
    )
    _baseline.status = "active"
    return _baseline.model_dump(mode="json")


@router.post("/classify")
async def run_classification():
    if not _evidence:
        await ingest_fixture()
    if not _baseline:
        await build_baseline()
    from app.classification.engine import ClassificationEngine
    engine = ClassificationEngine()
    records = engine.classify(_evidence, _baseline)
    return [r.model_dump(mode="json") for r in records]


@router.post("/loop")
async def run_full_loop():
    if not _evidence:
        await ingest_fixture()
    if not _baseline:
        await build_baseline()
    loop = AgentLoop()
    result = loop.run(_evidence, _baseline)
    return {
        "classifications": [c.model_dump(mode="json") for c in result["classifications"]],
        "actions": [a.model_dump(mode="json") for a in result["actions"]],
        "verifications": [v.model_dump(mode="json") for v in result["verifications"]],
        "learning_proposals": [p.model_dump(mode="json") for p in result["learning_proposals"]],
    }
