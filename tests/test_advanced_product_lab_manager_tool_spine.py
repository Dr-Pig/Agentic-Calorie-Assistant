from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_manager_tool_spine import (
    MANAGER_TOOL_NAMES,
    build_product_lab_manager_tool_registry,
    run_product_lab_manager_tool_loop,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore


def test_product_lab_manager_tool_loop_runs_representative_dynamic_spine(
    tmp_path: Path,
) -> None:
    store = _seed_memory_store(tmp_path)
    artifact = run_product_lab_manager_tool_loop(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        manager_script=_manager_script(),
        store=store,
    )

    assert artifact["artifact_type"] == "advanced_product_lab_manager_tool_loop_artifact"
    assert artifact["status"] == "pass"
    assert artifact["lab_manager_tool_loop_enabled"] is True
    assert artifact["lab_runtime_connected"] is True
    assert artifact["dynamic_tool_results_returned_to_manager"] is True
    assert artifact["tool_call_count"] == 4
    assert artifact["product_capabilities_exercised"] == [
        "long_term_memory",
        "proactive",
        "recommendation",
        "rescue",
    ]
    assert artifact["manager_pass_trace"][0]["manager_action"] == "call_tools"
    assert artifact["manager_pass_trace"][-1]["manager_action"] == "final"
    assert artifact["final_response_packet"]["source_tool_call_ids"] == [
        "memory-search-1",
        "recommendation-1",
        "rescue-1",
        "proactive-1",
    ]

    by_call = {result["call_id"]: result for result in artifact["tool_result_trace"]}
    memory_search = by_call["memory-search-1"]["result_artifact"]
    assert memory_search["context_pack"]["selected_record_ids"] == ["golden-bento-1"]
    assert by_call["recommendation-1"]["result_artifact_type"] == (
        "advanced_product_lab_recommendation_runtime_artifact"
    )
    assert by_call["rescue-1"]["result_artifact_type"] == (
        "advanced_product_lab_rescue_runtime_artifact"
    )
    assert by_call["proactive-1"]["result_artifact_type"] == (
        "advanced_product_lab_proactive_runtime_artifact"
    )
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["self_use_v1_affected"] is False
    assert artifact["production_scheduler_delivery_allowed"] is False
    assert artifact["production_db_migration_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False


def test_product_lab_manager_tool_registry_is_typed_and_dormant() -> None:
    registry = build_product_lab_manager_tool_registry()

    assert registry["status"] == "pass"
    assert set(registry["tool_names"]) == set(MANAGER_TOOL_NAMES)
    assert {
        spec["tool_name"]: spec["tool_mode"]
        for spec in registry["tool_specs"]
    }["proactive.run"] == "chat_first_no_send_candidate"
    assert all(spec["lab_only"] is True for spec in registry["tool_specs"])
    assert all(
        spec["canonical_mutation_allowed"] is False
        for spec in registry["tool_specs"]
    )
    assert registry["session_history_is_not_memory_store"] is True
    assert registry["tool_results_must_return_to_manager_pass"] is True
    assert registry["mainline_activation_enabled"] is False


def test_product_lab_manager_tool_loop_blocks_unsupported_tool(tmp_path: Path) -> None:
    artifact = run_product_lab_manager_tool_loop(
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
        store=_seed_memory_store(tmp_path),
    )

    assert artifact["status"] == "blocked"
    assert "bad-tool-1.tool.unsupported:generic.workflow_engine.run" in artifact["blockers"]
    assert artifact["product_capabilities_exercised"] == []
    assert artifact["lab_runtime_connected"] is False
    assert artifact["mainline_activation_enabled"] is False


def test_product_lab_manager_tool_loop_requires_prior_tool_results() -> None:
    artifact = run_product_lab_manager_tool_loop(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        manager_script=[
            {
                "pass_id": "manager-pass-1",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "call_id": "proactive-1",
                        "tool_name": "proactive.run",
                        "arguments": {
                            "recommendation_call_id": "missing-recommendation",
                            "rescue_call_id": "missing-rescue",
                        },
                    }
                ],
            },
            {
                "pass_id": "manager-pass-2",
                "action": "final",
                "final_response": {
                    "copy": "blocked fixture",
                    "source_tool_call_ids": ["proactive-1"],
                },
            },
        ],
    )

    assert artifact["status"] == "blocked"
    assert (
        "proactive-1.prior_tool_result.missing:recommendation_call_id"
        in artifact["blockers"]
    )
    assert "proactive-1.prior_tool_result.missing:rescue_call_id" in artifact["blockers"]
    assert artifact["dynamic_tool_results_returned_to_manager"] is False


def test_product_lab_manager_tool_loop_blocks_non_lab_mode() -> None:
    artifact = run_product_lab_manager_tool_loop(
        lab_mode="",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        manager_script=_manager_script(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["lab_mode.not_isolated_advanced_product_lab"]
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["mainline_runtime_connected"] is False


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
