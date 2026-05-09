from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.recommendation.application.candidate_quality_gate import (
    evaluate_recommendation_candidate_quality,
)
from app.recommendation.domain.candidate_quality import RecommendationCandidateQualityInput


_REQUIRED_CASE_IDS = (
    "high_quality_prepared_candidate_activation_candidate",
    "uncertain_valid_candidate_offer_only",
    "generic_or_missing_candidate_silent",
    "negative_or_over_budget_candidate_silent",
    "live_search_and_ranking_blocked",
)
_FALSE_FIELDS = (
    "runtime_connected",
    "recommendation_served",
    "proactive_sent",
    "live_search_used",
    "ranking_llm_invoked",
    "intake_handoff_created",
    "mutation_changed",
    "day_budget_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
)


def _quality(candidate: RecommendationCandidateQualityInput) -> dict[str, Any]:
    result = evaluate_recommendation_candidate_quality(candidate)
    return {
        "candidate_id": result.candidate_id,
        "quality_gate_passed": result.passed,
        "quality_tier": result.quality_tier,
        "proactive_intensity": result.proactive_intensity,
        "disqualifier_flags": list(result.disqualifier_flags),
        "quality_signals": list(result.quality_signals),
    }


def _candidate(
    candidate_id: str,
    title: str,
    *,
    estimated_kcal: int | None = 520,
    remaining_budget_kcal: int = 700,
    evidence_posture: str = "anchored",
    availability_posture: str = "available",
    realistic_executable: bool = True,
    violates_negative_preference: bool = False,
    user_accessible: bool = True,
) -> RecommendationCandidateQualityInput:
    return RecommendationCandidateQualityInput(
        candidate_id=candidate_id,
        title=title,
        estimated_kcal=estimated_kcal,
        remaining_budget_kcal=remaining_budget_kcal,
        evidence_posture=evidence_posture,  # type: ignore[arg-type]
        availability_posture=availability_posture,  # type: ignore[arg-type]
        realistic_executable=realistic_executable,
        violates_negative_preference=violates_negative_preference,
        user_accessible=user_accessible,
    )


def _base_case(case_id: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "semantic_owner": "recommendation_candidate_quality_gate",
        "deterministic_role": "classify_prepared_candidate_quality_without_serving",
        "candidate_generation_stage": "prepared_candidate_only",
        "serving_stage": "not_connected",
        **dict.fromkeys(_FALSE_FIELDS, False),
    }


def _quality_case(
    case_id: str,
    candidate: RecommendationCandidateQualityInput,
    *,
    presentation_posture: str,
    secondary: RecommendationCandidateQualityInput | None = None,
) -> dict[str, Any]:
    primary_quality = _quality(candidate)
    secondary_quality = _quality(secondary) if secondary is not None else {}
    return _base_case(case_id) | primary_quality | {
        "presentation_posture": presentation_posture,
        "secondary_disqualifier_flags": secondary_quality.get("disqualifier_flags", []),
    }


def _cases() -> list[dict[str, Any]]:
    return [
        _quality_case(
            "high_quality_prepared_candidate_activation_candidate",
            _candidate("high-1", "Chicken bento with half rice", evidence_posture="exact"),
            presentation_posture="activation_candidate",
        ),
        _quality_case(
            "uncertain_valid_candidate_offer_only",
            _candidate("offer-1", "Convenience store salad chicken combo", availability_posture="unknown"),
            presentation_posture="low_friction_offer_only",
        ),
        _quality_case(
            "generic_or_missing_candidate_silent",
            _candidate("generic-1", "Something light", evidence_posture="generic"),
            presentation_posture="silent",
            secondary=_candidate("missing-1", "Specific but unestimated meal", estimated_kcal=None),
        ),
        _quality_case(
            "negative_or_over_budget_candidate_silent",
            _candidate("negative-1", "Fried tofu snack", violates_negative_preference=True),
            presentation_posture="silent",
            secondary=_candidate("over-1", "Large pork cutlet rice", estimated_kcal=980, remaining_budget_kcal=600),
        ),
        _base_case("live_search_and_ranking_blocked")
        | {
            "presentation_posture": "not_applicable",
            "quality_gate_passed": False,
            "quality_tier": "not_evaluated",
            "proactive_intensity": "none",
        },
    ]


def _validate_cases(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if [str(case.get("case_id") or "") for case in cases] != list(_REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")
    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        for field in _FALSE_FIELDS:
            if case.get(field) is not False:
                blockers.append(f"{case_id}.{field}")
    return blockers


def build_recommendation_offer_silent_shadow_contract_artifact() -> dict[str, Any]:
    cases = _cases()
    blockers = _validate_cases(cases)
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_recommendation_offer_silent_shadow_contract",
        "status": "pass" if not blockers else "fail",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "owner": "app/recommendation",
        "consumer": "future recommendation/proactive activation slices",
        "retirement_trigger": "approved recommendation_runtime_activation_plan",
        "local_only": True,
        "diagnostic_only": True,
        "shadow_only": True,
        **dict.fromkeys(_FALSE_FIELDS, False),
        "best_practice_evidence": {
            "required": True,
            "sources_checked": [
                "https://developers.google.com/machine-learning/recommendation/overview/types",
            ],
            "adopted_guidance": [
                "separate candidate generation, scoring, and re-ranking",
                "apply additional constraints before final serving",
            ],
        },
        "blockers": blockers,
        "cases": cases,
    }


__all__ = ["build_recommendation_offer_silent_shadow_contract_artifact"]
