from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Protocol

from app.advanced_shadow_lab.product_lab_pending_meal_intent_store_support import (
    history,
    history_event,
    segment_blockers,
    store_artifact,
)
from app.runtime.contracts.pending_meal_intent import (
    PendingMealIntent,
    PendingMealIntentMealWindowPosture,
)


class PendingMealIntentStoreProtocol(Protocol):
    def list_intents(self, *, session_id: str, **kwargs: Any) -> list[dict[str, Any]]:
        ...

    def _persist_records(
        self,
        session_id: str,
        records: list[Mapping[str, Any]],
    ) -> None:
        ...


def expire_stale_intents(
    store: PendingMealIntentStoreProtocol,
    *,
    session_id: str,
    turn_id: str,
    now: datetime,
) -> dict[str, Any]:
    blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
    if blockers:
        return store_artifact(
            operation="expire",
            status="blocked",
            blockers=blockers,
            expired_intent_ids=[],
        )

    changed = False
    expired_ids: list[str] = []
    records = store.list_intents(session_id=session_id)
    for record in records:
        intent = PendingMealIntent.model_validate(record)
        if intent.status == "created" and not intent.is_active_at(now):
            record["status"] = "expired"
            record["history"] = history(record) + [
                history_event(
                    operation="expire",
                    turn_id=turn_id,
                    source_ref=f"pending_meal_intent:{intent.intent_id}",
                )
            ]
            expired_ids.append(intent.intent_id)
            changed = True
    if changed:
        store._persist_records(session_id, records)
    return store_artifact(
        operation="expire",
        status="pass",
        blockers=[],
        expired_intent_ids=expired_ids,
        closed_intent_ids=expired_ids,
    )


def mutate_intent(
    store: PendingMealIntentStoreProtocol,
    *,
    session_id: str,
    turn_id: str,
    intent_id: str,
    operation: str,
    update: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
    if blockers:
        return store_artifact(
            operation=operation,
            status="blocked",
            blockers=blockers,
            closed_intent_ids=[],
        )

    records = store.list_intents(session_id=session_id)
    target = next(
        (record for record in records if str(record.get("intent_id") or "") == intent_id),
        None,
    )
    if target is None:
        return store_artifact(
            operation=operation,
            status="blocked",
            blockers=["pending_meal_intent.intent_not_found"],
            closed_intent_ids=[],
        )

    if operation == "update":
        _apply_update(target, update)
    elif operation == "dismiss":
        target["status"] = "dismissed"

    target["history"] = history(target) + [
        history_event(
            operation=operation,
            turn_id=turn_id,
            source_ref=f"pending_meal_intent:{intent_id}",
            reason=str(update.get("reason") or "") or None,
        )
    ]
    PendingMealIntent.model_validate(target)
    store._persist_records(session_id, records)
    closed_ids = [intent_id] if operation == "dismiss" else []
    return store_artifact(
        operation=operation,
        status="pass",
        blockers=[],
        updated_intent_ids=[intent_id] if operation == "update" else [],
        closed_intent_ids=closed_ids,
    )


def _apply_update(target: dict[str, Any], update: Mapping[str, Any]) -> None:
    target["candidate_metadata"] = {
        **dict(target.get("candidate_metadata") or {}),
        **dict(update.get("candidate_metadata_patch") or {}),
    }
    posture = update.get("meal_window_posture")
    if isinstance(posture, PendingMealIntentMealWindowPosture):
        target["meal_window_posture"] = posture.model_dump(mode="json")


__all__ = ["expire_stale_intents", "mutate_intent"]
