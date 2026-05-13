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
    normalized = artifact["manager_tool_loop_artifact"]["tool_result_trace"][0][
        "normalized_result_envelope"
    ]
    assert normalized["artifact_type"] == "shared_manager_tool_result_envelope"
    assert normalized["source_runtime"] == "advanced_product_lab"
    assert normalized["capability_id"] == "memory"
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


def test_product_lab_turn_default_path_runs_compiled_manager_tool_loop() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert artifact["status"] == "pass"
    assert artifact["manager_tool_loop_enabled"] is True
    assert artifact["manager_tool_loop_source"] == "shared_planner_compiled_default"
    assert artifact["compiled_default_manager_script"]["status"] == "pass"
    assert artifact["shared_manager_turn_plan_preview"]["primary_workflow"] == (
        "advanced_recommendation_rescue_proactive_loop"
    )
    assert artifact["manager_tool_loop_artifact"]["status"] == "pass"
    assert artifact["manager_tool_loop_source_refs"] == [
        "manager_tool_call:recommendation-1:recommendation.run",
        "manager_tool_call:rescue-1:rescue.run",
        "manager_tool_call:proactive-1:proactive.run",
    ]
    assert artifact["manager_selected_memory_context_adapter"] is None
    assert artifact["manager_selected_rescue_artifact"]["status"] == "pass"
    assert artifact["manager_selected_rescue_artifact"]["primary_actions"] == [
        "accept_rescue_plan",
        "dismiss_rescue_plan",
    ]
    assert artifact["product_capabilities_exercised"] == [
        "long_term_memory",
        "recommendation",
        "rescue",
        "proactive",
        "chat_first_controls",
    ]


def test_product_lab_turn_default_path_can_run_memory_via_shared_turn_plan_when_store_present(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs=build_product_lab_fixture_inputs(),
        manager_tool_store=_seed_memory_store(tmp_path),
    )

    assert artifact["status"] == "pass"
    assert artifact["manager_tool_loop_source"] == "shared_planner_compiled_default"
    assert artifact["compiled_default_manager_script"]["executable_capabilities"] == [
        "memory",
        "recommendation",
        "rescue",
        "proactive",
    ]
    assert artifact["shared_manager_turn_plan_preview"]["requested_capabilities"][0][
        "capability_id"
    ] == "memory"
    assert artifact["manager_tool_loop_source_refs"][0] == (
        "manager_tool_call:memory-search-1:memory.search"
    )
    assert artifact["manager_selected_memory_context_adapter"]["status"] == "pass"
    assert artifact["manager_selected_memory_context_adapter"]["memory_record_summary"][
        "selected_record_ids"
    ] == ["golden-bento-1"]
    assert artifact["manager_selected_rescue_artifact"]["proposal_presented_to_lab"] is True
    assert artifact["manager_selected_rescue_artifact"]["pending_rescue_commit_packet"][
        "lab_rescue_intent_created"
    ] is True


def test_product_lab_turn_default_path_integrates_memory_rescue_and_reusable_meal(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            "session_id": "lab-session-1",
            "turn_id": "lab-turn-1",
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "surface": "chat",
            "user_utterance": "same as before plus help me recover today",
            "semantic_intent_fixture": "repeat_meal_rescue_shadow",
        },
        fixture_inputs={
            **build_product_lab_fixture_inputs(),
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "surface": "chat",
            "reusable_meal_intake_signal": {
                "normalized_signature": "mom_fried_rice",
                "explicit_same_as_before": True,
                "repetition_count": 4,
            },
            "reusable_meal_entities": [_reusable_meal_entity()],
        },
        manager_tool_store=_seed_reusable_meal_memory_store(tmp_path),
    )

    assert artifact["status"] == "pass"
    assert artifact["compiled_default_manager_script"]["requested_capabilities"] == [
        "memory",
        "reusable_meal",
        "rescue",
    ]
    assert artifact["manager_tool_loop_source_refs"] == [
        "manager_tool_call:memory-search-1:memory.search",
        "manager_tool_call:reusable-meal-search-1:reusable_meal.search",
        "manager_tool_call:rescue-1:rescue.run",
    ]
    assert artifact["manager_tool_loop_artifact"]["product_capabilities_exercised"] == [
        "long_term_memory",
        "rescue",
        "reusable_meal",
    ]
    assert artifact["manager_selected_memory_context_adapter"]["memory_record_summary"][
        "selected_record_ids"
    ] == ["reusable-meal-hint-1"]
    reusable = artifact["manager_selected_reusable_meal_artifact"]
    assert reusable["status"] == "pass"
    assert reusable["reusable_meal_candidates"][0]["entity_id"] == "ufe-fried-rice"
    assert reusable["reusable_meal_candidates"][0]["estimate_posture_decision"] == "reuse_exact"
    assert artifact["manager_selected_rescue_artifact"]["proposal_presented_to_lab"] is True
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["durable_product_memory_written"] is False


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


def _seed_reusable_meal_memory_store(tmp_path: Path) -> ProductLabMemoryStore:
    store = ProductLabMemoryStore(tmp_path / "memory-store")
    write = store.write_memory_events(
        session_id="lab-session-1",
        turn_id="seed-turn",
        events=[
            {
                "memory_id": "reusable-meal-hint-1",
                "memory_type": "pattern_memory",
                "summary": "Mom fried rice often maps to reusable meal ufe-fried-rice.",
                "review_status": "accepted_lab",
                "source_object_refs": ["meal_thread:mt-101"],
                "intended_consumers": ["reusable_meal", "rescue"],
            }
        ],
    )
    assert write["status"] == "pass"
    return store


def _reusable_meal_entity() -> dict[str, object]:
    return {
        "entity_id": "ufe-fried-rice",
        "user_id": "user-1",
        "workspace_id": "ws-1",
        "display_name": "Mom fried rice",
        "status": "confirmed",
        "review_required": False,
        "current_version_id": "v1",
        "correction_count": 0,
        "drift_status": "stable",
        "version_history": [
            {
                "version_id": "v1",
                "normalized_signature": "mom_fried_rice",
                "source_kind": "mom_bought",
                "ingredient_profile": ["rice", "egg", "pork"],
                "portion_profile": {"serving": "large_plate"},
                "estimate_posture": "reuse_anchored",
                "source_refs": ["meal_thread:mt-101", "memory_record:reusable-meal-hint-1"],
            }
        ],
    }
