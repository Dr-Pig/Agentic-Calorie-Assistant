from __future__ import annotations

from app.body.application.body_calibration_service import (
    BodyCalibrationDiagnosticRequest,
    build_body_calibration_diagnostic,
)
from app.body.application.calibration_model import CalibrationModelInputs
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView


def _current_budget_view() -> CurrentBudgetView:
    return CurrentBudgetView(
        user_id=1,
        local_date="2026-05-14",
        budget_kcal=1800,
        remaining_kcal=-200,
    )


def _active_body_plan_view() -> ActiveBodyPlanView:
    return ActiveBodyPlanView(
        body_plan_id=10,
        user_id=1,
        plan_status="active",
        daily_budget_kcal=1800,
        recommended_target_kcal=1800,
        safety_floor_kcal=1200,
        estimated_tdee=2100,
        target_pace_kg_per_week=0.5,
        profile_status="ready",
    )


def _high_confidence_request() -> BodyCalibrationDiagnosticRequest:
    return BodyCalibrationDiagnosticRequest(
        model_inputs=CalibrationModelInputs(
            body_plan_estimated_tdee_kcal=2100,
            observation_window_days=21,
            body_observation_count=9,
            intake_coverage=0.93,
            operating_expenditure_shift_kcal=340,
            trend_mismatch_consistency=0.9,
            trend_volatility=0.1,
            logging_gap_ratio=0.05,
            late_logged_meal_ratio=0.05,
        ),
        current_budget_status="over_budget",
        rescue_recovery_viability="non_viable",
        current_budget_view=_current_budget_view(),
        active_body_plan_view=_active_body_plan_view(),
    )


def test_calibration_proposal_response_exposes_single_primary_card_and_hidden_alternatives() -> None:
    result = build_body_calibration_diagnostic(_high_confidence_request())
    response = result.response

    assert response.surfaced is True
    assert response.proposal_family == "budget_adjustment"
    assert len(response.proposal_cards) == 3
    primary, *alternatives = response.proposal_cards
    assert primary["option_type"] == "budget_adjustment"
    assert primary["is_primary"] is True
    assert primary["default_visibility"] == "primary_visible"
    assert primary["requires_accept_before_plan_mutation"] is True
    assert primary["effect_payload"]["new_daily_budget_kcal"] == 2000
    assert primary["effect_payload"]["delta_kcal"] == 200
    assert primary["effect_payload"]["effective_from_policy"] == "accepted_before_11_local_today_else_next_day"
    assert "calibration_adjustment_delta_kcal" not in primary["effect_payload"]
    assert [card["default_visibility"] for card in alternatives] == ["hidden_alternative", "hidden_alternative"]
    assert response.ui_hints["presentation_policy"] == "single_primary_recommendation"
    assert response.ui_hints["backup_options_default_visibility"] == "hidden"


def test_calibration_proposal_quick_actions_are_structured_and_do_not_infer_mutation_from_labels() -> None:
    result = build_body_calibration_diagnostic(_high_confidence_request())
    quick_actions = result.response.quick_actions

    actions_by_id = {action["action"]: action for action in quick_actions}
    assert list(actions_by_id) == [
        "accept_calibration_proposal",
        "view_calibration_alternatives",
        "reject_calibration_proposal",
        "defer_calibration_proposal",
    ]
    assert actions_by_id["accept_calibration_proposal"]["action_kind"] == "stored_proposal_action"
    assert actions_by_id["accept_calibration_proposal"]["requires_proposal_container_id"] is True
    assert actions_by_id["accept_calibration_proposal"]["raw_text_authorized_mutation"] is False
    assert actions_by_id["view_calibration_alternatives"]["action_kind"] == "reveal_hidden_alternatives"
    assert actions_by_id["view_calibration_alternatives"]["mutation_authorized"] is False
    assert actions_by_id["reject_calibration_proposal"]["action_kind"] == "stored_proposal_action"
    assert actions_by_id["defer_calibration_proposal"]["action_kind"] == "stored_proposal_action"


def test_logging_quality_first_uses_clean_logging_effect_payload_without_plan_mutation() -> None:
    result = build_body_calibration_diagnostic(
        BodyCalibrationDiagnosticRequest(
            model_inputs=CalibrationModelInputs(
                body_plan_estimated_tdee_kcal=2100,
                observation_window_days=14,
                body_observation_count=5,
                intake_coverage=0.79,
                operating_expenditure_shift_kcal=260,
                trend_mismatch_consistency=0.8,
                trend_volatility=0.2,
                logging_gap_ratio=0.2,
                late_logged_meal_ratio=0.3,
            ),
            current_budget_status="on_track",
            current_budget_view=_current_budget_view(),
            active_body_plan_view=_active_body_plan_view(),
        )
    )

    top_option = result.response.top_option
    assert top_option is not None
    assert top_option.option_type == "logging_quality_first"
    assert top_option.effect_payload == {
        "recording_window_days": 7,
        "required_weight_check_count": 3,
        "required_intake_coverage_target": 0.8,
        "follow_up_strategy": "clean_logging_window",
        "plan_change_required": False,
        "rationale_summary": "improve logging quality before changing the active plan",
    }
    assert result.response.proposal_cards[0]["requires_accept_before_plan_mutation"] is False
