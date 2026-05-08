from __future__ import annotations

from typing import Any


INTAKE_EXECUTION_TOOLS = frozenset({"estimate_nutrition", "resolve_correction_target", "compare_against_budget"})


def safe_failure_payload() -> dict[str, Any]:
    return {
        "intent": "manager_unavailable",
        "intent_type": "manager_unavailable",
        "manager_action": "final",
        "final_action": "no_commit",
        "workflow_effect": "safe_failure",
        "target_attachment": {"mode": "none"},
        "exactness": "unknown",
        "confidence": "low",
        "evidence_posture": "insufficient",
        "repair_ack": False,
        "answer_contract": {
            "reply_text": "I could not complete that request safely, so I did not change your log."
        },
        "uncertainty_posture": "blocked",
        "evidence_honesty_posture": "insufficient",
    }


def manager_scope_policy_payload(manager_loop_scope: str, available_tools: tuple[str, ...]) -> dict[str, Any]:
    if manager_loop_scope != "turn_entry_or_read_only":
        return {
            "policy_id": f"manager_scope_policy.{manager_loop_scope}.v1",
            "manager_loop_scope": manager_loop_scope,
            "available_tools": list(available_tools),
            "deterministic_boundary": "runtime_validates_tool_scope_only_no_raw_text_semantic_routing",
        }
    return {
        "policy_id": "manager_scope_policy.turn_entry_or_read_only.v1",
        "manager_loop_scope": manager_loop_scope,
        "available_tools": list(available_tools),
        "unavailable_intake_tools": sorted(INTAKE_EXECUTION_TOOLS.difference(available_tools)),
        "if_intake_execution_needed": {
            "manager_action": "final",
            "tool_calls": [],
            "intent_type": "log_meal",
            "final_action": "no_commit",
            "workflow_effect": "route_to_intake",
        },
        "deterministic_boundary": "runtime_validates_tool_scope_only_no_raw_text_semantic_routing",
    }


def tool_call_scope_boundary(
    *,
    payload: dict[str, Any],
    calls: list[dict[str, Any]],
    available_tools: tuple[str, ...],
    manager_loop_scope: str,
) -> dict[str, Any] | None:
    unavailable_tools = [
        str(call.get("name") or call.get("tool_name") or "")
        for call in calls
        if str(call.get("name") or call.get("tool_name") or "") not in available_tools
    ]
    if not unavailable_tools:
        return None
    if manager_loop_scope == "turn_entry_or_read_only" and set(unavailable_tools).issubset(INTAKE_EXECUTION_TOOLS):
        return {
            "payload": _route_to_intake_payload(payload),
            "tool_result": {
                "handoff_family": "entry_scope_requested_intake_tool",
                "requested_tools": unavailable_tools,
                "available_tools": list(available_tools),
                "target_scope": "intake_execution",
                "mutation_result": {"state_mutation": "none"},
                "confidence": "bounded_handoff",
            },
            "failure_family": None,
        }
    return {
        "payload": safe_failure_payload(),
        "tool_result": {
            "failure_family": "tool_not_available",
            "requested_tools": unavailable_tools,
            "available_tools": list(available_tools),
            "mutation_result": {"state_mutation": "none"},
            "confidence": "none",
        },
        "failure_family": "tool_not_available",
    }


def _route_to_intake_payload(payload: dict[str, Any]) -> dict[str, Any]:
    routed = dict(payload)
    routed["manager_action"] = "final"
    routed["tool_calls"] = []
    routed["intent"] = str(payload.get("intent") or payload.get("intent_type") or "log_meal")
    routed["intent_type"] = str(payload.get("intent_type") or "log_meal")
    routed["final_action"] = "no_commit"
    routed["workflow_effect"] = "route_to_intake"
    routed.setdefault("target_attachment", {})
    routed.setdefault("exactness", "unknown")
    routed.setdefault("confidence", "low")
    routed.setdefault("evidence_posture", "requires_intake_execution")
    routed.setdefault("repair_ack", False)
    routed.setdefault("answer_contract", {})
    routed.setdefault("uncertainty_posture", "pending_intake_execution")
    routed.setdefault("evidence_honesty_posture", "pending_intake_execution")
    return routed


__all__ = ["manager_scope_policy_payload", "safe_failure_payload", "tool_call_scope_boundary"]
