from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Request

from app.composition.body_observation_manager_turn import (
    execute_body_observation_manager_turn,
)
from app.composition.calibration_estimate_route_support import (
    build_calibration_action_route_payload,
    build_calibration_preview_route_payload,
    build_calibration_raw_text_fallback_route_payload,
    has_explicit_calibration_action_request,
    has_explicit_calibration_preview_request,
    parse_calibration_action_accepted_at,
)
from app.composition.conversation_turn_trace import record_runtime_turn_messages
from app.composition.general_chat_service import build_general_chat_response_pass
from app.composition.intake_turn_orchestrator import execute_intake_turn
from app.composition.manager_context_runtime import (
    build_runtime_manager_context_packet_v1,
)
from app.composition.phase_a_boundary_projection import (
    attach_boundary_projection,
    build_budget_boundary_projection,
)
from app.composition.state_resolver import resolve_intake_state
from app.database import get_db
from app.intake.application.boundary_output_honesty import enforce_budget_output_honesty
from app.intake.application.current_turn_context_assembler import (
    build_current_turn_context_v1,
)
from app.intake.application.workflow_routing import build_workflow_routing_decision
from app.intake.interface.intake_error_response import build_estimate_error_response
from app.runtime.application.request_trace_artifacts import (
    write_general_chat_request_trace_artifact,
)
from app.runtime.interface.provider_runtime import (
    extract_provider,
    manager_provider,
    search_provider,
)
from app.schemas import EstimateRequest

router = APIRouter()


def _request_local_date(request: EstimateRequest) -> str:
    return request.local_date or datetime.now().date().isoformat()


@router.post("/estimate")
async def estimate(request: EstimateRequest, raw_request: Request, db: Any = Depends(get_db)) -> dict:
    request_id = uuid4().hex
    source_page_version = raw_request.headers.get("X-Canary-Page-Version")
    try:
        user_id = request.user_id if getattr(request, "user_id", None) else "default_user"
        local_date = _request_local_date(request)

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
        if has_explicit_calibration_preview_request(request):
            general_chat_result = build_general_chat_response_pass(
                db,
                user_external_id=user_id,
                raw_user_input=request.text,
                mode="calibration_preview",
                local_date=local_date,
                persist_calibration_proposal=request.persist_calibration_proposal,
            )
            phase_a_trace = {
                **routing_result.phase_a_trace,
                "explicit_calibration_preview_request": {
                    "present": True,
                    "persist_calibration_proposal": request.persist_calibration_proposal,
                    "raw_text_authorized_preview": False,
                    "raw_text_authorized_proposal_persistence": False,
                    "plan_mutation_authorized": False,
                    "ledger_mutation_authorized": False,
                },
            }
            route_payload = build_calibration_preview_route_payload(general_chat_result)
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
                result=route_payload,
            )
            return {
                "request_id": request_id,
                "coach_message": general_chat_result.reply_text,
                "payload": route_payload,
            }
        if has_explicit_calibration_action_request(request):
            general_chat_result = build_general_chat_response_pass(
                db,
                user_external_id=user_id,
                raw_user_input=request.text,
                mode="calibration_action",
                local_date=local_date,
                calibration_proposal_container_id=request.calibration_proposal_container_id,
                calibration_action=request.calibration_action,
                accepted_at=parse_calibration_action_accepted_at(request),
            )
            state_after = resolve_intake_state(
                db,
                user_external_id=user_id,
                local_date=local_date,
            )
            phase_a_trace = {
                **routing_result.phase_a_trace,
                "explicit_calibration_action_request": {
                    "present": True,
                    "proposal_container_id": request.calibration_proposal_container_id,
                    "calibration_action": request.calibration_action,
                    "calibration_action_accepted_at": request.calibration_action_accepted_at,
                    "raw_text_authorized_mutation": False,
                    "frontend_effective_date_calculation_authorized": False,
                },
            }
            route_payload = build_calibration_action_route_payload(general_chat_result)
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
                state_after=state_after,
                phase_a_trace=phase_a_trace,
                result=route_payload,
            )
            return {
                "request_id": request_id,
                "coach_message": general_chat_result.reply_text,
                "payload": route_payload,
            }
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
            result = await execute_body_observation_manager_turn(
                db,
                request_id=request_id,
                user_external_id=user_id,
                raw_user_input=request.text,
                local_date=local_date,
                allow_search=request.allow_search,
                manager_provider=manager_provider,
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
                state_after=resolve_intake_state(
                    db,
                    user_external_id=user_id,
                    local_date=local_date,
                ),
                phase_a_trace=routing_result.phase_a_trace,
                result=result,
            )
            return {
                "request_id": result["request_id"],
                "coach_message": result["assistant_message"],
                "payload": result,
            }

        if routing_result.target_workflow_family == "calibration":
            general_chat_result = build_general_chat_response_pass(
                db,
                user_external_id=user_id,
                raw_user_input=request.text,
                mode="fallback_answer",
                local_date=local_date,
            )
            route_payload = build_calibration_raw_text_fallback_route_payload(general_chat_result)
            write_general_chat_request_trace_artifact(
                request_id=request_id,
                user_external_id=user_id,
                local_date=local_date,
                raw_user_input=request.text,
                state_before=state_before,
                general_chat_result=general_chat_result,
                assistant_message=general_chat_result.reply_text,
                phase_a_trace=routing_result.phase_a_trace,
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
                phase_a_trace=routing_result.phase_a_trace,
                result=route_payload,
            )
            return {
                "request_id": request_id,
                "coach_message": general_chat_result.reply_text,
                "payload": route_payload,
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
