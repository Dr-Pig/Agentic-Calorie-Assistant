from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from .. import CANARY_VERSION, SCHEMA_SIGNATURE
from .provider_runtime import planner_provider, primary_provider, search_provider

router = APIRouter()


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
    html = (Path(__file__).resolve().parent.parent.parent / "static" / "test-chat.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    html_path = Path(__file__).resolve().parent.parent.parent / "static" / "dashboard.html"
    if not html_path.exists():
        return HTMLResponse(content="<h1>Dashboard missing</h1>", status_code=404)
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"), media_type="text/html; charset=utf-8")
