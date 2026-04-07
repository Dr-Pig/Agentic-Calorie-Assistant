from __future__ import annotations

import os
from typing import Any, Callable

from ..schemas import PlanningBrief, TurnIntentResult


NormalizeText = Callable[[str], str]
NormalizeUserInput = Callable[[str], dict[str, Any]]


def planner_enabled() -> bool:
    return os.getenv("TEXT_MEAL_ENABLE_PLANNER", "1").strip().lower() in {"1", "true", "yes", "on"}


def ensure_planning_brief_model(value: Any) -> PlanningBrief:
    if isinstance(value, PlanningBrief):
        return value
    if isinstance(value, dict):
        return PlanningBrief(**value)
    return PlanningBrief()


def fallback_planner_result(
    raw_user_input: str,
    *,
    normalize_text: NormalizeText,
    normalize_user_input_for_estimation: NormalizeUserInput,
) -> TurnIntentResult:
    normalization = normalize_user_input_for_estimation(raw_user_input)
    normalized_text = str(normalization["normalized_text"]).strip() or normalize_text(raw_user_input)
    planning_brief = PlanningBrief(
        intent="food_estimation",
        resolved_query=normalized_text,
        resolution_mode="none",
        entity_type="unknown",
        state_link="standalone",
        clarification_needed=False,
        evidence_strategy="local_retrieval_first",
        primary_prompt_hints=[],
        confidence="low",
        active_object="new_meal",
        slot_state="enough_to_estimate",
        candidate_tool_calls=["resolve_exact_item", "resolve_ingredient_anchors"],
    )
    return TurnIntentResult(
        intent="food_estimation",
        meal_boundary="start_new_meal",
        active_meal_reference=None,
        boundary_confidence="low",
        resolved_query="",
        resolution_mode="none",
        normalized_user_input=normalized_text,
        input_signals={
            "modalities": ["text"],
            "foods": [],
            "brands": [],
            "portion_clues": [],
        },
        missing_info=[],
        route_hints={
            "planner_source": "fallback_normalizer",
            "normalizer_applied": bool(normalization["normalizer_applied"]),
            "normalizer_notes": list(normalization["notes"]),
        },
        planning_brief=planning_brief,
    )


def normalize_planner_result(
    raw: dict[str, Any],
    *,
    raw_user_input: str,
    normalize_text: NormalizeText,
    normalize_user_input_for_estimation: NormalizeUserInput,
) -> TurnIntentResult:
    if not isinstance(raw, dict):
        return fallback_planner_result(
            raw_user_input,
            normalize_text=normalize_text,
            normalize_user_input_for_estimation=normalize_user_input_for_estimation,
        )

    normalized_user_input = normalize_text(str(raw.get("normalized_user_input", "")))
    if not normalized_user_input:
        normalized_user_input = fallback_planner_result(
            raw_user_input,
            normalize_text=normalize_text,
            normalize_user_input_for_estimation=normalize_user_input_for_estimation,
        ).normalized_user_input

    input_signals_raw = raw.get("input_signals") if isinstance(raw.get("input_signals"), dict) else {}
    modalities = [str(item).strip() for item in input_signals_raw.get("modalities", []) if str(item).strip()]
    foods = [str(item).strip() for item in input_signals_raw.get("foods", []) if str(item).strip()]
    brands = [str(item).strip() for item in input_signals_raw.get("brands", []) if str(item).strip()]
    portion_clues = [str(item).strip() for item in input_signals_raw.get("portion_clues", []) if str(item).strip()]

    try:
        planning_brief_raw = raw.get("planning_brief") if isinstance(raw.get("planning_brief"), dict) else {}
        planning_brief = PlanningBrief(
            intent=str(planning_brief_raw.get("intent") or raw.get("intent") or "food_estimation"),
            resolved_query=str(planning_brief_raw.get("resolved_query") or raw.get("resolved_query") or normalized_user_input),
            resolution_mode=str(planning_brief_raw.get("resolution_mode") or raw.get("resolution_mode") or "none"),
            entity_type=str(planning_brief_raw.get("entity_type") or raw.get("entity_type") or "unknown"),
            state_link=str(planning_brief_raw.get("state_link") or raw.get("state_link") or "standalone"),
            clarification_needed=bool(planning_brief_raw.get("clarification_needed", raw.get("clarification_needed", False))),
            clarification_targets=[str(item).strip() for item in planning_brief_raw.get("clarification_targets", raw.get("clarification_targets", [])) if str(item).strip()],
            risk_focus=[str(item).strip() for item in planning_brief_raw.get("risk_focus", raw.get("risk_focus", [])) if str(item).strip()],
            evidence_strategy=str(planning_brief_raw.get("evidence_strategy") or raw.get("evidence_strategy") or "local_retrieval_first"),
            primary_prompt_hints=[str(item).strip() for item in planning_brief_raw.get("primary_prompt_hints", raw.get("primary_prompt_hints", [])) if str(item).strip()],
            confidence=str(planning_brief_raw.get("confidence") or raw.get("confidence") or "low"),
            active_object=str(planning_brief_raw.get("active_object") or raw.get("active_object") or "new_meal"),
            slot_state=str(planning_brief_raw.get("slot_state") or raw.get("slot_state") or "enough_to_estimate"),
            candidate_tool_calls=[str(item).strip() for item in planning_brief_raw.get("candidate_tool_calls", raw.get("candidate_tool_calls", [])) if str(item).strip()],
        )
        intent = str(raw.get("intent") or "food_estimation")
        meal_boundary = str(raw.get("meal_boundary") or "start_new_meal")
        if planning_brief.intent and planning_brief.intent != intent:
            intent = planning_brief.intent
        if planning_brief.slot_state == "enough_to_estimate" and intent == "clarification":
            intent = planning_brief.intent if planning_brief.intent != "clarification" else "food_estimation"
        if planning_brief.slot_state == "enough_to_estimate" and meal_boundary == "boundary_clarification":
            meal_boundary = "start_new_meal"
        return TurnIntentResult(
            intent=intent,
            meal_boundary=meal_boundary,
            active_meal_reference=raw.get("active_meal_reference") if isinstance(raw.get("active_meal_reference"), int) or raw.get("active_meal_reference") is None else None,
            boundary_confidence=str(raw.get("boundary_confidence") or "low"),
            resolved_query=str(raw.get("resolved_query") or ""),
            resolution_mode=str(raw.get("resolution_mode") or "none"),
            normalized_user_input=normalized_user_input,
            input_signals={
                "modalities": modalities or ["text"],
                "foods": foods,
                "brands": brands,
                "portion_clues": portion_clues,
            },
            missing_info=[str(item).strip() for item in raw.get("missing_info", []) if str(item).strip()],
            route_hints=raw.get("route_hints") if isinstance(raw.get("route_hints"), dict) else {},
            planning_brief=planning_brief,
        )
    except Exception:
        return fallback_planner_result(
            raw_user_input,
            normalize_text=normalize_text,
            normalize_user_input_for_estimation=normalize_user_input_for_estimation,
        )
