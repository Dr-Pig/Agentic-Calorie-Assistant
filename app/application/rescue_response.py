from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Any, Literal

from ..domain import ProposalContainer, ProposalOption

RescueSurfaceSource = Literal["proactive", "reactive_explicit_rescue_request"]
RescuePlanIntensity = Literal["normal", "aggressive"]
RescuePlanAction = Literal[
    "accept_rescue_plan",
    "shorten_rescue_plan",
    "extend_rescue_plan",
    "reject_rescue_plan",
    "explain_rescue_plan",
]

NORMAL_CAP_PERCENT = 0.15
AGGRESSIVE_CAP_PERCENT = 0.20
MAX_RESCUE_DAYS = 5


@dataclass(frozen=True)
class RescuePlanView:
    overshoot_kcal: int
    daily_budget_kcal: int
    recommended_days: int
    daily_kcal_adjustment: int
    cap_percent: float
    intensity: RescuePlanIntensity
    feasible_within_window: bool


@dataclass(frozen=True)
class RescueResponseResult:
    surfaced: bool
    reply_text: str
    recommended_days: int | None
    daily_kcal_adjustment: int | None
    overshoot_kcal: int | None
    quick_actions: list[dict[str, Any]]
    top_option: ProposalOption | None
    backup_options: list[ProposalOption]
    ui_hints: dict[str, Any]


