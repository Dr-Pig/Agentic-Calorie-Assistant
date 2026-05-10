from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_product_lab_runtime import _turn


def test_product_lab_chat_action_outcomes_cover_recommendation_and_rescue() -> None:
    from app.advanced_shadow_lab.product_lab_chat_actions import (
        apply_product_lab_chat_action,
    )

    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("action-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )
    recommendation_message = artifact["lab_chat_surface"]["messages"][0]
    rescue_message = artifact["lab_chat_surface"]["messages"][1]

    log_this = apply_product_lab_chat_action(
        message=recommendation_message,
        action="log_this",
    )
    show_backups = apply_product_lab_chat_action(
        message=recommendation_message,
        action="show_backups",
    )
    accept_rescue = apply_product_lab_chat_action(
        message=rescue_message,
        action="accept_rescue_plan",
    )
    gentler = apply_product_lab_chat_action(
        message=rescue_message,
        action="request_gentler_plan",
    )

    assert log_this["status"] == "pass"
    assert log_this["outcome_type"] == "recommendation_intake_draft"
    assert log_this["lab_intake_draft_created"] is True
    assert log_this["lab_pending_intake_draft_created"] is True
    assert log_this["canonical_product_mutation_allowed"] is False
    draft = log_this["pending_intake_draft_packet"]
    assert draft["artifact_type"] == "advanced_product_lab_pending_intake_draft_packet"
    assert draft["status"] == "pass"
    assert draft["primary_candidate_id"] == "golden-1"
    assert draft["selected_candidate_snapshot"]["candidate_id"] == "golden-1"
    assert draft["requires_followup_commit_confirmation"] is True
    assert draft["actual_intake_observed"] is False
    assert draft["canonical_product_mutation_allowed"] is False
    assert draft["meal_thread_mutated"] is False
    assert draft["ledger_entry_created"] is False
    assert "memory_candidate:golden-1" in draft["source_refs"]
    assert show_backups["status"] == "pass"
    assert show_backups["lab_pending_intake_draft_created"] is False
    assert show_backups["pending_intake_draft_packet"] == {}
    assert accept_rescue["outcome_type"] == "rescue_commit_confirmation"
    assert accept_rescue["lab_rescue_commit_pending"] is True
    assert accept_rescue["ledger_entry_created"] is False
    assert gentler["outcome_type"] == "rescue_gentler_plan_requested"
    assert gentler["proposal_committed"] is False


def test_product_lab_chat_action_blocks_unsupported_workflow_action() -> None:
    from app.advanced_shadow_lab.product_lab_chat_actions import (
        apply_product_lab_chat_action,
    )

    outcome = apply_product_lab_chat_action(
        message={"workflow_family": "recommendation", "candidate_id": "rec"},
        action="accept_rescue_plan",
    )

    assert outcome["status"] == "blocked"
    assert outcome["blockers"] == ["recommendation.action_unsupported:accept_rescue_plan"]
    assert outcome["canonical_product_mutation_allowed"] is False


def test_product_lab_recommendation_log_action_requires_handoff_source() -> None:
    from app.advanced_shadow_lab.product_lab_chat_actions import (
        apply_product_lab_chat_action,
    )

    outcome = apply_product_lab_chat_action(
        message={
            "workflow_family": "recommendation",
            "candidate_id": "rec",
            "recommendation_offer": {
                "primary_candidate_id": "rec",
                "intake_handoff_state": "pending_user_intake_confirmation",
                "requires_explicit_user_intake_action": True,
                "canonical_commit_requested": False,
            },
        },
        action="log_this",
    )

    assert outcome["status"] == "blocked"
    assert outcome["lab_pending_intake_draft_created"] is False
    assert outcome["blockers"] == [
        "pending_intake_draft.recommendation_offer.candidate_snapshot_missing"
    ]
    assert outcome["pending_intake_draft_packet"]["actual_intake_observed"] is False
    assert outcome["canonical_product_mutation_allowed"] is False
