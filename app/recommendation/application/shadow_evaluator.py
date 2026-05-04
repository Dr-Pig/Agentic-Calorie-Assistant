from __future__ import annotations

from collections import Counter
from typing import Any

from app.recommendation.domain.shadow import (
    CandidateSourceSummary,
    FilteredRecommendationCandidate,
    RankedRecommendationCandidate,
    RecommendationCandidateFixture,
    RecommendationHintPacket,
    RecommendationShadowContextFixture,
    RecommendationShadowEvalArtifact,
    RecommendationShadowEvalResult,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.shadow_evaluator"
)


SOURCE_PRIORITY = {
    "historical_preference": 24,
    "context_valid_nearby_fixture": 22,
    "nearby_fixture": 22,
    "golden_order": 26,
    "menu_scan_item": 18,
    "safe_fallback": 12,
    "generic_healthy": 6,
}


def build_recommendation_shadow_eval_artifact(
    scenarios: list[RecommendationShadowContextFixture],
) -> RecommendationShadowEvalArtifact:
    evals = [evaluate_recommendation_shadow_scenario(scenario) for scenario in scenarios]
    return RecommendationShadowEvalArtifact(
        track_status=_track_status(),
        summary=_artifact_summary(evals),
        evals=evals,
    )


def evaluate_recommendation_shadow_scenario(
    scenario: RecommendationShadowContextFixture,
) -> RecommendationShadowEvalResult:
    cold_start_used = _is_cold_start(scenario.preference_profile_summary)
    hard_constraints = _hard_constraints(scenario)
    source_candidates = list(scenario.candidate_source_fixture)
    filtered_candidates: list[FilteredRecommendationCandidate] = []
    allowed_candidates: list[RecommendationCandidateFixture] = []

    for candidate in source_candidates:
        reason_codes = _filter_reason_codes(candidate, scenario)
        if reason_codes:
            filtered_candidates.append(
                FilteredRecommendationCandidate(
                    candidate_id=candidate.candidate_id,
                    title=candidate.title,
                    reason_codes=reason_codes,
                )
            )
            continue
        allowed_candidates.append(candidate)

    soft_preferences = _soft_preferences(scenario, allowed_candidates)
    ranked_candidates, ranking_basis, used_memory, ignored_memory = _rank_candidates(
        scenario, allowed_candidates
    )
    source_summary = _source_summary(allowed_candidates, source_candidates)
    top_pick = ranked_candidates[0] if ranked_candidates else None
    backup_picks = ranked_candidates[1:3]
    hint_packet = _hint_packet(scenario, top_pick, allowed_candidates)
    confidence = _confidence(top_pick)
    risk_if_wrong = _risk_if_wrong(scenario, filtered_candidates)
    freshness_notes = _freshness_notes(scenario)

    return RecommendationShadowEvalResult(
        scenario_id=scenario.scenario_id,
        recommendation_mode=scenario.recommendation_mode,
        input_context_summary=_input_context_summary(scenario),
        candidate_spec=scenario.candidate_spec,
        candidate_source_summary=source_summary,
        candidate_items=allowed_candidates,
        filtered_candidates=filtered_candidates,
        ranked_candidates=ranked_candidates,
        top_pick=top_pick,
        backup_picks=backup_picks,
        ranking_basis=ranking_basis,
        hint_packet=hint_packet,
        memory_candidates_used=used_memory,
        memory_candidates_ignored=ignored_memory,
        hard_constraints=hard_constraints,
        soft_preferences=soft_preferences,
        cold_start_used=cold_start_used,
        coverage_gaps=source_summary.coverage_gaps,
        risk_if_wrong=risk_if_wrong,
        expected_user_value=_expected_user_value(scenario),
        confidence=confidence,
        freshness_notes=freshness_notes,
        presentation_policy=_presentation_policy(scenario),
        mode_notes=_mode_notes(scenario),
    )


def _track_status() -> dict[str, Any]:
    return {
        "track": "RecommendationShadow",
        "slice_id": "recommendation_shadow_evaluator",
        "shadow_mode": True,
        "recommendation_served": False,
        "intake_committed": False,
        "meal_thread_mutated": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
        "live_provider_used": False,
    }