def _normalize_non_negative(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _find_top_option(proposal: ProposalContainer) -> ProposalOption | None:
    if proposal.top_option_id is not None:
        for option in proposal.options:
            if option.proposal_option_id == proposal.top_option_id:
                return option
    for option in proposal.options:
        if option.is_primary:
            return option
    return proposal.options[0] if proposal.options else None


def _base_budget_from_proposal(proposal: ProposalContainer, top_option: ProposalOption | None) -> int:
    metadata = proposal.metadata or {}
    trigger_summary = metadata.get("trigger_summary") if isinstance(metadata.get("trigger_summary"), dict) else {}
    ledger_summary = (
        trigger_summary.get("relevant_ledger_summary")
        if isinstance(trigger_summary.get("relevant_ledger_summary"), dict)
        else {}
    )
    budget = _normalize_non_negative(
        ledger_summary.get("effective_budget_kcal") or ledger_summary.get("budget_kcal")
    )
    if budget > 0:
        return budget

    effect_payload = top_option.effect_payload if top_option is not None else {}
    overlay_days = effect_payload.get("overlay_days")
    if isinstance(overlay_days, list):
        for day in overlay_days:
            if isinstance(day, dict):
                budget = _normalize_non_negative(day.get("base_budget_kcal"))
                if budget > 0:
                    return budget
    return 0


def _overshoot_from_proposal(proposal: ProposalContainer) -> int:
    metadata = proposal.metadata or {}
    return _normalize_non_negative(metadata.get("target_recovery_kcal"))


def _build_plan(
    *,
    overshoot_kcal: int,
    daily_budget_kcal: int,
    intensity: RescuePlanIntensity,
    forced_days: int | None = None,
) -> RescuePlanView:
    cap_percent = AGGRESSIVE_CAP_PERCENT if intensity == "aggressive" else NORMAL_CAP_PERCENT
    daily_cap = max(1, int(round(daily_budget_kcal * cap_percent)))
    min_days = max(1, ceil(overshoot_kcal / daily_cap)) if overshoot_kcal > 0 and daily_budget_kcal > 0 else 1
    feasible_within_window = min_days <= MAX_RESCUE_DAYS
    recommended_days = forced_days or min(min_days, MAX_RESCUE_DAYS)
    recommended_days = max(1, min(MAX_RESCUE_DAYS, recommended_days))
    daily_kcal_adjustment = ceil(overshoot_kcal / recommended_days) if overshoot_kcal > 0 else 0
    if daily_kcal_adjustment > daily_cap:
        daily_kcal_adjustment = daily_cap
    return RescuePlanView(
        overshoot_kcal=overshoot_kcal,
        daily_budget_kcal=daily_budget_kcal,
        recommended_days=recommended_days,
        daily_kcal_adjustment=daily_kcal_adjustment,
        cap_percent=cap_percent,
        intensity=intensity,
        feasible_within_window=feasible_within_window,
    )


def should_surface_rescue_response(
    *,
    proposal: ProposalContainer | None,
    source: RescueSurfaceSource,
) -> bool:
    if proposal is None:
        return False
    if proposal.proposal_type != "rescue" or proposal.proposal_status != "open":
        return False
    top_option = _find_top_option(proposal)
    if top_option is None:
        return False
    metadata = proposal.metadata or {}
    if metadata.get("proposal_posture") == "no_rescue":
        return False
    if source == "proactive":
        return top_option.effect_payload.get("confidence", "medium") in {"medium", "high"}
    return True


def _reply_for_plan(plan: RescuePlanView, *, source: RescueSurfaceSource) -> str:
    tone_prefix = "我先幫你抓一個補回節奏：" if source == "proactive" else "如果你現在想補回，我會建議："
    percent_text = int(round(plan.cap_percent * 100))
    reply = (
        f"{tone_prefix}你這次大約超出 {plan.overshoot_kcal} kcal。"
        f" 我建議用 {plan.recommended_days} 天攤回來，"
        f"每天大約少 {plan.daily_kcal_adjustment} kcal。"
        f" 這版會把每日回收上限控制在每日預算的 {percent_text}%。"
    )
    if not plan.feasible_within_window:
        reply += (
            f" 以目前的健康上限來看，完整攤回需要超過 {MAX_RESCUE_DAYS} 天。"
            f" 我先給你最保守的 {MAX_RESCUE_DAYS} 天版本。"
        )
    elif plan.intensity == "aggressive":
        reply += " 這是比較積極的版本，會把每日回收上限放寬到 20%。"
    return reply


def _quick_actions(*, include_adjustments: bool = True) -> list[dict[str, Any]]:
    actions = [
        {"action": "accept_rescue_plan", "label": "接受這個方案"},
        {"action": "reject_rescue_plan", "label": "不要這個方案"},
        {"action": "explain_rescue_plan", "label": "問理由"},
    ]
    if include_adjustments:
        actions.insert(1, {"action": "shorten_rescue_plan", "label": "更短更積極"})
        actions.insert(2, {"action": "extend_rescue_plan", "label": "更長更緩和"})
    return actions


def build_rescue_response_result(
    *,
    proposal: ProposalContainer | None,
    source: RescueSurfaceSource,
) -> RescueResponseResult:
    if not should_surface_rescue_response(proposal=proposal, source=source):
        return RescueResponseResult(
            surfaced=False,
            reply_text="",
            recommended_days=None,
            daily_kcal_adjustment=None,
            overshoot_kcal=None,
            quick_actions=[],
            top_option=None,
            backup_options=[],
            ui_hints={"mode": "no_rescue_surface"},
        )

    assert proposal is not None
    top_option = _find_top_option(proposal)
    daily_budget_kcal = _base_budget_from_proposal(proposal, top_option)
    overshoot_kcal = _overshoot_from_proposal(proposal)
    plan = _build_plan(
        overshoot_kcal=overshoot_kcal,
        daily_budget_kcal=daily_budget_kcal,
        intensity="normal",
    )
    return RescueResponseResult(
        surfaced=True,
        reply_text=_reply_for_plan(plan, source=source),
        recommended_days=plan.recommended_days,
        daily_kcal_adjustment=plan.daily_kcal_adjustment,
        overshoot_kcal=plan.overshoot_kcal,
        quick_actions=_quick_actions(),
        top_option=top_option,
        backup_options=[],
        ui_hints={
            "mode": "rescue_single_plan",
            "delivery": "chat_only",
            "ui_role": "proposal_inbox_mirror",
            "intake_separate": True,
            "cap_basis": "daily_budget_kcal",
            "normal_cap_percent": NORMAL_CAP_PERCENT,
            "aggressive_cap_percent": AGGRESSIVE_CAP_PERCENT,
            "max_days": MAX_RESCUE_DAYS,
        },
    )


def apply_rescue_plan_action(
    *,
    proposal: ProposalContainer,
    action: RescuePlanAction,
) -> RescueResponseResult:
    top_option = _find_top_option(proposal)
    daily_budget_kcal = _base_budget_from_proposal(proposal, top_option)
    overshoot_kcal = _overshoot_from_proposal(proposal)
    base_plan = _build_plan(
        overshoot_kcal=overshoot_kcal,
        daily_budget_kcal=daily_budget_kcal,
        intensity="normal",
    )

    if action == "accept_rescue_plan":
        return RescueResponseResult(
            surfaced=True,
            reply_text="好，我會照這個補回節奏幫你套用到接下來幾天。",
            recommended_days=base_plan.recommended_days,
            daily_kcal_adjustment=base_plan.daily_kcal_adjustment,
            overshoot_kcal=base_plan.overshoot_kcal,
            quick_actions=[],
            top_option=top_option,
            backup_options=[],
            ui_hints={"mode": "rescue_accept_pending_commit"},
        )

    if action == "reject_rescue_plan":
        return RescueResponseResult(
            surfaced=True,
            reply_text="可以，我先不套用這個方案。你是覺得太激進、太保守，還是時間安排不適合？",
            recommended_days=base_plan.recommended_days,
            daily_kcal_adjustment=base_plan.daily_kcal_adjustment,
            overshoot_kcal=base_plan.overshoot_kcal,
            quick_actions=[],
            top_option=top_option,
            backup_options=[],
            ui_hints={"mode": "rescue_reject_reason_request", "reason_surface": "chat_only"},
        )

    if action == "explain_rescue_plan":
        return RescueResponseResult(
            surfaced=True,
            reply_text=(
                f"這個方案是用每日預算的 15% 當健康上限來算。"
                f" 你這次大約超出 {base_plan.overshoot_kcal} kcal，"
                f" 分成 {base_plan.recommended_days} 天時，每天大約少 {base_plan.daily_kcal_adjustment} kcal，"
                f" 比較不容易變成過度補償。"
            ),
            recommended_days=base_plan.recommended_days,
            daily_kcal_adjustment=base_plan.daily_kcal_adjustment,
            overshoot_kcal=base_plan.overshoot_kcal,
            quick_actions=_quick_actions(include_adjustments=True),
            top_option=top_option,
            backup_options=[],
            ui_hints={"mode": "rescue_explanation"},
        )

    if action == "extend_rescue_plan":
        extended_days = min(MAX_RESCUE_DAYS, base_plan.recommended_days + 1)
        if extended_days == base_plan.recommended_days:
            reply_text = "這已經是目前最緩和的版本了，我不能再往更長天數攤。"
            plan = base_plan
        else:
            plan = _build_plan(
                overshoot_kcal=overshoot_kcal,
                daily_budget_kcal=daily_budget_kcal,
                intensity="normal",
                forced_days=extended_days,
            )
            reply_text = (
                f"可以，我把它調成 {plan.recommended_days} 天的較緩和版本，"
                f"每天大約少 {plan.daily_kcal_adjustment} kcal。"
            )
        return RescueResponseResult(
            surfaced=True,
            reply_text=reply_text,
            recommended_days=plan.recommended_days,
            daily_kcal_adjustment=plan.daily_kcal_adjustment,
            overshoot_kcal=plan.overshoot_kcal,
            quick_actions=_quick_actions(),
            top_option=top_option,
            backup_options=[],
            ui_hints={"mode": "rescue_single_plan", "intensity": "normal"},
        )

    aggressive_plan = _build_plan(
        overshoot_kcal=overshoot_kcal,
        daily_budget_kcal=daily_budget_kcal,
        intensity="aggressive",
    )
    if aggressive_plan.recommended_days >= base_plan.recommended_days and aggressive_plan.feasible_within_window:
        reply_text = "這個方案已經接近最短可行範圍了，再縮會不健康，所以我先維持目前版本。"
        plan = base_plan
    elif not aggressive_plan.feasible_within_window:
        reply_text = "就算把每日回收上限放寬到 20%，你要的更短版本還是不可行。"
        plan = aggressive_plan
    else:
        reply_text = (
            f"可以，我改成比較積極的版本：{aggressive_plan.recommended_days} 天攤回來，"
            f"每天大約少 {aggressive_plan.daily_kcal_adjustment} kcal。"
        )
        plan = aggressive_plan
    return RescueResponseResult(
        surfaced=True,
        reply_text=reply_text,
        recommended_days=plan.recommended_days,
        daily_kcal_adjustment=plan.daily_kcal_adjustment,
        overshoot_kcal=plan.overshoot_kcal,
        quick_actions=_quick_actions(),
        top_option=top_option,
        backup_options=[],
        ui_hints={"mode": "rescue_single_plan", "intensity": plan.intensity},
    )
