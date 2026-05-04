from __future__ import annotations

from collections.abc import Iterable

from app.rescue.domain.shadow_artifact import RescueShadowCandidateArtifact
from app.rescue.domain.shadow_review_queue import (
    RescueShadowReviewPriority,
    RescueShadowReviewQueue,
    RescueShadowReviewQueueItem,
    RescueShadowReviewQueueSummary,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.shadow_review_queue"
)


def build_rescue_shadow_review_queue(
    *,
    candidates: Iterable[RescueShadowCandidateArtifact],
) -> RescueShadowReviewQueue:
    high: list[RescueShadowReviewQueueItem] = []
    medium: list[RescueShadowReviewQueueItem] = []
    low: list[RescueShadowReviewQueueItem] = []
    rejected_or_deferred: list[RescueShadowReviewQueueItem] = []

    for candidate in candidates:
        priority, reasons = _classify_candidate(candidate)
        item = _queue_item(candidate, priority=priority, reasons=reasons)
        if priority == "high":
            high.append(item)
        elif priority == "medium":
            medium.append(item)
        elif priority == "low":
            low.append(item)
        else:
            rejected_or_deferred.append(item)

    return RescueShadowReviewQueue(
        summary=RescueShadowReviewQueueSummary(
            total_candidate_count=len(high)
            + len(medium)
            + len(low)
            + len(rejected_or_deferred),
            high_priority_count=len(high),
            medium_priority_count=len(medium),
            low_priority_count=len(low),
            rejected_or_deferred_count=len(rejected_or_deferred),
            scenario_ids=tuple(
                item.scenario_id
                for bucket in (high, medium, low, rejected_or_deferred)
                for item in bucket
            ),
        ),
        high_priority_rescue_candidates=high,
        medium_priority_rescue_candidates=medium,
        low_priority_rescue_candidates=low,
        rejected_or_deferred=rejected_or_deferred,
        reasons=_unique(
            [
                *(reason for item in high for reason in item.reasons),
                *(reason for item in medium for reason in item.reasons),
                *(reason for item in low for reason in item.reasons),
                *(reason for item in rejected_or_deferred for reason in item.reasons),
            ]
        ),
    )


def _queue_item(
    candidate: RescueShadowCandidateArtifact,
    *,
    priority: RescueShadowReviewPriority,
    reasons: tuple[str, ...],
) -> RescueShadowReviewQueueItem:
    selected_type = (
        candidate.selected_shadow_option.option_type
        if candidate.selected_shadow_option is not None
        else None
    )
    return RescueShadowReviewQueueItem(
        scenario_id=candidate.scenario_id,
        priority=priority,
        reasons=reasons,
        recommended_action=candidate.recommended_action,
        viability_band=candidate.viability_band,
        confidence=candidate.confidence,
        trigger_candidate=candidate.trigger_candidate,
        selected_shadow_option_type=selected_type,
    )


def _classify_candidate(
    candidate: RescueShadowCandidateArtifact,
) -> tuple[RescueShadowReviewPriority, tuple[str, ...]]:
    summary = candidate.input_context_summary
    reason_codes = set(candidate.reason_codes)
    option_rejections = {rejection.reason_code for rejection in candidate.options_rejected}

    if not (summary.current_budget_active and summary.active_body_plan_active) or (
        "no_active_plan" in reason_codes or "no_active_plan" in option_rejections
    ):
        return "rejected_or_deferred", _candidate_reasons(
            candidate,
            "no_active_plan",
            "review_deferred_no_active_plan",
        )

    if (
        summary.has_open_rescue_like_proposal
        or summary.has_open_calibration_proposal
        or "existing_open_proposal" in reason_codes
        or "existing_open_proposal" in option_rejections
    ):
        return "rejected_or_deferred", _candidate_reasons(
            candidate,
            "existing_open_proposal",
            "review_deferred_duplicate_proposal",
        )

    if "rescue_risk_too_aggressive" in reason_codes:
        return "rejected_or_deferred", _candidate_reasons(
            candidate,
            "rescue_risk_too_aggressive",
            "review_deferred_aggressive_correction_risk",
        )

    if _has_low_logging_quality(candidate):
        return "low", _candidate_reasons(
            candidate,
            "low_logging_quality",
            "low_priority_poor_logging_quality",
        )

    if _is_small_or_not_needed(candidate):
        return "low", _candidate_reasons(
            candidate,
            "overshoot_small",
            "low_priority_informational_or_not_needed",
        )

    if _is_high_priority_repeated(candidate):
        return "high", _candidate_reasons(
            candidate,
            "repeated_overshoot",
            "weekly_deficit_off_track",
            "high_priority_repeated_overshoot_clear_weekly_gap",
        )

    if _is_one_time_large_overshoot(candidate):
        return "medium", _candidate_reasons(
            candidate,
            "overshoot_large",
            "medium_priority_one_time_large_overshoot",
        )

    if _has_sparse_evidence(candidate):
        return "low", _candidate_reasons(
            candidate,
            "rescue_history_sparse",
            "low_priority_sparse_evidence",
        )

    return "low", _candidate_reasons(candidate, "low_priority_shadow_review")


def _has_low_logging_quality(candidate: RescueShadowCandidateArtifact) -> bool:
    summary = candidate.input_context_summary
    return (
        summary.logging_coverage < 0.6
        or summary.logging_quality in {"low", "unknown"}
        or "low_logging_quality" in candidate.reason_codes
    )


def _is_small_or_not_needed(candidate: RescueShadowCandidateArtifact) -> bool:
    selected_type = (
        candidate.selected_shadow_option.option_type
        if candidate.selected_shadow_option is not None
        else None
    )
    return (
        candidate.overshoot_summary.today_overshoot_kcal <= 100
        or candidate.viability_band == "not_needed"
        or candidate.recommended_action == "discard"
        or selected_type in {"informational_only", "no_rescue_needed"}
    )


def _is_high_priority_repeated(candidate: RescueShadowCandidateArtifact) -> bool:
    summary = candidate.input_context_summary
    repeated = (
        candidate.trigger_candidate == "repeated_overshoot_pattern"
        or "repeated_overshoot" in candidate.reason_codes
        or candidate.overshoot_summary.recent_overshoot_days >= 3
    )
    good_logging = summary.logging_coverage >= 0.6 and summary.logging_quality not in {
        "low",
        "unknown",
    }
    clear_weekly_gap = summary.weekly_deficit_gap_kcal >= 500
    return repeated and good_logging and clear_weekly_gap


def _is_one_time_large_overshoot(candidate: RescueShadowCandidateArtifact) -> bool:
    repeated = (
        candidate.trigger_candidate == "repeated_overshoot_pattern"
        or candidate.overshoot_summary.recent_overshoot_days >= 3
    )
    return (
        not repeated
        and (
            candidate.overshoot_summary.today_overshoot_kcal >= 500
            or "overshoot_large" in candidate.reason_codes
        )
    )


def _has_sparse_evidence(candidate: RescueShadowCandidateArtifact) -> bool:
    return (
        candidate.input_context_summary.rescue_history_quality == "sparse"
        or "rescue_history_sparse" in candidate.reason_codes
    )


def _candidate_reasons(
    candidate: RescueShadowCandidateArtifact,
    *additional_reasons: str,
) -> tuple[str, ...]:
    return _unique([*candidate.reason_codes, *additional_reasons])


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_shadow_review_queue",
]
