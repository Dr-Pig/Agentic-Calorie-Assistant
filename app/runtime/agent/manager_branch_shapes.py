from __future__ import annotations

from typing import Any


def manager_item_results_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "food_name": {"type": "string"},
                "kcal_range": {
                    "type": "array",
                    "items": {"type": "number"},
                },
                "likely_kcal": {"type": "number"},
                "uncertainty": {"type": "string"},
                "evidence_used": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["food_name", "kcal_range", "likely_kcal", "uncertainty", "evidence_used"],
            "additionalProperties": False,
        },
    }


def tool_call_names(payload: dict[str, Any]) -> list[str]:
    tool_calls = payload.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    names: list[str] = []
    for item in tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
            if name:
                names.append(name)
    return names


def contains_any_key(value: Any, keys: set[str]) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in keys:
                found.append(key)
            found.extend(contains_any_key(item, keys))
    elif isinstance(value, list):
        for item in value:
            found.extend(contains_any_key(item, keys))
    return sorted(set(found))


def actual_shape(payload: dict[str, Any]) -> str:
    manager_action = str(payload.get("manager_action") or "")
    final_action = str(payload.get("final_action") or "")
    response_mode = str(payload.get("response_mode") or "")
    workflow_effect = str(payload.get("workflow_effect") or "")
    uncertainty_posture = str(payload.get("uncertainty_posture") or "")
    names = tool_call_names(payload)
    parts: list[str] = []
    if manager_action:
        parts.append(manager_action)
    if final_action:
        parts.append(final_action)
    if names:
        parts.extend(names)
    if response_mode:
        parts.append(f"response_mode={response_mode}")
    if workflow_effect:
        parts.append(f"workflow_effect={workflow_effect}")
    if uncertainty_posture:
        parts.append(f"uncertainty_posture={uncertainty_posture}")
    if contains_any_key(payload, {"item_results", "kcal_range", "likely_kcal"}):
        parts.append("pass1_estimate_fields")
    return ".".join(parts) if parts else "empty"
