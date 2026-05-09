from __future__ import annotations


def _input_packet() -> dict[str, object]:
    from app.rescue.application.no_commit_viability import (
        build_rescue_no_commit_viability_shadow_packet,
    )
    from app.rescue.application.option_generation_shadow import (
        build_rescue_option_generation_shadow_packet,
    )
    from app.rescue.application.proposal_shaping_input_shadow import (
        build_rescue_proposal_shaping_input_shadow_packet,
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
            "meal_consumption_total_kcal": 2100,
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
    option = build_rescue_option_generation_shadow_packet(
        viability_shadow_packet=viability
    )
    return build_rescue_proposal_shaping_input_shadow_packet(
        option_generation_shadow_packet=option,
    )


def _candidate_output() -> dict[str, object]:
    return {
        "proposal_headline": "Fixture headline, not user-facing",
        "proposal_summary": "Fixture summary, not user-facing",
        "coaching_frame": "Fixture frame, not user-facing",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "rubric": {
            "future_oriented": True,
            "no_shame": True,
            "not_user_facing": True,
            "fixture_only": True,
        },
    }


def test_output_validator_accepts_fixture_copy_by_declared_rubric_only() -> None:
    from app.rescue.application.proposal_shaping_output_validator_shadow import (
        validate_rescue_proposal_shaping_output_shadow,
    )

    artifact = validate_rescue_proposal_shaping_output_shadow(
        proposal_shaping_input_shadow_packet=_input_packet(),
        candidate_output=_candidate_output(),
    )

    assert artifact["artifact_type"] == "rescue_proposal_shaping_output_validation_shadow"
    assert artifact["status"] == "pass"
    assert artifact["fixture_output_validated"] is True
    assert artifact["deterministic_option"] == {
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
    }
    assert artifact["copy_payload_evaluated_semantically"] is False
    assert artifact["raw_candidate_output_included"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["provider_called"] is False
    assert artifact["runtime_effect_allowed"] is False


def test_output_validator_rejects_math_override() -> None:
    from app.rescue.application.proposal_shaping_output_validator_shadow import (
        validate_rescue_proposal_shaping_output_shadow,
    )

    candidate = _candidate_output()
    candidate["recommended_days"] = 1
    candidate["daily_kcal_adjustment"] = -300

    artifact = validate_rescue_proposal_shaping_output_shadow(
        proposal_shaping_input_shadow_packet=_input_packet(),
        candidate_output=candidate,
    )

    assert artifact["status"] == "fail"
    assert "candidate_output.recommended_days_override" in artifact["blockers"]
    assert "candidate_output.daily_kcal_adjustment_override" in artifact["blockers"]
    assert artifact["fixture_output_validated"] is False


def test_output_validator_rejects_actions_or_commit_authority() -> None:
    from app.rescue.application.proposal_shaping_output_validator_shadow import (
        validate_rescue_proposal_shaping_output_shadow,
    )

    candidate = _candidate_output()
    candidate["primary_actions"] = ["accept_rescue_plan"]
    candidate["proposal_card"] = {"title": "do not surface"}
    candidate["proposal_id"] = "proposal-1"
    candidate["commit"] = True

    artifact = validate_rescue_proposal_shaping_output_shadow(
        proposal_shaping_input_shadow_packet=_input_packet(),
        candidate_output=candidate,
    )

    assert artifact["status"] == "fail"
    assert "candidate_output.primary_actions_forbidden" in artifact["blockers"]
    assert "candidate_output.proposal_card_forbidden" in artifact["blockers"]
    assert "candidate_output.proposal_id_forbidden" in artifact["blockers"]
    assert "candidate_output.commit_forbidden" in artifact["blockers"]
    assert artifact["proposal_committed"] is False
    assert artifact["ledger_entry_created"] is False


def test_output_validator_rejects_missing_or_false_rubric_flags() -> None:
    from app.rescue.application.proposal_shaping_output_validator_shadow import (
        validate_rescue_proposal_shaping_output_shadow,
    )

    candidate = _candidate_output()
    candidate["rubric"] = {
        "future_oriented": True,
        "no_shame": False,
        "fixture_only": True,
    }

    artifact = validate_rescue_proposal_shaping_output_shadow(
        proposal_shaping_input_shadow_packet=_input_packet(),
        candidate_output=candidate,
    )

    assert artifact["status"] == "fail"
    assert "candidate_output.rubric.no_shame_not_true" in artifact["blockers"]
    assert "candidate_output.rubric.not_user_facing_not_true" in artifact["blockers"]


def test_output_validator_blocks_input_packet_drift() -> None:
    from app.rescue.application.proposal_shaping_output_validator_shadow import (
        validate_rescue_proposal_shaping_output_shadow,
    )

    input_packet = _input_packet()
    input_packet["provider_called"] = True

    artifact = validate_rescue_proposal_shaping_output_shadow(
        proposal_shaping_input_shadow_packet=input_packet,
        candidate_output=_candidate_output(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["fixture_output_validated"] is False
    assert "proposal_shaping_input_shadow_packet.provider_called" in artifact["blockers"]
    assert artifact["provider_called"] is False
