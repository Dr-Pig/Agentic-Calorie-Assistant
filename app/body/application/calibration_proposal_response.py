from __future__ import annotations

from typing import Any

from ...shared.domain import ActiveBodyPlanView, CurrentBudgetView, ProposalOption
from .calibration_model import CalibrationModelResult
from .calibration_proposal_gate import CalibrationProposalGateResult, CalibrationProposalOptionFamily
from .calibration_proposal_response_contract import (
    CalibrationProposalResponseResult,
    CalibrationSurfaceAction,
    PLAN_CHANGING_FAMILIES,
    PRIMARY_FAMILY_ORDER,
)


def _family_priority(family: CalibrationProposalOptionFamily) -> int:
    try:
        return len(PRIMARY_FAMILY_ORDER) - PRIMARY_FAMILY_ORDER.index(family)
    except ValueError:
        return 0


def _build_budget_adjustment_effect_payload(
    *,
    calibration_result: CalibrationModelResult,
    active_body_plan_view: ActiveBodyPlanView,
) -> dict[str, Any]:
    current_budget = int(active_body_plan_view.daily_budget_kcal or active_body_plan_view.recommended_target_kcal or 0)
    current_tdee = int(active_body_plan_view.estimated_tdee or 0)
    shifted_tdee = int(calibration_result.operating_expenditure_estimate_kcal or current_tdee)
    delta_tdee = shifted_tdee - current_tdee
    step = 200 if abs(delta_tdee) >= 300 else 150
    signed_step = step if delta_tdee >= 0 else -step
    safety_floor = int(active_body_plan_view.safety_floor_kcal or 0)
    new_daily_budget = max(safety_floor, current_budget + signed_step)
    delta_kcal = new_daily_budget - current_budget
    return {
        "new_daily_budget_kcal": new_daily_budget,
        "new_estimated_tdee_kcal": shifted_tdee,
        "delta_kcal": delta_kcal,
        "effective_from_policy": "accepted_before_11_local_today_else_next_day",
        "review_after_days": 14,
        "rationale_summary": "calibration budget adjustment from expenditure mismatch evidence",
        "expected_effect_summary": f"Daily target changes by {delta_kcal:+d} kcal.",
        "guardrail_summary": f"Target remains at or above safety floor {safety_floor} kcal.",
    }


def _build_pace_adjustment_effect_payload(
    *,
    active_body_plan_view: ActiveBodyPlanView,
) -> dict[str, Any]:
    current_pace = float(active_body_plan_view.target_pace_kg_per_week or 0.5)
    slower_pace = max(0.1, round(current_pace - 0.1, 2))
    current_budget = int(active_body_plan_view.daily_budget_kcal or active_body_plan_view.recommended_target_kcal or 0)
    safety_floor = int(active_body_plan_view.safety_floor_kcal or 0)
    new_daily_budget = max(safety_floor, current_budget + 150)
    delta_kcal = new_daily_budget - current_budget
    return {
        "new_target_pace_kg_per_week": slower_pace,
        "new_daily_budget_kcal": new_daily_budget,
        "delta_kcal": delta_kcal,
        "effective_from_policy": "accepted_before_11_local_today_else_next_day",
        "review_after_days": 21,
        "rationale_summary": "pace adjustment toward a more sustainable deficit target",
        "expected_effect_summary": f"Weekly target pace changes to {slower_pace} kg.",
        "guardrail_summary": f"Target remains at or above safety floor {safety_floor} kcal.",
    }


def _build_plan_reset_effect_payload(
    *,
    active_body_plan_view: ActiveBodyPlanView,
) -> dict[str, Any]:
    current_budget = int(active_body_plan_view.daily_budget_kcal or active_body_plan_view.recommended_target_kcal or 0)
    safety_floor = int(active_body_plan_view.safety_floor_kcal or 0)
    new_daily_budget = max(safety_floor, current_budget + 200)
    delta_kcal = new_daily_budget - current_budget
    return {
        "new_daily_budget_kcal": new_daily_budget,
        "new_target_pace_kg_per_week": 0.25,
        "delta_kcal": delta_kcal,
        "effective_from_policy": "accepted_before_11_local_today_else_next_day",
        "review_after_days": 28,
        "rationale_summary": "plan reset because short-horizon recovery is no longer viable",
        "expected_effect_summary": "Reset to a slower, more sustainable plan.",
        "guardrail_summary": f"Target remains at or above safety floor {safety_floor} kcal.",
        "plan_source": "calibration_plan_reset",
    }


