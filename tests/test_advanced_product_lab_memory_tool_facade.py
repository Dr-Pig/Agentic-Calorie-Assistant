from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_memory import ProductLabMemoryStore


def test_product_lab_memory_tool_facade_search_get_and_recall(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory_tools import (
        execute_product_lab_memory_tool_call,
    )

    store = _store_with_memory(tmp_path)

    search = execute_product_lab_memory_tool_call(
        store=store,
        session_id="tool-session",
        turn_id="t2",
        tool_name="memory.search",
        arguments={"consumers": ["recommendation"], "token_budget": 80},
    )
    get = execute_product_lab_memory_tool_call(
        store=store,
        session_id="tool-session",
        turn_id="t2",
        tool_name="memory.get",
        arguments={"memory_id": "memory-oatmeal"},
    )
    recall = execute_product_lab_memory_tool_call(
        store=store,
        session_id="tool-session",
        turn_id="t2",
        tool_name="conversation_recall.search",
        arguments={"query": "late dinner", "limit": 2},
    )
    serialized = json.dumps([search, get, recall], ensure_ascii=False)

    assert search["status"] == "pass"
    assert search["tool_name"] == "memory.search"
    assert search["selected_record_ids"] == ["late-dinner-style", "memory-oatmeal"]
    assert get["status"] == "pass"
    assert get["record"]["record_id"] == "memory-oatmeal"
    assert get["record"]["source_object_refs"] == ["turn:t1:user"]
    assert recall["status"] == "pass"
    assert [hit["record_id"] for hit in recall["hits"]] == ["late-dinner-style"]
    assert "RAW TEXT SHOULD NOT LEAK" not in serialized
    for artifact in (search, get, recall):
        assert artifact["mainline_activation_enabled"] is False
        assert artifact["canonical_product_mutation_allowed"] is False


def test_product_lab_memory_tool_facade_rejects_missing_scope(tmp_path: Path) -> None:
    from app.advanced_shadow_lab.product_lab_memory_tools import (
        execute_product_lab_memory_tool_call,
    )

    artifact = execute_product_lab_memory_tool_call(
        store=ProductLabMemoryStore(tmp_path),
        session_id="",
        turn_id="t1",
        tool_name="memory.search",
        arguments={"consumers": ["recommendation"], "token_budget": 80},
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["session_id.missing_or_unsafe"]


def _store_with_memory(tmp_path: Path) -> ProductLabMemoryStore:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="tool-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is reliable.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "store_name": "Morning Bar",
                "item_names": ["oatmeal"],
                "estimated_kcal": 420,
                "intended_consumers": ["recommendation"],
            },
            {
                "memory_id": "late-dinner-style",
                "memory_type": "interaction_preference",
                "summary": "User prefers late dinner nudges to be brief.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "raw_user_utterance": "RAW TEXT SHOULD NOT LEAK",
                "intended_consumers": ["recommendation", "proactive"],
            },
        ],
    )
    return store
