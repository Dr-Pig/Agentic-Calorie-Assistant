from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def test_product_lab_rescue_builds_pending_commit_handoff_for_chat() -> None:
    from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue

    artifact = run_product_lab_rescue(fixture_inputs=build_product_lab_fixture_inputs())
    handoff = artifact["pending_rescue_commit_packet"]

    assert handoff["artifact_type"] == "advanced_product_lab_pending_rescue_commit"
    assert handoff["handoff_state"] == "pending_user_rescue_commit_confirmation"
    assert handoff["lab_rescue_intent_created"] is True
    assert handoff["canonical_commit_requested"] is False
    assert handoff["proposal_committed"] is False
    assert handoff["proposal_card"]["recommended_days"] == 2
    assert artifact["rescue_intent_state_created"] is True


def test_product_lab_rescue_proposal_is_mirrored_on_chat_message() -> None:
    from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
    from tests.test_advanced_product_lab_runtime import _turn

    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("rescue-handoff-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )
    rescue_message = artifact["lab_chat_surface"]["messages"][1]
    proposal = rescue_message["rescue_proposal"]

    assert proposal["handoff_state"] == "pending_user_rescue_commit_confirmation"
    assert proposal["primary_actions"] == [
        "accept_rescue_plan",
        "dismiss_rescue_plan",
        "request_gentler_plan",
        "ask_why_this_plan",
    ]
    assert proposal["canonical_commit_requested"] is False
    assert rescue_message["canonical_mutation_requested"] is False