def _build_logging_quality_effect_payload() -> dict[str, Any]:
    return {
        "recording_window_days": 7,
        "required_weight_check_count": 3,
        "required_intake_coverage_target": 0.8,
        "follow_up_strategy": "clean_logging_window",
        "plan_change_required": False,
        "rationale_summary": "improve logging quality before changing the active plan",
    }


def _build_option(
    *,
    option_id_seed: int,
    family: CalibrationProposalOptionFamily,
    calibration_result: CalibrationModelResult,
    active_body_plan_view: ActiveBodyPlanView,
) -> ProposalOption:
    if family == "budget_adjustment":
        effect_payload = _build_budget_adjustment_effect_payload(
            calibration_result=calibration_result,
            active_body_plan_view=active_body_plan_view,
        )
        summary = (
            f"Adjust daily target to {effect_payload['new_daily_budget_kcal']} kcal "
            "and review again after 14 days."
        )
    elif family == "pace_adjustment":
        effect_payload = _build_pace_adjustment_effect_payload(active_body_plan_view=active_body_plan_view)
        summary = (
            f"Slow weekly target pace to {effect_payload['new_target_pace_kg_per_week']} kg "
            f"and set daily target to {effect_payload['new_daily_budget_kcal']} kcal."
        )
    elif family == "plan_reset":
        effect_payload = _build_plan_reset_effect_payload(active_body_plan_view=active_body_plan_view)
        summary = (
            f"Reset to a more sustainable plan at {effect_payload['new_daily_budget_kcal']} kcal "
            "and review again after 28 days."
        )
    elif family == "logging_quality_first":
        effect_payload = _build_logging_quality_effect_payload()
        summary = "Run a 7-day clean logging window before changing the active body plan."
    else:
        effect_payload = {"plan_change_required": False}
        summary = "Keep monitoring; do not change the active body plan yet."

    return ProposalOption(
        proposal_option_id=option_id_seed,
        option_type=family,
        option_label=family,
        option_summary=summary,
        rank_order=option_id_seed - 1,
        is_primary=option_id_seed == 1,
        effect_payload=effect_payload,
    )


def _select_option_families(
    *,
    calibration_result: CalibrationModelResult,
    gate_result: CalibrationProposalGateResult,
) -> tuple[CalibrationProposalOptionFamily, ...]:
    if calibration_result.calibration_posture == "logging_quality_first":
        return ("logging_quality_first",)
    if gate_result.proposal_eligibility:
        ordered = sorted(gate_result.allowed_option_families, key=_family_priority, reverse=True)
        return tuple(ordered)
    if calibration_result.calibration_posture == "monitor_only":
        return ("monitor_only",)
    return tuple()


def _build_reply_text(
    *,
    top_option: ProposalOption,
    backup_options: list[ProposalOption],
) -> str:
    if top_option.option_type == "logging_quality_first":
        return "Logging quality is not clean enough for a plan change yet. Start with a 7-day clean logging window."
    if top_option.option_type == "plan_reset":
        return f"Calibration suggests a plan reset. {top_option.option_summary}"
    if top_option.option_type == "pace_adjustment":
        return f"Calibration suggests a pace adjustment. {top_option.option_summary}"
    if top_option.option_type == "budget_adjustment":
        backup_text = f" Hidden alternative: {backup_options[0].option_summary}" if backup_options else ""
        return f"Calibration suggests one primary budget adjustment. {top_option.option_summary}{backup_text}"
    return "Calibration should stay in monitor mode for now."


