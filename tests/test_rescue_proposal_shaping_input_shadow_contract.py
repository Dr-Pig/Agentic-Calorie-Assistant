from __future__ import annotations


def _option_packet(*, consumed: int = 2100) -> dict[str, object]:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )

    viability = build_rescue_no_commit_viability_shadow_packet(
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
            "base_budget_kcal": 1800,
            "effective_budget_kcal": 1800,
            "meal_consumption_total_kcal": consumed,
        },
        active_body_plan_view={
            "safety_floor_kcal": 1200,
            "target_days": [
                {
                    "local_date": f"2026-05-{10 + index:02d}",
                    "base_budget_kcal": 1800,
                    "calibration_adjustment_total_kcal": 0,
                }
                for index in range(5)
            ],
        },
        open_proposals_view={"open_rescue_proposal_count": 0},
    )
    return build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=viability
    )


def test_proposal_shaping_input_wraps_option_math_without_user_facing_copy() -> None:
    from app.rescue.application.proposal_shaping_input_shadow import (
        build_rescue_proposal_shaping_input_shadow_packet,
    )

    packet = build_rescue_proposal_shaping_input_shadow_packet(
        option_generation_shadow_packet=_option_packet(consumed=2100),
        budget_context={"current_date": "2026-05-09", "overshoot_kcal": 300},
        body_plan_context={"safety_floor_kcal": 1200},
        rescue_history_context={"recent_rescue_count": 1},
        suppression_context=[{"trigger_type": "rescue_nudge", "summary": "dismissed once"}],
    )

    assert packet["artifact_type"] == "rescue_proposal_shaping_input_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["option_generation_shadow_packet_used"] is True
    assert packet["llm_role"] == "future_proposal_framing_only"
    assert packet["deterministic_role"] == "validate_input_and_forbid_runtime_effects"
    assert packet["shaping_input_envelope"]["deterministic_option"] == {
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "recovery_viability": "viable",
        "guardrail_notes": [
            "daily_cap_denominator_is_base_budget",
            "safety_floor_checked",
            "proposal_required_before_commit",
        ],
    }
    assert packet["shaping_input_envelope"]["review_context"] == {
        "budget_context": {"current_date": "2026-05-09", "overshoot_kcal": 300},
        "body_plan_context": {"safety_floor_kcal": 1200},
        "rescue_history_context": {"recent_rescue_count": 1},
        "suppression_context": [
            {"trigger_type": "rescue_nudge", "summary": "dismissed once"}
        ],
    }
    assert packet["proposal_headline"] is None
    assert packet["proposal_summary"] is None
    assert packet["coaching_frame"] is None
    assert packet["quick_action_posture"] is None
    assert packet["primary_actions"] == []
    assert packet["proposal_committed"] is False
    assert packet["runtime_effect_allowed"] is False


def test_proposal_shaping_input_allows_escalation_posture_as_context_not_copy() -> None:
    from app.rescue.application.proposal_shaping_input_shadow import (
        build_rescue_proposal_shaping_input_shadow_packet,
    )

    packet = build_rescue_proposal_shaping_input_shadow_packet(
        option_generation_shadow_packet=_option_packet(consumed=4000),
    )

    option = packet["shaping_input_envelope"]["deterministic_option"]
    assert packet["status"] == "pass"
    assert option["special_posture"] == "rescue_stop_and_escalate"
    assert option["recommended_days"] is None
    assert option["daily_kcal_adjustment"] is None
    assert packet["proposal_summary"] is None
    assert packet["quick_action_posture"] is None


def test_proposal_shaping_input_blocks_upstream_copy_or_action_drift() -> None:
    from app.rescue.application.proposal_shaping_input_shadow import (
        build_rescue_proposal_shaping_input_shadow_packet,
    )

    option = _option_packet(consumed=2100)
    option["proposal_headline"] = "Try a two-day rescue."
    option["primary_actions"] = ["accept_rescue_plan"]

    packet = build_rescue_proposal_shaping_input_shadow_packet(
        option_generation_shadow_packet=option,
    )

    assert packet["status"] == "blocked"
    assert packet["option_generation_shadow_packet_used"] is False
    assert "option_generation_shadow_packet.proposal_headline" in packet["blockers"]
    assert "option_generation_shadow_packet.primary_actions" in packet["blockers"]
    assert packet["proposal_headline"] is None
    assert packet["primary_actions"] == []


def test_proposal_shaping_input_has_no_live_llm_or_runtime_attachment() -> None:
    from app.rescue.application.proposal_shaping_input_shadow import (
        build_rescue_proposal_shaping_input_shadow_packet,
    )

    packet = build_rescue_proposal_shaping_input_shadow_packet(
        option_generation_shadow_packet=_option_packet(consumed=2100),
    )

    assert packet["live_llm_invoked"] is False
    assert packet["provider_called"] is False
    assert packet["manager_context_injected"] is False
    assert packet["rescue_committed"] is False
    assert packet["ledger_entry_created"] is False
    assert packet["day_budget_mutated"] is False
    assert packet["body_plan_mutated"] is False
    assert packet["durable_memory_written"] is False
