from __future__ import annotations

from datetime import datetime, timezone

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID


PRIMARY_ACTIONS = [
    {"action_id": "accept_rescue_plan", "label": "接受這個方案"},
    {"action_id": "dismiss_rescue_plan", "label": "先不要"},
]


def _option_result() -> dict:
    return {
        "artifact_type": "rescue_option_generation_result",
        "status": "pass",
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


def _shaping_payload() -> dict:
    from app.rescue.application.proposal_shaping_seam import (
        build_rescue_proposal_shaping_payload,
    )

    return build_rescue_proposal_shaping_payload(
        independent_message_flow={
            "artifact_type": "reactive_rescue_independent_message_flow",
            "status": "pass",
            "rescue_message_created": True,
            "independent_message": {"message_id": "rescue-message-1"},
            "runtime_effect_allowed": False,
            "canonical_mutation_changed": False,
            "production_scheduler_delivery_allowed": False,
        },
        option_generation_result=_option_result(),
        budget_context={"local_date": "2026-05-13", "overshoot_kcal": 450},
        rescue_history_context={"recent_rescue_count": 0},
    )


def _shaping_validation() -> dict:
    from app.rescue.application.proposal_shaping_seam import (
        validate_rescue_proposal_shaping_output,
    )

    return validate_rescue_proposal_shaping_output(
        proposal_shaping_payload=_shaping_payload(),
        candidate_output={
            "proposal_headline": "A small two-day recovery plan is ready.",
            "proposal_summary": "Shift 225 kcal from each of the next two days.",
            "coaching_frame": "Keep this as planning, not punishment.",
            "quick_action_posture": "accept_or_adjust",
            "recommended_days": 2,
            "daily_kcal_adjustment": -225,
            "cap_mode": "standard_15_percent",
            "claim_scope": "lab_proposal_shaping_only",
            "action_request": False,
            "delivery_request": False,
            "mutation_request": False,
            "reason_codes": ["future_oriented", "no_shame"],
        },
    )


def _effective_policy() -> dict:
    from app.rescue.application.effective_from_policy import (
        build_rescue_effective_from_policy,
    )

    return build_rescue_effective_from_policy(
        option_generation_result=_option_result(),
        accepted_at_local=datetime(2026, 5, 13, 10, 30, tzinfo=timezone.utc),
        local_date="2026-05-13",
    )


def _payload() -> dict:
    from app.rescue.application.response_presentation_seam import (
        build_rescue_response_presentation_payload,
    )

    return build_rescue_response_presentation_payload(
        proposal_id="rescue-proposal-1",
        proposal_shaping_payload=_shaping_payload(),
        proposal_shaping_validation=_shaping_validation(),
        option_generation_result=_option_result(),
        effective_from_policy=_effective_policy(),
    )


def _candidate() -> dict:
    return {
        "reply_text": "Here is a two-day plan you can accept or adjust in chat.",
        "primary_actions": list(PRIMARY_ACTIONS),
        "negotiation_affordance": {
            "allowed_secondary_intents": [
                "shorten_rescue_plan",
                "extend_rescue_plan",
                "explain_rescue_plan",
            ],
            "not_primary_actions": True,
        },
        "ui_hints": {"display_mode": "single_rescue_proposal_card"},
        "claim_scope": "lab_response_presentation_only",
        "action_request": False,
        "delivery_request": False,
        "mutation_request": False,
        "reason_codes": ["chat_first", "single_proposal"],
    }


def test_response_presentation_payload_fixes_primary_action_contract() -> None:
    payload = _payload()

    assert payload["artifact_type"] == "rescue_response_presentation_payload"
    assert payload["status"] == "pass"
    assert payload["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert payload["primary_actions_contract"] == PRIMARY_ACTIONS
    required_fields = payload["provider_request"]["user_payload"]["output_contract"][
        "required_top_level_fields"
    ]
    assert {"reply_text", "primary_actions", "claim_scope", "reason_codes"}.issubset(
        required_fields
    )
    assert payload["provider_request"]["user_payload"]["constraints"][
        "primary_actions_must_match_contract"
    ] is True
    assert payload["mainline_activation_enabled"] is False


def test_response_presentation_validator_accepts_only_lifecycle_primary_actions() -> None:
    from app.rescue.application.response_presentation_seam import (
        validate_rescue_response_presentation_output,
    )

    validation = validate_rescue_response_presentation_output(
        response_presentation_payload=_payload(),
        candidate_output=_candidate(),
    )

    assert validation["status"] == "pass"
    assert validation["primary_actions_guard_passed"] is True
    assert validation["validated_presentation"]["primary_actions"] == PRIMARY_ACTIONS
    assert validation["validated_presentation"]["negotiation_affordance"][
        "not_primary_actions"
    ] is True
    assert validation["lab_user_facing_surface_allowed"] is True
    assert validation["proposal_committed"] is False


def test_response_presentation_validator_rejects_extra_actions_and_math_drift() -> None:
    from app.rescue.application.response_presentation_seam import (
        validate_rescue_response_presentation_output,
    )

    candidate = {
        **_candidate(),
        "primary_actions": [*PRIMARY_ACTIONS, {"action_id": "shorten_rescue_plan"}],
        "negotiation_affordance": {},
        "recommended_days": 1,
        "mutation_request": True,
    }

    validation = validate_rescue_response_presentation_output(
        response_presentation_payload=_payload(),
        candidate_output=candidate,
    )

    assert validation["status"] == "fail"
    assert validation["validated_presentation"] is None
    assert validation["blockers"] == [
        "candidate_output.primary_actions_must_match_contract",
        "candidate_output.primary_action_label_missing:shorten_rescue_plan",
        "candidate_output.negotiation_affordance.not_primary_actions_not_true",
        "candidate_output.negotiation_affordance.secondary_intents_mismatch",
        "candidate_output.recommended_days_override",
        "candidate_output.mutation_request_not_allowed",
    ]


def test_response_card_builds_single_proposal_card_without_commit_authority() -> None:
    from app.rescue.application.response_presentation_seam import (
        build_rescue_response_card,
        validate_rescue_response_presentation_output,
    )

    validation = validate_rescue_response_presentation_output(
        response_presentation_payload=_payload(),
        candidate_output=_candidate(),
    )
    packet = build_rescue_response_card(
        response_presentation_payload=_payload(),
        response_presentation_validation=validation,
    )

    card = packet["rescue_response_card"]
    assert packet["status"] == "pass"
    assert card["card_id"] == "rescue-proposal-1"
    assert card["overshoot_kcal"] == 450
    assert card["recommended_days"] == 2
    assert card["daily_kcal_adjustment"] == -225
    assert card["effective_from"] == "today"
    assert card["primary_actions"] == PRIMARY_ACTIONS
    assert card["backup_options"] == []
    assert card["negotiation_affordance"]["not_primary_actions"] is True
    assert packet["proposal_container_ref"]["status"] == "presented_contract_only"
    assert packet["proposal_committed"] is False
    assert packet["ledger_entry_created"] is False
