from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ...shared.domain import ActiveBodyPlanView, CurrentBudgetView, ProposalContainer
from ..infrastructure.preference_profile_persistence import PreferenceProfileSummary

RecommendationMode = Literal["reactive_chat", "cold_start", "default"]
BudgetPosture = Literal["within_budget", "tight_budget", "over_budget"]


@dataclass(frozen=True)
class RecommendationHardConstraints:
    remaining_budget_kcal: int
    daily_budget_kcal: int
    rescue_active: bool
    calibration_proposal_active: bool
    location_required: bool


@dataclass(frozen=True)
class RecommendationSoftPreferences:
    preferred_item_kinds: tuple[str, ...] = ()
    preferred_staple_types: tuple[str, ...] = ()
    preferred_cuisine_families: tuple[str, ...] = ()
    preferred_store_names: tuple[str, ...] = ()
    drink_preference_strength: float = 0.0
    protein_posture_preference: str = "neutral"
    time_of_day_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecommendationContextPacket:
    user_id: int
    recommendation_mode: RecommendationMode
    budget_posture: BudgetPosture
    hard_constraints: RecommendationHardConstraints
    soft_preferences: RecommendationSoftPreferences
    context_window_summary: dict[str, object] = field(default_factory=dict)
    recommendation_goal: str = "meal_recommendation"
    raw_user_input: str = ""


def _looks_like_location_request(raw_user_input: str) -> bool:
    normalized = raw_user_input.strip()
    return any(token in normalized for token in ("附近", "最近", "nearby", "哪裡", "哪家"))


def _budget_posture(*, remaining_budget_kcal: int, daily_budget_kcal: int) -> BudgetPosture:
    if remaining_budget_kcal <= 0:
        return "over_budget"
    if daily_budget_kcal <= 0:
        return "tight_budget"
    if remaining_budget_kcal <= min(600, int(daily_budget_kcal * 0.35)):
        return "tight_budget"
    return "within_budget"


def _proposal_flags(open_proposals: list[ProposalContainer] | None) -> tuple[bool, bool]:
    rescue_active = False
    calibration_active = False
    for proposal in open_proposals or []:
        if proposal.proposal_status not in {"open", "deferred_pending_reminder"}:
            continue
        if proposal.proposal_type == "rescue":
            rescue_active = True
        if proposal.proposal_type == "calibration":
            calibration_active = True
    return rescue_active, calibration_active


def build_recommendation_context(
    *,
    user_id: int,
    current_budget_view: CurrentBudgetView,
    active_body_plan_view: ActiveBodyPlanView,
    preference_profile_summary: PreferenceProfileSummary | None = None,
    open_proposals: list[ProposalContainer] | None = None,
    raw_user_input: str = "",
) -> RecommendationContextPacket:
    preference_summary = preference_profile_summary or PreferenceProfileSummary(
        user_id=user_id,
        generated_at=None,
        freshness_posture="empty",
    )
    rescue_active, calibration_active = _proposal_flags(open_proposals)
    remaining_budget_kcal = int(current_budget_view.remaining_kcal or 0)
    daily_budget_kcal = int(
        current_budget_view.budget_kcal
        or active_body_plan_view.daily_budget_kcal
        or active_body_plan_view.recommended_target_kcal
        or 0
    )
    location_required = _looks_like_location_request(raw_user_input)
    recommendation_mode: RecommendationMode
    if raw_user_input.strip():
        recommendation_mode = "reactive_chat"
    elif preference_summary.freshness_posture == "empty":
        recommendation_mode = "cold_start"
    else:
        recommendation_mode = "default"

    return RecommendationContextPacket(
        user_id=user_id,
        recommendation_mode=recommendation_mode,
        budget_posture=_budget_posture(
            remaining_budget_kcal=remaining_budget_kcal,
            daily_budget_kcal=daily_budget_kcal,
        ),
        hard_constraints=RecommendationHardConstraints(
            remaining_budget_kcal=remaining_budget_kcal,
            daily_budget_kcal=daily_budget_kcal,
            rescue_active=rescue_active,
            calibration_proposal_active=calibration_active,
            location_required=location_required,
        ),
        soft_preferences=RecommendationSoftPreferences(
            preferred_item_kinds=tuple(
                facet.value for facet in preference_summary.common_item_kinds[:3]
            ),
            preferred_staple_types=tuple(
                facet.value for facet in preference_summary.common_staple_types[:3]
            ),
            preferred_cuisine_families=tuple(
                facet.value for facet in preference_summary.common_cuisine_families[:3]
            ),
            preferred_store_names=tuple(
                facet.value for facet in preference_summary.common_store_names[:3]
            ),
            drink_preference_strength=preference_summary.drink_preference_strength,
            protein_posture_preference=preference_summary.protein_posture_preference,
            time_of_day_patterns=preference_summary.time_of_day_patterns,
        ),
        context_window_summary={
            "active_meal_count": current_budget_view.active_meal_count,
            "preference_freshness": preference_summary.freshness_posture,
            "source_meal_count": preference_summary.source_meal_count,
            "source_item_count": preference_summary.source_item_count,
        },
        raw_user_input=raw_user_input,
    )
