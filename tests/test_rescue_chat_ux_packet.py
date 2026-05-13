from __future__ import annotations

from app.rescue.application.chat_ux_packet import build_rescue_chat_ux_packet


def _message_flow() -> dict:
    return {
        "artifact_type": "reactive_rescue_independent_message_flow",
        "status": "pass",
        "rescue_message_created": True,
        "message_independent": True,
        "independent_message": {
            "message_id": "rescue-message-1",
            "message_kind": "independent_rescue_message",
            "source_message_event_id": "msg-1",
            "rendering_state": "pending_proposal_shaping",
            "contains_formal_proposal": False,
        },
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
    }


def _option_result() -> dict:
    return {
        "artifact_type": "rescue_option_generation_result",
        "status": "pass",
        "rescue_needed": True,
        "selected_option": {
            "rescue_family": "short_horizon_spread",
            "recommended_days": 2,
            "daily_kcal_adjustment": -225,
            "cap_mode": "standard_15_percent",
            "recovery_viability": "strained",
            "special_posture": "strained_standard_spread",
        },
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
    }


def test_chat_ux_packet_builds_chat_first_guarded_packet() -> None:
    packet = build_rescue_chat_ux_packet(
        independent_message_flow=_message_flow(),
        option_generation_result=_option_result(),
    )

    assert packet["status"] == "pass"
    assert packet["chat_first"] is True
    assert packet["copy_guard_passed"] is True
    assert packet["ux_packet"]["message_id"] == "rescue-message-1"
    assert packet["ux_packet"]["primary_actions"] == [
        "accept_rescue_plan",
        "dismiss_rescue_plan",
    ]
    assert packet["ux_packet"]["deterministic_option"] == {
        "recommended_days": 2,
        "daily_kcal_adjustment": -225,
        "cap_mode": "standard_15_percent",
    }
    assert packet["proposal_committed"] is False
    assert packet["ledger_entry_created"] is False


def test_chat_ux_copy_guard_rejects_shame_or_punishment_language() -> None:
    packet = build_rescue_chat_ux_packet(
        independent_message_flow=_message_flow(),
        option_generation_result=_option_result(),
        copy_candidate={
            "headline": "You failed today",
            "summary": "Punish yourself by eating less tomorrow.",
            "explanation": "This is guilt-based.",
        },
    )

    assert packet["status"] == "fail"
    assert packet["copy_guard_passed"] is False
    assert packet["blockers"] == [
        "copy.headline.forbidden_tone_token:failed",
        "copy.summary.forbidden_tone_token:punish",
        "copy.explanation.forbidden_tone_token:guilt",
    ]


def test_chat_ux_copy_guard_rejects_deterministic_math_overrides() -> None:
    packet = build_rescue_chat_ux_packet(
        independent_message_flow=_message_flow(),
        option_generation_result=_option_result(),
        copy_candidate={
            "headline": "Small recovery plan",
            "summary": "Spread it over one day.",
            "explanation": "You can decide whether to accept.",
            "recommended_days": 1,
            "daily_kcal_adjustment": -450,
        },
    )

    assert packet["status"] == "fail"
    assert packet["blockers"] == [
        "copy.recommended_days_override",
        "copy.daily_kcal_adjustment_override",
    ]


def test_chat_ux_packet_blocks_without_independent_message() -> None:
    flow = {**_message_flow(), "rescue_message_created": False}
    packet = build_rescue_chat_ux_packet(
        independent_message_flow=flow,
        option_generation_result=_option_result(),
    )

    assert packet["status"] == "blocked"
    assert packet["blockers"] == ["independent_message_flow.message_not_created"]
    assert packet["ux_packet"] is None
