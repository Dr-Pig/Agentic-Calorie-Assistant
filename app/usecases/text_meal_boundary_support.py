from __future__ import annotations

from typing import Any

from .text_meal_finalize_support import build_boundary_clarification_payload
from .text_meal_persistence_support import apply_persistence_decision


def maybe_handle_boundary_clarification(
    *,
    task_meal_link_result: Any,
    request: Any,
    effective_request: Any,
    request_id: str,
    planner_result: Any,
    planner_enabled: bool,
    conversation_state: Any,
    context_str: str,
    boundary_trace: dict[str, Any],
    risk_packet: dict[str, Any],
    meal_template: dict[str, Any] | None,
    debug_steps: list[dict[str, Any]],
    llm_traces: list[dict[str, Any]],
    available_tools: list[str],
    evidence_guardrail_prompt: str,
    db: Any = None,
    user: Any = None,
    latest_log: Any = None,
    incoming_user_message_id: int | None = None,
) -> Any | None:
    if not (
        task_meal_link_result.meal_link_action == "boundary_ambiguous"
        and task_meal_link_result.clarification_blocking
    ):
        return None

    payload = build_boundary_clarification_payload(
        request=request,
        effective_request=effective_request,
        request_id=request_id,
        planner_result=planner_result,
        planner_enabled=planner_enabled,
        conversation_state=conversation_state,
        context_str=context_str,
        boundary_trace=boundary_trace,
        risk_packet=risk_packet,
        meal_template=meal_template,
        debug_steps=debug_steps,
        llm_traces=llm_traces,
        available_tools=available_tools,
        evidence_guardrail_prompt=evidence_guardrail_prompt,
    )
    if db and user:
        payload.trace_contract["persistence_decision"] = apply_persistence_decision(
            db=db,
            user=user,
            latest_log=latest_log,
            planner_intent=planner_result.intent,
            payload=payload,
            raw_input=request.text,
            request_id=request_id,
            incoming_user_message_id=incoming_user_message_id,
            conversation_state=conversation_state,
            planner_result=planner_result,
        )
        payload.boundary_trace["boundary_resolution_state"] = "open"
    return payload