def _artifact_summary(evals: list[RecommendationShadowEvalResult]) -> dict[str, Any]:
    mode_counts = Counter(eval_item.recommendation_mode for eval_item in evals)
    return {
        "scenario_count": len(evals),
        "mode_counts": dict(sorted(mode_counts.items())),
        "runtime_effect_allowed_count": sum(
            1 for eval_item in evals if eval_item.runtime_effect_allowed
        ),
        "recommendation_served_count": sum(
            1 for eval_item in evals if eval_item.recommendation_served
        ),
        "intake_committed_count": sum(
            1 for eval_item in evals if eval_item.intake_committed
        ),
    }


def _is_cold_start(preference_profile_summary: dict[str, Any]) -> bool:
    if not preference_profile_summary:
        return True
    if preference_profile_summary.get("event_count", 0) <= 0:
        return True
    signal_keys = ("top_items", "top_stores", "cuisine_families")
    return all(not preference_profile_summary.get(key) for key in signal_keys)


def _hard_constraints(scenario: RecommendationShadowContextFixture) -> list[str]:
    constraints: list[str] = []
    remaining_kcal = _remaining_kcal(scenario)
    if remaining_kcal is not None:
        constraints.append(f"remaining_budget_kcal:{remaining_kcal}")
    for pattern in _confirmed_negative_patterns(scenario):
        constraints.append(f"confirmed_negative_preference:{pattern}")
    for pattern in scenario.candidate_spec.excluded_item_patterns:
        constraints.append(f"candidate_spec_excluded_pattern:{pattern}")
    if _accepted_rescue_conflicts(scenario):
        constraints.append("accepted_rescue_conflict_check")
    return constraints


def _filter_reason_codes(
    candidate: RecommendationCandidateFixture,
    scenario: RecommendationShadowContextFixture,
) -> list[str]:
    reason_codes: list[str] = []
    remaining_kcal = _remaining_kcal(scenario)
    kcal_max = candidate.estimated_kcal_range.get("max")
    if remaining_kcal is not None and kcal_max is not None and kcal_max > remaining_kcal:
        reason_codes.append("over_budget")

    if _matches_any_pattern(candidate, _confirmed_negative_patterns(scenario)):
        reason_codes.append("confirmed_negative_preference")

    if _matches_any_pattern(candidate, scenario.candidate_spec.excluded_item_patterns):
        reason_codes.append("candidate_spec_excluded_pattern")

    if candidate.hard_avoid_flags:
        reason_codes.extend(sorted(set(candidate.hard_avoid_flags)))

    if _matches_any_pattern(candidate, _accepted_rescue_conflicts(scenario)):
        reason_codes.append("accepted_rescue_conflict")

    return _dedupe(reason_codes)


