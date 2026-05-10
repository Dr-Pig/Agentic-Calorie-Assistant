from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_lifecycle import (
    history,
    history_event,
)
from app.advanced_shadow_lab.product_lab_memory_records import segment_blockers


def apply_product_lab_memory_lifecycle_policy(
    *,
    store: Any,
    session_id: str,
    turn_id: str,
    lab_now_day: int,
    lab_now_minute: int = 0,
) -> dict[str, Any]:
    blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
    records = store.list_records(session_id)
    updates: list[dict[str, Any]] = []
    next_records: list[dict[str, Any]] = []
    for record in records:
        updated, action = policy_update(
            record,
            turn_id=turn_id,
            lab_now_day=lab_now_day,
            lab_now_minute=lab_now_minute,
        )
        next_records.append(updated)
        if action:
            updates.append(action)
    if not blockers and updates:
        store._persist_records(session_id, next_records, turn_id=turn_id)
    return {
        "artifact_type": "advanced_product_lab_memory_lifecycle_policy_artifact",
        "status": "blocked" if blockers else "pass",
        "session_id": session_id,
        "turn_id": turn_id,
        "applied_actions": updates if not blockers else [],
        "updated_record_ids": [item["record_id"] for item in updates]
        if not blockers
        else [],
        "negative_preference_auto_demoted": False,
        "lab_memory_store_written": bool(updates) and not blockers,
        "isolated_lab_durable_memory_written": bool(updates) and not blockers,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
    }


def policy_update(
    record: Mapping[str, Any],
    *,
    turn_id: str,
    lab_now_day: int,
    lab_now_minute: int,
) -> tuple[dict[str, Any], dict[str, str] | None]:
    record_id = str(record.get("record_id") or "")
    memory_type = str(record.get("memory_type") or "")
    payload = dict(record.get("payload") or {})
    if memory_type == "negative_preference":
        return dict(record), None
    if should_expire_temporary(memory_type, payload, lab_now_minute):
        return updated_record(
            record,
            payload={**payload, "freshness_posture": "expired"},
            updates={
                "review_status": "expired_lab",
                "record_state": "archived_lab",
                "active_in_lab_context": False,
            },
            action="expire",
            turn_id=turn_id,
        ), {"record_id": record_id, "action": "expire"}
    last_observed_day = payload.get("last_observed_day")
    if not isinstance(last_observed_day, int | float):
        return dict(record), None
    age_days = lab_now_day - int(last_observed_day)
    if memory_type == "pattern_memory" and age_days >= 60:
        return archive_record(record, payload, turn_id=turn_id), {
            "record_id": record_id,
            "action": "archive",
        }
    if memory_type == "golden_order" and age_days >= 60:
        return updated_record(
            record,
            payload={**payload, "is_active": False, "freshness_posture": "stale"},
            updates={"active_in_lab_context": False},
            action="deactivate",
            turn_id=turn_id,
        ), {"record_id": record_id, "action": "deactivate"}
    return dict(record), None


def should_expire_temporary(
    memory_type: str,
    payload: Mapping[str, Any],
    lab_now_minute: int,
) -> bool:
    valid_until = payload.get("valid_until_minute")
    return (
        memory_type == "temporary_preference"
        and isinstance(valid_until, int | float)
        and valid_until < lab_now_minute
    )


def archive_record(
    record: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    turn_id: str,
) -> dict[str, Any]:
    return updated_record(
        record,
        payload={**dict(payload), "freshness_posture": "archived"},
        updates={
            "review_status": "archived_lab",
            "record_state": "archived_lab",
            "active_in_lab_context": False,
        },
        action="archive",
        turn_id=turn_id,
    )


def updated_record(
    record: Mapping[str, Any],
    *,
    payload: Mapping[str, Any],
    updates: Mapping[str, Any],
    action: str,
    turn_id: str,
) -> dict[str, Any]:
    updated = {**dict(record), **dict(updates), "payload": dict(payload)}
    updated["history"] = history(record) + [
        history_event(action, turn_id=turn_id, reason="lifecycle_policy")
    ]
    return updated


__all__ = ["apply_product_lab_memory_lifecycle_policy"]
