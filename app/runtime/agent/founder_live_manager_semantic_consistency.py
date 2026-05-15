from __future__ import annotations

from typing import Any


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