def _rank_candidates(
    scenario: RecommendationShadowContextFixture,
    candidates: list[RecommendationCandidateFixture],
) -> tuple[list[RankedRecommendationCandidate], dict[str, Any], list[str], list[str]]:
    scored: list[tuple[float, RecommendationCandidateFixture, list[str]]] = []
    used_memory: list[str] = []
    ignored_memory: list[str] = []
    golden_orders = scenario.golden_order_summary.get("orders", [])

    for candidate in candidates:
        score = 50.0
        reasons: list[str] = []

        source_score = SOURCE_PRIORITY.get(candidate.source_type, 0)
        score += source_score
        reasons.append(f"source:{candidate.source_type}")

        target_score = _kcal_target_score(candidate, scenario)
        if target_score:
            score += target_score
            reasons.append("kcal_target_fit")

        if _budget_fits(candidate, scenario):
            score += 8
            reasons.append("budget_fit")

        cuisine_score = _cuisine_score(candidate, scenario)
        if cuisine_score:
            score += cuisine_score
            reasons.append(f"preferred_cuisine:{candidate.cuisine_family}")

        if _is_high_protein(candidate, scenario):
            score += 10
            reasons.append("high_protein")

        golden_order_ref = _matching_golden_order_ref(candidate, golden_orders)
        if golden_order_ref:
            score += 18
            reasons.append("golden_order")
            used_memory.append(golden_order_ref)

        repeat_patterns = _repeat_patterns(candidate, scenario)
        if repeat_patterns:
            score -= 24
            reasons.append("avoid_repeat_from_today")
            ignored_memory.append(candidate.candidate_id)

        score += max(min(candidate.confidence, 1.0), 0.0) * 5
        scored.append((score, candidate, reasons))

    scored.sort(key=lambda item: (-item[0], item[1].title, item[1].candidate_id))
    ranked = [
        RankedRecommendationCandidate(
            candidate_id=candidate.candidate_id,
            title=candidate.title,
            rank=index + 1,
            score=round(score, 2),
            source_type=candidate.source_type,
            estimated_kcal_range=candidate.estimated_kcal_range,
            store_name=candidate.store_name,
            ranking_reasons=reasons,
        )
        for index, (score, candidate, reasons) in enumerate(scored)
    ]

    ranking_basis = {
        "algorithm": "deterministic_shadow_rule_basis",
        "source_priority": SOURCE_PRIORITY,
        "candidate_spec_priority_signals": scenario.candidate_spec.priority_signals,
        "hard_filters_applied_before_ranking": True,
        "llm_ranking_used": False,
    }
    return ranked, ranking_basis, _dedupe(used_memory), _dedupe(ignored_memory)


def _source_summary(
    allowed_candidates: list[RecommendationCandidateFixture],
    source_candidates: list[RecommendationCandidateFixture],
) -> CandidateSourceSummary:
    source_counts = Counter(candidate.source_type for candidate in allowed_candidates)
    coverage_gaps: list[str] = []
    if not source_candidates:
        coverage_gaps.append("no_candidate_source_fixture")
    source_types = {candidate.source_type for candidate in source_candidates}
    if "context_valid_nearby_fixture" not in source_types and "nearby_fixture" not in source_types:
        coverage_gaps.append("location_context_fixture_not_used")
    if not allowed_candidates and source_candidates:
        coverage_gaps.append("all_candidates_filtered")
    return CandidateSourceSummary(
        candidate_count=len(allowed_candidates),
        source_counts=dict(sorted(source_counts.items())),
        coverage_gaps=coverage_gaps,
    )


def _hint_packet(
    scenario: RecommendationShadowContextFixture,
    top_pick: RankedRecommendationCandidate | None,
    candidates: list[RecommendationCandidateFixture],
) -> RecommendationHintPacket | None:
    if top_pick is None:
        return None
    candidate = next(
        item for item in candidates if item.candidate_id == top_pick.candidate_id
    )
    return RecommendationHintPacket(
        candidate_id=candidate.candidate_id,
        title=candidate.title,
        store_metadata={
            "store_name": candidate.store_name,
            **candidate.store_metadata,
        },
        source_type=candidate.source_type,
        estimated_kcal_range=candidate.estimated_kcal_range,
        current_surface_channel=scenario.channel,
        selection_context={
            "scenario_id": scenario.scenario_id,
            "recommendation_mode": scenario.recommendation_mode,
            "runtime_effect_allowed": False,
        },
        ranking_reason_summary=", ".join(top_pick.ranking_reasons[:3]),
        confidence=_confidence(top_pick),
        source_refs=candidate.source_refs,
    )


def _soft_preferences(
    scenario: RecommendationShadowContextFixture,
    candidates: list[RecommendationCandidateFixture],
) -> list[str]:
    preferences: list[str] = []
    acceptable_cuisines = {
        cuisine
        for cuisine in scenario.candidate_spec.acceptable_cuisine_families
        if cuisine != "any"
    }
    for candidate in candidates:
        if candidate.cuisine_family in acceptable_cuisines:
            preferences.append(f"preferred_cuisine:{candidate.cuisine_family}")
        for pattern in _repeat_patterns(candidate, scenario):
            preferences.append(f"avoid_repeat_from_today:{pattern}")
        if _is_high_protein(candidate, scenario):
            preferences.append("high_protein")
    if scenario.app_usage_style_candidate.get("presentation_density") == "concise":
        preferences.append("presentation_density:concise")
    return _dedupe(preferences)


