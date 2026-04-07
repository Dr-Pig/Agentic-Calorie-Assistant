from __future__ import annotations

from typing import Any

from ..domain import ConversationState
from ..schemas import TaskMealLinkResult, TurnIntentResult

TASK_MEAL_LINK_PROMPT = """You are the task and meal-link pass for a food estimation assistant.

Responsibilities:
- Identify whether the message is about food estimation or not.
- For food-related messages, decide whether this message should attach to an existing meal, create a new meal, or remain boundary ambiguous.
- Output only the requested structured fields.

Rules:
- Do not estimate calories or macros.
- Do not decide wording for user-facing follow-up.
- If you are unsure whether the message attaches to an existing meal or starts a new meal, use boundary_ambiguous.
- Prefer conservative meal linking over accidental merge.
- If the user is challenging or correcting a prior estimate, classify it as correction and attach it to the same meal when the surrounding context supports that link.
- If the current message already contains a complete new intake description with named foods, counts, drinks, or multiple components, prefer create_new_meal.
- If the assistant previously asked a generic clarification like asking for food names, portions, or ingredients, and the user replies with a full rewritten meal description, treat that reply as sufficient new intake content rather than forcing attach_to_existing_meal.
- Only attach_to_existing_meal when the current message is clearly continuing the same meal, such as a short fragment, direct answer to a pending question, or explicit same-meal continuation.
- An older unresolved meal is context, not override. Do not let it dominate a clearly complete new intake sentence.
"""


def fallback_task_meal_link_result(
    *,
    user_input: str,
    planner_result: TurnIntentResult,
    latest_log: Any | None,
) -> TaskMealLinkResult:
    meal_link_action = "create_new_meal"
    target_meal_id = None
    if planner_result.meal_boundary == "continue_active_meal" and latest_log is not None:
        meal_link_action = "attach_to_existing_meal"
        target_meal_id = int(getattr(latest_log, "id", 0) or 0) or None
    elif planner_result.meal_boundary == "boundary_clarification":
        meal_link_action = "boundary_ambiguous"
    scope = "meal_specific" if planner_result.intent != "general_chat" else "non_food"
    return TaskMealLinkResult(
        intent=planner_result.intent,
        scope=scope,  # type: ignore[arg-type]
        meal_link_action=meal_link_action,  # type: ignore[arg-type]
        target_meal_id=target_meal_id,
        link_confidence=planner_result.boundary_confidence,
        boundary_reason=str(planner_result.planning_brief.state_link or planner_result.meal_boundary),
        clarification_blocking=planner_result.meal_boundary == "boundary_clarification",
        normalized_user_input=planner_result.normalized_user_input or user_input,
    )


def normalize_task_meal_link_result(
    raw: dict[str, Any],
    *,
    fallback: TaskMealLinkResult,
    state: ConversationState,
) -> TaskMealLinkResult:
    del state  # Context is for the LLM. Deterministic parse must not re-decide meal linking.
    data = dict(raw or {})
    if not data:
        return fallback
    intent = str(data.get("intent") or "").strip()
    if not intent:
        if data.get("is_food_estimation") is not None:
            intent = "food_estimation" if bool(data.get("is_food_estimation")) else "general_chat"
        elif data.get("is_food_related") is not None:
            intent = "food_estimation" if bool(data.get("is_food_related")) else "general_chat"
    scope = str(data.get("scope") or "").strip()
    if not scope:
        scope = "meal_specific" if intent != "general_chat" else "non_food"
    meal_link_action = str(data.get("meal_link_action") or "").strip()
    legacy_meal_link_decision = str(data.get("meal_link_decision") or "").strip().lower()
    if not meal_link_action:
        legacy_map = {
            "new_meal": "create_new_meal",
            "create_new_meal": "create_new_meal",
            "new_intake": "create_new_meal",
            "attach": "attach_to_existing_meal",
            "attach_to_existing_meal": "attach_to_existing_meal",
            "attach_to_existing": "attach_to_existing_meal",
            "attach_to_active": "attach_to_existing_meal",
            "continue_active_meal": "attach_to_existing_meal",
            "boundary_ambiguous": "boundary_ambiguous",
            "ambiguous": "boundary_ambiguous",
            "none": "none",
        }
        meal_link_action = legacy_map.get(legacy_meal_link_decision, fallback.meal_link_action)
    if meal_link_action == "boundary_ambiguous" and not intent:
        intent = "clarification"
    target_meal_id = _safe_int(
        data.get("target_meal_id", data.get("attach_to_meal_id", data.get("active_meal_log_id", data.get("candidate_meal_id")))),
        fallback.target_meal_id,
    )
    clarification_blocking = data.get("clarification_blocking")
    if clarification_blocking is None:
        clarification_blocking = bool(data.get("boundary_ambiguous", False))
    boundary_reason = str(data.get("boundary_reason") or data.get("reasoning") or fallback.boundary_reason)
    return TaskMealLinkResult(
        intent=str(intent or fallback.intent),  # type: ignore[arg-type]
        scope=str(scope or fallback.scope),  # type: ignore[arg-type]
        meal_link_action=str(meal_link_action or fallback.meal_link_action),  # type: ignore[arg-type]
        target_meal_id=target_meal_id,
        link_confidence=str(data.get("link_confidence") or fallback.link_confidence),  # type: ignore[arg-type]
        boundary_reason=boundary_reason,
        clarification_blocking=bool(clarification_blocking),
        normalized_user_input=str(
            data.get("normalized_user_input")
            or data.get("candidate_meal_title")
            or fallback.normalized_user_input
        ),
    )


def _safe_int(value: Any, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
