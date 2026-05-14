from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_feedback_event_bridge import (
    feedback_projection_for_chat_control,
)


CONTROL_ACTIONS = {"dismiss", "snooze", "undo", "opt_out", "reopen_or_modify"}


def post_turn_chat_control_events(
    *,
    turn_spec: Mapping[str, Any],
    turn_artifact: Mapping[str, Any],
) -> list[dict[str, Any]]:
    packets = _visible_packets_by_id(turn_artifact)
    return [
        _control_event(turn_spec, action_spec, packets[target_id])
        for action_spec in _post_turn_chat_actions(turn_spec)
        if _action(action_spec) in CONTROL_ACTIONS
        for target_id in [str(action_spec.get("target_candidate_id") or "")]
        if target_id in packets
    ]


def _control_event(
    turn_spec: Mapping[str, Any],
    action_spec: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    action = _action(action_spec)
    target_id = str(action_spec.get("target_candidate_id") or "")
    next_signal = str(
        action_spec.get("next_signal_required")
        or packet.get("next_signal_required")
        or ""
    )
    source_refs = _source_refs(packet)
    return {
        "event_id": str(action_spec.get("event_id") or ""),
        "action": action,
        "target_candidate_id": target_id,
        "trigger_type": str(packet.get("trigger_type") or ""),
        "scope": str(action_spec.get("scope") or "candidate_instance"),
        "dismiss_reason": action_spec.get("dismiss_reason"),
        "next_signal_required": next_signal,
        "snooze_minutes": action_spec.get("snooze_minutes"),
        "release_signal": str(action_spec.get("release_signal") or next_signal),
        "undo_event_id": str(action_spec.get("undo_event_id") or ""),
        "reopen_target_event_id": str(
            action_spec.get("reopen_target_event_id")
            or action_spec.get("undo_event_id")
            or ""
        ),
        "source_packet_id": target_id,
        "source_workflow_family": str(packet.get("workflow_family") or ""),
        "source_chat_action_event_id": str(action_spec.get("event_id") or ""),
        "source_refs": source_refs,
        "chat_control_action_bridge_used": True,
        **feedback_projection_for_chat_control(
            turn_spec=turn_spec,
            action_spec=action_spec,
            packet=packet,
            source_refs=source_refs,
        ),
    }


def _visible_packets_by_id(
    turn_artifact: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    packet = turn_artifact.get("lab_chat_response_packet")
    if not isinstance(packet, Mapping):
        return {}
    return {
        str(item.get("packet_id") or ""): item
        for item in packet.get("visible_chat_packets") or []
        if isinstance(item, Mapping) and str(item.get("packet_id") or "")
    }


def _post_turn_chat_actions(turn_spec: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in turn_spec.get("post_turn_chat_actions") or []
        if isinstance(item, Mapping)
    ]


def _source_refs(packet: Mapping[str, Any]) -> list[str]:
    return [
        str(item)
        for item in [
            packet.get("artifact_type"),
            packet.get("packet_kind"),
            *list(packet.get("product_runtime_output_refs") or []),
            *list(packet.get("source_artifact_refs") or []),
        ]
        if str(item or "")
    ]


def _action(action_spec: Mapping[str, Any]) -> str:
    return str(action_spec.get("action") or "")


__all__ = ["CONTROL_ACTIONS", "post_turn_chat_control_events"]
