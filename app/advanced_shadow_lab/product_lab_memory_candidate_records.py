from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_records import (
    DEFAULT_CONSUMERS,
    RAW_FIELD_NAMES,
    scope_keys,
)
from app.advanced_shadow_lab.product_lab_session_store import unsafe_segment_blocker


CORE_SIGNAL_FIELDS = {
    "signal_id",
    "signal_type",
    "summary",
    "source_object_refs",
    "intended_consumers",
}
REJECTION_SIGNAL_TYPES = {
    "correction_not_memory": "single_turn_correction_not_long_term_memory",
}
SIGNAL_POLICIES = {
    "explicit_preference": {
        "memory_type": "preference",
        "review_action": "promote_with_confirmation",
        "requires_confirmation": True,
    },
    "negative_preference": {
        "memory_type": "negative_preference",
        "review_action": "promote_with_confirmation",
        "requires_confirmation": True,
    },
    "temporary_preference": {
        "memory_type": "temporary_preference",
        "review_action": "promote_until_expiry_with_confirmation",
        "requires_confirmation": True,
    },
    "golden_order": {
        "memory_type": "golden_order",
        "review_action": "promote_with_confirmation",
        "requires_confirmation": True,
    },
    "interaction_preference": {
        "memory_type": "interaction_preference",
        "review_action": "promote_with_confirmation",
        "requires_confirmation": True,
    },
}


def candidate_from_signal(
    signal: Mapping[str, Any],
    *,
    session_id: str,
    turn_id: str,
) -> tuple[dict[str, Any] | None, list[str], dict[str, str] | None]:
    signal_id = str(signal.get("signal_id") or "")
    signal_type = str(signal.get("signal_type") or "")
    blockers = signal_blockers(signal, signal_id=signal_id, signal_type=signal_type)
    if blockers:
        return None, blockers, None
    rejection_reason = REJECTION_SIGNAL_TYPES.get(signal_type)
    if rejection_reason:
        return None, [], {"signal_id": signal_id, "reason": rejection_reason}
    policy = SIGNAL_POLICIES.get(signal_type)
    if policy is None:
        return None, [], {"signal_id": signal_id, "reason": "unsupported_signal_type"}

    candidate_scope = scope_keys(session_id)
    payload = signal_payload(signal)
    return {
        "candidate_id": signal_id,
        "candidate_type": signal_type,
        "memory_type": str(policy["memory_type"]),
        "summary": str(signal.get("summary") or "").strip(),
        "review_status": "pending_review_lab",
        "review_action": str(policy["review_action"]),
        "requires_confirmation": policy["requires_confirmation"] is True,
        "requires_human_review": True,
        "source_object_refs": source_refs(signal),
        "scope_keys": candidate_scope,
        "turn_id": turn_id,
        "intended_consumers": intended_consumers(signal),
        "valid_until_minute": signal.get("valid_until_minute"),
        "payload": payload,
        "runtime_effect_allowed": False,
        "lab_only_memory_candidate": True,
        "lab_memory_store_written": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
    }, [], None


def signal_blockers(
    signal: Mapping[str, Any],
    *,
    signal_id: str,
    signal_type: str,
) -> list[str]:
    label = signal_id or "missing"
    blockers = [
        blocker
        for blocker in (
            unsafe_segment_blocker("signal_id", signal_id),
            None if signal_type else "signal_type.missing",
            None if str(signal.get("summary") or "").strip() else "summary.missing",
            None if source_refs(signal) else "source_object_refs.missing",
        )
        if blocker
    ]
    return [f"signal.{label}.{blocker}" for blocker in blockers]


def source_refs(signal: Mapping[str, Any]) -> list[str]:
    return [str(ref) for ref in signal.get("source_object_refs") or [] if str(ref)]


def intended_consumers(signal: Mapping[str, Any]) -> list[str]:
    return [
        str(consumer)
        for consumer in signal.get("intended_consumers") or DEFAULT_CONSUMERS
    ]


def signal_payload(signal: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in signal.items()
        if str(key) not in RAW_FIELD_NAMES and str(key) not in CORE_SIGNAL_FIELDS
    }


__all__ = ["candidate_from_signal"]
