from __future__ import annotations

from typing import Any, Mapping

from app.runtime.application.proactive_recommendation_prompt_bridge import (
    NO_RECOMMENDATION_PROMPT_REVIEW,
    build_recommendation_prompt_no_send_review,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_summary_consumer"
)
CONSUMER_SUMMARY_ARTIFACT = "runtime_lab_memory_consumer_summary_projection"
CLAIM_FLAGS = (
    "runtime_effect_allowed",
    "durable_product_memory_written",
    "manager_context_packet_changed",
    "recommendation_served",
    "proactive_sent",
    "rescue_proposal_committed",
    "retrieval_ranking_changed",
)
NON_CLAIMS = [
    "not_scheduler_activation",
    "not_live_delivery",
    "not_proactive_readiness",
    "not_manager_context_injection",
    "not_runtime_memory_truth",
]


def build_proactive_no_send_summary_consumer_projection(
    consumer_summary_projection: Mapping[str, Any],
    *,
    recommendation_quality_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = _projection_blockers(consumer_summary_projection)
    preference_context = [] if blockers else _preference_context(consumer_summary_projection)
    golden_context = [] if blockers else _golden_context(consumer_summary_projection)
    suppression_context = [] if blockers else _suppression_context(consumer_summary_projection)
    review_context = [*preference_context, *golden_context, *suppression_context]
    recommendation_prompt_review = (
        dict(NO_RECOMMENDATION_PROMPT_REVIEW)
        if blockers or recommendation_quality_report is None
        else build_recommendation_prompt_no_send_review(recommendation_quality_report)
    )
    return {
        "artifact_type": "proactive_no_send_summary_consumer_projection",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/runtime",
        "consumer": "future_proactive_no_send_review",
        "retirement_trigger": "approved_proactive_scheduler_runtime_activation_plan",
        "allowed_input": CONSUMER_SUMMARY_ARTIFACT,
        "shadow_mode": True,
        "runtime_effect_allowed": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "push_or_line_delivery_connected": False,
        "manager_context_injected": False,
        "durable_memory_written": False,
        "user_facing_behavior_changed": False,
        "mutation_changed": False,
        "recommendation_served": False,
        "rescue_proposal_committed": False,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "promotion_allowed": False,
        "candidate_copy_generated": False,
        "delivery_decision_made": False,
        "summary": _summary(
            consumer_summary_projection=consumer_summary_projection,
            review_context=review_context,
            blocked=bool(blockers),
        ),
        "preference_review_context": preference_context,
        "golden_order_review_context": golden_context,
        "suppression_review_context": suppression_context,
        "recommendation_prompt_review": recommendation_prompt_review,
        "review_context": review_context,
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
    }


def _projection_blockers(projection: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if projection.get("artifact_type") != CONSUMER_SUMMARY_ARTIFACT:
        blockers.append("consumer_summary_projection.unsupported_artifact_type")
    if projection.get("status") != "pass":
        blockers.append("consumer_summary_projection.status_not_pass")
    for flag in CLAIM_FLAGS:
        if projection.get(flag) is True:
            blockers.append(f"consumer_summary_projection.{flag}")
    return blockers


def _preference_context(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    summary = _mapping(projection.get("preference_profile_summary"))
    return [
        {
            "candidate_id": str(item.get("candidate_id") or "unknown_candidate"),
            "summary": str(item.get("summary") or ""),
            "source_object_refs": list(item.get("source_object_refs") or []),
            "review_role": "preference_context_only",
            "runtime_effect_allowed": False,
            "proactive_sent": False,
        }
        for item in _mapping_items(summary.get("preference_summaries"))
    ]


def _golden_context(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    summary = _mapping(projection.get("golden_order_summary"))
    return [
        {
            "candidate_id": str(item.get("candidate_id") or "unknown_candidate"),
            "store_name": str(item.get("store_name") or ""),
            "item_names": list(item.get("item_names") or []),
            "summary": str(item.get("summary") or ""),
            "review_role": "golden_order_context_only",
            "runtime_effect_allowed": False,
            "proactive_sent": False,
        }
        for item in _mapping_items(summary.get("orders"))
    ]


def _suppression_context(projection: Mapping[str, Any]) -> list[dict[str, Any]]:
    summary = _mapping(projection.get("suppression_summary"))
    return [
        {
            "candidate_id": str(item.get("candidate_id") or "unknown_candidate"),
            "trigger_type": str(item.get("trigger_type") or "unknown"),
            "summary": str(item.get("summary") or ""),
            "review_role": "suppression_context_only",
            "runtime_effect_allowed": False,
            "proactive_sent": False,
        }
        for item in _mapping_items(summary.get("suppression_blockers"))
    ]


def _summary(
    *,
    consumer_summary_projection: Mapping[str, Any],
    review_context: list[dict[str, Any]],
    blocked: bool,
) -> dict[str, int]:
    if blocked:
        return {
            "preference_context_count": 0,
            "negative_preference_blocker_count": 0,
            "golden_order_context_count": 0,
            "suppression_context_count": 0,
            "memory_driven_trigger_count": 0,
            "review_context_count": 0,
        }
    preference = _mapping(consumer_summary_projection.get("preference_profile_summary"))
    golden = _mapping(consumer_summary_projection.get("golden_order_summary"))
    suppression = _mapping(consumer_summary_projection.get("suppression_summary"))
    return {
        "preference_context_count": len(_mapping_items(preference.get("preference_summaries"))),
        "negative_preference_blocker_count": len(
            list(preference.get("negative_preference_blockers") or [])
        ),
        "golden_order_context_count": len(_mapping_items(golden.get("orders"))),
        "suppression_context_count": len(_mapping_items(suppression.get("suppression_blockers"))),
        "memory_driven_trigger_count": 0,
        "review_context_count": len(review_context),
    }


def _mapping_items(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_proactive_no_send_summary_consumer_projection",
]
