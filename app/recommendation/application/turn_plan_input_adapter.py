from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel

from app.shared.contracts.recommendation_tool_arguments import (
    validate_recommendation_tool_arguments,
)


FORBIDDEN_CONTEXT_FIELDS = {"raw_transcript", "messages", "prompt", "raw_user_input"}


def build_recommendation_planning_input(
    *,
    manager_turn_plan: BaseModel | Mapping[str, Any],
    tool_arguments: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any] | None = None,
    rescue_context_pack: Mapping[str, Any] | None = None,
    query_context_pack: Mapping[str, Any] | None = None,
    reusable_meal_context_pack: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    plan = _mapping_from_model(manager_turn_plan)
    tool_validation = validate_recommendation_tool_arguments(tool_arguments)
    blockers = [
        *[
            f"tool_arguments.{blocker}"
            for blocker in tool_validation.get("blockers") or []
        ],
        *_turn_plan_blockers(plan),
        *_context_blockers("memory_context_pack", memory_context_pack or {}),
        *_context_blockers("rescue_context_pack", rescue_context_pack or {}),
        *_context_blockers("query_context_pack", query_context_pack or {}),
        *_context_blockers("reusable_meal_context_pack", reusable_meal_context_pack or {}),
    ]
    return {
        "artifact_type": "recommendation_turn_plan_input_adapter",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "manager_turn_plan_used": True,
        "tool_argument_validation": tool_validation,
        "planning_input": {}
        if blockers
        else _planning_input(
            plan=plan,
            tool_validation=tool_validation,
            memory_context_pack=memory_context_pack or {},
            rescue_context_pack=rescue_context_pack or {},
            query_context_pack=query_context_pack or {},
            reusable_meal_context_pack=reusable_meal_context_pack or {},
        ),
        "raw_user_text_semantic_inference_performed": False,
        "mainline_activation_enabled": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "blockers": blockers,
    }


def inactive_recommendation_planning_input_adapter() -> dict[str, Any]:
    return {
        "artifact_type": "recommendation_turn_plan_input_adapter",
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "manager_turn_plan_used": False,
        "planning_input": {},
        "raw_user_text_semantic_inference_performed": False,
        "mainline_activation_enabled": False,
        "blockers": [],
    }


def _planning_input(
    *,
    plan: Mapping[str, Any],
    tool_validation: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
    rescue_context_pack: Mapping[str, Any],
    query_context_pack: Mapping[str, Any],
    reusable_meal_context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "user_goal": str(plan.get("primary_workflow") or ""),
        "secondary_intents": _string_list(plan.get("secondary_intents")),
        "capability_request": _recommendation_request(plan),
        "ordering_constraints": _string_list(plan.get("ordering_constraints")),
        "response_obligations": _string_list(plan.get("response_obligations")),
        "scope_keys": dict(_mapping(tool_validation.get("normalized_scope_keys"))),
        "context_call_refs": dict(_mapping(tool_validation.get("context_call_refs"))),
        "memory_summary": _memory_summary(memory_context_pack),
        "rescue_summary": _rescue_summary(rescue_context_pack),
        "query_summary": _artifact_summary(query_context_pack),
        "reusable_meal_summary": _artifact_summary(reusable_meal_context_pack),
        "raw_user_text_semantic_inference_performed": False,
        "mainline_activation_enabled": False,
    }


def _turn_plan_blockers(plan: Mapping[str, Any]) -> list[str]:
    if _recommendation_request(plan) and _recommendation_tool_call(plan):
        return []
    return ["manager_turn_plan.recommendation_not_requested"]


def _recommendation_request(plan: Mapping[str, Any]) -> dict[str, Any]:
    for request in plan.get("requested_capabilities") or []:
        item = _mapping(request)
        if item.get("capability_id") == "recommendation":
            return {
                "capability_id": "recommendation",
                "request_mode": str(item.get("request_mode") or ""),
                "priority": item.get("priority") if isinstance(item.get("priority"), int) else 0,
            }
    return {}


def _recommendation_tool_call(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    for candidate in plan.get("candidate_tool_calls") or []:
        item = _mapping(candidate)
        if item.get("tool_name") == "recommendation.run":
            return item
    return {}


def _context_blockers(name: str, context: Mapping[str, Any]) -> list[str]:
    return [
        f"context.{name}.{key}_forbidden"
        for key in FORBIDDEN_CONTEXT_FIELDS
        if key in context
    ]


def _memory_summary(memory_context_pack: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "selected_record_ids": _string_list(memory_context_pack.get("selected_record_ids")),
        "negative_preference_blockers": _string_list(
            memory_context_pack.get("negative_preference_blockers")
        ),
        "entry_summaries": [
            {
                "record_id": str(entry.get("record_id") or ""),
                "memory_type": str(entry.get("memory_type") or ""),
                "summary": str(entry.get("summary") or ""),
            }
            for entry in memory_context_pack.get("entries") or []
            if isinstance(entry, Mapping)
        ][:5],
    }


def _rescue_summary(rescue_context_pack: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rescue_context_present": bool(rescue_context_pack),
        "proposal_presented_to_lab": rescue_context_pack.get("proposal_presented_to_lab")
        is True,
    }


def _artifact_summary(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "context_present": bool(context),
        "artifact_type": str(context.get("artifact_type") or ""),
        "status": str(context.get("status") or ""),
    }


def _mapping_from_model(value: BaseModel | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value if isinstance(value, Mapping) else {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


__all__ = [
    "build_recommendation_planning_input",
    "inactive_recommendation_planning_input_adapter",
]
