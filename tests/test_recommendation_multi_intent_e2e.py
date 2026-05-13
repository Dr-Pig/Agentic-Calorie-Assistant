from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_default_manager_script import (
    build_product_lab_default_manager_script,
)
from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory_store import ProductLabMemoryStore
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_runtime_bridge_contract import (
    bridge_product_lab_runtime_surface,
)


def test_multi_intent_e2e_runs_manager_style_query_memory_reusable_recommendation_rescue(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn(),
        fixture_inputs={
            **build_product_lab_fixture_inputs(),
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "surface": "chat",
            "reusable_meal_intake_signal": {
                "normalized_signature": "mom_fried_rice",
                "explicit_same_as_before": True,
                "repetition_count": 5,
            },
            "reusable_meal_entities": [_reusable_meal_entity()],
        },
        manager_tool_store=_seed_memory_store(tmp_path),
    )

    assert artifact["status"] == "pass"
    assert artifact["compiled_default_manager_script"]["requested_capabilities"] == [
        "query",
        "memory",
        "reusable_meal",
        "recommendation",
        "rescue",
        "proactive",
    ]
    assert artifact["manager_tool_loop_source_refs"] == [
        "manager_tool_call:memory-search-1:memory.search",
        "manager_tool_call:query-1:query.run",
        "manager_tool_call:reusable-meal-search-1:reusable_meal.search",
        "manager_tool_call:recommendation-1:recommendation.run",
        "manager_tool_call:rescue-1:rescue.run",
        "manager_tool_call:proactive-1:proactive.run",
    ]
    manager_by_call = {
        result["call_id"]: result
        for result in artifact["manager_tool_loop_artifact"]["tool_result_trace"]
    }
    recommendation = manager_by_call["recommendation-1"]["result_artifact"]
    source_port = recommendation["retrieval_guard_scoring"][
        "candidate_source_port_artifact"
    ]

    assert manager_by_call["query-1"]["result_artifact"]["status"] == "pass"
    assert manager_by_call["reusable-meal-search-1"]["result_artifact"]["status"] == "pass"
    assert "ufe-fried-rice" in recommendation["retrieval_guard_scoring"][
        "source_candidate_ids"
    ]
    assert source_port["source_context_views"]["reusable_meal"] == {
        "candidate_count": 1,
        "omitted_count": 0,
    }
    assert recommendation["pending_intake_handoff_created"] is True
    assert artifact["product_lab_rescue_artifact"]["proposal_presented_to_lab"] is True
    assert artifact["product_lab_proactive_artifact"]["status"] == "pass"
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["mainline_runtime_connected"] is False


def test_default_manager_script_and_bridge_accept_multi_intent_recommendation_e2e() -> None:
    script = build_product_lab_default_manager_script(
        turn=_turn(),
        manager_tool_store_present=True,
    )
    bridge = bridge_product_lab_runtime_surface(
        turn=_turn(),
        manager_script=script["manager_script"],
    )

    assert script["status"] == "pass"
    assert script["source_tool_call_ids"] == [
        "memory-search-1",
        "query-1",
        "reusable-meal-search-1",
        "recommendation-1",
        "rescue-1",
        "proactive-1",
    ]
    recommendation_call = script["manager_script"][2]["tool_calls"][0]
    assert recommendation_call["tool_name"] == "recommendation.run"
    assert recommendation_call["arguments"]["query_call_id"] == "query-1"
    assert recommendation_call["arguments"]["memory_context_call_id"] == "memory-search-1"
    assert recommendation_call["arguments"]["reusable_meal_call_id"] == (
        "reusable-meal-search-1"
    )
    assert bridge["status"] == "pass"
    assert [
        item["capability_id"]
        for item in bridge["shared_manager_turn_plan_preview"]["candidate_tool_calls"]
    ] == [
        "memory",
        "query",
        "reusable_meal",
        "recommendation",
        "rescue",
        "proactive",
    ]


def test_recommendation_train_records_pr17_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 7
    assert plan["last_completed_pr_number"] >= 17
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 18
    assert {
        "pr_number": 17,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_multi_intent_e2e_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]


def _turn() -> dict[str, object]:
    return {
        "session_id": "lab-session-1",
        "turn_id": "multi-intent-rec-turn",
        "user_id": "user-1",
        "workspace_id": "ws-1",
        "surface": "chat",
        "user_utterance": "fixture text is not a semantic oracle",
        "semantic_intent_fixture": "multi_intent_recommendation_e2e",
    }


def _seed_memory_store(tmp_path: Path) -> ProductLabMemoryStore:
    store = ProductLabMemoryStore(tmp_path / "memory-store")
    write = store.write_memory_events(
        session_id="lab-session-1",
        turn_id="seed-turn",
        events=[
            {
                "memory_id": "reusable-meal-hint-1",
                "memory_type": "pattern_memory",
                "summary": "Mom fried rice maps to reusable meal ufe-fried-rice.",
                "review_status": "accepted_lab",
                "source_object_refs": ["meal_thread:mt-101"],
                "intended_consumers": ["reusable_meal", "recommendation"],
            },
            {
                "memory_id": "golden-bento-1",
                "memory_type": "golden_order",
                "summary": "Often chooses a FamilyMart chicken bento.",
                "review_status": "accepted_lab",
                "source_object_refs": ["meal_thread:seed-1"],
                "intended_consumers": ["recommendation", "proactive"],
                "store_name": "FamilyMart",
                "item_names": ["chicken bento"],
                "estimated_kcal": 520,
            },
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
                "estimated_kcal": 650,
                "estimated_kcal_range": {"min": 590, "max": 690},
                "source_refs": ["meal_thread:mt-101"],
            }
        ],
    }
