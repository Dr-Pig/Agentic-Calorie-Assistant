from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ..domain import ActiveBodyPlanView, CurrentBudgetView, ProposalOption
from .calibration_model import CalibrationModelResult
from .calibration_proposal_gate import CalibrationProposalGateResult, CalibrationProposalOptionFamily

CalibrationSurfaceAction = Literal[
    "accept_calibration_proposal",
    "defer_calibration_proposal",
    "reject_calibration_proposal",
]

_PRIMARY_FAMILY_ORDER: tuple[CalibrationProposalOptionFamily, ...] = (
    "logging_quality_first",
    "monitor_only",
    "budget_adjustment",
    "pace_adjustment",
    "plan_reset",
)


@dataclass(frozen=True)
class CalibrationProposalResponseResult:
    surfaced: bool
    proposal_family: str | None
    reply_text: str
    top_option: ProposalOption | None
    backup_options: list[ProposalOption]
    quick_actions: list[dict[str, Any]]
    ui_hints: dict[str, Any]


def _family_priority(family: CalibrationProposalOptionFamily) -> int:
    try:
        return len(_PRIMARY_FAMILY_ORDER) - _PRIMARY_FAMILY_ORDER.index(family)
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
    return {
        "new_daily_budget_kcal": new_daily_budget,
        "new_estimated_tdee_kcal": shifted_tdee,
        "review_after_days": 14,
        "rationale_summary": "calibration budget adjustment from expenditure mismatch evidence",
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
    return {
        "new_target_pace_kg_per_week": slower_pace,
        "new_daily_budget_kcal": new_daily_budget,
        "review_after_days": 21,
        "rationale_summary": "pace adjustment toward a more sustainable deficit target",
    }


def _build_plan_reset_effect_payload(
    *,
    active_body_plan_view: ActiveBodyPlanView,
) -> dict[str, Any]:
    current_budget = int(active_body_plan_view.daily_budget_kcal or active_body_plan_view.recommended_target_kcal or 0)
    safety_floor = int(active_body_plan_view.safety_floor_kcal or 0)
    new_daily_budget = max(safety_floor, current_budget + 200)
    return {
        "new_daily_budget_kcal": new_daily_budget,
        "new_target_pace_kg_per_week": 0.25,
        "review_after_days": 28,
        "rationale_summary": "plan reset because short-horizon recovery is no longer viable",
        "plan_source": "calibration_plan_reset",
    }


def _build_logging_quality_effect_payload() -> dict[str, Any]:
    return {
        "logging_window_days": 7,
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
        summary = f"把每日目標調到 {effect_payload['new_daily_budget_kcal']} kcal，先跑 14 天再看。"
    elif family == "pace_adjustment":
        effect_payload = _build_pace_adjustment_effect_payload(active_body_plan_view=active_body_plan_view)
        summary = (
            f"把每週目標速度放慢到 {effect_payload['new_target_pace_kg_per_week']} kg，"
            f"同時把每日目標調到 {effect_payload['new_daily_budget_kcal']} kcal。"
        )
    elif family == "plan_reset":
        effect_payload = _build_plan_reset_effect_payload(active_body_plan_view=active_body_plan_view)
        summary = (
            f"重設成較可持續的 plan，新的每日目標先用 {effect_payload['new_daily_budget_kcal']} kcal，"
            f"之後 28 天再 review。"
        )
    elif family == "logging_quality_first":
        effect_payload = _build_logging_quality_effect_payload()
        summary = "先做 7 天乾淨記錄，暫時不直接改 body plan。"
    else:
        effect_payload = {"plan_change_required": False}
        summary = "先維持現況觀察，不立即修改 active body plan。"

    return ProposalOption(
        proposal_option_id=option_id_seed,
        option_type=family,
        option_label=family,
        option_summary=summary,
        rank_order=0,
        is_primary=True,
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
        return "這一輪我不建議直接改 plan。先做 7 天比較乾淨的記錄，之後再決定要不要校準每日目標。"
    if top_option.option_type == "plan_reset":
        return f"我建議直接重設成較可持續的 plan。主方案是：{top_option.option_summary}"
    if top_option.option_type == "pace_adjustment":
        return f"我建議先把節奏放緩。主方案是：{top_option.option_summary}"
    if top_option.option_type == "budget_adjustment":
        backup_text = f" 備選：{backup_options[0].option_summary}" if backup_options else ""
        return f"我建議先做一個單一主方案校準：{top_option.option_summary}{backup_text}"
    return "目前先維持不變，再繼續觀察。"


def _quick_actions(*, top_option: ProposalOption | None) -> list[dict[str, Any]]:
    if top_option is None:
        return []
    actions = [
        {"action": "accept_calibration_proposal", "label": "套用這個方案"},
        {"action": "defer_calibration_proposal", "label": "先維持不變"},
        {"action": "reject_calibration_proposal", "label": "不要這個"},
    ]
    if top_option.option_type == "logging_quality_first":
        actions[0]["label"] = "開始 7 天乾淨記錄"
    return actions


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
            reply_text="目前還不適合進 proposal lane，先維持觀察或補強資料品質。",
            top_option=None,
            backup_options=[],
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
        quick_actions=_quick_actions(top_option=top_option),
        ui_hints={
            "mode": "calibration_single_primary_proposal",
            "delivery": "chat_primary_ui_mirror",
            "current_budget_kcal": current_budget_view.budget_kcal,
            "active_daily_budget_kcal": active_body_plan_view.daily_budget_kcal,
            "primary_policy_posture": gate_result.primary_policy_posture,
        },
    )
