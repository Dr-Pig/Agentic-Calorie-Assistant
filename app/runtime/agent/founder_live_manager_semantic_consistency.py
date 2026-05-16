from __future__ import annotations

from typing import Any


def _non_empty_string_items(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _estimate_nutrition_tool_calls(payload: dict[str, Any]) -> list[dict[str, Any]]:
    tool_calls = payload.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    return [
        item
        for item in tool_calls
        if isinstance(item, dict)
        and str(item.get("name") or item.get("tool_name") or "").strip() == "estimate_nutrition"
    ]


def _tool_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
    arguments = tool_call.get("arguments")
    return arguments if isinstance(arguments, dict) else {}


def _tool_argument_semantic_decision(arguments: dict[str, Any]) -> dict[str, Any]:
    nested = arguments.get("manager_semantic_decision")
    return nested if isinstance(nested, dict) else arguments


def _validate_listed_item_tool_argument_consistency(
    *,
    payload: dict[str, Any],
    semantic_decision: dict[str, Any],
) -> None:
    listed_items = _non_empty_string_items(semantic_decision.get("listed_items"))
    retrieval_goal = str(semantic_decision.get("retrieval_goal") or "")
    if not listed_items and retrieval_goal != "listed_item_lookup":
        return
    if str(payload.get("manager_action") or "") != "call_tools":
        return
    for tool_call in _estimate_nutrition_tool_calls(payload):
        arguments = _tool_arguments(tool_call)
        tool_semantic_decision = _tool_argument_semantic_decision(arguments)
        tool_retrieval_goal = str(
            tool_semantic_decision.get("retrieval_goal")
            or arguments.get("retrieval_goal")
            or ""
        )
        tool_listed_items = _non_empty_string_items(
            tool_semantic_decision.get("listed_items")
            or arguments.get("listed_items")
        )
        if tool_retrieval_goal != "listed_item_lookup":
            raise RuntimeError(
                "founder live manager contract listed-item estimate_nutrition arguments "
                "must use retrieval_goal='listed_item_lookup'"
            )
        if not tool_listed_items:
            raise RuntimeError(
                "founder live manager contract listed-item estimate_nutrition arguments "
                "must carry Manager-owned listed_items"
            )


def validate_semantic_field_consistency(payload: dict[str, Any]) -> None:
    semantic_decision = payload.get("semantic_decision")
    if not isinstance(semantic_decision, dict):
        return
    retrieval_goal = str(semantic_decision.get("retrieval_goal") or "")
    listed_items = semantic_decision.get("listed_items")
    if retrieval_goal == "listed_item_lookup" and not (
        isinstance(listed_items, list) and any(str(item or "").strip() for item in listed_items)
    ):
        raise RuntimeError(
            "founder live manager contract listed_item_lookup requires "
            "semantic_decision.listed_items from the Manager-owned semantic decision"
        )
    if retrieval_goal == "listed_item_lookup" and len(_non_empty_string_items(listed_items)) == 1:
        raise RuntimeError(
            "founder live manager contract listed_item_lookup requires multiple Manager-owned "
            "component items; a single base dish must use generic/exact retrieval, or ask follow-up "
            "when bundle composition is unclear"
        )
    if (
        isinstance(listed_items, list)
        and any(str(item or "").strip() for item in listed_items)
        and retrieval_goal
        and retrieval_goal != "listed_item_lookup"
    ):
        raise RuntimeError(
            "founder live manager contract non-empty semantic_decision.listed_items "
            "requires retrieval_goal='listed_item_lookup'"
        )
    modifier_hints = semantic_decision.get("modifier_hints")
    manager_identified_component_hints = (
        isinstance(modifier_hints, list) and any(str(item or "").strip() for item in modifier_hints)
    )
    if (
        str(semantic_decision.get("source") or "") == "branded_combo"
        and retrieval_goal == "exact_brand_lookup"
        and manager_identified_component_hints
        and not (isinstance(listed_items, list) and any(str(item or "").strip() for item in listed_items))
    ):
        raise RuntimeError(
            "founder live manager contract branded_combo with manager-identified component hints "
            "requires semantic_decision.listed_items and retrieval_goal='listed_item_lookup'"
        )
    _validate_listed_item_tool_argument_consistency(
        payload=payload,
        semantic_decision=semantic_decision,
    )


def validate_body_observation_scope_handoff(
    *,
    payload: dict[str, Any],
    semantic_decision: dict[str, Any],
    semantic_intent: str,
    final_action: str,
    constraints: dict[str, Any] | None,
) -> None:
    manager_loop_scope = str(constraints.get("manager_loop_scope") or "") if isinstance(constraints, dict) else ""
    if semantic_intent != "body_observation" or manager_loop_scope == "body_observation":
        return
    observed_workflow_effect = str(payload.get("workflow_effect") or semantic_decision.get("workflow_effect") or "")
    if (
        str(payload.get("manager_action") or "") != "final"
        or final_action != "no_commit"
        or observed_workflow_effect != "route_to_body_observation"
        or payload.get("tool_calls") not in ([], None)
    ):
        raise RuntimeError(
            "founder live manager contract body_observation handoff requires "
            "manager_action='final', tool_calls=[], final_action='no_commit', "
            "and workflow_effect='route_to_body_observation' outside body_observation scope"
        )
    final_action_candidate = str(semantic_decision.get("final_action_candidate") or "")
    if final_action_candidate not in {"", "no_commit", "route_to_body_observation"}:
        raise RuntimeError(
            "founder live manager contract body_observation handoff requires "
            "semantic_decision.final_action_candidate='no_commit' outside body_observation scope"
        )
