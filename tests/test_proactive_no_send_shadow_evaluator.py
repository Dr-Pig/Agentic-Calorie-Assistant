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


def test_ignored_or_dismissed_proactive_feedback_lowers_future_trigger_strength() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="missing_log_reminder_with_cooldown",
                ignored_count=2,
            ),
            ProactiveNoSendShadowInput(
                trigger_type="weekly_insight",
                dismissed_count=1,
            ),
        ]
    )

    rows = _by_type(artifact)

    meal_reminder = rows["missing_log_reminder_with_cooldown"]
    weekly = rows["weekly_insight"]

    assert meal_reminder["suppression_status"] == "suppressed"
    assert "interaction_feedback_lower_frequency_required" in meal_reminder["suppression_reasons"]
    assert meal_reminder["interaction_feedback"]["adaptation"] == "lower_frequency"
    assert meal_reminder["stay_silent_until_signal"] == "next_user_engagement_or_cooldown_window"

    assert weekly["suppression_status"] == "suppressed"
    assert "interaction_feedback_dismissed_recently" in weekly["suppression_reasons"]
    assert weekly["interaction_feedback"]["adaptation"] == "suppress_once"


def test_explicit_trigger_opt_out_suppresses_but_keeps_capability_user_callable() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="meal_reminder",
                explicit_trigger_opt_out=True,
            )
        ]
    )

    row = _by_type(artifact)["meal_reminder"]

    assert row["suppression_status"] == "suppressed"
    assert "explicit_trigger_opt_out" in row["suppression_reasons"]
    assert row["interaction_feedback"]["adaptation"] == "category_suppressed"
    assert row["user_callable_when_suppressed"] is True


def test_channel_sensitivity_records_background_delivery_as_higher_interrupt_cost() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_nudge_nearby",
                delivery_surface="background",
            ),
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_nudge_nearby",
                delivery_surface="app_open",
            ),
        ]
    )

    rows = artifact["trigger_evaluations"]
    background = rows[0]
    app_open = rows[1]

    assert background["interrupt_cost"] == "high"
    assert background["suppression_status"] == "suppressed"
    assert "permission_no_push_allowed" in background["suppression_reasons"]
    assert app_open["interrupt_cost"] == "low"
    assert "permission_no_push_allowed" not in app_open["suppression_reasons"]


def test_trigger_requires_user_relevant_reason_not_only_wake_source() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="weekly_insight",
                wake_source="scheduled_check",
            ),
            ProactiveNoSendShadowInput(
                trigger_type="weekly_insight",
                wake_source="scheduled_check",
                user_relevant_reason="weekly_summary_expected_after_enough_data",
            ),
        ]
    )

    rows = artifact["trigger_evaluations"]
    missing_reason = rows[0]
    reasoned = rows[1]

    assert missing_reason["wake_source"] == "scheduled_check"
    assert missing_reason["suppression_status"] == "suppressed"
    assert "missing_user_relevant_reason" in missing_reason["suppression_reasons"]
    assert missing_reason["why_now"] == "missing_user_relevant_reason"

    assert reasoned["wake_source"] == "scheduled_check"
    assert reasoned["suppression_status"] == "not_suppressed"
    assert reasoned["why_now"] == "weekly_summary_expected_after_enough_data"


def test_manual_shadow_review_without_reason_records_review_context_not_missing_reason() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="weekly_insight",
                wake_source="manual_shadow_review",
            )
        ]
    )

    row = artifact["trigger_evaluations"][0]

    assert row["suppression_status"] == "not_suppressed"
    assert "missing_user_relevant_reason" not in row["suppression_reasons"]
    assert row["why_now"] == "manual_shadow_review_for_weekly_insight"


