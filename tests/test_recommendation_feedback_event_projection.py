from __future__ import annotations

from pathlib import Path

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_memory import (
    ProductLabMemoryStore,
    build_product_lab_memory_context_pack,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from app.advanced_shadow_lab.product_lab_memory_records import scope_keys
from tests.test_advanced_product_lab_runtime import _turn


def test_recommendation_feedback_actions_project_to_shared_feedback_events() -> None:
    from app.recommendation.application.feedback_event_projection import (
        build_recommendation_feedback_event_projection,
    )

    target = _feedback_target()
    cases = [
        ("accept", "confirm"),
        ("reject", "reject"),
        ("correction", "correct"),
        ("undo", "undo"),
    ]

    for user_action, expected_action in cases:
        artifact = build_recommendation_feedback_event_projection(
            user_action=user_action,
            recommendation_feedback_target=target,
            reason="user action from chat",
        )

        assert artifact["status"] == "pass"
        assert artifact["feedback_event"]["target_type"] == "recommendation_offer"
        assert artifact["feedback_event"]["target_id"] == target["target_id"]
        assert artifact["feedback_event"]["action"] == expected_action
        assert artifact["feedback_event_role"] == "audit_input_only"
        assert artifact["source_projection_artifact_type"] == "memory_feedback_event_projection"
        assert artifact["recommendation_offer_mutated"] is False
        assert artifact["canonical_product_mutation_allowed"] is False
        assert artifact["meal_thread_mutated"] is False
        assert artifact["intake_committed"] is False
        assert artifact["ledger_entry_created"] is False
        assert artifact["durable_product_memory_written"] is False


def test_lab_runtime_exposes_recommendation_feedback_target_without_mutation(
    tmp_path: Path,
) -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-feedback-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
        lab_memory_context_pack=_memory_pack(tmp_path),
    )

    recommendation = artifact["product_lab_recommendation_artifact"]
    feedback_target = recommendation["feedback_target"]
    message_offer = artifact["lab_chat_surface"]["messages"][0][
        "recommendation_offer"
    ]

    assert feedback_target["target_type"] == "recommendation_offer"
    assert feedback_target["target_id"] == (
        "recommendation-offer:recommendation-feedback-turn:memory-oatmeal"
    )
    assert feedback_target["selected_candidate_id"] == "memory-oatmeal"
    assert feedback_target["source_turn_ids"] == ["recommendation-feedback-turn"]
    assert feedback_target["scope_keys"]["user_id"] == "advanced-product-lab-user"
    assert feedback_target["source_refs"] == [
        "recommendation_offer:recommendation-offer:recommendation-feedback-turn:memory-oatmeal",
        "turn:recommendation-feedback-turn",
        "memory_candidate:memory-oatmeal",
    ]
    assert message_offer["feedback_target"] == feedback_target
    assert message_offer["feedback_actions"] == [
        "accept",
        "reject",
        "correction",
        "undo",
    ]
    assert recommendation["feedback_event_projection_ready"] is True
    assert recommendation["canonical_product_mutation_allowed"] is False


def test_recommendation_train_records_pr13_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 11
    assert plan["last_completed_pr_number"] >= 13
    assert plan["active_pr_number"] >= 14
    assert {
        "pr_number": 13,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_feedback_event_projection_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]


def _feedback_target() -> dict[str, object]:
    return {
        "target_type": "recommendation_offer",
        "target_id": "recommendation-offer:turn-1:memory-oatmeal",
        "selected_candidate_id": "memory-oatmeal",
        "scope_keys": scope_keys("lab-session-1"),
        "source_turn_ids": ["turn-1"],
        "source_refs": [
            "recommendation_offer:recommendation-offer:turn-1:memory-oatmeal",
            "turn:turn-1",
            "memory_candidate:memory-oatmeal",
        ],
    }


def _memory_pack(tmp_path: Path) -> dict[str, object]:
    store = ProductLabMemoryStore(tmp_path)
    store.write_memory_events(
        session_id="closure-session",
        turn_id="t1",
        events=[
            {
                "memory_id": "memory-oatmeal",
                "memory_type": "golden_order",
                "summary": "Morning Bar oatmeal is reliable before meetings.",
                "review_status": "accepted_lab",
                "source_object_refs": ["turn:t1:user"],
                "store_name": "Morning Bar",
                "item_names": ["oatmeal"],
                "estimated_kcal": 420,
                "intended_consumers": ["recommendation", "proactive"],
            }
        ],
    )
    return build_product_lab_memory_context_pack(
        store=store,
        session_id="closure-session",
        turn_id="t2",
        consumers=["recommendation", "proactive"],
        token_budget=120,
    )
