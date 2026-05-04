from __future__ import annotations

from collections import Counter

from app.recommendation.application.shadow_artifact_gate import (
    evaluate_recommendation_shadow_artifact_quality,
)
from app.recommendation.domain.shadow import (
    RecommendationShadowArtifactGateResult,
    RecommendationShadowEvalArtifact,
    RecommendationShadowEvalResult,
    RecommendationShadowScorecard,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.shadow_scorecard"
)


def build_recommendation_shadow_scorecard(
    artifact: RecommendationShadowEvalArtifact,
    gate_result: RecommendationShadowArtifactGateResult | None = None,
) -> RecommendationShadowScorecard:
    if gate_result is None:
        gate_result = evaluate_recommendation_shadow_artifact_quality(artifact)
    scenario_scorecards = [_scenario_scorecard(eval_item) for eval_item in artifact.evals]
    return RecommendationShadowScorecard(
        gate_passed=gate_result.passed,
        issue_codes=gate_result.failure_codes,
        summary=_summary(artifact, scenario_scorecards, gate_result),
        scenario_scorecards=scenario_scorecards,
    )


def _summary(
    artifact: RecommendationShadowEvalArtifact,
    scenario_scorecards: list[dict],
    gate_result: RecommendationShadowArtifactGateResult,
) -> dict:
    source_counts: Counter[str] = Counter()
    filtered_reason_counts: Counter[str] = Counter()
    for scenario in scenario_scorecards:
        source_counts.update(scenario["source_counts"])
        filtered_reason_counts.update(scenario["filtered_reason_counts"])
    return {
        "scenario_count": len(artifact.evals),
        "mode_counts": dict(
            sorted(Counter(eval_item.recommendation_mode for eval_item in artifact.evals).items())
        ),
        "source_counts": dict(sorted(source_counts.items())),
        "filtered_reason_counts": dict(sorted(filtered_reason_counts.items())),
        "runtime_effect_allowed_count": sum(
            1 for eval_item in artifact.evals if eval_item.runtime_effect_allowed
        ),
        "recommendation_served_count": sum(
            1 for eval_item in artifact.evals if eval_item.recommendation_served
        ),
        "intake_committed_count": sum(
            1 for eval_item in artifact.evals if eval_item.intake_committed
        ),
        "canonical_hint_packet_count": sum(
            1
            for eval_item in artifact.evals
            if eval_item.hint_packet is not None and eval_item.hint_packet.is_canonical_truth
        ),
        "failure_count": len(gate_result.failure_codes),
        "warning_count": len(gate_result.warning_codes),
        "scenario_ids": [eval_item.scenario_id for eval_item in artifact.evals],
    }


def _scenario_scorecard(eval_item: RecommendationShadowEvalResult) -> dict:
    return {
        "scenario_id": eval_item.scenario_id,
        "recommendation_mode": eval_item.recommendation_mode,
        "candidate_count": len(eval_item.candidate_items),
        "filtered_count": len(eval_item.filtered_candidates),
        "ranked_count": len(eval_item.ranked_candidates),
        "source_counts": eval_item.candidate_source_summary.source_counts,
        "filtered_reason_counts": _filtered_reason_counts(eval_item),
        "top_pick_candidate_id": (
            eval_item.top_pick.candidate_id if eval_item.top_pick else None
        ),
        "top_pick_title": eval_item.top_pick.title if eval_item.top_pick else None,
        "backup_pick_candidate_ids": [
            candidate.candidate_id for candidate in eval_item.backup_picks
        ],
        "hint_packet_present": eval_item.hint_packet is not None,
        "hint_packet_canonical": (
            eval_item.hint_packet.is_canonical_truth
            if eval_item.hint_packet is not None
            else None
        ),
        "cold_start_used": eval_item.cold_start_used,
        "coverage_gaps": eval_item.coverage_gaps,
        "memory_candidates_used": eval_item.memory_candidates_used,
        "memory_candidates_ignored": eval_item.memory_candidates_ignored,
        "hard_constraints": eval_item.hard_constraints,
        "soft_preferences": eval_item.soft_preferences,
        "risk_if_wrong": eval_item.risk_if_wrong,
        "expected_user_value": eval_item.expected_user_value,
        "confidence": eval_item.confidence,
        "presentation_policy": eval_item.presentation_policy,
        "mode_notes": eval_item.mode_notes,
        "runtime_effect_allowed": eval_item.runtime_effect_allowed,
        "recommendation_served": eval_item.recommendation_served,
        "intake_committed": eval_item.intake_committed,
    }


def _filtered_reason_counts(eval_item: RecommendationShadowEvalResult) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for candidate in eval_item.filtered_candidates:
        counts.update(candidate.reason_codes)
    return dict(sorted(counts.items()))


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_shadow_scorecard",
]
