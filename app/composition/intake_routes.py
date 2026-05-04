from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from app.composition.canonical_commit_bridge import (
    record_body_observation_to_canonical,
    record_budget_adjustment_to_canonical,
)
from app.composition.conversation_turn_trace import record_runtime_turn_messages
from app.composition.general_chat_service import build_general_chat_response_pass
from app.composition.intake_turn_orchestrator import execute_intake_turn
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1
from app.composition.phase_a_boundary_projection import attach_boundary_projection, build_budget_boundary_projection
from app.composition.state_resolver import resolve_intake_state
from app.database import get_db, get_or_create_user
from app.intake.application.boundary_output_honesty import enforce_budget_output_honesty
from app.intake.application.chat_intents import parse_weight_or_budget_intent
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.workflow_routing import build_workflow_routing_decision
from app.intake.interface.intake_error_response import build_estimate_error_response
from app.runtime.application.request_trace_artifacts import write_general_chat_request_trace_artifact
from app.runtime.interface.provider_runtime import extract_provider, manager_provider, search_provider
from app.schemas import EstimateRequest

router = APIRouter()


@router.post("/estimate")
async def estimate(request: EstimateRequest, raw_request: Request, db: Any = Depends(get_db)) -> dict:
    request_id = uuid4().hex
    source_page_version = raw_request.headers.get("X-Canary-Page-Version")
    try:
        user_id = request.user_id if getattr(request, "user_id", None) else "default_user"
        local_date = datetime.now().date().isoformat()

        state_before = resolve_intake_state(
            db,
            user_external_id=user_id,
            local_date=local_date,
            incoming_user_text=request.text,
        )
        current_turn_context = build_current_turn_context_v1(
            raw_user_input=request.text,
            resolved_state=state_before,
        )
        manager_context_packet_v1 = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=current_turn_context,
            user_external_id=user_id,
            local_date=local_date,
            session_id=request_id,
        )
        routing_result = build_workflow_routing_decision(
            raw_user_input=request.text,
            current_turn_context=current_turn_context,
            resolved_state=state_before,
        )
        if routing_result.target_workflow_family == "general_chat" and routing_result.disposition == "answer_only":
            if "CurrentBudgetView" in routing_result.required_read_surfaces:
                general_chat_mode = "budget_summary"
            elif "ActiveBodyPlanView" in routing_result.required_read_surfaces:
                general_chat_mode = "goal_summary"
            else:
                general_chat_mode = "fallback_answer"
            general_chat_result = build_general_chat_response_pass(
                db,
                user_external_id=user_id,
                raw_user_input=request.text,
                mode=general_chat_mode,
                local_date=local_date,
            )
            if general_chat_result.disposition != "open_new_workflow":
                phase_a_trace = routing_result.phase_a_trace
                if general_chat_result.remaining_budget_contract is not None:
                    output_honesty = enforce_budget_output_honesty(
                        reply_text=general_chat_result.reply_text,
                        remaining_budget=general_chat_result.remaining_budget_contract,
                        active_body_plan_present=bool(general_chat_result.active_body_plan_present),
                        phase_a_trace=phase_a_trace,
                    )
                    if output_honesty.reply_text != general_chat_result.reply_text:
                        general_chat_result = replace(general_chat_result, reply_text=output_honesty.reply_text)
                    phase_a_trace = output_honesty.phase_a_trace
                    phase_a_trace = attach_boundary_projection(
                        phase_a_trace,
                        build_budget_boundary_projection(
                            remaining_budget=general_chat_result.remaining_budget_contract,
                            active_body_plan_present=bool(general_chat_result.active_body_plan_present),
                            observed_reply_text=general_chat_result.reply_text,
                        ),
                    )
                write_general_chat_request_trace_artifact(
                    request_id=request_id,
                    user_external_id=user_id,
                    local_date=local_date,
                    raw_user_input=request.text,
                    state_before=state_before,
                    general_chat_result=general_chat_result,
                    assistant_message=general_chat_result.reply_text,
                    phase_a_trace=phase_a_trace,
                )
                record_runtime_turn_messages(
                    db,
                    user_external_id=user_id,
                    request_id=request_id,
                    local_date=local_date,
                    raw_user_input=request.text,
                    assistant_message=general_chat_result.reply_text,
                    state_before=state_before,
                    current_turn_context=current_turn_context,
                    manager_context_packet_v1=manager_context_packet_v1,
                    state_after=state_before,
                    phase_a_trace=phase_a_trace,
                    result={
                        "manager_decision": {
                            "intent_type": "general_chat",
                            "workflow_effect": "answer_only",
                            "tool_calls": [],
                        },
                        "intake_execution_manager": {
                            "final": {"final_action": "answer_only", "workflow_effect": "answer_only"},
                            "persistence_result": None,
                        },
                        "state_delta": {},
                        "sidecar": {},
                    },
                )
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
                assistant_message = f"Recorded weight {parsed['weight_kg']} kg. Body plan was not changed."
                state_after = resolve_intake_state(
                    db,
                    user_external_id=user_id,
                    local_date=local_date,
                )
                record_runtime_turn_messages(
                    db,
                    user_external_id=user_id,
                    request_id=request_id,
                    local_date=local_date,
                    raw_user_input=request.text,
                    assistant_message=assistant_message,
                    state_before=state_before,
                    current_turn_context=current_turn_context,
                    manager_context_packet_v1=manager_context_packet_v1,
                    state_after=state_after,
                    phase_a_trace=routing_result.phase_a_trace,
                    result={
                        "manager_decision": {"intent_type": "body_observation", "workflow_effect": "record_weight"},
                        "intake_execution_manager": {
                            "final": {"final_action": "answer_only", "workflow_effect": "body_observation_recorded"},
                            "persistence_result": None,
                        },
                        "state_delta": {"body_observation_recorded": True},
                        "sidecar": {},
                    },
                )
                return {
                    "request_id": request_id,
                    "coach_message": assistant_message,
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
                state_after = resolve_intake_state(
                    db,
                    user_external_id=user_id,
                    local_date=local_date,
                )
                direction = "增加" if parsed["delta_kcal"] > 0 else "減少"
                assistant_message = f"已調整今天預算，{direction} {abs(parsed['delta_kcal'])} kcal。"
                record_runtime_turn_messages(
                    db,
                    user_external_id=user_id,
                    request_id=request_id,
                    local_date=local_date,
                    raw_user_input=request.text,
                    assistant_message=assistant_message,
                    state_before=state_before,
                    current_turn_context=current_turn_context,
                    manager_context_packet_v1=manager_context_packet_v1,
                    state_after=state_after,
                    phase_a_trace=routing_result.phase_a_trace,
                    result={
                        "manager_decision": {"intent_type": "calibration", "workflow_effect": "adjust_budget"},
                        "intake_execution_manager": {
                            "final": {"final_action": "answer_only", "workflow_effect": "budget_adjusted"},
                            "persistence_result": None,
                        },
                        "state_delta": {"budget_adjusted": True, "delta_kcal": parsed["delta_kcal"]},
                        "sidecar": {},
                    },
                )
                return {
                    "request_id": request_id,
                    "coach_message": assistant_message,
                    "payload": None,
                }

        result = await execute_intake_turn(
            db,
            user_external_id=user_id,
            raw_user_input=request.text,
            onboarding_payload=None,
            local_date=local_date,
            allow_search=request.allow_search,
            manager_provider=manager_provider,
            provider=manager_provider,
            search_port=search_provider,
            extract_port=extract_provider,
            state_before=state_before,
            current_turn_context=current_turn_context,
            manager_context_packet_v1=manager_context_packet_v1,
            phase_a_trace=routing_result.phase_a_trace,
        )
        record_runtime_turn_messages(
            db,
            user_external_id=user_id,
            request_id=result["request_id"],
            local_date=local_date,
            raw_user_input=request.text,
            assistant_message=result["assistant_message"],
            state_before=state_before,
            current_turn_context=current_turn_context,
            manager_context_packet_v1=manager_context_packet_v1,
            state_after=result.get("state_after"),
            phase_a_trace=routing_result.phase_a_trace,
            result=result,
        )
        return {
            "request_id": result["request_id"],
            "coach_message": result["assistant_message"],
            "payload": result,
        }
    except Exception as exc:
        return build_estimate_error_response(
            request_id=request_id,
            request=request,
            source_page_version=source_page_version,
            exc=exc,
        )
