from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ..database import get_db
from ..schemas import EstimateRequest
from ..usecases.text_meal import record_error, record_success, run_text_meal_canary
from .provider_runtime import planner_provider, primary_provider, search_provider

router = APIRouter()


@router.post("/estimate")
async def estimate(request: EstimateRequest, raw_request: Request, db: Any = Depends(get_db)) -> dict:
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
            db=db,
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
