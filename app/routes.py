from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from . import CANARY_VERSION, SCHEMA_SIGNATURE
from .logging import read_recent_events
from .providers.builderspace_adapter import BuilderSpaceAdapter
from .schemas import EstimateRequest
from .search.tavily_adapter import TavilyAdapter
from .usecases.text_meal import record_error, record_success, run_text_meal_canary

router = APIRouter()

provider = BuilderSpaceAdapter()
search = TavilyAdapter()


@router.get("/ping")
async def ping() -> dict:
    return {
        "canary_version": CANARY_VERSION,
        "schema_signature": SCHEMA_SIGNATURE,
        "provider": provider.readiness(),
        "search": search.readiness(),
    }


@router.get("/")
async def index() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parent.parent / "static" / "local-test.html")


@router.post("/estimate")
async def estimate(request: EstimateRequest) -> dict:
    try:
        payload = await run_text_meal_canary(request, provider=provider, search=search)
        record_success(request, payload)
        return {"coach_message": payload.reply_text, "payload": payload.model_dump(mode="json")}
    except Exception as exc:
        record_error(request, str(exc))
        raise


@router.get("/logs")
async def logs(limit: int = 20) -> dict:
    return {"items": read_recent_events(limit=limit)}
