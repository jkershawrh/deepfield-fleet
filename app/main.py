"""DeepField Multimodal — FastAPI application."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.db import close_db, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("DeepField Multimodal started")
    yield
    await close_db()
    logger.info("DeepField Multimodal stopped")


app = FastAPI(
    title="DeepField Multimodal",
    description="Agentic Signal Classification Engine — deterministic nanoagents, rule-backed microagents, LLM macroagents",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from app.api.multimodal import router as multimodal_router
from app.api.baseline import router as baseline_router
from app.api.classification import router as classification_router
from app.api.agent_loop import router as agent_loop_router
from app.api.demo import router as demo_router
from app.api.sse import router as sse_router
from app.api.bootstrap import router as bootstrap_router

app.include_router(multimodal_router)
app.include_router(baseline_router)
app.include_router(classification_router)
app.include_router(agent_loop_router)
app.include_router(demo_router)
app.include_router(sse_router)
app.include_router(bootstrap_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "deepfield-multimodal"}


_STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"

if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa_fallback(request: Request, path: str):
        file_path = _STATIC_DIR / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_STATIC_DIR / "index.html")
