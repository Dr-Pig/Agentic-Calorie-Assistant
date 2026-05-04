from pathlib import Path

from app.runtime.application.proactive_no_send_shadow_evaluator import (
    ProactiveNoSendShadowInput,
    build_proactive_no_send_simulation,
)
from scripts.build_proactive_no_send_simulation import write_proactive_no_send_simulation


def _by_type(artifact: dict[str, object]) -> dict[str, dict[str, object]]:
    rows = artifact["trigger_evaluations"]
    assert isinstance(rows, list)
    return {str(row["trigger_type"]): row for row in rows}


def test_no_send_simulation_records_permission_posture_and_side_effect_guards() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="weekly_insight",
                local_time="08:00",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
            ),
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                local_time="17:30",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
            ),
        ]
    )

    assert artifact["artifact_type"] == "proactive_no_send_simulation"
    assert artifact["shadow_mode"] is True
    assert artifact["real_runtime_effect"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["rescue_committed"] is False
    assert artifact["day_budget_mutated"] is False
    assert artifact["body_plan_mutated"] is False
    assert artifact["meal_thread_mutated"] is False

    rows = _by_type(artifact)
    assert rows["weekly_insight"]["permission_posture"] == "user_expected"
    assert rows["recommendation_prompt"]["permission_posture"] == "app_open_only"
    assert rows["weekly_insight"]["sent"] is False
    assert rows["weekly_insight"]["runtime_effect_allowed"] is False


def test_level_2_triggers_require_higher_threshold_and_explicit_skip_reason() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="overshoot_risk",
                local_time="17:30",
                data_sufficiency_status="basic",
                user_benefit_strength="strong",
            ),
            ProactiveNoSendShadowInput(
                trigger_type="calibration_insight",
                local_time="09:30",
                data_sufficiency_status="higher",
                user_benefit_strength="weak",
            ),
        ]
    )

    rows = _by_type(artifact)
    overshoot = rows["overshoot_risk"]
    calibration = rows["calibration_insight"]

    assert overshoot["permission_posture"] == "later_requires_explicit_consent"
    assert overshoot["suppression_status"] == "suppressed"
    assert "level_2_higher_data_sufficiency_required" in overshoot["suppression_reasons"]
    assert overshoot["level_2_gate"] == {
        "required": [
            "higher_data_sufficiency",
            "lower_frequency",
            "stronger_user_benefit",
            "explicit_suppression_reason_if_skipped",
        ],
        "passed": False,
    }
    assert calibration["suppression_status"] == "suppressed"
    assert "level_2_stronger_user_benefit_required" in calibration["suppression_reasons"]


def test_level_2_triggers_require_lower_frequency_signal() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                local_time="17:30",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
            )
        ]
    )

    row = _by_type(artifact)["recommendation_prompt"]

    assert row["suppression_status"] == "suppressed"
    assert "level_2_lower_frequency_required" in row["suppression_reasons"]
    assert row["level_2_gate"]["passed"] is False


def test_permission_posture_covers_canonical_trigger_aliases() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(trigger_type="meal_reminder"),
            ProactiveNoSendShadowInput(trigger_type="weight_reminder"),
            ProactiveNoSendShadowInput(trigger_type="recommendation_nudge_meal_time"),
            ProactiveNoSendShadowInput(trigger_type="recommendation_nudge_nearby"),
            ProactiveNoSendShadowInput(trigger_type="swap_suggestion"),
            ProactiveNoSendShadowInput(trigger_type="calibration_nudge"),
        ]
    )

    rows = _by_type(artifact)

    assert rows["meal_reminder"]["permission_posture"] == "user_expected"
    assert rows["weight_reminder"]["permission_posture"] == "user_opted_in"
    assert rows["recommendation_nudge_meal_time"]["permission_posture"] == "no_push_allowed"
    assert rows["recommendation_nudge_nearby"]["permission_posture"] == "no_push_allowed"
    assert rows["swap_suggestion"]["permission_posture"] == "no_push_allowed"
    assert rows["calibration_nudge"]["permission_posture"] == "later_requires_explicit_consent"


def test_recommendation_prompt_is_invitation_only_not_recommendation_runtime() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                local_time="17:30",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
                delivery_surface="app_open",
            )
        ]
    )

    row = _by_type(artifact)["recommendation_prompt"]

    assert row["suppression_status"] == "not_suppressed"
    assert row["recommendation_prompt_boundary"] == {
        "allowed": ["candidate_invitation_only"],
        "forbidden": [
            "output_actual_ranked_food_candidates",
            "query_live_menu_or_search",
            "create_intake_hint_packet",
            "serve_recommendation_result",
        ],
    }
    assert row["recommendation_served"] is False
    assert row["intake_hint_packet_created"] is False


