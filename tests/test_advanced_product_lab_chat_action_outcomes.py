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
    assert log_this["canonical_product_mutation_allowed"] is False
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
