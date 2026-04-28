from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ...body.application import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from ...database import get_db, get_or_create_user
from ...logging import append_audit_event, now_iso, write_request_trace_artifact
from ...runtime.interface.provider_runtime import manager_provider, search_provider
from ...schemas import EstimateRequest
from ...shared.contracts.audit import AuditEvent
from ..application import execute_bundle1_turn
from ..application.canonical_commit_bridge import (
    get_active_body_profile_record,
    record_body_observation_to_canonical,
    record_budget_adjustment_to_canonical,
)
from ..application.chat_intents import parse_weight_or_budget_intent
from ..application.general_chat_service import build_general_chat_response_pass
from ..application.workflow_routing import build_workflow_routing_decision

router = APIRouter()


@router.post("/estimate")
async def estimate(request: EstimateRequest, raw_request: Request, db: Any = Depends(get_db)) -> dict:
    request_id = uuid4().hex
    source_page_version = raw_request.headers.get("X-Canary-Page-Version")
    try:
        user_id = request.user_id if getattr(request, "user_id", None) else "default_user"
        local_date = datetime.now().date().isoformat()

        routing_result = build_workflow_routing_decision(raw_user_input=request.text)
        if routing_result.target_workflow_family == "general_chat":
            general_chat_result = build_general_chat_response_pass(
                db,
                user_external_id=user_id,
                raw_user_input=request.text,
                local_date=local_date,
            )
            if general_chat_result.disposition != "open_new_workflow":
                return {
                    "request_id": request_id,
                    "coach_message": general_chat_result.reply_text,
                    "payload": None,
                }

        if routing_result.target_workflow_family == "body_observation":
            parsed = await parse_weight_or_budget_intent(manager_provider, request.text)
            if parsed.get("weight_kg"):
                user = get_or_create_user(db, user_id)
                record_body_observation_to_canonical(
                    db,
                    user=user,
                    value=parsed["weight_kg"],
                    local_date=local_date,
                )
                profile = get_active_body_profile_record(db, user_id=user.id)
                if profile:
                    profile_meta = dict(profile.metadata_json or {})
                    bootstrap_body_plan_for_date(
                        db,
                        user=user,
                        inputs=OnboardingBootstrapInput(
                            sex=profile.sex,
                            age_years=profile.age_years,
                            height_cm=profile.height_cm,
                            current_weight_kg=parsed["weight_kg"],
                            activity_level=profile.activity_level,
                            goal_type=profile.goal_type,
                            weekly_target_rate_kg=profile_meta.get("weekly_target_rate_kg", 0.5),
                            local_date=local_date,
                            timezone="UTC",
                        ),
                    )
                return {
                    "request_id": request_id,
                    "coach_message": f"已記錄體重 {parsed['weight_kg']} kg，並依最新數據重新整理 body plan。",
                    "payload": None,
                }

        if routing_result.target_workflow_family == "calibration":
            parsed = await parse_weight_or_budget_intent(manager_provider, request.text)
            if parsed.get("delta_kcal"):
                user = get_or_create_user(db, user_id)
                record_budget_adjustment_to_canonical(
                    db,
                    user=user,
                    delta_kcal=parsed["delta_kcal"],
                    local_date=local_date,
                    metadata={"source": "chat_adjustment"},
                )
                direction = "增加" if parsed["delta_kcal"] > 0 else "減少"
                return {
                    "request_id": request_id,
                    "coach_message": f"已調整今天預算，{direction} {abs(parsed['delta_kcal'])} kcal。",
                    "payload": None,
                }

        result = await execute_bundle1_turn(
            db,
            user_external_id=user_id,
            raw_user_input=request.text,
            onboarding_payload=None,
            local_date=local_date,
            allow_search=request.allow_search,
            manager_provider=manager_provider,
            provider=manager_provider,
            search_adapter=search_provider,
        )
        return {
            "request_id": result["request_id"],
            "coach_message": result["assistant_message"],
            "payload": result,
        }
    except Exception as exc:
        trace_path = write_request_trace_artifact(
            request_id,
            {
                "request_id": request_id,
                "timestamp": now_iso(),
                "request": {
                    "user_id": getattr(request, "user_id", "anonymous"),
                    "text": request.text,
                    "allow_search": request.allow_search,
                },
                "source_page_version": source_page_version,
                "status": "error",
                "error": str(exc),
            },
        )
        append_audit_event(
            AuditEvent(
                request_id=request_id,
                timestamp=now_iso(),
                text=request.text,
                allow_search=request.allow_search,
                status="error",
                error=str(exc),
                source_page_version=source_page_version,
                trace_artifact_path=str(trace_path),
            )
        )
        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "error": str(exc) or "Internal Server Error",
                "coach_message": "處理這則訊息時發生錯誤，請稍後再試。",
                "payload": None,
            },
        )
