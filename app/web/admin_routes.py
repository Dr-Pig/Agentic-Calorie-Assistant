from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..logging import get_full_trace, get_trace_summaries, read_recent_events

router = APIRouter()


@router.get("/logs")
async def logs(limit: int = 20) -> dict:
    return {"items": read_recent_events(limit=limit)}


@router.get("/admin/traces")
async def list_admin_traces(limit: int = 100) -> dict:
    return get_trace_summaries(limit=limit)


@router.get("/admin/trace/{request_id}")
async def get_admin_trace(request_id: str) -> dict:
    trace = get_full_trace(request_id)
    if not trace:
        return JSONResponse(status_code=404, content={"error": "Trace not found"})
    return trace
