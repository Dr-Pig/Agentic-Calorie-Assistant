from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from ... import CANARY_VERSION, SCHEMA_SIGNATURE
from .provider_runtime import extract_provider, manager_provider, search_provider

router = APIRouter()
_INDEX_HTML_PATH = Path(__file__).resolve().parent.parent.parent.parent / "static" / "test-chat.html"
_INDEX_HTML_CACHE: str | None = None


def _public_readiness(readiness: dict) -> dict:
    return {"status": "ok"} if readiness else {"status": "unknown"}


def _load_index_html() -> str:
    global _INDEX_HTML_CACHE
    if _INDEX_HTML_CACHE is None:
        _INDEX_HTML_CACHE = _INDEX_HTML_PATH.read_text(encoding="utf-8")
    return _INDEX_HTML_CACHE


@router.get("/ping")
async def ping() -> dict:
    return {
        "canary_version": CANARY_VERSION,
        "schema_signature": SCHEMA_SIGNATURE,
        "provider": _public_readiness(manager_provider.readiness()),
        "manager_provider": _public_readiness(manager_provider.readiness()),
        "search": _public_readiness(search_provider.readiness()),
        "extract": _public_readiness(extract_provider.readiness()),
    }


@router.get("/")
async def index() -> HTMLResponse:
    return HTMLResponse(content=_load_index_html(), media_type="text/html; charset=utf-8")
