from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_memory_records import RAW_FIELD_NAMES
from app.advanced_shadow_lab.product_lab_session_store import unsafe_segment_blocker


SUPPORTED_ACTIONS = {"remember_memory"}
ACTION_FIELDS = {
    "event_id",
    "action",
    "target_candidate_id",
    "signal_type",
    "summary",
    "source_object_refs",
    "intended_consumers",
}


def build_memory_signals_from_action_events(
    *,
    session_id: str,
    turn_id: str,
    turn_artifact: Mapping[str, Any] | None,
    action_events: list[Mapping[str, Any]],
) -> dict[str, Any]:
    messages = _messages_by_candidate_id(turn_artifact or {})
    blockers: list[str] = []
    signals: list[dict[str, Any]] = []
    for event in action_events:
        signal, event_blockers = _signal_from_action_event(event, messages=messages)
        blockers.extend(event_blockers)
        if signal:
            signals.append(signal)
    if blockers:
        signals = []
    return {
        "artifact_type": "advanced_product_lab_memory_action_signal_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "session_id": session_id,
        "turn_id": turn_id,
        "action_event_count": len(action_events),
        "derived_signal_count": len(signals),
        "memory_signal_events": signals,
        "raw_user_text_semantic_inference_performed": False,
        "semantic_inference_used": False,
        "no_raw_keyword_semantic_oracle": True,
        "lab_only_memory_candidate": True,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _signal_from_action_event(
    event: Mapping[str, Any],
    *,
    messages: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, Any] | None, list[str]]:
    event_id = str(event.get("event_id") or "")
    action = str(event.get("action") or "")
    target_candidate_id = str(event.get("target_candidate_id") or "")
    blockers = _event_blockers(event_id, action, target_candidate_id, messages)
    if blockers:
        return None, blockers
    message = messages.get(target_candidate_id, {})
    signal = {
        "signal_id": event_id,
        "signal_type": str(event.get("signal_type") or ""),
        "summary": str(event.get("summary") or "").strip(),
        "source_object_refs": _source_refs(event, message, target_candidate_id),
        "intended_consumers": [
            str(consumer) for consumer in event.get("intended_consumers") or []
        ],
        **_payload(event),
    }
    return signal, []


def _event_blockers(
    event_id: str,
    action: str,
    target_candidate_id: str,
    messages: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    label = event_id or "missing"
    blockers = [
        blocker
        for blocker in (
            unsafe_segment_blocker("event_id", event_id),
            None if action in SUPPORTED_ACTIONS else f"action.unsupported:{action}",
            None if target_candidate_id else "target_candidate_id.missing",
            None
            if target_candidate_id in messages
            else f"target_candidate_id.not_visible:{target_candidate_id}",
        )
        if blocker
    ]
    return [f"memory_action.{label}.{blocker}" for blocker in blockers]


def _source_refs(
    event: Mapping[str, Any],
    message: Mapping[str, Any],
    target_candidate_id: str,
) -> list[str]:
    refs = [
        str(ref) for ref in event.get("source_object_refs") or [] if str(ref)
    ]
    if not refs:
        refs = [
            f"memory_action:{event.get('event_id')}",
            f"candidate:{target_candidate_id}",
        ]
    refs.extend(str(ref) for ref in message.get("product_runtime_output_refs") or [])
    return refs


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in event.items()
        if str(key) not in ACTION_FIELDS and str(key) not in RAW_FIELD_NAMES
    }


def _messages_by_candidate_id(
    turn_artifact: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    surface = turn_artifact.get("lab_chat_surface")
    if not isinstance(surface, Mapping):
        return {}
    return {
        str(message.get("candidate_id") or ""): message
        for message in surface.get("messages") or []
        if isinstance(message, Mapping)
    }


__all__ = ["build_memory_signals_from_action_events"]
