from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn


def test_product_lab_turn_can_include_manager_tool_loop_trace(tmp_path: Path) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        manager_script=_manager_script(),
        manager_tool_store=_seed_memory_store(tmp_path),
    )

    assert artifact["status"] == "pass"
    assert artifact["manager_tool_loop_enabled"] is True
    assert artifact["manager_tool_loop_artifact"]["status"] == "pass"
    assert artifact["manager_tool_loop_artifact"]["tool_call_count"] == 4
    assert artifact["manager_tool_loop_source_refs"] == [
        "manager_tool_call:memory-search-1:memory.search",
        "manager_tool_call:recommendation-1:recommendation.run",
        "manager_tool_call:rescue-1:rescue.run",
        "manager_tool_call:proactive-1:proactive.run",
    ]
    assert artifact["manager_tool_loop_artifact"][
        "dynamic_tool_results_returned_to_manager"
    ] is True
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["production_scheduler_delivery_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["manager_context_packet_changed"] is False


def test_product_lab_turn_folds_manager_tool_loop_blockers(tmp_path: Path) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        manager_script=[
            {
                "pass_id": "manager-pass-1",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "call_id": "bad-tool-1",
                        "tool_name": "generic.workflow_engine.run",
                        "arguments": {},
                    }
                ],
            },
            {
                "pass_id": "manager-pass-2",
                "action": "final",
                "final_response": {
                    "copy": "blocked fixture",
                    "source_tool_call_ids": ["bad-tool-1"],
                },
            },
        ],
        manager_tool_store=_seed_memory_store(tmp_path),
    )

    assert artifact["status"] == "blocked"
    assert artifact["lab_user_facing_behavior_changed"] is False
    assert artifact["manager_tool_loop_artifact"]["status"] == "blocked"
    assert (
        "manager_tool_loop.bad-tool-1.tool.unsupported:generic.workflow_engine.run"
        in artifact["blockers"]
    )
    assert artifact["product_capabilities_exercised"] == []
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mainline_runtime_connected"] is False


def test_product_lab_turn_default_path_does_not_run_manager_tool_loop() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert artifact["status"] == "pass"
    assert artifact["manager_tool_loop_enabled"] is False
    assert artifact["manager_tool_loop_artifact"] is None
    assert artifact["manager_tool_loop_source_refs"] == []
    assert artifact["product_capabilities_exercised"] == [
        "long_term_memory",
        "recommendation",
        "rescue",
        "proactive",
        "chat_first_controls",
    ]


def _manager_script() -> list[dict[str, object]]:
    return [
        {
            "pass_id": "manager-pass-1",
            "action": "call_tools",
            "tool_calls": [
                {
                    "call_id": "memory-search-1",
                    "tool_name": "memory.search",
                    "arguments": {
                        "consumers": ["recommendation", "proactive"],
                        "token_budget": 200,
                    },
                }
            ],
        },
        {
            "pass_id": "manager-pass-2",
            "action": "call_tools",
            "tool_calls": [
                {
                    "call_id": "recommendation-1",
                    "tool_name": "recommendation.run",
                    "arguments": {"memory_context_call_id": "memory-search-1"},
                },
                {
                    "call_id": "rescue-1",
                    "tool_name": "rescue.run",
                    "arguments": {},
                },
            ],
        },
        {
            "pass_id": "manager-pass-3",
            "action": "call_tools",
            "tool_calls": [
                {
                    "call_id": "proactive-1",
                    "tool_name": "proactive.run",
                    "arguments": {
                        "memory_context_call_id": "memory-search-1",
                        "recommendation_call_id": "recommendation-1",
                        "rescue_call_id": "rescue-1",
                    },
                }
            ],
        },
        {
            "pass_id": "manager-pass-4",
            "action": "final",
            "final_response": {
                "copy": "Fixture manager synthesis from returned tool results.",
                "source_tool_call_ids": [
                    "memory-search-1",
                    "recommendation-1",
                    "rescue-1",
                    "proactive-1",
                ],
            },
        },
    ]


def _turn() -> dict[str, object]:
    return {
        "session_id": "lab-session-1",
        "turn_id": "lab-turn-1",
        "surface": "chat",
        "user_utterance": "fixture text is not a semantic oracle",
        "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
    }


def _seed_memory_store(tmp_path: Path) -> ProductLabMemoryStore:
    store = ProductLabMemoryStore(tmp_path / "memory-store")
    write = store.write_memory_events(
        session_id="lab-session-1",
        turn_id="seed-turn",
        events=[
            {
                "memory_id": "golden-bento-1",
                "memory_type": "golden_order",
                "summary": "Often chooses a FamilyMart chicken bento for lunch.",
                "review_status": "accepted_lab",
                "source_object_refs": ["meal_thread:seed-1"],
                "intended_consumers": ["recommendation", "proactive"],
                "store_name": "FamilyMart",
                "item_names": ["chicken bento"],
                "estimated_kcal": 520,
            }
        ],
    )
    assert write["status"] == "pass"
    return store
