from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ... import CANARY_VERSION, SCHEMA_SIGNATURE
from .provider_runtime import extract_provider, manager_provider, search_provider

router = APIRouter()


@router.get("/ping")
async def ping() -> dict:
    return {
        "canary_version": CANARY_VERSION,
        "schema_signature": SCHEMA_SIGNATURE,
        "provider": manager_provider.readiness(),
        "manager_provider": manager_provider.readiness(),
        "search": search_provider.readiness(),
        "extract": extract_provider.readiness(),
    }


@router.get("/")
async def index() -> HTMLResponse:
    html = (Path(__file__).resolve().parent.parent.parent.parent / "static" / "test-chat.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
