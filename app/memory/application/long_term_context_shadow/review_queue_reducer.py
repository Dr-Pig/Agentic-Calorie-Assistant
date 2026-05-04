from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.application.long_term_context_shadow.context_value_scoring import (
    _context_value_score_v2,
)
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _review_queue_reducer_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    scores = {
        score["candidate_id"]: score
        for score in (
            _context_value_score_v2(fixture, candidate) for candidate in candidates
        )
    }
    queue: dict[str, list[dict[str, Any]]] = {
        "high": [],
        "medium": [],
        "low": [],
        "rejected_or_deferred": [],
    }
    pseudo_runtime_truth_risks = 0
    for candidate in candidates:
        score = scores[candidate.candidate_id]
        if (
            candidate.runtime_effect_allowed
            or not candidate.why_this_is_not_runtime_truth
        ):
            pseudo_runtime_truth_risks += 1
        item = _review_queue_item(candidate, score)
        if score["recommended_action"] == "discard":
            queue["rejected_or_deferred"].append(item)
        else:
            queue[score["review_priority_bucket"]].append(item)

    for bucket_items in queue.values():
        bucket_items.sort(
            key=lambda item: (
                -item["review_priority_score"],
                item["candidate_type"],
                item["candidate_id"],
            )
        )

    return _base_artifact(
        artifact_type="review_queue_reducer",
        fixture=fixture,
        extra={
            "artifact_sprawl_control": {
                "new_artifact_requires_declared_consumer": True,
                "new_artifact_requires_scoring_or_replay_use": True,
                "consumerless_candidates_deferred": True,
            },
            "deferred_mechanism_reviews": _deferred_mechanism_reviews(),
            "summary": {
                "candidate_count": len(candidates),
                "high_priority_count": len(queue["high"]),
                "medium_priority_count": len(queue["medium"]),
                "low_priority_count": len(queue["low"]),
                "rejected_or_deferred_count": len(queue["rejected_or_deferred"]),
                "pseudo_runtime_truth_risk_count": pseudo_runtime_truth_risks,
            },
            "review_queue": queue,
        },
    )


def _review_queue_item(
    candidate: LongTermContextCandidate,
    score: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "candidate_type": candidate.candidate_type,
        "review_priority_score": score["review_priority_score"],
        "review_priority_bucket": score["review_priority_bucket"],
        "recommended_action": score["recommended_action"],
        "product_capability_value": score["product_capability_value"],
        "intended_consumers": candidate.intended_consumers,
        "risk_if_wrong": candidate.risk_if_wrong,
        "promotion_path": candidate.promotion_path,
        "runtime_effect_allowed": False,
        "durable_memory_written": False,
        "manager_context_injected": False,
    }


def _deferred_mechanism_reviews() -> list[dict[str, Any]]:
    return [
        {
            "mechanism_id": "active_conversation_recall_tool",
            "product_capability_value": "Lets the future manager find prior conversations without prompt-dumping history.",
            "blocked_by_dependency": True,
            "deferred_reason": "Requires approved retrieval tool contract and ManagerContextPacket integration.",
            "current_shadow_coverage": "conversation_recall_shadow_replay",
            "runtime_effect_allowed": False,
        },
        {
            "mechanism_id": "durable_memory_write_service",
            "product_capability_value": "Turns reviewed preferences into persistent user memory.",
            "blocked_by_dependency": True,
            "deferred_reason": "Requires storage schema, promotion policy, deletion/correction surface, and human approval.",
            "current_shadow_coverage": "memory_review_action_shadow_result",
            "runtime_effect_allowed": False,
        },
        {
            "mechanism_id": "semantic_pattern_llm_extraction",
            "product_capability_value": "Finds richer behavioral patterns than deterministic counts can extract.",
            "blocked_by_dependency": True,
            "deferred_reason": "Requires live or approved LLM extraction path plus holdout evals.",
            "current_shadow_coverage": "semantic_pattern_extraction_shadow_plan",
            "runtime_effect_allowed": False,
        },
        {
            "mechanism_id": "style_profile_materialization",
            "product_capability_value": "Adapts response style, follow-up density, and proactive wording.",
            "blocked_by_dependency": True,
            "deferred_reason": "L4A marks conversation_style_profile as a later extension, not active runtime truth.",
            "current_shadow_coverage": "app_usage_style and interaction_preference candidates",
            "runtime_effect_allowed": False,
        },
        {
            "mechanism_id": "live_menu_scan_runtime",
            "product_capability_value": "Uses menu input before eating to rank concrete choices.",
            "blocked_by_dependency": True,
            "deferred_reason": "Requires vision/parser and recommendation runtime activation; shadow lab only reviews candidate-source value.",
            "current_shadow_coverage": "candidate_extraction_engine_v2.menu_scan_shadow_context",
            "runtime_effect_allowed": False,
        },
    ]
