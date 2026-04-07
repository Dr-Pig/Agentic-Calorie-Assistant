from __future__ import annotations

from pathlib import Path
import os
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session
from .database import get_db, get_meal_log_history, get_or_create_user
from . import CANARY_VERSION, SCHEMA_SIGNATURE
from .logging import read_recent_events, get_trace_summaries, get_full_trace
from .providers.builderspace_adapter import BuilderSpaceAdapter
from .providers.gemini_adapter import GeminiAdapter
from .search.tavily_adapter import TavilyAdapter
from .schemas import EstimateRequest
from .usecases.text_meal import record_error, record_success, run_text_meal_canary
from fastapi import Depends

router = APIRouter()


def _create_provider(
    *,
    provider_env: str,
    default_provider: str,
    role_label: str,
) -> BuilderSpaceAdapter | GeminiAdapter:
    provider_name = os.getenv(provider_env, default_provider).strip().lower()
    if provider_name == "gemini":
        return GeminiAdapter()
    if role_label == "planner":
        return BuilderSpaceAdapter(role_label=role_label)
    return BuilderSpaceAdapter(role_label=role_label)


planner_provider = _create_provider(
    provider_env="AI_PLANNER_PROVIDER",
    default_provider=os.getenv("AI_PROVIDER", "builderspace"),
    role_label="planner",
)
primary_provider = _create_provider(
    provider_env="AI_PRIMARY_PROVIDER",
    default_provider=os.getenv("AI_PROVIDER", "builderspace"),
    role_label="primary",
)
provider = primary_provider
search_provider = TavilyAdapter()


@router.get("/ping")
async def ping() -> dict:
    return {
        "canary_version": CANARY_VERSION,
        "schema_signature": SCHEMA_SIGNATURE,
        "provider": primary_provider.readiness(),
        "planner_provider": planner_provider.readiness(),
        "primary_provider": primary_provider.readiness(),
        "search": search_provider.readiness(),
    }


@router.get("/")
async def index() -> HTMLResponse:
    html = (Path(__file__).resolve().parent.parent / "static" / "test-chat.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@router.post("/estimate")
async def estimate(request: EstimateRequest, raw_request: Request, db: Session = Depends(get_db)) -> dict:
    request_id = uuid4().hex
    source_page_version = raw_request.headers.get("X-Canary-Page-Version")
    try:
        payload = await run_text_meal_canary(
            request, 
            provider=primary_provider,
            planner_provider=planner_provider,
            primary_provider=primary_provider,
            request_id=request_id, 
            search_adapter=search_provider,
            db=db
        )
        record_success(request, payload, source_page_version=source_page_version)
        return {
            "request_id": request_id,
            "coach_message": payload.reply_text,
            "payload": payload.model_dump(mode="json"),
        }
    except Exception as exc:
        import traceback
        print(traceback.format_exc())
        record_error(request, str(exc), request_id=request_id, source_page_version=source_page_version)
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": str(exc) or "Internal Server Error",
                "coach_message": "這次估算逾時或失敗了，請再試一次。",
                "payload": None,
            },
        )


@router.get("/user/{user_id}/logs")
async def get_user_logs(user_id: str, include_superseded: bool = False, db: Session = Depends(get_db)) -> dict:
    user = get_or_create_user(db, user_id)
    logs = get_meal_log_history(db, user, limit=10, include_superseded=include_superseded)
    
    return {
        "user_id": user_id,
        "logs": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "status": log.status,
                "parent_log_id": log.parent_log_id,
                "meal_title": log.meal_title,
                "kcal": log.kcal,
                "protein": log.protein_g,
                "carb": log.carb_g,
                "fat": log.fat_g,
                "components": log.components_json,
                "pending_question": log.pending_question,
            } for log in logs
        ]
    }


@router.post("/user/{user_id}/context/reset")
async def reset_user_context(user_id: str, db: Session = Depends(get_db)) -> dict:
    user = get_or_create_user(db, user_id)
    from .models import MealLog
    # Clear all draft MealLogs for this user
    drafts = db.query(MealLog).filter(MealLog.user_id == user.id, MealLog.status == "draft").all()
    for d in drafts:
        d.status = "superseded"
    db.commit()
    return {"status": "ok", "message": "Draft logs cleared"}


@router.get("/logs")
async def logs(limit: int = 20) -> dict:
    return {"items": read_recent_events(limit=limit)}


@router.get("/admin/traces")
async def list_admin_traces(limit: int = 100) -> dict:
    """Return Metadata Summaries for the Ryo Lu Insight Dashboard."""
    return get_trace_summaries(limit=limit)


@router.get("/admin/trace/{request_id}")
async def get_admin_trace(request_id: str) -> dict:
    """Return the full JSON trace for a specific request."""
    trace = get_full_trace(request_id)
    if not trace:
        return JSONResponse(status_code=404, content={"error": "Trace not found"})
    return trace


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    """Serve the Ryo Lu Inspired Insight Dashboard."""
    html_path = Path(__file__).resolve().parent.parent / "static" / "dashboard.html"
    if not html_path.exists():
        return HTMLResponse(content="<h1>Dashboard missing</h1>", status_code=404)
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"), media_type="text/html; charset=utf-8")
