from __future__ import annotations

import json

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def test_product_lab_rescue_runtime_builds_chat_first_proposal_lifecycle() -> None:
    from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue

    artifact = run_product_lab_rescue(fixture_inputs=build_product_lab_fixture_inputs())
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "advanced_product_lab_rescue_runtime_artifact"
    assert artifact["status"] == "pass"
    assert artifact["source_shadow_chain_status"] == "pass"
    assert artifact["proposal_card"] == {
        "card_kind": "same_day_rescue_lab",
        "default_surface": "chat",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "headline": "Smooth today over 2 days.",
        "summary": "Shift 150 kcal per day while keeping the safety floor intact.",
    }
    assert [item["lab_lifecycle_state"] for item in artifact["lifecycle_packets"]] == [
        "presented_lab",
        "accepted_lab_pending_explicit_commit",
        "dismissed_lab",
        "gentler_requested_lab",
        "shorter_requested_lab",
        "explanation_requested_lab",
    ]
    assert artifact["primary_actions"] == [
        "accept_rescue_plan",
        "dismiss_rescue_plan",
    ]
    assert artifact["negotiation_affordances"] == [
        "request_gentler_plan",
        "request_shorter_plan",
        "ask_why_this_plan",
    ]
    assert artifact["proposal_presented_to_lab"] is True
    assert artifact["rescue_lifecycle_enabled"] is True
    assert artifact["canonical_commit_requested"] is False
    assert artifact["ledger_entry_created"] is False
    assert artifact["day_budget_mutated"] is False
    assert artifact["body_plan_mutated"] is False
    assert artifact["chat_first"] is True
    assert "Fixture headline" not in serialized


def test_product_lab_rescue_preserves_guardrail_math_from_chain() -> None:
    from app.advanced_shadow_lab.product_lab_rescue import run_product_lab_rescue

    artifact = run_product_lab_rescue(fixture_inputs=build_product_lab_fixture_inputs())

    assert artifact["guardrail_math"] == {
        "rescue_needed": True,
        "recovery_viability": "viable",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "guardrail_notes": [
            "daily_cap_denominator_is_base_budget",
            "safety_floor_checked",
            "proposal_required_before_commit",
        ],
    }
    assert artifact["proposal_card"]["daily_kcal_adjustment"] == -150
    assert artifact["proposal_card"]["recommended_days"] == 2


def test_product_lab_turn_exposes_product_rescue_artifact() -> None:
    from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
    from tests.test_advanced_product_lab_runtime import _turn

    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("rescue-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    rescue = artifact["product_lab_rescue_artifact"]
    assert rescue["status"] == "pass"
    assert rescue["proposal_presented_to_lab"] is True
    assert rescue["lifecycle_packets"][1]["lab_lifecycle_state"] == (
        "accepted_lab_pending_explicit_commit"
    )
    assert rescue["canonical_commit_requested"] is False
