from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_records import segment_blockers
from app.advanced_shadow_lab.product_lab_session_store import unsafe_segment_blocker


CLOSED_STATES = {"deleted_lab", "forgotten_lab"}


def correct_memory_record(
    store: Any,
    *,
    session_id: str,
    turn_id: str,
    memory_id: str,
    summary: str,
    source_object_refs: list[str],
    reason: str,
) -> dict[str, Any]:
    clean_summary = str(summary).strip()
    source_refs = [str(ref) for ref in source_object_refs if str(ref)]
    blockers = lifecycle_blockers(session_id, turn_id, memory_id)
    if not clean_summary:
        blockers.append("summary.missing")
    if not source_refs:
        blockers.append("source_object_refs.missing")
    return change_record(
        store,
        session_id=session_id,
        turn_id=turn_id,
        memory_id=memory_id,
        action="correct",
        reason=reason,
        blockers=blockers,
        updates={
            "summary": clean_summary,
            "source_object_refs": source_refs,
            "review_status": "corrected_lab",
            "record_state": "active_lab",
            "active_in_lab_context": True,
        },
    )


def delete_memory_record(
    store: Any,
    *,
    session_id: str,
    turn_id: str,
    memory_id: str,
    reason: str,
) -> dict[str, Any]:
    return change_record(
        store,
        session_id=session_id,
        turn_id=turn_id,
        memory_id=memory_id,
        action="delete",
        reason=reason,
        blockers=lifecycle_blockers(session_id, turn_id, memory_id),
        updates={
            "review_status": "deleted_lab",
            "record_state": "deleted_lab",
            "active_in_lab_context": False,
        },
    )


def forget_memory_record(
    store: Any,
    *,
    session_id: str,
    turn_id: str,
    memory_id: str,
    reason: str,
) -> dict[str, Any]:
    return change_record(
        store,
        session_id=session_id,
        turn_id=turn_id,
        memory_id=memory_id,
        action="forget",
        reason=reason,
        blockers=lifecycle_blockers(session_id, turn_id, memory_id),
        updates={
            "summary": "",
            "source_object_refs": [],
            "payload": {},
            "review_status": "forgotten_lab",
            "record_state": "forgotten_lab",
            "active_in_lab_context": False,
        },
        memory_text_retained=False,
    )


def change_record(
    store: Any,
    *,
    session_id: str,
    turn_id: str,
    memory_id: str,
    action: str,
    reason: str,
    blockers: list[str],
    updates: Mapping[str, Any],
    memory_text_retained: bool = True,
) -> dict[str, Any]:
    records = store.list_records(session_id)
    for index, record in enumerate(records):
        if str(record.get("record_id") or "") != str(memory_id):
            continue
        updated = {**record, **dict(updates)}
        updated["history"] = history(record) + [
            history_event(action, turn_id=turn_id, reason=reason)
        ]
        records[index] = updated
        if not blockers:
            store._persist_records(session_id, records, turn_id=turn_id)
        return lifecycle_artifact(
            action=action,
            blockers=blockers,
            record=updated,
            memory_text_retained=memory_text_retained,
        )
    blockers.append("memory_id.not_found")
    return lifecycle_artifact(
        action=action,
        blockers=blockers,
        record={},
        memory_text_retained=memory_text_retained,
    )


def lifecycle_blockers(session_id: str, turn_id: str, memory_id: str) -> list[str]:
    blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
    id_blocker = unsafe_segment_blocker("memory_id", str(memory_id))
    if id_blocker:
        blockers.append(id_blocker)
    return blockers


def history(record: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(record, Mapping):
        return []
    return [
        dict(item)
        for item in record.get("history") or []
        if isinstance(item, Mapping)
    ]


def history_event(
    action: str,
    *,
    turn_id: str,
    reason: str = "",
    source_object_refs: list[Any] | tuple[Any, ...] = (),
) -> dict[str, Any]:
    event: dict[str, Any] = {"action": action, "turn_id": turn_id}
    if reason:
        event["reason"] = reason
    if source_object_refs:
        event["source_object_refs"] = [str(ref) for ref in source_object_refs]
    return event


def lifecycle_artifact(
    *,
    action: str,
    blockers: list[str],
    record: Mapping[str, Any],
    memory_text_retained: bool,
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_lifecycle_artifact",
        "status": "blocked" if blockers else "pass",
        "action": action,
        "record": dict(record),
        "record_state": str(record.get("record_state") or ""),
        "memory_text_retained": memory_text_retained,
        "isolated_lab_durable_memory_written": not blockers,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
    }


__all__ = [
    "CLOSED_STATES",
    "correct_memory_record",
    "delete_memory_record",
    "forget_memory_record",
    "history",
    "history_event",
]
