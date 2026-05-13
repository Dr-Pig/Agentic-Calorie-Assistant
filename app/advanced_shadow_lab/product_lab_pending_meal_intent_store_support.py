from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_session_store import (
    session_dir,
    unsafe_segment_blocker,
)
from app.runtime.contracts.pending_meal_intent import PendingMealIntentScopeKeys


FALSE_FLAGS = {
    "canonical_product_mutation_allowed": False,
    "meal_thread_mutated": False,
    "ledger_entry_created": False,
    "durable_product_memory_written": False,
    "scheduler_delivery_allowed": False,
    "mainline_activation_enabled": False,
}


def records_path(*, artifact_root: Path | str, session_id: str) -> Path:
    return (
        session_dir(artifact_root=artifact_root, session_id=session_id)
        / "pending_meal_intents"
        / "intents.json"
    )


def segment_blockers(*, session_id: str, turn_id: str | None = None) -> list[str]:
    blockers = [unsafe_segment_blocker("session_id", session_id)]
    if turn_id is not None:
        blockers.append(unsafe_segment_blocker("turn_id", turn_id))
    return [blocker for blocker in blockers if blocker is not None]


def store_artifact(
    *,
    operation: str,
    status: str,
    blockers: list[str],
    written_intent_ids: list[str] | None = None,
    updated_intent_ids: list[str] | None = None,
    closed_intent_ids: list[str] | None = None,
    expired_intent_ids: list[str] | None = None,
    active_intent_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_pending_meal_intent_store_artifact",
        "artifact_schema_version": "1.0",
        "status": status,
        "operation": operation,
        "lab_isolated": True,
        "written_intent_ids": written_intent_ids or [],
        "updated_intent_ids": updated_intent_ids or [],
        "closed_intent_ids": closed_intent_ids or [],
        "expired_intent_ids": expired_intent_ids or [],
        "active_intent_ids": active_intent_ids or [],
        "blockers": blockers,
        **FALSE_FLAGS,
    }


def scope_matches(
    record_scope: object,
    requested_scope: PendingMealIntentScopeKeys,
) -> bool:
    if not isinstance(record_scope, Mapping):
        return False
    return (
        record_scope.get("user_id") == requested_scope.user_id
        and record_scope.get("workspace_id") == requested_scope.workspace_id
        and record_scope.get("project_id") == requested_scope.project_id
        and (
            requested_scope.surface == "unknown"
            or record_scope.get("surface") == requested_scope.surface
        )
    )


def history(record: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not record:
        return []
    return [
        dict(item)
        for item in record.get("history") or []
        if isinstance(item, Mapping)
    ]


def history_event(
    *,
    operation: str,
    turn_id: str,
    source_ref: str,
    reason: str | None = None,
) -> dict[str, Any]:
    event = {
        "operation": operation,
        "turn_id": turn_id,
        "occurred_at": datetime.now(UTC).isoformat(),
        "source_ref": source_ref,
    }
    if reason:
        event["reason"] = reason
    return event


__all__ = [
    "history",
    "history_event",
    "records_path",
    "scope_matches",
    "segment_blockers",
    "store_artifact",
]
