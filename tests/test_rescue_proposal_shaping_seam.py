from __future__ import annotations

from app.advanced_shadow_lab.model_profiles import ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID


def _message_flow() -> dict:
    return {
        "artifact_type": "reactive_rescue_independent_message_flow",
        "status": "pass",
        "rescue_message_created": True,
        "independent_message": {
            "message_id": "rescue-message-1",
            "message_kind": "independent_rescue_message",
            "source_message_event_id": "msg-1",
            "rendering_state": "pending_proposal_shaping",
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


def _candidate() -> dict:
    return {
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
    }


def _payload() -> dict:
    from app.rescue.application.proposal_shaping_seam import (
        build_rescue_proposal_shaping_payload,
    )

    return build_rescue_proposal_shaping_payload(
        independent_message_flow=_message_flow(),
        option_generation_result=_option_result(),
        budget_context={"local_date": "2026-05-13", "overshoot_kcal": 450},
        rescue_history_context={"recent_rescue_count": 0},
    )


def test_proposal_shaping_payload_declares_grokfast_dependency_inversion() -> None:
    payload = _payload()

    assert payload["artifact_type"] == "rescue_proposal_shaping_payload"
    assert payload["status"] == "pass"
    assert payload["stage"] == "rescue_phase1_proposal_shaping"
    assert payload["provider_profile_id"] == ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID
    assert payload["provider_contract"] == {
        "provider_family": "builderspace",
        "diagnostic_live_model": "grok-4-fast",
        "target_reasoning_model": "kimi-k2.5",
        "provider_dependency_inversion_required": True,
        "provider_specific_product_semantics_allowed": False,
        "kimi_live_calls_allowed": False,
    }
    assert payload["provider_request"]["user_payload"]["deterministic_option"] == {
        "recommended_days": 2,
        "daily_kcal_adjustment": -225,
        "cap_mode": "standard_15_percent",
        "special_posture": "strained_standard_spread",
    }
    assert payload["provider_request"]["user_payload"]["constraints"][
        "lab_user_facing_output_allowed"
    ] is True
    assert payload["provider_request"]["user_payload"]["output_contract"][
        "required_top_level_fields"
    ] == [
        "proposal_headline",
        "proposal_summary",
        "coaching_frame",
        "quick_action_posture",
        "claim_scope",
        "action_request",
        "delivery_request",
        "mutation_request",
        "reason_codes",
    ]
    assert payload["provider_request"]["user_payload"]["output_contract"][
        "nested_container_keys_forbidden"
    ] == ["proposal_shaping", "proposal", "result"]
    assert "primary_actions" in payload["forbidden_authority_fields"]
    assert payload["live_llm_invoked"] is False
    assert payload["provider_called"] is False
    assert payload["mainline_activation_enabled"] is False


def test_proposal_shaping_validator_accepts_lab_copy_without_math_authority() -> None:
    from app.rescue.application.proposal_shaping_seam import (
        validate_rescue_proposal_shaping_output,
    )

    validation = validate_rescue_proposal_shaping_output(
        proposal_shaping_payload=_payload(),
        candidate_output=_candidate(),
    )

    assert validation["status"] == "pass"
    assert validation["copy_guard_passed"] is True
    assert validation["lab_user_facing_surface_allowed"] is True
    assert validation["mainline_activation_enabled"] is False
    assert validation["shaped_proposal"]["proposal_headline"].startswith("A small")
    assert validation["shaped_proposal"]["quick_action_posture"] == "accept_or_adjust"
    assert "primary_actions" not in validation["shaped_proposal"]
    assert validation["deterministic_option"]["daily_kcal_adjustment"] == -225
    assert validation["proposal_committed"] is False
    assert validation["ledger_entry_created"] is False


def test_proposal_shaping_validator_rejects_math_and_authority_drift() -> None:
    from app.rescue.application.proposal_shaping_seam import (
        validate_rescue_proposal_shaping_output,
    )

    candidate = {
        **_candidate(),
        "daily_kcal_adjustment": -450,
        "proposal_id": "proposal-1",
        "primary_actions": ["accept_rescue_plan"],
        "mutation_request": True,
        "proposal_summary": "I saved this rescue plan for you.",
    }

    validation = validate_rescue_proposal_shaping_output(
        proposal_shaping_payload=_payload(),
        candidate_output=candidate,
    )

    assert validation["status"] == "fail"
    assert validation["copy_guard_passed"] is False
    assert validation["shaped_proposal"] is None
    assert validation["blockers"] == [
        "candidate_output.daily_kcal_adjustment_override",
        "candidate_output.proposal_id_forbidden",
        "candidate_output.primary_actions_forbidden",
        "candidate_output.mutation_request_not_allowed",
        "candidate_output.mutation_language_present",
    ]


def test_fake_provider_runner_shapes_copy_without_live_or_mainline_activation() -> None:
    from app.rescue.application.proposal_shaping_seam import (
        run_rescue_proposal_shaping_fake_provider,
    )

    artifact = run_rescue_proposal_shaping_fake_provider(
        proposal_shaping_payload=_payload(),
        candidate_output=_candidate(),
    )

    assert artifact["artifact_type"] == "rescue_proposal_shaping_fake_provider_artifact"
    assert artifact["status"] == "pass"
    assert artifact["provider_mode"] == "fake"
    assert artifact["provider_called"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["lab_user_facing_surface_allowed"] is True
    assert artifact["validation"]["status"] == "pass"
    assert artifact["validation"]["shaped_proposal"]["proposal_summary"]
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["canonical_mutation_changed"] is False


def test_grokfast_diagnostic_runner_validates_provider_output_advisory_only() -> None:
    from app.rescue.application.proposal_shaping_seam import (
        FakeRescueProposalShapingProvider,
        run_rescue_proposal_shaping_provider_diagnostic,
    )

    artifact = run_rescue_proposal_shaping_provider_diagnostic(
        proposal_shaping_payload=_payload(),
        provider=FakeRescueProposalShapingProvider(_candidate()),
        provider_mode=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        live_llm_invoked=True,
    )

    assert artifact["artifact_type"] == "rescue_proposal_shaping_provider_diagnostic"
    assert artifact["status"] == "pass"
    assert artifact["provider_called"] is True
    assert artifact["live_llm_invoked"] is True
    assert artifact["live_provider_used"] is True
    assert artifact["provider_readiness"]["model_id"] == "grok-4-fast"
    assert artifact["validation"]["status"] == "pass"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["mainline_activation_enabled"] is False
    assert "not_production_model_selection" in artifact["non_claims"]
