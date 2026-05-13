from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import empty_product_lab_memory_context_pack
from app.advanced_shadow_lab.product_lab_recommendation import (
    run_product_lab_recommendation,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn


def test_reusable_meal_candidate_enters_recommendation_with_drift_guard() -> None:
    artifact = run_product_lab_recommendation(
        turn={
            "session_id": "lab-session-1",
            "turn_id": "reusable-rec-turn",
            "surface": "chat",
            "semantic_intent_fixture": "next_meal_recommendation",
        },
        fixture_inputs=_recommendation_only_inputs(),
        memory_context_pack=empty_product_lab_memory_context_pack(
            session_id="lab-session-1",
            turn_id="reusable-rec-turn",
        ),
        reusable_meal_context_pack=_reusable_meal_context_pack(),
    )

    source_port = artifact["retrieval_guard_scoring"]["candidate_source_port_artifact"]

    assert "reusable-stable" in artifact["retrieval_guard_scoring"]["source_candidate_ids"]
    assert "reusable-drifted" not in artifact["retrieval_guard_scoring"][
        "source_candidate_ids"
    ]
    assert source_port["omitted_candidate_sources"] == [
        {
            "candidate_id": "reusable-drifted",
            "source_family": "reusable_meal",
            "reason": "reusable_meal_drift_requires_reestimate",
        }
    ]
    assert artifact["offer_synthesis"]["selected_primary"]["candidate_id"] == (
        "reusable-stable"
    )
    assert artifact["offer_synthesis"]["selected_primary"]["source_type"] == (
        "reusable_meal_entity"
    )


def test_manager_selected_reusable_meal_feeds_recommendation_source_port() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            "session_id": "lab-session-1",
            "turn_id": "manager-reusable-rec-turn",
            "user_id": "user-1",
            "workspace_id": "ws-1",
            "surface": "chat",
            "user_utterance": "fixture text is not a semantic oracle",
            "semantic_intent_fixture": "advanced_recommendation_rescue_proactive_loop",
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
        manager_script=_manager_script(),
    )

    reusable = artifact["manager_selected_reusable_meal_artifact"]
    recommendation = artifact["product_lab_recommendation_artifact"]
    source_port = recommendation["retrieval_guard_scoring"]["candidate_source_port_artifact"]

    assert reusable["status"] == "pass"
    assert reusable["reusable_meal_candidates"][0]["entity_id"] == "ufe-fried-rice"
    assert "ufe-fried-rice" in recommendation["retrieval_guard_scoring"][
        "source_candidate_ids"
    ]
    assert source_port["source_context_views"]["reusable_meal"] == {
        "candidate_count": 1,
        "omitted_count": 0,
    }
    assert recommendation["canonical_product_mutation_allowed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False


def test_recommendation_train_records_pr16_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] == 8
    assert plan["last_completed_pr_number"] == 16
    assert plan["active_pr_number"] == 17
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 16,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_reusable_meal_and_golden_order_bridge_completed_locally",
    }


def _recommendation_only_inputs() -> dict[str, object]:
    return {
        **build_product_lab_fixture_inputs(),
        "recommendation_payload": {
            "current_budget_view": {"remaining_kcal": 800},
            "negative_preference_summary": {"items": []},
            "open_rescue_context": {"accepted_conflict_patterns": []},
            "candidate_source_fixture": [],
        },
    }


def _reusable_meal_context_pack() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_manager_selected_reusable_meal_artifact",
        "status": "pass",
        "reusable_meal_candidates": [
            _reusable_candidate("reusable-stable", "reuse_exact", {}),
            _reusable_candidate(
                "reusable-drifted",
                "re_estimate_required",
                {"ingredient_drift": True},
            ),
        ],
    }


def _reusable_candidate(
    entity_id: str,
    decision: str,
    drift_flags: dict[str, bool],
) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "display_name": "Mom fried rice",
        "status": "confirmed",
        "review_required": False,
        "normalized_signature": "mom_fried_rice",
        "estimate_posture_decision": decision,
        "reuse_without_reestimate_allowed": decision == "reuse_exact",
        "estimated_kcal": 650,
        "estimated_kcal_range": {"min": 590, "max": 690},
        "source_refs": [f"reusable_meal:{entity_id}"],
        "drift_flags": drift_flags,
    }


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


def _manager_script() -> list[dict[str, object]]:
    return [
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
                "copy": "Compiled fixture response.",
                "source_tool_call_ids": ["reusable-meal-search-1"],
            },
        },
    ]
