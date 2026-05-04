from __future__ import annotations

from collections.abc import Iterable

from app.rescue.application.shadow_option_generator import generate_rescue_option_packet
from app.rescue.application.shadow_trigger_detector import detect_rescue_trigger_candidate
from app.rescue.application.shadow_viability_scorer import score_rescue_viability
from app.rescue.domain.shadow_artifact import (
    RescueShadowCandidateArtifact,
    RescueShadowCandidatesArtifact,
    RescueShadowCandidatesSummary,
    RescueShadowInputContextSummary,
    RescueShadowOvershootSummary,
)
from app.rescue.domain.shadow_context import (
    HARD_RESCUE_CONTEXT_BLOCKS,
    RescueContextFixture,
    SOFT_RESCUE_CONTEXT_BLOCKS,
)
from app.rescue.domain.shadow_options import RescueOptionCandidate, RescueOptionPacket
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.shadow_candidate_artifact"
)

CONTEXT_CANDIDATES_IGNORED = (
    "ManagerContextPacket",
    "DurableMemory",
    "LiveProviderRuntime",
    "ProactiveSend",
    "RecommendationServing",
    "ProposalContainerCommit",
    "DayBudgetLedgerMutation",
    "BodyPlanMutation",
    "MealThreadMutation",
    "FutureBudgetOverlay",
)

FUTURE_REQUIRED_GATE_BEFORE_RUNTIME = (
    "formal_proposal_contract",
    "user_confirmation_acceptance_flow",
    "day_budget_ledger_mutation_authority",
    "body_plan_mutation_gate",
    "manager_context_packing_contract",
    "live_runtime_provider_gate",
    "proactive_gate",
    "recommendation_serving_gate",
)

_FIXTURE_CONTEXT_BLOCKS = (
    "ActiveBodyPlanView",
    "RecentCommittedMealsView",
    "DeficitSummary",
    "CalibrationPosture",
    "AdherenceSummary",
    "RescueHistorySummary",
    "OpenProposalsView",
    "ProactiveStatusView",
)


def build_rescue_shadow_candidate_artifact(
    *,
    scenario_id: str,
    context: RescueContextFixture,
) -> RescueShadowCandidateArtifact:
    trigger = detect_rescue_trigger_candidate(context)
    viability = score_rescue_viability(context, trigger)
    option_packet = generate_rescue_option_packet(context, trigger, viability)

    return RescueShadowCandidateArtifact(
        scenario_id=scenario_id,
        input_context_summary=_input_context_summary(context),
        overshoot_summary=RescueShadowOvershootSummary(
            today_overshoot_kcal=context.overshoot_summary.today_overshoot_kcal,
            weekly_overshoot_kcal=context.overshoot_summary.weekly_overshoot_kcal,
            recent_overshoot_days=context.overshoot_summary.recent_overshoot_days,
        ),
        trigger_candidate=trigger.trigger_candidate,
        rescue_viability_score=viability.rescue_viability_score,
        viability_band=viability.viability_band,
        option_candidates=option_packet.option_candidates,
        selected_shadow_option_for_review=_resolve_selected_shadow_option_for_review(
            option_packet
        ),
        options_rejected=option_packet.options_rejected,
        reason_codes=_unique(
            [
                *trigger.trigger_reason_codes,
                *viability.reason_codes,
                *option_packet.reason_codes,
            ]
        ),
        confidence=viability.confidence,
        harm_if_wrong=viability.harm_if_wrong,
        shadow_review_posture=viability.shadow_review_posture,
        context_candidates_used=_context_candidates_used(),
        context_candidates_ignored=CONTEXT_CANDIDATES_IGNORED,
        future_required_gate_before_runtime=FUTURE_REQUIRED_GATE_BEFORE_RUNTIME,
    )


