from __future__ import annotations

from typing import Any

from app.runtime.contracts.trace import MANAGER_LOOP_STAGE


def entry_handoff_tool_calls(manager_decision: Any) -> list[dict[str, Any]]:
    if str(getattr(manager_decision, "workflow_effect", "") or "") != "route_to_intake":
        return []
    semantic_decision = dict(getattr(manager_decision, "semantic_decision", {}) or {})
    target = dict(getattr(manager_decision, "target_attachment", {}) or {})
    semantic_target = dict(semantic_decision.get("target_attachment") or {})
    merged_target = {**target, **semantic_target}
    final_candidate = str(semantic_decision.get("final_action_candidate") or "")
    operation = str(merged_target.get("operation") or merged_target.get("correction_operation") or "").strip()
    if final_candidate != "correction_applied" or operation != "remove_item":
        return []
    arguments = {
        key: value
        for key, value in {
            "canonical_name": merged_target.get("canonical_name"),
            "meal_thread_id": merged_target.get("meal_thread_id"),
            "meal_item_id": merged_target.get("meal_item_id"),
            "operation": "remove_item",
            "target_proposal_source": "entry_manager_handoff",
        }.items()
        if value not in (None, "")
    }
    return [{"name": "resolve_correction_target", "arguments": arguments}]


def entry_handoff_manager_round(
    *,
    manager_decision: Any,
    tool_calls: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "round_index": 0,
        "stage": MANAGER_LOOP_STAGE,
        "manager_loop_scope": "intake_execution",
        "decision": {
            "manager_action": "call_tools",
            "tool_calls": tool_calls,
            "final_action": dict(getattr(manager_decision, "semantic_decision", {}) or {}).get(
                "final_action_candidate",
                "no_commit",
            ),
            "workflow_effect": "entry_handoff_tool_execution",
            "semantic_decision": dict(getattr(manager_decision, "semantic_decision", {}) or {}),
        },
        "trace": {
            "source": "entry_manager_route_to_intake_handoff",
            "entry_manager_scope": "turn_entry_or_read_only",
            "deterministic_role": "execute_manager_owned_handoff_tool_plan_only",
        },
        "tool_results": tool_results,
    }


async def execute_entry_handoff_seed(
    *,
    manager_decision: Any,
    tool_executor: Any,
    raw_user_input: str,
    resolved_state: Any,
    now_ms: Any,
    record_timing: Any,
) -> dict[str, Any]:
    tool_calls = entry_handoff_tool_calls(manager_decision)
    if not tool_calls:
        return {"tool_results": [], "manager_rounds": []}
    stage_start = now_ms()
    executed = await tool_executor(
        tool_calls=tool_calls,
        raw_user_input=raw_user_input,
        resolved_state=resolved_state,
        tool_results=[],
    )
    tool_results = [dict(item) for item in executed if isinstance(item, dict)]
    record_timing("entry_handoff_tool_plan", now_ms() - stage_start)
    return {
        "tool_results": tool_results,
        "manager_rounds": [
            entry_handoff_manager_round(
                manager_decision=manager_decision,
                tool_calls=tool_calls,
                tool_results=tool_results,
            )
        ],
    }
