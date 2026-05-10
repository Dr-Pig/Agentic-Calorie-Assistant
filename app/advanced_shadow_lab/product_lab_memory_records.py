from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_session_store import unsafe_segment_blocker


DEFAULT_CONSUMERS = ("recommendation", "rescue", "proactive")
ACCEPTED_REVIEW_STATUSES = {"accepted_lab", "corrected_lab"}
RAW_FIELD_NAMES = {"raw_user_utterance", "raw_user_input", "raw_transcript"}


def record_from_event(
    event: Mapping[str, Any],
    *,
    session_id: str,
    turn_id: str,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    record_id = str(event.get("memory_id") or "")
    id_blocker = unsafe_segment_blocker("memory_id", record_id)
    if id_blocker:
        blockers.append(id_blocker)
    memory_type = str(event.get("memory_type") or "")
    if not memory_type:
        blockers.append("memory_type.missing")
    summary = str(event.get("summary") or "").strip()
    if not summary:
        blockers.append("summary.missing")
    source_refs = [str(ref) for ref in event.get("source_object_refs") or [] if str(ref)]
    if not source_refs:
        blockers.append("source_object_refs.missing")
    if blockers:
        return {}, blockers
    payload = {
        key: value
        for key, value in event.items()
        if key not in RAW_FIELD_NAMES
        and key
        not in {
            "memory_id",
            "memory_type",
            "summary",
            "source_object_refs",
            "review_status",
            "intended_consumers",
        }
    }
    return {
        "record_id": record_id,
        "memory_type": memory_type,
        "summary": summary,
        "review_status": str(event.get("review_status") or "pending_lab"),
        "source_object_refs": source_refs,
        "scope_keys": scope_keys(session_id),
        "turn_id": turn_id,
        "record_state": "active_lab",
        "intended_consumers": [
            str(consumer) for consumer in event.get("intended_consumers") or DEFAULT_CONSUMERS
        ],
        "payload": payload,
        "active_in_lab_context": True,
        "lab_memory_written": True,
        "isolated_lab_durable_memory_written": True,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
    }, []


def context_entry(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = mapping(record.get("payload"))
    return {
        "record_id": str(record.get("record_id") or ""),
        "record_state": str(record.get("record_state") or "active_lab"),
        "memory_type": str(record.get("memory_type") or ""),
        "summary": str(record.get("summary") or ""),
        "source_object_refs": list(record.get("source_object_refs") or []),
        "review_status": str(record.get("review_status") or ""),
        "intended_consumers": list(record.get("intended_consumers") or []),
        "freshness_posture": str(payload.get("freshness_posture") or "fresh"),
        "valid_until_minute": payload.get("valid_until_minute"),
        "conflict_review_required": payload.get("conflict_review_required") is True,
        "store_name": str(payload.get("store_name") or ""),
        "item_names": [str(item) for item in payload.get("item_names") or []],
        "estimated_kcal": payload.get("estimated_kcal"),
        "blocks_candidate_types": [
            str(item) for item in payload.get("blocks_candidate_types") or []
        ],
        "blocked_item_patterns": [
            str(item) for item in payload.get("blocked_item_patterns") or []
        ],
        "suppressed_trigger_types": [
            str(item) for item in payload.get("suppressed_trigger_types") or []
        ],
    }


def scope_keys(session_id: str) -> dict[str, str]:
    return {
        "user_id": "advanced-product-lab-user",
        "workspace_id": "advanced-product-lab-workspace",
        "project_id": "advanced-product-lab",
        "surface": "chat",
        "session_id": session_id,
    }


def segment_blockers(*, session_id: str, turn_id: str) -> list[str]:
    return [
        blocker
        for blocker in (
            unsafe_segment_blocker("session_id", session_id),
            unsafe_segment_blocker("turn_id", turn_id),
        )
        if blocker
    ]


def token_estimate(entry: Mapping[str, Any]) -> int:
    return max(len(str(entry.get("summary") or "").split()), 1)


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "ACCEPTED_REVIEW_STATUSES",
    "DEFAULT_CONSUMERS",
    "context_entry",
    "mapping",
    "record_from_event",
    "scope_keys",
    "segment_blockers",
    "token_estimate",
]
