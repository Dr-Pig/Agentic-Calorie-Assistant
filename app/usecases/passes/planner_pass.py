"""
Planner Pass - Intent detection and meal boundary resolution.

Responsibilities:
- Detect user intent (food_estimation, clarification, modification, etc.)
- Determine meal boundary (start_new, continue, clarify)
- Generate planning brief for downstream passes

Best Practices:
- Does NOT estimate calories or make nutrition decisions
- Falls back to conservative defaults on failure
- Strict output validation before passing context
"""

from __future__ import annotations

from typing import Any

from ...agent.task_meal_link_llm import (
    TASK_MEAL_LINK_PROMPT,
    fallback_task_meal_link_result,
    normalize_task_meal_link_result,
)
from ...application.context_assembly import (
    build_boundary_features,
    build_task_meal_link_payload,
    normalize_text as _normalize_text,
)
from ...application.pass_runner import run_pass
from ...application.planner import (
    ensure_planning_brief_model,
    fallback_planner_result,
    planner_enabled,
)
from ...schemas import TaskMealLinkResult, TurnIntentResult
from .base import run_text_stage


PLANNER_MAX_TOKENS = 2048


async def run_planner_pass(
    provider: Any,
    request_id: str,
    user_input: str,
    conversation_state: Any,
    planner_provider: Any | None = None,
    llm_traces: list[dict[str, Any]] | None = None,
    debug_steps: list[dict[str, Any]] | None = None,
) -> tuple[TurnIntentResult, TaskMealLinkResult, dict[str, Any]]:
    """
    Execute the planner pass.

    Returns:
        tuple: (planner_result, task_meal_link_result, context_str)
    """
    llm_traces = llm_traces or []
    debug_steps = debug_steps or []

    planner_llm = planner_provider or provider
    planner_enabled_flag = planner_enabled()

    # Fallback planner result
    raw_input_normalized = _normalize_text(user_input)
    planner_result = fallback_planner_result(
        user_input,
        normalize_text=_normalize_text,
        normalize_user_input_for_estimation=lambda x: {
            "raw_text": x,
            "normalized_text": x,
            "normalizer_applied": False,
            "notes": [],
        },
    )
    planner_result = planner_result.model_copy(
        update={"planning_brief": ensure_planning_brief_model(planner_result.planning_brief)}
    )

    # Load conversation context
    from ...infrastructure.conversation_state_loader import load_conversation_state
    loaded = load_conversation_state(
        conversation_state.db,  # type: ignore
        user_id=conversation_state.user_id,
        incoming_user_text=user_input
    )
    context_str = _render_conversation_prompt(loaded.state) if loaded.state else ""

    # Build boundary features
    boundary_features = build_boundary_features(
        state=loaded.state,
        latest_log=loaded.latest_log
    )

    # Meal log summaries
    meal_log_summaries = [
        chunk.model_dump(mode="json")
        for chunk in (loaded.state.retrieved_meal_records[:5] if loaded.state else [])
    ]

    # Fallback task meal link
    fallback_tml = fallback_task_meal_link_result(
        user_input=user_input,
        planner_result=planner_result,
        latest_log=loaded.latest_log,
    )

    task_meal_link_result = fallback_tml
    planner_mode = "disabled"

    if planner_enabled_flag:
        planner_mode = "fallback"
        tml_payload = build_task_meal_link_payload(
            user_input=user_input,
            state=loaded.state,
            meal_log_summaries=meal_log_summaries,
            boundary_features=boundary_features,
        )

        tml_result, tml_envelope = await run_pass(
            provider=planner_llm,
            stage="task_meal_link_pass",
            system_prompt=TASK_MEAL_LINK_PROMPT + "\n\n[CONTEXT]\n" + context_str,
            user_payload=tml_payload,
            max_tokens=PLANNER_MAX_TOKENS,
            fallback_result=fallback_tml,
            normalize=lambda raw, fb: normalize_task_meal_link_result(
                dict(raw or {}), fallback=fb, state=loaded.state
            ),
            dump=lambda r: r.model_dump(mode="json"),
            run_stage=run_text_stage,
            request_id=request_id,
            llm_traces=llm_traces,
            trigger_reason="task_meal_link",
            handoff_contract={
                "context_snapshot_present": bool(context_str),
                "recent_message_count": len(loaded.state.recent_messages) if loaded.state else 0,
            },
            required_fields=["intent", "meal_link_action", "target_meal_id", "clarification_blocking"],
            required_fields_source="normalized",
            nullable_required_fields=["target_meal_id"],
        )

        if tml_envelope.status == "success":
            planner_mode = "llm"
            task_meal_link_result = tml_result
        else:
            debug_steps.append({
                "request_id": request_id,
                "step": "planner_pass",
                "planner_mode": "fallback",
                "planner_error": tml_envelope.error,
            })

    # Merge planner result with task_meal_link info
    final_planner = planner_result.model_copy(update={
        "intent": (
            "food_estimation"
            if task_meal_link_result.intent == "food_estimation"
            else task_meal_link_result.intent
        ),
        "meal_boundary": (
            "continue_active_meal"
            if task_meal_link_result.meal_link_action == "attach_to_existing_meal"
            else "boundary_clarification"
            if task_meal_link_result.meal_link_action == "boundary_ambiguous"
            else "start_new_meal"
        ),
        "active_meal_reference": task_meal_link_result.target_meal_id,
        "boundary_confidence": task_meal_link_result.link_confidence,
        "normalized_user_input": task_meal_link_result.normalized_user_input or planner_result.normalized_user_input or user_input,
    })

    debug_steps.append({
        "request_id": request_id,
        "step": "planner_pass",
        "planner_mode": planner_mode,
        "raw_user_input": user_input,
        "thin_sanitized_input": raw_input_normalized,
        "intent": final_planner.intent,
        "meal_boundary": final_planner.meal_boundary,
        "normalized_user_input": final_planner.normalized_user_input,
        "input_signals": final_planner.input_signals,
        "missing_info": final_planner.missing_info,
        "route_hints": final_planner.route_hints,
    })

    return final_planner, task_meal_link_result, context_str


def _render_conversation_prompt(state: Any) -> str:
    """Render conversation state as prompt string."""
    if not state:
        return ""
    from ...application.context_assembly import render_conversation_state_prompt
    return render_conversation_state_prompt(state)
