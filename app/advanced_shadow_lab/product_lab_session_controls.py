from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_control_state import (
    build_product_lab_control_state,
)
from app.advanced_shadow_lab.product_lab_chat_control_events import (
    post_turn_chat_control_events,
)
from app.advanced_shadow_lab.product_lab_session_policy import lab_now_minute
from app.advanced_shadow_lab.product_lab_turn_policy import observed_material_signals


def post_turn_control_state(
    *,
    session_id: str,
    turn_id: str,
    turn_spec: Mapping[str, Any],
    turn_artifact: Mapping[str, Any],
    prior_journal: list[Mapping[str, Any]],
    control_events: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    events = (
        list(control_events)
        if control_events is not None
        else post_turn_control_events(turn_spec=turn_spec, turn_artifact=turn_artifact)
    )
    return build_product_lab_control_state(
        session_id=session_id,
        turn_id=turn_id,
        lab_now_minute=lab_now_minute(turn_spec),
        observed_material_signals=observed_material_signals(turn_spec),
        candidates=chat_packets(turn_artifact),
        prior_control_journal=prior_journal,
        control_events=events,
    )


def post_turn_control_state_and_event_ids(
    *,
    session_id: str,
    turn_id: str,
    turn_spec: Mapping[str, Any],
    turn_artifact: Mapping[str, Any],
    prior_journal: list[Mapping[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    events = post_turn_control_events(turn_spec=turn_spec, turn_artifact=turn_artifact)
    return (
        post_turn_control_state(
            session_id=session_id,
            turn_id=turn_id,
            turn_spec=turn_spec,
            turn_artifact=turn_artifact,
            prior_journal=prior_journal,
            control_events=events,
        ),
        event_ids(events),
    )


def release_completed_controls(
    journal: list[Mapping[str, Any]],
    turn_artifact: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    released = {
        str(state.get("active_control_event_id") or "")
        for state in candidate_states(turn_artifact)
        if state.get("suppression_reason")
        in {"released_by_material_signal", "released_by_snooze_window"}
    }
    return [
        entry
        for entry in journal
        if str(entry.get("event_id") or "") not in released
    ]


def event_ids(journal: Any) -> list[str]:
    return [
        str(entry.get("event_id") or "")
        for entry in journal
        if isinstance(entry, Mapping)
    ]


def post_turn_events(turn_spec: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [
        item
        for item in turn_spec.get("post_turn_control_events") or []
        if isinstance(item, Mapping)
    ]


def post_turn_control_events(
    *,
    turn_spec: Mapping[str, Any],
    turn_artifact: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    return [
        *post_turn_events(turn_spec),
        *post_turn_chat_control_events(
            turn_spec=turn_spec,
            turn_artifact=turn_artifact,
        ),
    ]


def chat_packets(turn_artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    packet = turn_artifact.get("lab_chat_response_packet")
    if not isinstance(packet, Mapping):
        return []
    return [item for item in packet.get("chat_packets") or [] if isinstance(item, Mapping)]


def candidate_states(turn_artifact: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    packet = turn_artifact.get("lab_chat_response_packet")
    if not isinstance(packet, Mapping):
        return []
    return [
        item for item in packet.get("candidate_states") or [] if isinstance(item, Mapping)
    ]


__all__ = [
    "event_ids",
    "post_turn_control_events",
    "post_turn_control_state",
    "post_turn_control_state_and_event_ids",
    "post_turn_events",
    "release_completed_controls",
]
