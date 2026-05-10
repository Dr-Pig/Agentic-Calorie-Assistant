from __future__ import annotations

from app.rescue.application.option_generation_shadow import (
    build_rescue_option_generation_shadow_packet,
)


def test_same_day_rescue_presents_lab_only_proposal_actions_without_mutation() -> None:
    from app.rescue.application.chat_negotiation_lifecycle_shadow import (
        build_rescue_chat_negotiation_lifecycle_shadow,
    )

    artifact = build_rescue_chat_negotiation_lifecycle_shadow(
        option_generation_shadow_packet=_option_packet(),
        interaction_intent="present",
    )

    assert artifact["artifact_type"] == "rescue_chat_negotiation_lifecycle_shadow_packet"
    assert artifact["status"] == "pass"
    assert artifact["lifecycle_state"] == "presented"
    assert artifact["proposal_card"]["card_kind"] == "same_day_rescue_shadow"
    assert artifact["proposal_card"]["recommended_days"] == 2
    assert artifact["proposal_card"]["daily_kcal_adjustment"] == -150
    assert artifact["primary_actions"] == [
        {"action_id": "accept_rescue_plan", "effect": "accepted_shadow_only"},
        {"action_id": "dismiss_rescue_plan", "effect": "dismissed_shadow_only"},
    ]
    assert artifact["negotiation_affordances"] == [
        "request_shorter_more_aggressive",
        "request_longer_gentler",
        "ask_why_this_plan",
    ]
    assert artifact["explicit_accept_required"] is True
    assert artifact["interaction_intent_source"] == "bounded_lab_fixture_not_raw_text"
    assert artifact["semantic_interaction_owner"] == "future_llm_or_human_confirmation"
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["proposal_committed"] is False
    assert artifact["ledger_entry_created"] is False
    assert artifact["day_budget_mutated"] is False
    assert artifact["manager_context_packet_changed"] is False


def test_rescue_complaint_or_too_hard_feedback_is_negotiation_not_dismiss() -> None:
    from app.rescue.application.chat_negotiation_lifecycle_shadow import (
        build_rescue_chat_negotiation_lifecycle_shadow,
    )

    artifact = build_rescue_chat_negotiation_lifecycle_shadow(
        option_generation_shadow_packet=_option_packet(),
        interaction_intent="complaint_only",
    )

    assert artifact["lifecycle_state"] == "negotiating"
    assert artifact["negotiation_intent"] == "complaint_or_hardness_feedback"
    assert artifact["dismiss_requested"] is False
    assert artifact["proposal_committed"] is False
    assert artifact["ledger_entry_created"] is False
    assert artifact["next_shadow_step"] == "ask_or_offer_adjustment_without_state_mutation"


def test_rescue_accept_and_dismiss_are_shadow_only_lifecycle_states() -> None:
    from app.rescue.application.chat_negotiation_lifecycle_shadow import (
        build_rescue_chat_negotiation_lifecycle_shadow,
    )

    accepted = build_rescue_chat_negotiation_lifecycle_shadow(
        option_generation_shadow_packet=_option_packet(),
        interaction_intent="accept",
    )
    dismissed = build_rescue_chat_negotiation_lifecycle_shadow(
        option_generation_shadow_packet=_option_packet(),
        interaction_intent="dismiss",
    )

    assert accepted["lifecycle_state"] == "accepted_shadow"
    assert accepted["explicit_accept_detected"] is True
    assert accepted["commit_effect_requested"] is False
    assert accepted["proposal_committed"] is False
    assert accepted["ledger_entry_created"] is False

    assert dismissed["lifecycle_state"] == "dismissed_shadow"
    assert dismissed["dismiss_requested"] is True
    assert dismissed["permanent_rescue_suppression"] is False
    assert dismissed["snooze_created"] is False
    assert dismissed["proposal_committed"] is False


def test_rescue_lifecycle_blocks_option_drift_or_unknown_intent() -> None:
    from app.rescue.application.chat_negotiation_lifecycle_shadow import (
        build_rescue_chat_negotiation_lifecycle_shadow,
    )

    drifted_option = {**_option_packet(), "proposal_committed": True}
    drifted = build_rescue_chat_negotiation_lifecycle_shadow(
        option_generation_shadow_packet=drifted_option,
        interaction_intent="present",
    )
    unknown = build_rescue_chat_negotiation_lifecycle_shadow(
        option_generation_shadow_packet=_option_packet(),
        interaction_intent="raw_text_accept",
    )

    assert drifted["status"] == "blocked"
    assert "option_generation_shadow_packet.proposal_committed" in drifted["blockers"]
    assert drifted["proposal_card"] is None
    assert drifted["primary_actions"] == []
    assert unknown["status"] == "blocked"
    assert "interaction_intent.unsupported" in unknown["blockers"]
    assert unknown["proposal_committed"] is False


def _option_packet() -> dict[str, object]:
    return build_rescue_option_generation_shadow_packet(
        viability_shadow_packet={
            "artifact_type": "rescue_no_commit_viability_shadow_packet",
            "status": "pass",
            "overshoot_summary": {
                "meal_consumption_total_kcal": 2100,
                "effective_budget_kcal": 1800,
                "overshoot_kcal": 300,
            },
            "target_day_checks": [
                {
                    "local_date": "2026-05-11",
                    "base_budget_kcal": 1800,
                    "proposed_rescue_overlay_kcal": -150,
                    "candidate_effective_budget_kcal": 1650,
                    "max_10_percent_kcal": 180,
                    "max_15_percent_kcal": 270,
                    "safety_floor_kcal": 1200,
                },
                {
                    "local_date": "2026-05-12",
                    "base_budget_kcal": 1800,
                    "proposed_rescue_overlay_kcal": -150,
                    "candidate_effective_budget_kcal": 1650,
                    "max_10_percent_kcal": 180,
                    "max_15_percent_kcal": 270,
                    "safety_floor_kcal": 1200,
                },
            ],
            "runtime_effect_allowed": False,
            "proposal_committed": False,
            "rescue_committed": False,
            "ledger_entry_created": False,
            "day_budget_mutated": False,
            "body_plan_mutated": False,
            "meal_thread_mutated": False,
            "durable_memory_written": False,
            "manager_context_injected": False,
            "proactive_sent": False,
            "recommendation_served": False,
        }
    )