def test_unsafe_candidate_copy_suppresses_otherwise_reviewable_trigger() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="weekly_insight",
                wake_source="scheduled_check",
                user_relevant_reason="weekly_summary_expected_after_enough_data",
                candidate_copy="You must stop eating like this.",
                copy_posture="directive",
                copy_has_user_agency=False,
                copy_has_no_shame=False,
            )
        ]
    )

    row = artifact["trigger_evaluations"][0]

    assert row["suppression_status"] == "suppressed"
    assert "copy_posture_not_safe" in row["suppression_reasons"]
    assert "copy_user_agency_required" in row["suppression_reasons"]
    assert "copy_no_shame_required" in row["suppression_reasons"]
    assert artifact["summary"]["copy_suppressed_count"] == 1
    assert row["copy_review"] == {
        "candidate_copy_provided": True,
        "posture": "directive",
        "passed": False,
        "checks": {
            "user_agency": False,
            "no_shame": False,
            "uncertainty_honest": True,
            "invitation_only": True,
        },
        "deterministic_role": "validate_or_suppress_only",
        "llm_role": "write_or_judge_candidate_copy_before_shadow_input",
        "rewritten_by_evaluator": False,
    }
    assert row["sent"] is False
    assert row["runtime_effect_allowed"] is False


def test_safe_candidate_copy_is_reviewable_but_still_no_send() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                wake_source="app_open",
                user_relevant_reason="app_open_dinner_context_can_reduce_decision_cost",
                local_time="17:30",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
                delivery_surface="app_open",
                candidate_copy="If you are choosing dinner, I can help pick a few steady options.",
                copy_posture="invitation",
            )
        ]
    )

    row = _by_type(artifact)["recommendation_prompt"]

    assert row["suppression_status"] == "not_suppressed"
    assert row["copy_review"]["passed"] is True
    assert row["copy_review"]["rewritten_by_evaluator"] is False
    assert row["recommendation_served"] is False
    assert row["sent"] is False


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

    assert '"interaction_feedback_lower_frequency_required"' in artifact_text
    assert '"interaction_feedback_dismissed_recently"' in artifact_text
    assert '"explicit_trigger_opt_out"' in artifact_text
    assert '"wake_source": "scheduled_check"' in artifact_text
    assert '"wake_source": "state_threshold"' in artifact_text
    assert '"wake_source": "app_open"' in artifact_text
    assert '"weekly_summary_expected_after_enough_data"' in artifact_text
    assert '"budget_threshold_may_help_next_meal_decision"' in artifact_text
    assert '"app_open_dinner_context_can_reduce_decision_cost"' in artifact_text


def test_no_send_summary_groups_review_candidates_and_promotion_blockers() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            ProactiveNoSendShadowInput(
                trigger_type="recommendation_prompt",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
                delivery_surface="app_open",
            ),
            ProactiveNoSendShadowInput(
                trigger_type="calibration_insight",
                data_sufficiency_status="higher",
                user_benefit_strength="strong",
                lower_frequency_ready=True,
            ),
            ProactiveNoSendShadowInput(trigger_type="memory_driven_intervention"),
        ]
    )

    summary = artifact["summary"]

    assert summary["trigger_count"] == 3
    assert summary["candidate_for_human_review_trigger_types"] == ["recommendation_prompt"]
    assert summary["suppressed_trigger_types"] == {
        "calibration_insight": ["permission_explicit_consent_required"],
    }
    assert summary["deferred_later_only_trigger_types"] == ["memory_driven_intervention"]
    assert summary["permission_suppressed_count"] == 1
    assert summary["later_only_count"] == 1
    assert summary["live_delivery_allowed"] is False
    assert summary["scheduler_activation_allowed"] is False
    assert summary["promotion_blockers"] == [
        "human_review_required_before_live_delivery",
        "live_scheduler_not_enabled",
        "no_send_shadow_only",
    ]


def test_proactive_spec_requires_user_relevant_reason_separate_from_wake_source() -> None:
    source = (Path(__file__).resolve().parents[1] / "docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md").read_text(
        encoding="utf-8-sig"
    )

    assert "### 4.11 Wake Source Is Not User Benefit" in source
    assert "`wake_source` records why the system evaluated a trigger" in source
    assert "`user_relevant_reason` records why this moment may help the user" in source
    assert "`missing_user_relevant_reason`" in source


def test_proactive_spec_requires_copy_safety_rubric() -> None:
    source = (Path(__file__).resolve().parents[1] / "docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md").read_text(
        encoding="utf-8-sig"
    )

    assert "### 4.12 Candidate Copy Safety Rubric" in source
    assert "deterministic evaluator may validate or suppress candidate copy" in source
    assert "must not rewrite candidate copy" in source
    assert "`copy_suppressed_count`" in source
    assert "`copy_review_issues_present`" in source
