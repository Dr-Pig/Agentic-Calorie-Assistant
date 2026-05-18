from __future__ import annotations

from typing import Any

from app.shared.contracts.manager_evidence_target import manager_owned_target_failure_reason


def payload_requests_estimate_nutrition(payload: dict[str, Any]) -> bool:
    tool_calls = payload.get("tool_calls")
    if not isinstance(tool_calls, list):
        return False
    return any(
        isinstance(item, dict)
        and str(item.get("name") or item.get("tool_name") or "").strip() == "estimate_nutrition"
        for item in tool_calls
    )


def payload_has_unselected_resolve_correction_target(payload: dict[str, Any]) -> bool:
    tool_calls = payload.get("tool_calls")
    if not isinstance(tool_calls, list):
        return False
    for item in tool_calls:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("tool_name") or "").strip()
        if name != "resolve_correction_target":
            continue
        arguments = item.get("arguments")
        if not isinstance(arguments, dict):
            return True
        if any(
            arguments.get(key) not in (None, "")
            for key in ("meal_thread_id", "meal_item_id", "canonical_name", "target_display_name")
        ):
            continue
        return True
    return False


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


def _targetless_estimate_nutrition_reason(payload: dict[str, Any]) -> str | None:
    for tool_call in _estimate_nutrition_tool_calls(payload):
        arguments = tool_call.get("arguments")
        reason = manager_owned_target_failure_reason(arguments if isinstance(arguments, dict) else {})
        if reason is not None:
            return reason
    return None


def validate_tool_call_contracts(payload: dict[str, Any], evidence_state: Any) -> None:
    nutrition_evidence_present = (
        evidence_state.get("nutrition_evidence_present")
        if isinstance(evidence_state, dict)
        else None
    )
    if (
        nutrition_evidence_present is True
        and str(payload.get("manager_action") or "") == "call_tools"
        and payload_requests_estimate_nutrition(payload)
    ):
        raise RuntimeError(
            "founder live manager contract nutrition evidence already present; "
            "return manager_action='final' and map the existing current-loop nutrition evidence to the "
            "Manager-owned final_action instead of calling estimate_nutrition again"
        )
    if (
        str(payload.get("manager_action") or "") == "call_tools"
        and payload_has_unselected_resolve_correction_target(payload)
    ):
        raise RuntimeError(
            "founder live manager contract resolve_correction_target requires Manager-selected target argument; "
            "select a concrete meal_thread_id, meal_item_id, canonical_name, or target_display_name from context "
            "candidates before calling the tool"
        )
    if str(payload.get("manager_action") or "") == "call_tools":
        targetless_reason = _targetless_estimate_nutrition_reason(payload)
        if targetless_reason is not None:
            raise RuntimeError(
                "founder live manager contract estimate_nutrition requires Manager-owned "
                f"evidence target: {targetless_reason}; provide base_dish, exact product "
                "identity, multiple listed_items, or ask a follow-up before calling the tool"
            )