def _remaining_kcal(scenario: RecommendationShadowContextFixture) -> int | None:
    value = scenario.current_budget_view.get("remaining_kcal")
    return value if isinstance(value, int) else None


def _confirmed_negative_patterns(scenario: RecommendationShadowContextFixture) -> list[str]:
    items = scenario.negative_preference_summary.get("items", [])
    patterns: list[str] = []
    for item in items:
        if item.get("status") in {"confirmed_negative_preference", "allergy", "diet_constraint"}:
            pattern = item.get("pattern")
            if pattern:
                patterns.append(str(pattern))
    return patterns


def _accepted_rescue_conflicts(scenario: RecommendationShadowContextFixture) -> list[str]:
    proposals = scenario.open_proposals_view.get("proposals", [])
    conflicts: list[str] = []
    for proposal in proposals:
        if proposal.get("status") != "accepted":
            continue
        conflicts.extend(str(pattern) for pattern in proposal.get("conflict_patterns", []))
    return conflicts


def _matches_any_pattern(
    candidate: RecommendationCandidateFixture, patterns: list[str]
) -> bool:
    candidate_tokens = {
        _normalize_pattern(candidate.title),
        _normalize_pattern(candidate.cuisine_family),
        _normalize_pattern(candidate.item_kind),
        _normalize_pattern(candidate.staple_type or ""),
        *[_normalize_pattern(pattern) for pattern in candidate.item_patterns],
    }
    for pattern in patterns:
        normalized = _normalize_pattern(pattern)
        if not normalized:
            continue
        if normalized in candidate_tokens:
            return True
        if normalized in _normalize_pattern(candidate.title):
            return True
    return False


def _normalize_pattern(value: str) -> str:
    return value.lower().replace(" ", "_").replace("-", "_")


def _kcal_target_score(
    candidate: RecommendationCandidateFixture,
    scenario: RecommendationShadowContextFixture,
) -> float:
    band = scenario.candidate_spec.soft_target_kcal_band
    kcal_min = candidate.estimated_kcal_range.get("min", 0)
    kcal_max = candidate.estimated_kcal_range.get("max", 0)
    target_min = band.get("min", 0)
    target_max = band.get("max", 99999)
    if kcal_max <= 0:
        return 0
    if kcal_min >= target_min and kcal_max <= target_max:
        return 12
    if kcal_min <= target_max and kcal_max >= target_min:
        return 5
    return 0


def _budget_fits(
    candidate: RecommendationCandidateFixture,
    scenario: RecommendationShadowContextFixture,
) -> bool:
    remaining_kcal = _remaining_kcal(scenario)
    kcal_max = candidate.estimated_kcal_range.get("max")
    return remaining_kcal is not None and kcal_max is not None and kcal_max <= remaining_kcal


def _cuisine_score(
    candidate: RecommendationCandidateFixture,
    scenario: RecommendationShadowContextFixture,
) -> float:
    cuisines = scenario.candidate_spec.acceptable_cuisine_families
    if "any" in cuisines or candidate.cuisine_family not in cuisines:
        return 0
    return 8


def _is_high_protein(
    candidate: RecommendationCandidateFixture,
    scenario: RecommendationShadowContextFixture,
) -> bool:
    wants_high_protein = (
        scenario.candidate_spec.protein_posture == "high"
        or "high_protein" in scenario.candidate_spec.priority_signals
    )
    return wants_high_protein and candidate.protein_posture == "high"


def _matching_golden_order_ref(
    candidate: RecommendationCandidateFixture,
    golden_orders: list[dict[str, Any]],
) -> str | None:
    candidate_title = _normalize_pattern(candidate.title)
    candidate_store = _normalize_pattern(candidate.store_name or "")
    for order in golden_orders:
        store_name = str(order.get("store_name", ""))
        item_names = [str(item) for item in order.get("item_names", [])]
        store_matches = candidate_store and candidate_store == _normalize_pattern(store_name)
        item_matches = bool(item_names) and all(
            _normalize_pattern(item) in candidate_title for item in item_names
        )
        if store_matches or item_matches:
            return f"golden_order:{store_name}"
    return None


