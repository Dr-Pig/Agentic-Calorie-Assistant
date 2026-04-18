from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from datetime import datetime
from ..database import get_db, get_or_create_user
from ..schemas import EstimateRequest
from ..usecases.text_meal import record_error, record_success, run_text_meal_canary
from ..application.workflow_routing_pass import build_workflow_routing_pass
from ..application.general_chat_pass import build_general_chat_response_pass
from ..usecases.chat_intents import parse_weight_or_budget_intent
from ..application.canonical_commit_bridge import record_body_observation_to_canonical, record_budget_adjustment_to_canonical, get_active_body_profile_record
from ..application.onboarding_service import bootstrap_body_plan_for_date, OnboardingBootstrapInput
from .provider_runtime import planner_provider, primary_provider, search_provider

router = APIRouter()


@router.post("/estimate")
async def estimate(request: EstimateRequest, raw_request: Request, db: Any = Depends(get_db)) -> dict:
    request_id = uuid4().hex
    source_page_version = raw_request.headers.get("X-Canary-Page-Version")
    try:
        user_id = request.user_id if hasattr(request, "user_id") and request.user_id else "default_user"
        local_date = datetime.now().date().isoformat()

        # 1. Global Router Pass
        routing_result = build_workflow_routing_pass(raw_user_input=request.text)

        # --- general_chat: answer budget/goal/product questions without state mutation ---
        if routing_result.target_workflow_family == "general_chat":
            gc_result = build_general_chat_response_pass(
                db,
                user_external_id=user_id,
                raw_user_input=request.text,
                local_date=local_date,
            )
            if gc_result.disposition == "open_new_workflow":
                pass  # fall through to canonical intake below
            else:
                return {
                    "request_id": request_id,
                    "coach_message": gc_result.reply_text,
                    "payload": None,
                }

        # --- recommendation: non-mutating meal suggestion ---
        if routing_result.target_workflow_family == "recommendation":
            try:
                from ..application.recommendation_ranking import rank_recommendation_candidates
                from ..application.recommendation_response import build_recommendation_response
                from ..application.recommendation_context import build_recommendation_context
                from ..application.recommendation_candidate_retrieval import retrieve_recommendation_candidates

                rec_ctx = build_recommendation_context(db, user_external_id=user_id, local_date=local_date)
                candidates = retrieve_recommendation_candidates(db, context=rec_ctx)
                ranked = rank_recommendation_candidates(candidates=candidates, context=rec_ctx)
                rec_response = build_recommendation_response(ranked_candidates=ranked, context=rec_ctx)
                return {
                    "request_id": request_id,
                    "coach_message": rec_response.reply_text,
                    "payload": None,
                }
            except Exception:
                # If recommendation modules aren't fully wired yet, fall back gracefully
                return {
                    "request_id": request_id,
                    "coach_message": "推薦功能目前還在建置中，請稍後再試！",
                    "payload": None,
                }

        # --- body_observation: weight update + plan re-bootstrap ---
        if routing_result.target_workflow_family == "body_observation":
            parsed = await parse_weight_or_budget_intent(planner_provider, request.text)
            if parsed.get("weight_kg"):
                user = get_or_create_user(db, user_id)
                record_body_observation_to_canonical(db, user=user, value=parsed["weight_kg"], local_date=local_date)

                profile = get_active_body_profile_record(db, user_id=user.id)
                if profile:
                    profile_meta = dict(profile.metadata_json or {})
                    bootstrap_body_plan_for_date(db, user=user, inputs=OnboardingBootstrapInput(
                        sex=profile.sex,
                        age_years=profile.age_years,
                        height_cm=profile.height_cm,
                        current_weight_kg=parsed["weight_kg"],
                        activity_level=profile.activity_level,
                        goal_type=profile.goal_type,
                        weekly_target_rate_kg=profile_meta.get("weekly_target_rate_kg", 0.5),  # type: ignore
                        local_date=local_date,
                        timezone="UTC"
                    ))
                return {
                    "request_id": request_id,
                    "coach_message": f"已為您更新體重為 {parsed['weight_kg']} 公斤，並重新校準了運作計畫！",
                    "payload": None,
                }

        # --- calibration: budget adjustment via chat ---
        elif routing_result.target_workflow_family == "calibration":
            parsed = await parse_weight_or_budget_intent(planner_provider, request.text)
            if parsed.get("delta_kcal"):
                user = get_or_create_user(db, user_id)
                record_budget_adjustment_to_canonical(db, user=user, delta_kcal=parsed["delta_kcal"], local_date=local_date, metadata={"source": "chat_adjustment"})
                action = "增加" if parsed["delta_kcal"] > 0 else "減少"
                return {
                    "request_id": request_id,
                    "coach_message": f"好的，已為您今日預算{action}了 {abs(parsed['delta_kcal'])} 卡。",
                    "payload": None,
                }

        # 2. Default Canonical Intake
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

