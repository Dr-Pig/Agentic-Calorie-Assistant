from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.lab_product_shadow_inputs import (
    reviewed_consumer_shadow_input,
    reviewed_lab_memory_triggers,
    reviewed_lab_rescue_packets,
)
from app.memory.application.long_term_context_shadow.memory_action_artifacts import (
    _memory_promotion_demotion_shadow_artifact,
    _memory_review_action_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.semantic_pattern_artifacts import (
    _semantic_pattern_extraction_shadow_artifact,
)
from app.memory.application.long_term_context_shadow.utils import (
    _list_of_dicts,
    _token_estimate,
    _trigger_type,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _proactive_no_send_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    reviewed = reviewed_consumer_shadow_input(fixture, candidates, "proactive_context")
    triggers = [
        {
            "trigger_id": f"trigger-{candidate.candidate_id}",
            "source_candidate_id": candidate.candidate_id,
            "trigger_type": _trigger_type(candidate),
            "reason": candidate.proposed_memory_text,
            "review_status": "pending",
            "human_review_required": True,
            "runtime_effect_allowed": False,
        }
        for candidate in candidates
        if candidate.candidate_type
        in {"pattern", "preference", "food_preference", "golden_order"}
    ]
    return _base_artifact(
        artifact_type="proactive_no_send_simulation",
        fixture=fixture,
        extra={
            "scheduler_activated": False,
            "channel_send_attempted": False,
            "would_inject_context": False,
            "injection_position": "not_applicable_shadow",
            "token_estimate": _token_estimate(
                " ".join(str(trigger.get("reason") or "") for trigger in triggers)
            ),
            "candidate_triggers": triggers,
            "reviewed_lab_view_status": reviewed["reviewed_lab_view_status"],
            "reviewed_lab_context_source_artifact": reviewed[
                "reviewed_lab_context_source_artifact"
            ],
            "reviewed_lab_record_ids": reviewed["reviewed_lab_record_ids"],
            "reviewed_lab_record_summaries": reviewed[
                "reviewed_lab_record_summaries"
            ],
            "reviewed_lab_memory_triggers": reviewed_lab_memory_triggers(reviewed),
        },
    )


def _recommendation_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    pool = _list_of_dicts(fixture.get("candidate_pool"))
    context_candidates = _recommendation_context_candidates(candidates)
    reviewed = reviewed_consumer_shadow_input(fixture, candidates, "recommendation")
    evaluations = [
        _recommendation_candidate_evaluation(
            item,
            index,
            context_candidates,
            reviewed["reviewed_lab_record_ids"],
        )
        for index, item in enumerate(pool or [{"candidate_id": "fixture-empty-pool"}])
    ]
    return _base_artifact(
        artifact_type="recommendation_shadow_eval",
        fixture=fixture,
        extra={
            "live_search_used": False,
            "intake_commit_requested": False,
            "used_context_candidate_ids": [
                candidate.candidate_id for candidate in context_candidates
            ],
            "reviewed_lab_view_status": reviewed["reviewed_lab_view_status"],
            "reviewed_lab_context_source_artifact": reviewed[
                "reviewed_lab_context_source_artifact"
            ],
            "used_reviewed_lab_record_ids": reviewed["reviewed_lab_record_ids"],
            "reviewed_lab_record_summaries": reviewed[
                "reviewed_lab_record_summaries"
            ],
            "candidate_evaluations": evaluations,
        },
    )


def _recommendation_context_candidates(
    candidates: list[LongTermContextCandidate],
) -> list[LongTermContextCandidate]:
    return [
        candidate
        for candidate in candidates
        if candidate.candidate_type
        in {
            "food_preference",
            "golden_order",
            "negative_preference",
            "temporary_preference",
        }
    ]


def _recommendation_candidate_evaluation(
    item: dict[str, Any],
    index: int,
    context_candidates: list[LongTermContextCandidate],
    reviewed_lab_record_ids: list[str],
) -> dict[str, Any]:
    positive = [
        candidate.candidate_id
        for candidate in context_candidates
        if candidate.candidate_type in {"food_preference", "golden_order"}
        and _context_candidate_matches_item(candidate, item)
    ]
    negative = [
        candidate.candidate_id
        for candidate in context_candidates
        if candidate.candidate_type == "negative_preference"
        and _context_candidate_matches_item(candidate, item)
    ]
    temporary = [
        candidate.candidate_id
        for candidate in context_candidates
        if candidate.candidate_type == "temporary_preference"
    ]
    score = max(0, 100 - index * 5 + len(positive) * 25 - len(negative) * 70)
    return {
        "evaluation_id": f"recommendation-shadow-{item.get('candidate_id', index + 1)}",
        "candidate": item,
        "used_context_candidate_ids": [
            candidate.candidate_id for candidate in context_candidates
        ],
        "used_reviewed_lab_record_ids": reviewed_lab_record_ids,
        "review_only_rank_signal": index + 1,
        "review_only_score": score,
        "positive_context_matches": positive,
        "negative_context_matches": negative,
        "temporary_context_notes": temporary,
        "blocked_by_negative_preference": bool(negative),
        "ranking_basis": _recommendation_ranking_basis(positive, negative, temporary),
        "review_status": "pending",
        "human_review_required": True,
        "runtime_effect_allowed": False,
    }


def _context_candidate_matches_item(
    candidate: LongTermContextCandidate,
    item: dict[str, Any],
) -> bool:
    name = str(item.get("name") or "").lower()
    if candidate.candidate_type == "golden_order":
        return any(
            str(value).lower() in name
            for value in candidate.payload.get("item_names") or []
        )
    value = str(candidate.payload.get("value") or "").lower()
    return bool(value and value in name)


def _recommendation_ranking_basis(
    positive: list[str],
    negative: list[str],
    temporary: list[str],
) -> list[str]:
    basis = ["base_fixture_candidate_order"]
    if positive:
        basis.append("positive_preference_or_golden_order_match")
    if negative:
        basis.append("negative_preference_match")
    if temporary:
        basis.append("temporary_preference_context_available")
    return basis


def _rescue_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    reviewed = reviewed_consumer_shadow_input(fixture, candidates, "rescue_context")
    rescue_relevant = [
        candidate
        for candidate in candidates
        if any(
            "overshoot" in reason or "calibration" in reason
            for reason in candidate.reason_codes
        )
    ]
    packets = [
        {
            "packet_id": f"rescue-shadow-{candidate.candidate_id}",
            "source_candidate_id": candidate.candidate_id,
            "reason": candidate.proposed_memory_text,
            "review_status": "pending",
            "human_review_required": True,
            "runtime_effect_allowed": False,
        }
        for candidate in rescue_relevant
    ]
    return _base_artifact(
        artifact_type="rescue_shadow_candidates",
        fixture=fixture,
        extra={
            "budget_mutation_requested": False,
            "proposal_acceptance_side_effect": False,
            "candidate_packets": packets,
            "reviewed_lab_view_status": reviewed["reviewed_lab_view_status"],
            "reviewed_lab_context_source_artifact": reviewed[
                "reviewed_lab_context_source_artifact"
            ],
            "reviewed_lab_record_ids": reviewed["reviewed_lab_record_ids"],
            "reviewed_lab_record_summaries": reviewed[
                "reviewed_lab_record_summaries"
            ],
            "reviewed_lab_candidate_packets": reviewed_lab_rescue_packets(reviewed),
        },
    )


__all__ = [
    "_memory_promotion_demotion_shadow_artifact",
    "_memory_review_action_shadow_artifact",
    "_proactive_no_send_artifact",
    "_recommendation_shadow_artifact",
    "_rescue_shadow_artifact",
    "_semantic_pattern_extraction_shadow_artifact",
]
