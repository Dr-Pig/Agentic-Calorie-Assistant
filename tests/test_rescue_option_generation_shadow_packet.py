from __future__ import annotations


def _viability_packet(*, consumed: int, days: int = 5, base: int = 1800) -> dict[str, object]:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )

    return build_rescue_no_commit_viability_shadow_packet(
        rescue_context_projection={
            "artifact_type": "rescue_shadow_summary_context_projection",
            "status": "pass",
            "rescue_committed": False,
            "proposal_committed": False,
            "day_budget_mutated": False,
            "body_plan_mutated": False,
            "meal_thread_mutated": False,
            "durable_memory_written": False,
            "manager_context_injected": False,
            "proactive_sent": False,
            "recommendation_served": False,
        },
        current_budget_view={
            "base_budget_kcal": base,
            "effective_budget_kcal": 1800,
            "meal_consumption_total_kcal": consumed,
        },
        active_body_plan_view={
            "safety_floor_kcal": 1200,
            "target_days": [
                {
                    "local_date": f"2026-05-{10 + index:02d}",
                    "base_budget_kcal": base,
                    "calibration_adjustment_total_kcal": 0,
                }
                for index in range(days)
            ],
        },
        open_proposals_view={"open_rescue_proposal_count": 0},
    )


def test_rescue_option_generation_uses_min_days_under_standard_cap_without_commit() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=_viability_packet(consumed=2100, days=5)
    )

    assert packet["artifact_type"] == "rescue_option_generation_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["rescue_needed"] is True
    assert packet["recovery_viability"] == "viable"
    assert packet["recommended_days"] == 2
    assert packet["daily_kcal_adjustment"] == -150
    assert packet["cap_mode"] == "standard_15_percent"
    assert packet["special_posture"] == "standard_spread"
    assert packet["guardrail_notes"] == [
        "daily_cap_denominator_is_base_budget",
        "safety_floor_checked",
        "proposal_required_before_commit",
    ]
    assert packet["proposal_card"] is None
    assert packet["proposal_headline"] is None
    assert packet["candidate_copy"] is None
    assert packet["primary_actions"] == []
    assert packet["proposal_committed"] is False
    assert packet["day_budget_mutated"] is False


def test_rescue_option_generation_marks_strained_when_recovery_exceeds_ten_percent() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=_viability_packet(consumed=2520, days=5)
    )

    assert packet["recommended_days"] == 3
    assert packet["daily_kcal_adjustment"] == -240
    assert packet["recovery_viability"] == "strained"
    assert "daily_adjustment_above_10_percent" in packet["guardrail_notes"]


def test_rescue_option_generation_shorter_request_keeps_strict_fifteen_percent_cap() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=_viability_packet(consumed=2520, days=5),
        adjustment_request="shorter_more_aggressive",
    )

    assert packet["status"] == "pass"
    assert packet["rescue_needed"] is True
    assert packet["cap_mode"] == "standard_15_percent"
    assert packet["recommended_days"] == 3
    assert packet["daily_kcal_adjustment"] == -240
    assert packet["recovery_viability"] == "strained"
    assert packet["special_posture"] == "strict_15_shorter_request"
    assert "strict_15_percent_cap_enforced" in packet["guardrail_notes"]
    assert packet["proposal_committed"] is False
    assert packet["ledger_entry_created"] is False
    assert packet["runtime_effect_allowed"] is False


def test_rescue_option_generation_shorter_request_still_escalates_when_fifteen_percent_exceeds_five() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=_viability_packet(consumed=4000, days=5),
        adjustment_request="shorter_more_aggressive",
    )

    assert packet["status"] == "pass"
    assert packet["rescue_needed"] is False
    assert packet["recovery_viability"] == "non_viable"
    assert packet["cap_mode"] == "standard_15_percent"
    assert packet["special_posture"] == "rescue_stop_and_escalate"
    assert "min_days_exceeds_5" in packet["blockers"]
    assert "strict_15_percent_cap_enforced" in packet["guardrail_notes"]
    assert packet["proposal_card"] is None
    assert packet["proposal_committed"] is False


def test_rescue_option_generation_longer_gentler_extends_horizon_when_legal() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=_viability_packet(consumed=2100, days=5),
        adjustment_request="longer_gentler",
    )

    assert packet["status"] == "pass"
    assert packet["rescue_needed"] is True
    assert packet["cap_mode"] == "standard_15_percent"
    assert packet["recommended_days"] == 3
    assert packet["daily_kcal_adjustment"] == -100
    assert packet["recovery_viability"] == "viable"
    assert packet["special_posture"] == "longer_gentler_spread"
    assert "gentler_horizon_extended" in packet["guardrail_notes"]
    assert packet["proposal_headline"] is None
    assert packet["rescue_committed"] is False


def test_rescue_option_generation_blocks_strength_adjustment_below_safety_floor() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=_viability_packet(consumed=2100, days=5, base=1300),
        adjustment_request="shorter_more_aggressive",
    )

    assert packet["status"] == "pass"
    assert packet["rescue_needed"] is False
    assert packet["recovery_viability"] == "non_viable"
    assert packet["special_posture"] == "rescue_stop_and_escalate"
    assert "below_safety_floor" in packet["blockers"]
    assert packet["day_budget_mutated"] is False


def test_rescue_option_generation_escalates_when_min_days_exceeds_five() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=_viability_packet(consumed=4000, days=5)
    )

    assert packet["status"] == "pass"
    assert packet["rescue_needed"] is False
    assert packet["recovery_viability"] == "non_viable"
    assert packet["recommended_days"] is None
    assert packet["daily_kcal_adjustment"] is None
    assert packet["cap_mode"] == "standard_15_percent"
    assert packet["special_posture"] == "rescue_stop_and_escalate"
    assert "min_days_exceeds_5" in packet["blockers"]
    assert "escalate_to_calibration_review" in packet["guardrail_notes"]
    assert packet["proposal_card"] is None


def test_rescue_option_generation_blocks_input_claim_drift() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    viability = _viability_packet(consumed=2300, days=5)
    viability["proposal_committed"] = True

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=viability
    )

    assert packet["status"] == "blocked"
    assert packet["recovery_viability"] == "blocked"
    assert "viability_shadow_packet.proposal_committed" in packet["blockers"]
    assert packet["recommended_days"] is None
    assert packet["daily_kcal_adjustment"] is None
    assert packet["proposal_committed"] is False


def test_rescue_option_generation_does_not_shape_or_present_user_facing_proposal() -> None:
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    packet = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=_viability_packet(consumed=2300, days=5)
    )

    assert packet["proposal_headline"] is None
    assert packet["proposal_summary"] is None
    assert packet["coaching_frame"] is None
    assert packet["quick_action_posture"] is None
    assert packet["send_or_skip"] is None
    assert packet["runtime_effect_allowed"] is False
    assert packet["rescue_committed"] is False
    assert packet["ledger_entry_created"] is False
