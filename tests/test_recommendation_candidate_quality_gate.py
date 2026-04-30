from app.recommendation.application.candidate_quality_gate import (
    evaluate_recommendation_candidate_quality,
)
from app.recommendation.domain.candidate_quality import RecommendationCandidateQualityInput


def test_high_quality_prepared_candidate_can_be_proactive() -> None:
    result = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c1",
            title="Chicken bento with half rice",
            estimated_kcal=620,
            remaining_budget_kcal=750,
            evidence_posture="anchored",
            availability_posture="available",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )

    assert result.passed is True
    assert result.quality_tier == "high"
    assert result.proactive_intensity == "primary_plus_backup"
    assert result.disqualifier_flags == []


def test_negative_preference_rejects_candidate_even_if_budget_fits() -> None:
    result = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c2",
            title="Fried tofu snack",
            estimated_kcal=450,
            remaining_budget_kcal=800,
            evidence_posture="exact",
            availability_posture="available",
            realistic_executable=True,
            violates_negative_preference=True,
            user_accessible=True,
        )
    )

    assert result.passed is False
    assert result.quality_tier == "rejected"
    assert "negative_preference" in result.disqualifier_flags


def test_generic_or_over_budget_candidate_is_not_proactive() -> None:
    generic_result = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c3",
            title="Something light",
            estimated_kcal=350,
            remaining_budget_kcal=700,
            evidence_posture="generic",
            availability_posture="likely",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )
    over_budget_result = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c4",
            title="Large pork cutlet rice",
            estimated_kcal=980,
            remaining_budget_kcal=600,
            evidence_posture="anchored",
            availability_posture="available",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )

    assert generic_result.passed is False
    assert generic_result.proactive_intensity == "none"
    assert "generic_evidence_not_proactive" in generic_result.disqualifier_flags
    assert over_budget_result.passed is False
    assert "budget_mismatch" in over_budget_result.disqualifier_flags


def test_uncertain_but_valid_candidate_is_offer_only() -> None:
    result = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c5",
            title="Convenience store salad chicken combo",
            estimated_kcal=520,
            remaining_budget_kcal=700,
            evidence_posture="anchored",
            availability_posture="unknown",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )

    assert result.passed is True
    assert result.quality_tier == "medium"
    assert result.proactive_intensity == "offer"
