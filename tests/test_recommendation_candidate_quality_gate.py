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


def test_unavailable_candidate_is_rejected_before_any_proactive_use() -> None:
    result = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c6",
            title="Known chicken bento",
            estimated_kcal=520,
            remaining_budget_kcal=700,
            evidence_posture="anchored",
            availability_posture="unavailable",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )

    assert result.passed is False
    assert result.proactive_intensity == "none"
    assert "unavailable" in result.disqualifier_flags


def test_missing_or_range_over_budget_candidate_is_rejected() -> None:
    missing_kcal = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c7",
            title="Specific but unestimated meal",
            remaining_budget_kcal=700,
            evidence_posture="anchored",
            availability_posture="available",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )
    range_over_budget = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c8",
            title="Narrow menu estimate",
            kcal_range_min=580,
            kcal_range_max=760,
            remaining_budget_kcal=700,
            evidence_posture="anchored",
            availability_posture="available",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )

    assert missing_kcal.passed is False
    assert "missing_kcal_estimate" in missing_kcal.disqualifier_flags
    assert range_over_budget.passed is False
    assert "budget_mismatch" in range_over_budget.disqualifier_flags


def test_non_positive_kcal_candidate_is_rejected() -> None:
    result = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c9",
            title="Impossible zero kcal dinner",
            estimated_kcal=0,
            remaining_budget_kcal=700,
            evidence_posture="anchored",
            availability_posture="available",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )

    assert result.passed is False
    assert result.proactive_intensity == "none"
    assert "invalid_kcal_estimate" in result.disqualifier_flags


def test_invalid_identity_or_kcal_range_candidate_is_rejected() -> None:
    blank_identity = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="",
            title="Specific but unaddressable meal",
            estimated_kcal=520,
            remaining_budget_kcal=700,
            evidence_posture="anchored",
            availability_posture="available",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )
    inverted_range = evaluate_recommendation_candidate_quality(
        RecommendationCandidateQualityInput(
            candidate_id="c10",
            title="Inverted range meal",
            kcal_range_min=760,
            kcal_range_max=580,
            remaining_budget_kcal=700,
            evidence_posture="anchored",
            availability_posture="available",
            realistic_executable=True,
            violates_negative_preference=False,
            user_accessible=True,
        )
    )

    assert blank_identity.passed is False
    assert blank_identity.proactive_intensity == "none"
    assert "missing_candidate_id" in blank_identity.disqualifier_flags
    assert inverted_range.passed is False
    assert inverted_range.proactive_intensity == "none"
    assert "invalid_kcal_range" in inverted_range.disqualifier_flags
