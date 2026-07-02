"""Server-Sent Events — pushes demo state to frontend every 500ms."""

import asyncio
import json

from fastapi import APIRouter
from starlette.responses import StreamingResponse

router = APIRouter(tags=["stream"])

_demo_state: dict = {}


def get_demo_state() -> dict:
    return _demo_state


def set_demo_state(state: dict) -> None:
    global _demo_state
    _demo_state = state


async def _event_stream():
    while True:
        state = _demo_state if _demo_state else {"status": "idle"}
        data = json.dumps(state, default=str)
        yield f"event: demo\ndata: {data}\n\n"
        await asyncio.sleep(0.5)


@router.get("/api/v1/stream")
async def stream():
    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