def build_rescue_shadow_candidates_artifact(
    *,
    scenarios: Iterable[tuple[str, RescueContextFixture]],
) -> RescueShadowCandidatesArtifact:
    candidates = tuple(
        build_rescue_shadow_candidate_artifact(
            scenario_id=scenario_id,
            context=context,
        )
        for scenario_id, context in scenarios
    )
    return RescueShadowCandidatesArtifact(
        summary=RescueShadowCandidatesSummary(
            candidate_count=len(candidates),
            selected_shadow_option_for_review_count=sum(
                candidate.selected_shadow_option_for_review is not None
                for candidate in candidates
            ),
            rejected_option_count=sum(
                len(candidate.options_rejected) for candidate in candidates
            ),
            scenario_ids=tuple(candidate.scenario_id for candidate in candidates),
        ),
        rescue_shadow_candidates=candidates,
    )


def _resolve_selected_shadow_option_for_review(
    option_packet: RescueOptionPacket,
) -> RescueOptionCandidate | None:
    if not option_packet.selected_shadow_option_id_for_review:
        return None
    for option in option_packet.option_candidates:
        if option.option_id == option_packet.selected_shadow_option_id_for_review:
            return option
    return None


def _input_context_summary(context: RescueContextFixture) -> RescueShadowInputContextSummary:
    proactive_status = context.proactive_status
    return RescueShadowInputContextSummary(
        user_id=context.user_id,
        local_date=context.local_date,
        timezone=context.timezone,
        current_budget_active=context.current_budget.active,
        daily_budget_kcal=context.current_budget.daily_budget_kcal,
        consumed_kcal=context.current_budget.consumed_kcal,
        remaining_kcal=context.current_budget.remaining_kcal,
        day_part=context.current_budget.day_part,
        active_body_plan_active=context.active_body_plan.active,
        daily_target_kcal=context.active_body_plan.daily_target_kcal,
        safety_floor_kcal=context.active_body_plan.safety_floor_kcal,
        meal_count_today=context.recent_committed_meals.meal_count_today,
        logging_coverage=context.recent_committed_meals.logging_coverage,
        weekly_deficit_gap_kcal=context.deficit_summary.weekly_deficit_gap_kcal,
        weekly_deficit_posture=context.deficit_summary.weekly_deficit_posture,
        calibration_posture=context.calibration_posture.posture,
        calibration_confidence=context.calibration_posture.confidence,
        calibration_recently_accepted=context.calibration_posture.recently_accepted,
        calibration_uncertain=context.calibration_posture.uncertain,
        logging_quality=context.adherence_summary.logging_quality,
        adherence_score=context.adherence_summary.adherence_score,
        recent_low_adherence=context.adherence_summary.recent_low_adherence,
        user_strictness_tolerance=context.adherence_summary.user_strictness_tolerance,
        app_usage_style=context.adherence_summary.app_usage_style,
        recent_rescue_count=context.rescue_history_summary.recent_rescue_count,
        recent_non_viable_count=context.rescue_history_summary.recent_non_viable_count,
        ignored_strict_plans=context.rescue_history_summary.ignored_strict_plans,
        rescue_history_quality=context.rescue_history_summary.history_quality,
        has_open_rescue_like_proposal=(
            context.open_proposals.has_open_rescue_like_proposal
        ),
        has_open_calibration_proposal=context.open_proposals.has_open_calibration_proposal,
        proactive_suppressed=(
            proactive_status.suppressed if proactive_status is not None else None
        ),
        proactive_quiet_hours_active=(
            proactive_status.quiet_hours_active if proactive_status is not None else None
        ),
    )


def _context_candidates_used() -> tuple[str, ...]:
    return _unique(
        [
            *HARD_RESCUE_CONTEXT_BLOCKS,
            *_FIXTURE_CONTEXT_BLOCKS,
            *SOFT_RESCUE_CONTEXT_BLOCKS,
        ]
    )


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


__all__ = [
    "CONTEXT_CANDIDATES_IGNORED",
    "FUTURE_REQUIRED_GATE_BEFORE_RUNTIME",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_shadow_candidate_artifact",
    "build_rescue_shadow_candidates_artifact",
]
