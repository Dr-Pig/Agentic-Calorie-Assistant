from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_pending_meal_intent_lifecycle import (
    expire_stale_intents,
    mutate_intent,
)
from app.advanced_shadow_lab.product_lab_pending_meal_intent_store_support import (
    history,
    history_event,
    records_path,
    scope_matches,
    segment_blockers,
    store_artifact,
)
from app.runtime.contracts.pending_meal_intent import (
    PendingMealIntent,
    PendingMealIntentMealWindowPosture,
    PendingMealIntentScopeKeys,
)
from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact


class ProductLabPendingMealIntentStore:
    def __init__(self, artifact_root: Path | str) -> None:
        self.artifact_root = Path(artifact_root)

    def write_intent(
        self,
        *,
        session_id: str,
        turn_id: str,
        intent: PendingMealIntent,
    ) -> dict[str, Any]:
        blockers = segment_blockers(session_id=session_id, turn_id=turn_id)
        if blockers:
            return store_artifact(
                operation="write",
                status="blocked",
                blockers=blockers,
                written_intent_ids=[],
            )

        records = self.list_intents(session_id=session_id)
        by_id = {str(record["intent_id"]): record for record in records}
        previous = by_id.get(intent.intent_id)
        record = intent.model_dump(mode="json")
        record["history"] = history(previous) + [
            history_event(
                operation="write",
                turn_id=turn_id,
                source_ref=f"pending_meal_intent:{intent.intent_id}",
            )
        ]
        by_id[intent.intent_id] = record
        self._persist_records(session_id, list(by_id.values()))
        return store_artifact(
            operation="write",
            status="pass",
            blockers=[],
            written_intent_ids=[intent.intent_id],
            active_intent_ids=self._active_ids(session_id=session_id, now=intent.created_at),
        )

    def list_intents(
        self,
        *,
        session_id: str,
        scope_keys: PendingMealIntentScopeKeys | None = None,
        active_only: bool = False,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if segment_blockers(session_id=session_id):
            return []
        path = records_path(artifact_root=self.artifact_root, session_id=session_id)
        if not path.exists():
            return []
        payload = read_json_artifact(path)
        records = [
            dict(item)
            for item in payload.get("pending_meal_intents") or []
            if isinstance(item, Mapping)
        ]
        if scope_keys is not None:
            records = [
                record
                for record in records
                if scope_matches(record.get("scope_keys"), scope_keys)
            ]
        if active_only:
            active_at = now or datetime.now(UTC)
            records = [
                record
                for record in records
                if PendingMealIntent.model_validate(record).is_active_at(active_at)
            ]
        return sorted(records, key=lambda record: str(record.get("intent_id") or ""))

    def read_intent(self, *, session_id: str, intent_id: str) -> dict[str, Any] | None:
        for record in self.list_intents(session_id=session_id):
            if str(record.get("intent_id") or "") == intent_id:
                return record
        return None

    def update_intent(
        self,
        *,
        session_id: str,
        turn_id: str,
        intent_id: str,
        candidate_metadata_patch: Mapping[str, Any] | None = None,
        meal_window_posture: PendingMealIntentMealWindowPosture | None = None,
    ) -> dict[str, Any]:
        return self._mutate_intent(
            session_id=session_id,
            turn_id=turn_id,
            intent_id=intent_id,
            operation="update",
            update={
                "candidate_metadata_patch": dict(candidate_metadata_patch or {}),
                "meal_window_posture": meal_window_posture,
            },
        )

    def dismiss_intent(
        self,
        *,
        session_id: str,
        turn_id: str,
        intent_id: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._mutate_intent(
            session_id=session_id,
            turn_id=turn_id,
            intent_id=intent_id,
            operation="dismiss",
            update={"status": "dismissed", "reason": reason},
        )

    def expire_stale_intents(
        self,
        *,
        session_id: str,
        turn_id: str,
        now: datetime,
    ) -> dict[str, Any]:
        return expire_stale_intents(
            self,
            session_id=session_id,
            turn_id=turn_id,
            now=now,
        )

    def _mutate_intent(
        self,
        *,
        session_id: str,
        turn_id: str,
        intent_id: str,
        operation: str,
        update: Mapping[str, Any],
    ) -> dict[str, Any]:
        return mutate_intent(
            self,
            session_id=session_id,
            turn_id=turn_id,
            intent_id=intent_id,
            operation=operation,
            update=update,
        )

    def _persist_records(
        self,
        session_id: str,
        records: list[Mapping[str, Any]],
    ) -> None:
        write_json_artifact(
            records_path(artifact_root=self.artifact_root, session_id=session_id),
            {"pending_meal_intents": list(records)},
        )

    def _active_ids(self, *, session_id: str, now: datetime) -> list[str]:
        return [
            str(record["intent_id"])
            for record in self.list_intents(
                session_id=session_id,
                active_only=True,
                now=now,
            )
        ]


__all__ = ["ProductLabPendingMealIntentStore"]
