from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from datetime import datetime
from ...database import get_db, get_or_create_user
from ...schemas import EstimateRequest
from ...shared.contracts.audit import AuditEvent
from ..application import execute_bundle1_turn
from ..application.chat_intents import parse_weight_or_budget_intent
from ...logging import append_audit_event, now_iso, write_request_trace_artifact
from ..application.workflow_routing import build_workflow_routing_decision
from ..application.general_chat_service import build_general_chat_response_pass
from ..application.canonical_commit_bridge import record_body_observation_to_canonical, record_budget_adjustment_to_canonical, get_active_body_profile_record
from ...body.application import bootstrap_body_plan_for_date, OnboardingBootstrapInput
from ...runtime.interface.provider_runtime import manager_provider, search_provider

router = APIRouter()


@router.post("/estimate")
async def estimate(request: EstimateRequest, raw_request: Request, db: Any = Depends(get_db)) -> dict:
    request_id = uuid4().hex
    source_page_version = raw_request.headers.get("X-Canary-Page-Version")
    try:
        user_id = request.user_id if hasattr(request, "user_id") and request.user_id else "default_user"
        local_date = datetime.now().date().isoformat()

        # 1. Global Router Pass
        routing_result = build_workflow_routing_decision(raw_user_input=request.text)

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
                from ...body.application import build_active_body_plan_view
                from ...budget.application import build_current_budget_view
                from ...recommendation.application import build_recommendation_candidate_spec
                from ...recommendation.application import retrieve_recommendation_candidates
                from ...recommendation.application import build_recommendation_response
                from ...recommendation.application import build_recommendation_context
                from ...recommendation.application import build_recommendation_ranking_and_synthesis
                from ...schemas import RecommendationCandidate

                user = get_or_create_user(db, user_id)
                current_budget_view = build_current_budget_view(
                    db,
                    user_id=user.id,
                    local_date=local_date,
                )
                active_body_plan_view = build_active_body_plan_view(db, user_id=user.id)
                rec_ctx = build_recommendation_context(
                    user_id=user.id,
                    current_budget_view=current_budget_view,
                    active_body_plan_view=active_body_plan_view,
                    raw_user_input=request.text,
                )
                candidate_spec = build_recommendation_candidate_spec(
                    context_packet=rec_ctx,
                )
                candidates = retrieve_recommendation_candidates(
                    context_packet=rec_ctx,
                    candidate_spec=candidate_spec,
                    safe_defaults=[
                        RecommendationCandidate(
                            candidate_id="chat-safe-1",
                            candidate_kind="safe_fallback",
                            title="Chicken Salad Bowl",
                            store_name="Convenience Store",
                            estimated_kcal=430,
                            protein_g=30,
                            fit_summary="safe_fallback",
                            source_metadata={
                                "item_kind": "meal",
                                "staple_type": "salad",
                                "cuisine_family": "western",
                                "protein_posture": "high_protein",
                            },
                        ),
                        RecommendationCandidate(
                            candidate_id="chat-safe-2",
                            candidate_kind="safe_fallback",
                            title="Tofu Bento",
                            store_name="Bento House",
                            estimated_kcal=520,
                            protein_g=24,
                            fit_summary="balanced",
                            source_metadata={
                                "item_kind": "meal",
                                "staple_type": "rice",
                                "cuisine_family": "taiwanese",
                                "protein_posture": "balanced",
                            },
                        ),
                    ],
                )
                ranked = build_recommendation_ranking_and_synthesis(
                    context_packet=rec_ctx,
                    candidate_spec=candidate_spec,
                    retrieval_result=candidates,
                )
                rec_response = build_recommendation_response(
                    context_packet=rec_ctx,
                    ranking_result=ranked,
                )
                return {
                    "request_id": request_id,
                    "coach_message": rec_response.response.reply_text,
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
            parsed = await parse_weight_or_budget_intent(manager_provider, request.text)
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
            parsed = await parse_weight_or_budget_intent(manager_provider, request.text)
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
        import traceback

        print(traceback.format_exc())
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
                "coach_message": "這次估算逾時或失敗了，請再試一次。",
                "payload": None,
            },
        )