def _repeat_patterns(
    candidate: RecommendationCandidateFixture,
    scenario: RecommendationShadowContextFixture,
) -> list[str]:
    if not scenario.candidate_spec.avoid_repeat_from_today:
        return []
    repeated: list[str] = []
    for meal in scenario.recent_committed_meals_view.get("meals", []):
        repeated.extend(
            pattern
            for pattern in meal.get("item_patterns", [])
            if _normalize_pattern(pattern)
            in {_normalize_pattern(value) for value in candidate.item_patterns}
        )
        cuisine = meal.get("cuisine_family")
        if cuisine and _normalize_pattern(cuisine) == _normalize_pattern(candidate.cuisine_family):
            repeated.append(str(cuisine))
    return _dedupe(repeated)


def _input_context_summary(scenario: RecommendationShadowContextFixture) -> dict[str, Any]:
    return {
        "user_id": scenario.user_id,
        "local_date": scenario.local_date,
        "channel": scenario.channel,
        "recommendation_mode": scenario.recommendation_mode,
        "timezone": scenario.timezone,
        "remaining_kcal": scenario.current_budget_view.get("remaining_kcal"),
        "body_plan_status": scenario.active_body_plan_view.get("plan_status"),
        "recent_meal_count": len(scenario.recent_committed_meals_view.get("meals", [])),
        "open_proposal_count": len(scenario.open_proposals_view.get("proposals", [])),
        "preference_event_count": scenario.preference_profile_summary.get("event_count", 0),
    }


def _risk_if_wrong(
    scenario: RecommendationShadowContextFixture,
    filtered_candidates: list[FilteredRecommendationCandidate],
) -> str:
    if scenario.candidate_spec.budget_fit_posture == "tight":
        return "medium"
    if any("over_budget" in item.reason_codes for item in filtered_candidates):
        return "medium"
    if _confirmed_negative_patterns(scenario):
        return "medium"
    return "low"


def _expected_user_value(scenario: RecommendationShadowContextFixture) -> str:
    if scenario.recommendation_mode == "swap_suggestion":
        return "informational_swap_option_without_proposal"
    if scenario.recommendation_mode == "menu_scan":
        return "pre_intake_menu_choice_signal"
    return "shadow_candidate_quality_signal"


def _mode_notes(scenario: RecommendationShadowContextFixture) -> list[str]:
    if scenario.recommendation_mode == "menu_scan":
        return [
            "menu_scan_fixture_only",
            "parsed_menu_items_are_candidate_sources_not_intake_truth",
        ]
    if scenario.recommendation_mode == "swap_suggestion":
        return [
            "swap_suggestion_fixture_only",
            "informational_only_no_proposal_state",
        ]
    if scenario.recommendation_mode == "pre_meal_planning":
        return [
            "pre_meal_planning_fixture_only",
            "informational_only_no_budget_overlay",
        ]
    return []


def _freshness_notes(scenario: RecommendationShadowContextFixture) -> list[str]:
    notes: list[str] = []
    freshness = scenario.preference_profile_summary.get("freshness_posture")
    if freshness:
        notes.append(f"preference_profile:{freshness}")
    if _is_cold_start(scenario.preference_profile_summary):
        notes.append("preference_profile:cold_start_or_sparse")
    return notes


def _presentation_policy(scenario: RecommendationShadowContextFixture) -> str:
    if scenario.app_usage_style_candidate.get("presentation_density") == "concise":
        return "concise"
    return "standard"


def _confidence(top_pick: RankedRecommendationCandidate | None) -> float:
    if top_pick is None:
        return 0.0
    return round(min(max(top_pick.score / 120.0, 0.0), 0.95), 2)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_shadow_eval_artifact",
    "evaluate_recommendation_shadow_scenario",
]
