from __future__ import annotations

from app.advanced_shadow_lab.product_lab_default_manager_script import (
    build_product_lab_default_manager_script,
)
from app.advanced_shadow_lab.product_lab_manager_tool_contract import (
    build_product_lab_manager_tool_registry,
)
from app.advanced_shadow_lab.product_lab_manager_tool_loop import (
    run_product_lab_manager_tool_loop,
)
from app.advanced_shadow_lab.reusable_meal_intake_shadow_retrieval import (
    build_reusable_meal_intake_shadow_retrieval,
)


def _confirmed_entity(*, entity_id: str = "ufe-fried-rice") -> dict:
    return {
        "entity_id": entity_id,
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
                "source_refs": ["meal_thread:mt-101", "memory_record:rm-1"],
            }
        ],
    }


def test_manager_tool_registry_exposes_reusable_meal_search_as_lab_tool() -> None:
    artifact = build_product_lab_manager_tool_registry()

    assert "reusable_meal.search" in artifact["tool_names"]
    spec = {
        item["tool_name"]: item
        for item in artifact["tool_specs"]
    }["reusable_meal.search"]
    assert spec["capability_family"] == "reusable_meal"
    assert spec["tool_mode"] == "read_only_context"
    assert spec["canonical_mutation_allowed"] is False


def test_default_manager_script_compiles_reusable_meal_after_memory_hint() -> None:
    artifact = build_product_lab_default_manager_script(
        turn={
            "surface": "chat",
            "semantic_intent_fixture": "repeat_meal_intake_shadow",
        },
        manager_tool_store_present=True,
    )

    assert artifact["status"] == "pass"
    assert artifact["requested_capabilities"] == ["memory", "reusable_meal"]
    assert artifact["source_tool_call_ids"] == [
        "memory-search-1",
        "reusable-meal-search-1",
    ]
    first_pass = artifact["manager_script"][0]["tool_calls"]
    second_pass = artifact["manager_script"][1]["tool_calls"]
    assert [call["tool_name"] for call in first_pass] == ["memory.search"]
    assert second_pass == [
        {
            "call_id": "reusable-meal-search-1",
            "tool_name": "reusable_meal.search",
            "arguments": {"memory_context_call_id": "memory-search-1"},
        }
    ]


def test_reusable_meal_intake_shadow_retrieval_returns_typed_candidates() -> None:
    artifact = build_reusable_meal_intake_shadow_retrieval(
        scope_keys={"user_id": "user-1", "workspace_id": "ws-1", "surface": "chat"},
        intake_signal={
            "normalized_signature": "mom_fried_rice",
            "explicit_same_as_before": True,
            "repetition_count": 4,
            "ingredient_drift": False,
            "portion_drift": False,
            "source_drift": False,
        },
        reusable_meal_entities=[_confirmed_entity()],
        memory_summary={"suggested_reusable_meal_candidate_ids": ["ufe-fried-rice"]},
    )

    assert artifact["status"] == "pass"
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert artifact["raw_transcript_included"] is False

    candidates = artifact["typed_context_pack"]["reusable_meal_candidates"]
    assert len(candidates) == 1
    assert candidates[0]["entity_id"] == "ufe-fried-rice"
    assert candidates[0]["estimate_posture_decision"] == "reuse_exact"
    assert candidates[0]["memory_hint_used"] is True
    assert candidates[0]["nutrition_truth_included"] is False
    assert candidates[0]["source_refs"] == ["meal_thread:mt-101", "memory_record:rm-1"]


def test_reusable_meal_intake_shadow_retrieval_blocks_cross_scope_candidates() -> None:
    entity = _confirmed_entity()
    entity["workspace_id"] = "other-ws"

    artifact = build_reusable_meal_intake_shadow_retrieval(
        scope_keys={"user_id": "user-1", "workspace_id": "ws-1", "surface": "chat"},
        intake_signal={
            "normalized_signature": "mom_fried_rice",
            "explicit_same_as_before": True,
            "repetition_count": 4,
        },
        reusable_meal_entities=[entity],
        memory_summary={"suggested_reusable_meal_candidate_ids": ["ufe-fried-rice"]},
    )

    assert artifact["status"] == "pass"
    assert artifact["typed_context_pack"]["reusable_meal_candidates"] == []
    assert artifact["omission_trace"] == [
        {
            "entity_id": "ufe-fried-rice",
            "reason": "scope_mismatch",
        }
    ]


def test_reusable_meal_intake_shadow_retrieval_downgrades_drift_to_reestimate() -> None:
    artifact = build_reusable_meal_intake_shadow_retrieval(
        scope_keys={"user_id": "user-1", "workspace_id": "ws-1", "surface": "chat"},
        intake_signal={
            "normalized_signature": "mom_fried_rice",
            "explicit_same_as_before": True,
            "repetition_count": 6,
            "ingredient_drift": True,
            "portion_drift": False,
            "source_drift": False,
        },
        reusable_meal_entities=[_confirmed_entity()],
        memory_summary={"suggested_reusable_meal_candidate_ids": ["ufe-fried-rice"]},
    )

    candidate = artifact["typed_context_pack"]["reusable_meal_candidates"][0]
    assert candidate["estimate_posture_decision"] == "re_estimate_required"
    assert candidate["reuse_without_reestimate_allowed"] is False
    assert candidate["drift_flags"] == {
        "ingredient_drift": True,
        "portion_drift": False,
        "source_drift": False,
    }


def test_manager_tool_loop_returns_reusable_meal_search_result_to_manager() -> None:
    artifact = run_product_lab_manager_tool_loop(
        lab_mode="isolated_advanced_product_lab",
        turn={
            "session_id": "lab-session-1",
            "turn_id": "lab-turn-1",
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "surface": "chat",
            "semantic_intent_fixture": "repeat_meal_intake_shadow",
        },
        fixture_inputs={
            "reusable_meal_intake_signal": {
                "normalized_signature": "mom_fried_rice",
                "explicit_same_as_before": True,
                "repetition_count": 4,
            },
            "reusable_meal_entities": [_confirmed_entity()],
        },
        manager_script=[
            {
                "pass_id": "manager-pass-1",
                "action": "call_tools",
                "tool_calls": [
                    {
                        "call_id": "reusable-meal-search-1",
                        "tool_name": "reusable_meal.search",
                        "arguments": {},
                    }
                ],
            },
            {
                "pass_id": "manager-pass-2",
                "action": "final",
                "final_response": {
                    "copy": "Reuse candidate returned to Manager.",
                    "source_tool_call_ids": ["reusable-meal-search-1"],
                },
            },
        ],
    )

    assert artifact["status"] == "pass"
    assert artifact["product_capabilities_exercised"] == ["reusable_meal"]
    result = artifact["tool_result_trace"][0]
    assert result["tool_name"] == "reusable_meal.search"
    assert result["result_artifact_type"] == (
        "advanced_product_lab_reusable_meal_intake_shadow_retrieval"
    )
    candidates = result["result_artifact"]["typed_context_pack"][
        "reusable_meal_candidates"
    ]
    assert candidates[0]["entity_id"] == "ufe-fried-rice"
    assert result["returned_to_manager"] is True
