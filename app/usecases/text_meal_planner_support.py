from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..agent.task_meal_link_llm import (
    TASK_MEAL_LINK_PROMPT,
    fallback_task_meal_link_result,
    normalize_task_meal_link_result,
)
from ..application.context_assembly import (
    build_boundary_features as application_build_boundary_features,
    build_task_meal_link_payload,
    normalize_user_input_for_estimation as _normalize_user_input_for_estimation,
)
from ..application.pass_runner import run_pass
from ..application.planner import (
    ensure_planning_brief_model as application_ensure_planning_brief_model,
    fallback_planner_result as application_fallback_planner_result,
    planner_enabled as application_planner_enabled,
)
from ..application.state_transition import (
    active_meal_context_allowed as _active_meal_context_allowed,
    build_boundary_trace as application_build_boundary_trace,
)
from ..schemas import EstimateRequest, PassExecutionEnvelope


@dataclass
class PlannerStageOutcome:
    planner_result: Any
    task_meal_link_result: Any
    planner_enabled: bool
    effective_request: EstimateRequest
    active_meal_context_allowed: bool
    boundary_trace: dict[str, Any]
    normalization: dict[str, Any]


async def run_planner_orchestration(
    *,
    request: EstimateRequest,
    request_id: str,
    conversation_state: Any,
    latest_log: Any | None,
    context_str: str,
    planner_llm: Any,
    normalize_text: Any,
    pass_envelope: Any,
    run_stage: Any,
    llm_traces: list[dict[str, Any]],
    debug_steps: list[dict[str, Any]],
) -> PlannerStageOutcome:
    planner_result = application_fallback_planner_result(
        request.text,
        normalize_text=normalize_text,
        normalize_user_input_for_estimation=_normalize_user_input_for_estimation,
    )
    planner_result = planner_result.model_copy(
        update={"planning_brief": application_ensure_planning_brief_model(planner_result.planning_brief)}
    )
    planner_enabled = application_planner_enabled()
    planner_mode = "disabled"
    boundary_features = application_build_boundary_features(state=conversation_state, latest_log=latest_log)
    meal_log_summaries = [chunk.model_dump(mode="json") for chunk in conversation_state.retrieved_meal_records[:5]]
    fallback_task_link = fallback_task_meal_link_result(
        user_input=request.text,
        planner_result=planner_result,
        latest_log=latest_log,
    )
    task_meal_link_result = fallback_task_link
    task_meal_link_envelope = pass_envelope(status="failed", payload=fallback_task_link.model_dump(mode="json"), fallback_used=True)

    if planner_enabled:
        planner_mode = "fallback"
        task_meal_link_payload = build_task_meal_link_payload(
            user_input=request.text,
            state=conversation_state,
            meal_log_summaries=meal_log_summaries,
            boundary_features=boundary_features,
        )
        task_meal_link_result, task_meal_link_envelope = await run_pass(
            provider=planner_llm,
            stage="task_meal_link_pass",
            system_prompt=TASK_MEAL_LINK_PROMPT + "\n\n[CONTEXT]\n" + context_str,
            user_payload=task_meal_link_payload,
            max_tokens=2048,
            fallback_result=fallback_task_link,
            normalize=lambda raw, fallback: normalize_task_meal_link_result(raw, fallback=fallback, state=conversation_state),
            dump=lambda result: result.model_dump(mode="json"),
            run_stage=run_stage,
            request_id=request_id,
            llm_traces=llm_traces,
            trigger_reason="task_meal_link",
            handoff_contract={
                "context_snapshot_present": bool(context_str),
                "recent_message_count": len(conversation_state.recent_messages),
                "conversation_archive_hit_count": len(conversation_state.conversation_archive_hits),
                "planner_state_digest_present": bool(conversation_state.planner_state_digest),
            },
            required_fields=["intent", "meal_link_action", "target_meal_id", "clarification_blocking"],
            required_fields_source="normalized",
            nullable_required_fields=["target_meal_id"],
        )
        if task_meal_link_envelope.status == "success":
            planner_mode = "llm"
        else:
            debug_steps.append(
                {"request_id": request_id, "step": "planner_pass", "planner_mode": "fallback", "planner_error": task_meal_link_envelope.error}
            )
    else:
        debug_steps.append(
            {"request_id": request_id, "step": "planner_pass", "planner_mode": "disabled", "planner_reason": "feature_flag_off"}
        )

    planner_result = planner_result.model_copy(
        update={
            "intent": "food_estimation" if task_meal_link_result.intent == "food_estimation" else task_meal_link_result.intent,
            "meal_boundary": (
                "continue_active_meal"
                if task_meal_link_result.meal_link_action == "attach_to_existing_meal"
                else "boundary_clarification"
                if task_meal_link_result.meal_link_action == "boundary_ambiguous"
                else "start_new_meal"
            ),
            "active_meal_reference": task_meal_link_result.target_meal_id,
            "boundary_confidence": task_meal_link_result.link_confidence,
            "resolved_query": task_meal_link_result.normalized_user_input or request.text,
            "normalized_user_input": task_meal_link_result.normalized_user_input or request.text,
        }
    )
    effective_request = EstimateRequest(
        text=task_meal_link_result.normalized_user_input or planner_result.normalized_user_input,
        allow_search=request.allow_search,
    )
    active_meal_context_allowed = _active_meal_context_allowed(planner_result)
    boundary_trace = application_build_boundary_trace(
        planner_result=planner_result,
        state=conversation_state,
        active_meal_context_allowed=active_meal_context_allowed,
        confidence_signals={},
        downgrade_reasons=[],
    )
    normalization = (
        _normalize_user_input_for_estimation(request.text)
        if planner_result.route_hints.get("planner_source") == "fallback_normalizer"
        else {
            "raw_text": request.text,
            "normalized_text": effective_request.text,
            "normalizer_applied": False,
            "notes": [],
        }
    )
    debug_steps.append(
        {
            "request_id": request_id,
            "step": "planner_pass",
            "planner_mode": planner_mode,
            "raw_user_input": request.text,
            "thin_sanitized_input": normalize_text(request.text),
            "intent": planner_result.intent,
            "meal_boundary": planner_result.meal_boundary,
            "active_meal_reference": planner_result.active_meal_reference,
            "boundary_confidence": planner_result.boundary_confidence,
            "planner_self_reported_boundary_confidence": planner_result.boundary_confidence,
            "normalized_user_input": effective_request.text,
            "input_signals": planner_result.input_signals,
            "missing_info": planner_result.missing_info,
            "route_hints": planner_result.route_hints,
            "planning_brief": planner_result.planning_brief.model_dump(mode="json"),
        }
    )
    return PlannerStageOutcome(
        planner_result=planner_result,
        task_meal_link_result=task_meal_link_result,
        planner_enabled=planner_enabled,
        effective_request=effective_request,
        active_meal_context_allowed=active_meal_context_allowed,
        boundary_trace=boundary_trace,
        normalization=normalization,
    )