def test_permission_posture_suppresses_non_sendable_background_triggers() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="calibration_insight",
                local_time="09:30",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
            ),
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                local_time="17:30",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
            ),
        ]
    )

    rows = _by_type(artifact)

    assert rows["calibration_insight"]["suppression_status"] == "suppressed"
    assert "permission_explicit_consent_required" in rows["calibration_insight"]["suppression_reasons"]
    assert rows["recommendation_prompt"]["suppression_status"] == "suppressed"
    assert "permission_app_open_required" in rows["recommendation_prompt"]["suppression_reasons"]


def test_user_opted_in_triggers_require_trigger_opt_in_signal() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(trigger_type="weight_reminder"),
            ProactiveNoSendShadowInput(
                trigger_type="low_frequency_weight_log_reminder",
                trigger_opt_in_ready=True,
            ),
        ]
    )

    rows = _by_type(artifact)

    assert rows["weight_reminder"]["suppression_status"] == "suppressed"
    assert "permission_trigger_opt_in_required" in rows["weight_reminder"]["suppression_reasons"]
    assert rows["low_frequency_weight_log_reminder"]["suppression_status"] == "not_suppressed"


def test_calibration_and_rescue_related_triggers_are_invitations_not_decisions() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="calibration_insight",
                local_time="09:30",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
                explicit_consent_ready=True,
            ),
            ProactiveNoSendShadowInput(
                trigger_type="rescue_nudge",
                local_time="19:30",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
            ),
        ]
    )

    rows = _by_type(artifact)
    calibration = rows["calibration_insight"]
    rescue = rows["rescue_nudge"]

    assert calibration["allowed_output"] == ["offer_calibration_preview"]
    assert calibration["forbidden_output"] == [
        "tell_user_should_change_target",
        "output_specific_new_kcal_target",
        "mutate_body_plan",
    ]
    assert calibration["body_plan_mutated"] is False
    assert rescue["suppression_status"] == "deferred_later_only"
    assert rescue["allowed_output"] == ["invite_future_rescue_review"]
    assert rescue["forbidden_output"] == [
        "output_specific_future_deficit",
        "create_rescue_proposal",
        "mutate_day_budget_ledger",
    ]
    assert rescue["rescue_committed"] is False


def test_level_3_later_only_triggers_are_deferred_with_reason() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(trigger_type="location_based_food_push"),
            ProactiveNoSendShadowInput(trigger_type="strict_multi_day_correction"),
            ProactiveNoSendShadowInput(trigger_type="emotional_coaching_nudge"),
            ProactiveNoSendShadowInput(trigger_type="memory_driven_intervention"),
        ]
    )

    rows = _by_type(artifact)

    for trigger_type in [
        "location_based_food_push",
        "strict_multi_day_correction",
        "emotional_coaching_nudge",
        "memory_driven_intervention",
    ]:
        assert rows[trigger_type]["permission_posture"] == "later_requires_explicit_consent"
        assert rows[trigger_type]["suppression_status"] == "deferred_later_only"
        assert "later_only_trigger_not_live_eligible" in rows[trigger_type]["suppression_reasons"]


def test_writer_creates_default_no_send_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "proactive_no_send_simulation.json"

    written = write_proactive_no_send_simulation(output_path=output_path)

    assert written == output_path
    assert written.exists()
    payload = written.read_text(encoding="utf-8")
    assert '"artifact_type": "proactive_no_send_simulation"' in payload
    assert '"proactive_sent": false' in payload


def test_default_artifact_covers_canonical_and_shadow_trigger_sets(tmp_path: Path) -> None:
    output_path = tmp_path / "proactive_no_send_simulation.json"

    written = write_proactive_no_send_simulation(output_path=output_path)
    artifact_text = written.read_text(encoding="utf-8")

    for trigger_type in [
        "meal_reminder",
        "weight_reminder",
        "rescue_nudge",
        "recommendation_nudge_meal_time",
        "recommendation_nudge_nearby",
        "swap_suggestion",
        "weekly_insight",
        "calibration_nudge",
        "missing_log_reminder_with_cooldown",
        "low_frequency_weight_log_reminder",
        "pre_meal_budget_awareness",
        "overshoot_risk",
        "calibration_insight",
        "recommendation_prompt",
        "location_based_food_push",
        "strict_multi_day_correction",
        "emotional_coaching_nudge",
        "memory_driven_intervention",
    ]:
        assert f'"trigger_type": "{trigger_type}"' in artifact_text

    for trigger_type in [
        "location_based_food_push",
        "strict_multi_day_correction",
        "emotional_coaching_nudge",
        "memory_driven_intervention",
    ]:
        assert '"suppression_status": "deferred_later_only"' in artifact_text
        assert '"later_only_trigger_not_live_eligible"' in artifact_text
