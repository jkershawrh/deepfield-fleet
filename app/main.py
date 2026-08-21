"""DeepField Multimodal: FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import require_api_token
from app.db import close_db, init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("deepfield-fleet service started")
    yield
    await close_db()
    logger.info("deepfield-fleet service stopped")


app = FastAPI(
    title="DeepField Fleet: Governed Fleet Signal Intelligence",
    description=(
        "Canonical DeepField observation, finding, and forecast producer; "
        "consequential recommendations are advisory CloudEvents for GCL"
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# Starlette echoes the caller's own Origin back when allow_origins=["*"] is
# combined with allow_credentials=True, rather than sending a literal "*".
# That let any site on the internet make credentialed cross-origin requests
# and read the responses. Origins are now named explicitly, and credentials
# stay off because the API authenticates with a bearer token, not a cookie.
_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def _cors_origins() -> list[str]:
    configured = os.environ.get("DEEPFIELD_CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in configured.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


from app.api.multimodal import router as multimodal_router
from app.api.baseline import router as baseline_router
from app.api.classification import router as classification_router
from app.api.agent_loop import router as agent_loop_router
from app.api.demo import router as demo_router
from app.api.sse import router as sse_router
from app.api.bootstrap import router as bootstrap_router
from app.api.benchmark import router as benchmark_router
from app.api.ecosystem import router as ecosystem_router

app.include_router(multimodal_router, dependencies=[Depends(require_api_token)])
app.include_router(baseline_router, dependencies=[Depends(require_api_token)])
app.include_router(classification_router, dependencies=[Depends(require_api_token)])
app.include_router(agent_loop_router, dependencies=[Depends(require_api_token)])
app.include_router(demo_router, dependencies=[Depends(require_api_token)])
app.include_router(sse_router, dependencies=[Depends(require_api_token)])
app.include_router(bootstrap_router, dependencies=[Depends(require_api_token)])
app.include_router(benchmark_router, dependencies=[Depends(require_api_token)])
app.include_router(ecosystem_router, dependencies=[Depends(require_api_token)])

from app.api.fleet_demo import router as fleet_demo_router
app.include_router(fleet_demo_router, dependencies=[Depends(require_api_token)])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "deepfield-fleet"}


_STATIC_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"

if _STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    async def spa_fallback(request: Request, path: str):
        file_path = _STATIC_DIR / path
        if file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_STATIC_DIR / "index.html")
