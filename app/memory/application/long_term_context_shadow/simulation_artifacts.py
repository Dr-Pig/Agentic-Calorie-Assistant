from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
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
        },
    )


def _recommendation_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    pool = _list_of_dicts(fixture.get("candidate_pool"))
    evaluations = [
        {
            "evaluation_id": f"recommendation-shadow-{item.get('candidate_id', index + 1)}",
            "candidate": item,
            "used_context_candidate_ids": [
                candidate.candidate_id
                for candidate in candidates
                if candidate.candidate_type
                in {"preference", "food_preference", "golden_order"}
            ],
            "review_only_rank_signal": index + 1,
            "review_status": "pending",
            "human_review_required": True,
            "runtime_effect_allowed": False,
        }
        for index, item in enumerate(pool or [{"candidate_id": "fixture-empty-pool"}])
    ]
    return _base_artifact(
        artifact_type="recommendation_shadow_eval",
        fixture=fixture,
        extra={
            "live_search_used": False,
            "intake_commit_requested": False,
            "candidate_evaluations": evaluations,
        },
    )


def _rescue_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
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
