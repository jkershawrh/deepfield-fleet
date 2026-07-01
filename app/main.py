"""DeepField Multimodal — FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    description="Multimodal agent pack for enterprise signal classification and action loops",
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

app.include_router(multimodal_router)
app.include_router(baseline_router)
app.include_router(classification_router)
app.include_router(agent_loop_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "deepfield-multimodal"}
