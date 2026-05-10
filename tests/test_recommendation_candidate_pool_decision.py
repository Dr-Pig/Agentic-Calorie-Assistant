from __future__ import annotations

from app.recommendation.domain.candidate_quality import (
    RecommendationCandidateQualityInput,
)


def _candidate(
    candidate_id: str,
    *,
    title: str | None = None,
    estimated_kcal: int | None = 520,
    remaining_budget_kcal: int = 700,
    evidence_posture: str = "anchored",
    availability_posture: str = "available",
) -> RecommendationCandidateQualityInput:
    return RecommendationCandidateQualityInput(
        candidate_id=candidate_id,
        title=title or f"{candidate_id} prepared meal",
        estimated_kcal=estimated_kcal,
        remaining_budget_kcal=remaining_budget_kcal,
        evidence_posture=evidence_posture,  # type: ignore[arg-type]
        availability_posture=availability_posture,  # type: ignore[arg-type]
        realistic_executable=True,
        user_accessible=True,
    )


def test_pool_decision_returns_primary_plus_backup_only_when_backup_exists() -> None:
    from app.recommendation.application.candidate_quality_gate import (
        decide_recommendation_candidate_pool,
    )

    result = decide_recommendation_candidate_pool(
        [
            _candidate("high-1", availability_posture="available"),
            _candidate("backup-1", availability_posture="unknown"),
            _candidate("rejected-1", evidence_posture="generic"),
        ]
    )

    assert result.pool_decision == "primary_plus_backup"
    assert result.primary_candidate_id == "high-1"
    assert result.backup_candidate_ids == ["backup-1"]
    assert result.offer_candidate_ids == []
    assert result.rejected_candidate_ids == ["rejected-1"]


def test_pool_decision_uses_offer_when_candidates_pass_without_backup_posture() -> None:
    from app.recommendation.application.candidate_quality_gate import (
        decide_recommendation_candidate_pool,
    )

    result = decide_recommendation_candidate_pool(
        [
            _candidate("offer-1", availability_posture="unknown"),
            _candidate("offer-2", availability_posture="unknown"),
        ]
    )

    assert result.pool_decision == "offer"
    assert result.primary_candidate_id is None
    assert result.backup_candidate_ids == []
    assert result.offer_candidate_ids == ["offer-1", "offer-2"]


def test_pool_decision_stays_silent_when_no_candidate_qualifies() -> None:
    from app.recommendation.application.candidate_quality_gate import (
        decide_recommendation_candidate_pool,
    )

    result = decide_recommendation_candidate_pool(
        [
            _candidate("generic-1", evidence_posture="generic"),
            _candidate("over-1", estimated_kcal=980, remaining_budget_kcal=600),
        ]
    )

    assert result.pool_decision == "silent_no_qualified_candidate"
    assert result.primary_candidate_id is None
    assert result.backup_candidate_ids == []
    assert result.offer_candidate_ids == []
    assert result.rejected_candidate_ids == ["generic-1", "over-1"]


def test_pool_decision_has_no_runtime_or_serving_effects() -> None:
    from app.recommendation.application.candidate_quality_gate import (
        decide_recommendation_candidate_pool,
    )

    result = decide_recommendation_candidate_pool([_candidate("high-only")])

    assert result.pool_decision == "offer"
    assert result.runtime_effect_allowed is False
    assert result.recommendation_served is False
    assert result.intake_hint_packet_created is False
    assert result.manager_context_injected is False
    assert result.proactive_sent is False
    assert result.mutation_changed is False
    assert result.meal_thread_mutated is False
    assert result.day_budget_mutated is False
    assert result.body_plan_mutated is False
    assert result.live_search_used is False
    assert result.ranking_llm_invoked is False
    assert result.user_facing_behavior_changed is False


def test_pool_decision_does_not_repeat_primary_candidate_as_backup() -> None:
    from app.recommendation.application.candidate_quality_gate import (
        decide_recommendation_candidate_pool,
    )

    result = decide_recommendation_candidate_pool(
        [
            _candidate("primary-1", availability_posture="available"),
            _candidate("primary-1", availability_posture="available"),
            _candidate("backup-1", availability_posture="unknown"),
        ]
    )

    assert result.pool_decision == "primary_plus_backup"
    assert result.primary_candidate_id == "primary-1"
    assert result.backup_candidate_ids == ["backup-1"]
    assert result.offer_candidate_ids == []
