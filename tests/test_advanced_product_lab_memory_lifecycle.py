from __future__ import annotations

import json
from pathlib import Path


def test_product_lab_memory_lifecycle_correct_delete_forget_with_history(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory import ProductLabMemoryStore

    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="lifecycle-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "breakfast-pref",
                "memory_type": "preference",
                "summary": "User likes oatmeal every morning.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "intended_consumers": ["recommendation"],
            }
        ],
    )
    corrected = store.correct_memory(
        session_id="lifecycle-session",
        turn_id="t2",
        memory_id="breakfast-pref",
        summary="User likes oatmeal often, but not every morning.",
        source_object_refs=["turn:t2:review"],
        reason="review_correction",
    )
    deleted = store.delete_memory(
        session_id="lifecycle-session",
        turn_id="t3",
        memory_id="breakfast-pref",
        reason="stale_after_review",
    )
    forgotten = store.forget_memory(
        session_id="lifecycle-session",
        turn_id="t4",
        memory_id="breakfast-pref",
        reason="user_forget",
    )

    assert corrected["status"] == "pass"
    assert corrected["record"]["summary"] == (
        "User likes oatmeal often, but not every morning."
    )
    assert deleted["record_state"] == "deleted_lab"
    assert forgotten["record_state"] == "forgotten_lab"
    assert forgotten["memory_text_retained"] is False
    history = store.record_history("lifecycle-session", "breakfast-pref")
    assert [event["action"] for event in history] == [
        "write",
        "correct",
        "delete",
        "forget",
    ]
    assert store.read_memory("lifecycle-session", "breakfast-pref") is None
    records_json = json.dumps(store.list_records("lifecycle-session"), ensure_ascii=False)
    assert "User likes oatmeal often" not in records_json


def test_product_lab_memory_context_omits_expired_stale_conflict_and_deleted(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        ProductLabMemoryStore,
        build_product_lab_memory_context_pack,
    )

    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="context-session",
        turn_id="t1",
        events=[
            _memory("active-pref", "preference", "Active preference"),
            _memory(
                "temp-expired",
                "temporary_preference",
                "Temporary preference",
                valid_until_minute=10,
            ),
            _memory(
                "stale-pref",
                "preference",
                "Stale preference",
                freshness_posture="stale",
            ),
            _memory(
                "conflict-pref",
                "preference",
                "Conflict preference",
                conflict_review_required=True,
            ),
            _memory("deleted-pref", "preference", "Deleted preference"),
        ],
    )
    store.delete_memory(
        session_id="context-session",
        turn_id="t2",
        memory_id="deleted-pref",
        reason="review_delete",
    )

    pack = build_product_lab_memory_context_pack(
        store=store,
        session_id="context-session",
        turn_id="t3",
        consumers=["recommendation"],
        token_budget=120,
        lab_now_minute=20,
    )

    assert pack["selected_record_ids"] == ["active-pref"]
    assert {item["record_id"]: item["reason"] for item in pack["omission_trace"]} == {
        "conflict-pref": "conflict_review_required",
        "deleted-pref": "deleted_lab",
        "stale-pref": "stale_or_expired",
        "temp-expired": "stale_or_expired",
    }
    serialized = json.dumps(pack, ensure_ascii=False)
    assert "Conflict preference" not in serialized
    assert "Temporary preference" not in serialized


def test_product_lab_conversation_recall_searches_summaries_without_raw_dump(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        ProductLabMemoryStore,
        conversation_recall_search,
    )

    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="recall-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "late-dinner-style",
                "memory_type": "interaction_preference",
                "summary": "User prefers late dinner nudges to be brief.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "raw_user_utterance": "RAW TEXT SHOULD NOT LEAK",
                "intended_consumers": ["proactive"],
            }
        ],
    )

    recall = conversation_recall_search(
        store=store,
        session_id="recall-session",
        query="late dinner",
        limit=3,
    )
    serialized = json.dumps(recall, ensure_ascii=False)

    assert recall["artifact_type"] == "advanced_product_lab_conversation_recall"
    assert recall["status"] == "pass"
    assert recall["tool"] == "conversation_recall.search"
    assert [hit["record_id"] for hit in recall["hits"]] == ["late-dinner-style"]
    assert recall["raw_transcript_included"] is False
    assert "RAW TEXT SHOULD NOT LEAK" not in serialized


def _memory(
    memory_id: str,
    memory_type: str,
    summary: str,
    **payload: object,
) -> dict[str, object]:
    return {
        "memory_id": memory_id,
        "memory_type": memory_type,
        "summary": summary,
        "review_status": "accepted_lab",
        "source_object_refs": [f"turn:t1:{memory_id}"],
        "intended_consumers": ["recommendation"],
        **payload,
    }
