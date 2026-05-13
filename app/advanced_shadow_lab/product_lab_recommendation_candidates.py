from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_action_projection import (
    memory_action_projection_from_context,
    recommendation_memory_blocker_reasons,
)
from app.advanced_shadow_lab.product_lab_premeal_planning import (
    premeal_candidate_filter_reason,
)
from app.advanced_shadow_lab.product_lab_recommendation_candidate_quality import (
    hard_rejected_review,
    omission_traces,
    pool_decision,
    quality_signal,
    reviewed_candidate,
    sort_key,
)
from app.advanced_shadow_lab.product_lab_recommendation_allowed_pool_trace import (
    build_allowed_pool_trace,
)
from app.recommendation.application.candidate_source_port import (
    normalize_recommendation_candidate_sources,
)
from app.advanced_shadow_lab.product_lab_recommendation_guard_boundaries import (
    candidate_guard_boundary_result,
)


def build_candidate_retrieval_guard_scoring(
    *,
    planning: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _mapping(fixture_inputs.get("recommendation_payload"))
    candidate_source_port = normalize_recommendation_candidate_sources(
        payload=payload,
        memory_context_pack=memory_context_pack,
    )
    source_candidates = [
        dict(candidate)
        for candidate in candidate_source_port.get("candidate_sources") or []
        if isinstance(candidate, Mapping)
    ]
    qualified: list[dict[str, Any]] = []
    filtered: list[dict[str, Any]] = []
    quality_rejected: list[dict[str, Any]] = []
    candidate_reviews: list[dict[str, Any]] = []
    hard_blocker_trace: list[dict[str, Any]] = []
    soft_penalty_trace: list[dict[str, Any]] = []
    memory_action_projection = memory_action_projection_from_context(memory_context_pack)
    memory_negative_ids = [
        str(item) for item in memory_context_pack.get("negative_preference_blockers") or []
    ]
    premeal = _mapping(_mapping(planning.get("candidate_spec")).get("pre_meal_planning"))
    swap = _mapping(_mapping(planning.get("candidate_spec")).get("swap_suggestion"))
    for candidate in source_candidates:
        reasons = premeal_candidate_filter_reason(candidate, premeal)
        boundary = candidate_guard_boundary_result(
            candidate,
            payload,
            memory_negative_ids=memory_negative_ids,
        )
        hard_blocker_trace.extend(boundary["hard_blocker_trace"])
        soft_penalty_trace.extend(boundary["soft_penalty_trace"])
        reasons.extend(boundary["hard_reason_codes"])
        reasons.extend(
            recommendation_memory_blocker_reasons(candidate, memory_action_projection)
        )
        reasons = list(dict.fromkeys(reasons))
        if reasons:
            filtered.append(
                {
                    "candidate_id": str(candidate.get("candidate_id") or ""),
                    "reason_codes": reasons,
                }
            )
            candidate_reviews.append(hard_rejected_review(candidate, reasons))
            continue
        reviewed_input = {
            **candidate,
            "soft_penalty_codes": list(boundary["soft_penalty_codes"]),
            "quality_score_adjustment": boundary["quality_score_adjustment"],
        }
        scored, review, quality = reviewed_candidate(reviewed_input, payload)
        candidate_reviews.append(review)
        if not quality.passed:
            quality_rejected.append(
                {
                    "candidate_id": str(candidate.get("candidate_id") or ""),
                    "reason_codes": list(quality.disqualifier_flags),
                }
            )
            continue
        qualified.append(
            {
                **scored,
                "quality_tier": quality.quality_tier,
                "proactive_intensity": quality.proactive_intensity,
                "quality_signals": list(quality.quality_signals),
            }
        )
    qualified.sort(key=sort_key)
    pool = pool_decision(qualified)
    scoring_trace = _scoring_trace(qualified)
    return {
        "node": "candidate_retrieval_guard_scoring",
        "owner": "deterministic",
        "deterministic_guard_only": True,
        "llm_semantic_authority": False,
        "candidate_source_port_used": True,
        "candidate_source_port_status": str(candidate_source_port.get("status") or ""),
        "candidate_source_port_artifact": candidate_source_port,
        "hard_blocker_families": ["premeal_constraint", "budget", "negative_preference", "rescue_conflict", "availability", "memory_action"],
        "source_candidate_ids": [
            str(candidate.get("candidate_id") or "") for candidate in source_candidates
        ],
        "allowed_candidate_ids": [
            str(candidate.get("candidate_id") or "") for candidate in qualified
        ],
        "allowed_candidates": qualified,
        "qualified_candidate_ids": [
            str(candidate.get("candidate_id") or "") for candidate in qualified
        ],
        "qualified_candidates": qualified,
        "quality_rejected_candidate_ids": [
            str(candidate.get("candidate_id") or "") for candidate in quality_rejected
        ],
        "quality_rejected_candidates": quality_rejected,
        "filtered_candidates": filtered,
        "candidate_reviews": candidate_reviews,
        "quality_signals": [quality_signal(candidate) for candidate in qualified],
        "scoring_trace": scoring_trace,
        "allowed_pool_trace": build_allowed_pool_trace(
            allowed_candidates=qualified,
            filtered_candidates=filtered,
            quality_rejected_candidates=quality_rejected,
            candidate_reviews=candidate_reviews,
            scoring_trace=scoring_trace,
        ),
        "hard_blocker_trace": hard_blocker_trace,
        "soft_penalty_trace": soft_penalty_trace,
        "pool_decision": pool["pool_decision"],
        "primary_candidate_id": pool["primary_candidate_id"],
        "backup_candidate_ids": pool["backup_candidate_ids"],
        "offer_candidate_ids": pool["offer_candidate_ids"],
        "budget_posture": dict(_mapping(_mapping(planning.get("candidate_spec")).get("budget_posture"))),
        "pre_meal_planning_context": dict(premeal),
        "swap_suggestion_context": dict(swap),
        "omission_traces": [
            *omission_traces(quality_rejected),
            *_memory_action_omission_traces(filtered),
        ],
        "memory_action_projection": memory_action_projection,
        "memory_action_omission_traces": _memory_action_omission_traces(filtered),
        "candidate_spec_obeyed": bool(planning.get("candidate_spec")),
        "may_mutate_canonical_state": False,
        "canonical_product_mutation_allowed": False,
        "blockers": [str(item) for item in candidate_source_port.get("blockers") or []],
    }


def _memory_action_omission_traces(
    filtered: list[Mapping[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "candidate_id": str(item.get("candidate_id") or ""),
            "omission_reason": str(reason),
            "source_node": "candidate_retrieval_guard_scoring",
        }
        for item in filtered
        for reason in item.get("reason_codes") or []
        if str(reason).startswith("memory_")
    ]


def _scoring_trace(candidates: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": str(candidate.get("candidate_id") or ""),
            "source_node": "candidate_retrieval_guard_scoring",
            "score_owner": "deterministic",
            "quality_score": int(candidate.get("quality_score") or 0),
            "quality_tier": str(candidate.get("quality_tier") or ""),
        }
        for candidate in candidates
    ]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_candidate_retrieval_guard_scoring"]