def _quick_actions(*, top_option: ProposalOption | None) -> list[dict[str, Any]]:
    if top_option is None:
        return []
    actions: list[dict[str, Any]] = [
        {
            "action": "accept_calibration_proposal",
            "label": "Apply this plan",
            "action_kind": "stored_proposal_action",
            "requires_proposal_container_id": True,
            "mutation_authorized": top_option.option_type in PLAN_CHANGING_FAMILIES,
            "raw_text_authorized_mutation": False,
        },
        {
            "action": "view_calibration_alternatives",
            "label": "View other options",
            "action_kind": "reveal_hidden_alternatives",
            "requires_proposal_container_id": False,
            "mutation_authorized": False,
            "raw_text_authorized_mutation": False,
        },
        {
            "action": "reject_calibration_proposal",
            "label": "Keep current plan",
            "action_kind": "stored_proposal_action",
            "requires_proposal_container_id": True,
            "mutation_authorized": False,
            "raw_text_authorized_mutation": False,
        },
        {
            "action": "defer_calibration_proposal",
            "label": "Decide later",
            "action_kind": "stored_proposal_action",
            "requires_proposal_container_id": True,
            "mutation_authorized": False,
            "raw_text_authorized_mutation": False,
        },
    ]
    if top_option.option_type == "logging_quality_first":
        actions[0]["label"] = "Start 7-day clean logging"
    return actions


def _proposal_card(*, option: ProposalOption, is_primary: bool) -> dict[str, Any]:
    plan_changing = option.option_type in PLAN_CHANGING_FAMILIES
    effect_payload = dict(option.effect_payload or {})
    return {
        "proposal_option_id": option.proposal_option_id,
        "option_type": option.option_type,
        "option_label": option.option_label,
        "option_summary": option.option_summary,
        "rank_order": option.rank_order,
        "is_primary": is_primary,
        "default_visibility": "primary_visible" if is_primary else "hidden_alternative",
        "effect_payload": effect_payload,
        "expected_effect_summary": effect_payload.get("expected_effect_summary"),
        "guardrail_summary": effect_payload.get("guardrail_summary"),
        "requires_accept_before_plan_mutation": plan_changing,
        "stored_action_required": True,
        "raw_text_authorized_mutation": False,
    }


def _proposal_cards(*, top_option: ProposalOption | None, backup_options: list[ProposalOption]) -> list[dict[str, Any]]:
    if top_option is None:
        return []
    cards = [_proposal_card(option=top_option, is_primary=True)]
    cards.extend(_proposal_card(option=option, is_primary=False) for option in backup_options)
    return cards


def build_calibration_proposal_response(
    *,
    calibration_result: CalibrationModelResult,
    gate_result: CalibrationProposalGateResult,
    current_budget_view: CurrentBudgetView,
    active_body_plan_view: ActiveBodyPlanView,
) -> CalibrationProposalResponseResult:
    option_families = _select_option_families(
        calibration_result=calibration_result,
        gate_result=gate_result,
    )
    if not option_families:
        return CalibrationProposalResponseResult(
            surfaced=False,
            proposal_family=None,
            reply_text="Calibration did not enter the proposal lane. Keep monitoring before changing the active plan.",
            top_option=None,
            backup_options=[],
            proposal_cards=[],
            quick_actions=[],
            ui_hints={
                "mode": "calibration_no_surface",
                "primary_policy_posture": gate_result.primary_policy_posture,
            },
        )

    options = [
        _build_option(
            option_id_seed=index + 1,
            family=family,
            calibration_result=calibration_result,
            active_body_plan_view=active_body_plan_view,
        )
        for index, family in enumerate(option_families)
    ]
    top_option = options[0]
    backup_options = options[1:]
    return CalibrationProposalResponseResult(
        surfaced=True,
        proposal_family=top_option.option_type,
        reply_text=_build_reply_text(top_option=top_option, backup_options=backup_options),
        top_option=top_option,
        backup_options=backup_options,
        proposal_cards=_proposal_cards(top_option=top_option, backup_options=backup_options),
        quick_actions=_quick_actions(top_option=top_option),
        ui_hints={
            "mode": "calibration_single_primary_proposal",
            "delivery": "chat_primary_ui_mirror",
            "presentation_policy": "single_primary_recommendation",
            "backup_options_default_visibility": "hidden",
            "current_budget_kcal": current_budget_view.budget_kcal,
            "active_daily_budget_kcal": active_body_plan_view.daily_budget_kcal,
            "primary_policy_posture": gate_result.primary_policy_posture,
        },
    )
