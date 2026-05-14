from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.memory_feedback_projection import (
    project_feedback_event_to_shadow_controls,
)

LAB_SCOPE_KEYS = {
    "user_id": "advanced_product_lab_user",
    "workspace_id": "advanced_product_lab_workspace",
    "project_id": "advanced-product-lab",
    "surface": "chat",
}


def feedback_projection_for_chat_control(
    *,
    turn_spec: Mapping[str, Any],
    action_spec: Mapping[str, Any],
    packet: Mapping[str, Any],
    source_refs: list[str],
) -> dict[str, Any]:
    event = _feedback_event(turn_spec=turn_spec, action_spec=action_spec)
    projection = project_feedback_event_to_shadow_controls(
        feedback_event=event,
        targets=[
            {
                "target_type": "proactive_candidate",
                "target_id": event["target_id"],
                "scope_keys": event["scope_keys"],
                "source_turn_ids": [event["source_turn_id"]],
                "source_refs": list(source_refs),
                "trigger_type": str(packet.get("trigger_type") or ""),
                "next_signal_required": str(packet.get("next_signal_required") or ""),
            }
        ],
    )
    return {
        "feedback_event": event,
        "feedback_event_projection": projection,
        "feedback_event_projection_ready": projection.get("status") == "pass",
        "feedback_event_role": "audit_input_only",
    }


def _feedback_event(
    *,
    turn_spec: Mapping[str, Any],
    action_spec: Mapping[str, Any],
) -> dict[str, Any]:
    action = _feedback_action(str(action_spec.get("action") or ""))
    return {
        "target_type": "proactive_candidate",
        "target_id": str(action_spec.get("target_candidate_id") or ""),
        "action": action,
        "reason": str(action_spec.get("dismiss_reason") or ""),
        "snooze_until": _snooze_until(action=action, action_spec=action_spec),
        "source_turn_id": str(turn_spec.get("turn_id") or ""),
        "scope_keys": _scope_keys(turn_spec),
    }


def _feedback_action(action: str) -> str:
    return "reopen" if action == "reopen_or_modify" else action


def _snooze_until(*, action: str, action_spec: Mapping[str, Any]) -> str | None:
    if action != "snooze":
        return None
    explicit = str(action_spec.get("snooze_until") or "")
    if explicit:
        return explicit
    minutes = action_spec.get("snooze_minutes")
    return f"lab-minute:+{minutes}" if minutes else None


def _scope_keys(turn_spec: Mapping[str, Any]) -> dict[str, str]:
    scope = turn_spec.get("scope_keys")
    if not isinstance(scope, Mapping):
        return dict(LAB_SCOPE_KEYS)
    return {
        "user_id": str(scope.get("user_id") or LAB_SCOPE_KEYS["user_id"]),
        "workspace_id": str(scope.get("workspace_id") or LAB_SCOPE_KEYS["workspace_id"]),
        "project_id": str(scope.get("project_id") or LAB_SCOPE_KEYS["project_id"]),
        "surface": str(scope.get("surface") or LAB_SCOPE_KEYS["surface"]),
    }


__all__ = ["LAB_SCOPE_KEYS", "feedback_projection_for_chat_control"]
