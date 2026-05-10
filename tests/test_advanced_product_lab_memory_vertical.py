from __future__ import annotations

import json
from pathlib import Path

from app.advanced_shadow_lab.product_lab_session_replay import (
    run_advanced_product_lab_dogfood_session,
)
from app.shared.infra.json_artifacts import read_json_artifact
from tests.test_advanced_product_lab_runtime import _fixture_inputs


def test_product_lab_memory_vertical_writes_surfaces_and_injects_next_turn(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_dogfood_session(
        artifact_root=tmp_path,
        session_id="memory-vertical-session",
        fixture_inputs=_fixture_inputs(),
        turns=[
            {
                "turn_id": "t1-capture-memory",
                "lab_now_minute": 10,
                "post_turn_memory_events": [
                    {
                        "memory_id": "golden-breakfast-oatmeal",
                        "memory_type": "golden_order",
                        "summary": "Morning Bar oatmeal is a reliable breakfast option.",
                        "review_status": "accepted_lab",
                        "source_object_refs": ["turn:t1-capture-memory:user"],
                        "store_name": "Morning Bar",
                        "item_names": ["oatmeal"],
                        "estimated_kcal": 420,
                        "intended_consumers": [
                            "recommendation",
                            "rescue",
                            "proactive",
                        ],
                    },
                    {
                        "memory_id": "negative-cilantro",
                        "memory_type": "negative_preference",
                        "summary": "Avoid cilantro in recommendations.",
                        "review_status": "accepted_lab",
                        "source_object_refs": ["turn:t1-capture-memory:user"],
                        "blocks_candidate_types": ["recommendation_candidate"],
                        "intended_consumers": ["recommendation"],
                    },
                ],
            },
            {"turn_id": "t2-use-memory", "lab_now_minute": 20},
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["lab_memory_store_written"] is True
    assert artifact["lab_memory_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert artifact["lab_memory_tool_calls"] == [
        {
            "turn_id": "t1-capture-memory",
            "tool": "memory.search",
            "selected_record_ids": [],
        },
        {
            "turn_id": "t2-use-memory",
            "tool": "memory.search",
            "selected_record_ids": [
                "golden-breakfast-oatmeal",
                "negative-cilantro",
            ],
        },
    ]
    assert artifact["lab_memory_context_injected"] is True
    assert artifact["memory_context_injected"] is True
    assert artifact["lab_user_facing_behavior_changed"] is True
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["self_use_v1_affected"] is False

    surface_paths = {
        key: Path(value) for key, value in artifact["lab_memory_surface_paths"].items()
    }
    assert set(surface_paths) == {
        "user_md",
        "memory_md",
        "source_md",
        "sources_jsonl",
        "daily_md",
        "review_md",
        "conversation_archive_jsonl",
    }
    assert all(path.exists() for path in surface_paths.values())
    assert "Morning Bar oatmeal" in surface_paths["user_md"].read_text(
        encoding="utf-8"
    )
    assert "negative-cilantro" in surface_paths["sources_jsonl"].read_text(
        encoding="utf-8"
    )
    assert "raw_user_utterance" not in surface_paths["memory_md"].read_text(
        encoding="utf-8"
    )

    turn_paths = [Path(path) for path in artifact["turn_artifact_paths"]]
    t1 = read_json_artifact(turn_paths[0])["turn_artifact"]
    t2 = read_json_artifact(turn_paths[1])["turn_artifact"]

    assert t1["lab_memory_context_pack"]["selected_record_ids"] == []
    assert t1["lab_memory_context_pack"]["memory_context_injected"] is False
    assert t2["lab_memory_context_pack"]["selected_record_ids"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert t2["lab_memory_context_pack"]["memory_context_injected"] is True
    assert t2["lab_chat_response_packet"]["memory_context_applied"] is True
    assert t2["lab_chat_response_packet"]["lab_runtime_capabilities"][
        "recommendation_served_to_lab"
    ] is True
    assert t2["lab_chat_response_packet"]["lab_runtime_capabilities"][
        "proactive_chat_packet_served_to_lab"
    ] is True

    visible_messages = t2["lab_chat_surface"]["messages"]
    assert visible_messages
    assert visible_messages[0]["memory_context_refs"] == [
        "golden-breakfast-oatmeal",
        "negative-cilantro",
    ]
    assert visible_messages[0]["served_to_lab_user"] is True
    assert visible_messages[0]["served_to_mainline_user"] is False
    assert "no_send" not in json.dumps(t2["lab_chat_surface"], ensure_ascii=False)


def test_product_lab_memory_vertical_rejects_cross_scope_context_bypass(
    tmp_path: Path,
) -> None:
    from app.advanced_shadow_lab.product_lab_memory import (
        ProductLabMemoryStore,
        build_product_lab_memory_context_pack,
    )

    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="scope-a",
        turn_id="t1",
        events=[
            {
                "memory_id": "scope-a-memory",
                "memory_type": "preference",
                "summary": "Scope A memory.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "intended_consumers": ["recommendation"],
            }
        ],
    )

    pack = build_product_lab_memory_context_pack(
        store=store,
        session_id="scope-b",
        turn_id="t2",
        consumers=["recommendation"],
        token_budget=120,
    )
    serialized = json.dumps(pack, ensure_ascii=False)

    assert pack["status"] == "pass"
    assert pack["selected_record_ids"] == []
    assert pack["memory_context_injected"] is False
    assert pack["scope_keys"]["session_id"] == "scope-b"
    assert "Scope A memory" not in serialized
