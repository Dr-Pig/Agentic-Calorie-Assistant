from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.advanced_shadow_lab.product_lab_pending_meal_intent_store import (
    ProductLabPendingMealIntentStore,
)
from app.runtime.contracts.pending_meal_intent import (
    PendingMealIntent,
    PendingMealIntentMealWindowPosture,
    PendingMealIntentScopeKeys,
)


def test_pending_meal_intent_lab_store_writes_and_lists_scoped_active_intents(
    tmp_path: Path,
) -> None:
    store = ProductLabPendingMealIntentStore(tmp_path)
    created_at = datetime(2026, 5, 14, 18, 0, tzinfo=UTC)
    intent = _intent("intent-1", user_id="user-1", created_at=created_at)

    artifact = store.write_intent(
        session_id="session-a",
        turn_id="turn-1",
        intent=intent,
    )

    assert artifact["status"] == "pass"
    assert artifact["operation"] == "write"
    assert artifact["written_intent_ids"] == ["intent-1"]
    assert artifact["active_intent_ids"] == ["intent-1"]
    assert artifact["lab_isolated"] is True
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["meal_thread_mutated"] is False
    assert artifact["ledger_entry_created"] is False
    assert artifact["durable_product_memory_written"] is False

    scoped = store.list_intents(
        session_id="session-a",
        scope_keys=PendingMealIntentScopeKeys(user_id="user-1"),
        active_only=True,
        now=created_at + timedelta(hours=1),
    )
    assert [record["intent_id"] for record in scoped] == ["intent-1"]
    assert scoped[0]["context_pack_identity"]["block_id"] == "pending_meal_intent:intent-1"
    assert scoped[0]["history"][0]["operation"] == "write"


def test_pending_meal_intent_lab_store_isolates_sessions_and_scopes(
    tmp_path: Path,
) -> None:
    store = ProductLabPendingMealIntentStore(tmp_path)
    created_at = datetime(2026, 5, 14, 18, 0, tzinfo=UTC)
    store.write_intent(
        session_id="session-a",
        turn_id="turn-1",
        intent=_intent("intent-1", user_id="user-1", created_at=created_at),
    )
    store.write_intent(
        session_id="session-b",
        turn_id="turn-1",
        intent=_intent("intent-2", user_id="user-2", created_at=created_at),
    )

    assert store.list_intents(session_id="session-a")[0]["intent_id"] == "intent-1"
    assert store.list_intents(session_id="session-b")[0]["intent_id"] == "intent-2"
    assert (
        store.list_intents(
            session_id="session-a",
            scope_keys=PendingMealIntentScopeKeys(user_id="user-2"),
        )
        == []
    )


def test_pending_meal_intent_lab_store_updates_dismisses_and_expires_without_mutation(
    tmp_path: Path,
) -> None:
    store = ProductLabPendingMealIntentStore(tmp_path)
    created_at = datetime(2026, 5, 14, 18, 0, tzinfo=UTC)
    store.write_intent(
        session_id="session-a",
        turn_id="turn-1",
        intent=_intent("intent-1", user_id="user-1", created_at=created_at),
    )

    update = store.update_intent(
        session_id="session-a",
        turn_id="turn-2",
        intent_id="intent-1",
        candidate_metadata_patch={"meal_window": "dinner"},
        meal_window_posture=PendingMealIntentMealWindowPosture(target_window="dinner"),
    )
    dismiss = store.dismiss_intent(
        session_id="session-a",
        turn_id="turn-3",
        intent_id="intent-1",
        reason="user_said_nevermind",
    )

    assert update["status"] == "pass"
    assert dismiss["status"] == "pass"
    assert dismiss["closed_intent_ids"] == ["intent-1"]
    assert dismiss["canonical_product_mutation_allowed"] is False
    record = store.read_intent(session_id="session-a", intent_id="intent-1")
    assert record is not None
    assert record["status"] == "dismissed"
    assert record["candidate_metadata"]["meal_window"] == "dinner"
    assert [event["operation"] for event in record["history"]] == [
        "write",
        "update",
        "dismiss",
    ]

    expire = store.expire_stale_intents(
        session_id="session-a",
        turn_id="turn-4",
        now=created_at + timedelta(hours=8),
    )
    assert expire["expired_intent_ids"] == []

    store.write_intent(
        session_id="session-a",
        turn_id="turn-5",
        intent=_intent("intent-2", user_id="user-1", created_at=created_at),
    )
    expire = store.expire_stale_intents(
        session_id="session-a",
        turn_id="turn-6",
        now=created_at + timedelta(hours=8),
    )
    assert expire["expired_intent_ids"] == ["intent-2"]
    assert store.read_intent(session_id="session-a", intent_id="intent-2")["status"] == "expired"


def test_pending_meal_intent_lab_store_blocks_unsafe_segments(tmp_path: Path) -> None:
    store = ProductLabPendingMealIntentStore(tmp_path)
    created_at = datetime(2026, 5, 14, 18, 0, tzinfo=UTC)

    artifact = store.write_intent(
        session_id="../bad",
        turn_id="turn-1",
        intent=_intent("intent-1", user_id="user-1", created_at=created_at),
    )

    assert artifact["status"] == "blocked"
    assert "session_id.unsafe_path_segment" in artifact["blockers"]
    assert artifact["written_intent_ids"] == []
    assert store.list_intents(session_id="../bad") == []


def _intent(
    intent_id: str,
    *,
    user_id: str,
    created_at: datetime,
) -> PendingMealIntent:
    return PendingMealIntent(
        intent_id=intent_id,
        user_id=user_id,
        candidate_title="ramen dinner candidate",
        source_surface="chat",
        created_at=created_at,
        expires_at=created_at + timedelta(hours=6),
        candidate_metadata={"candidate_id": intent_id, "estimated_kcal": 720},
    )
