from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_downstream_boundary import (
    consumer_summary_projection_blockers,
)
from app.recommendation.application.candidate_quality_gate import (
    evaluate_recommendation_candidate_quality,
)
from app.recommendation.application.summary_consumer_candidate import (
    quality_input_from_prepared_candidate,
)
from app.recommendation.application.summary_pool_posture import (
    BLOCKED_POSTURE,
    build_summary_pool_posture,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.summary_consumer_quality"
)
FALSE_FLAGS = {
    "runtime_connected": False,
    "recommendation_served": False,
    "proactive_sent": False,
    "live_search_used": False,
    "ranking_llm_invoked": False,
    "intake_handoff_created": False,
    "mutation_changed": False,
    "meal_thread_mutated": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "durable_memory_written": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
}
SUPPORTED_MEMORY_ARTIFACT = "runtime_lab_memory_consumer_summary_projection"


def build_recommendation_shadow_summary_consumer_quality_report(
    *,
    memory_summary_projection: Mapping[str, Any],
    prepared_candidates: list[Mapping[str, Any]],
) -> dict[str, Any]:
    blockers = consumer_summary_projection_blockers(memory_summary_projection)
    status = "blocked" if blockers else "pass"
    evaluations = (
        []
        if blockers
        else [
            _evaluate_candidate(candidate, memory_summary_projection)
            for candidate in prepared_candidates
        ]
    )
    pool_posture = (
        dict(BLOCKED_POSTURE)
        if blockers
        else build_summary_pool_posture(
            prepared_candidates=prepared_candidates,
            negative_preference_ids=_memory_index(memory_summary_projection)[
                "negative_ids"
            ],
        )
    )
    return {
        "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
        "status": status,
        "blockers": blockers,
        "owner": "app/recommendation",
        "consumer": "future recommendation/proactive activation slices",
        "retirement_trigger": "approved recommendation_runtime_activation_plan",
        "source_memory_artifact_type": memory_summary_projection.get("artifact_type"),
        "memory_summary_projection_used": (
            status == "pass"
            and memory_summary_projection.get("artifact_type") == SUPPORTED_MEMORY_ARTIFACT
        ),
        "candidate_count": len(prepared_candidates),
        "candidate_evaluations": evaluations,
        **pool_posture,
        "local_only": True,
        "diagnostic_only": True,
        "shadow_only": True,
        "best_practice_evidence": {
            "required": True,
            "sources_checked": [
                "https://developers.google.com/machine-learning/recommendation/overview/types",
                "https://platform.openai.com/docs/guides/evaluation-best-practices",
                "https://platform.openai.com/docs/guides/trace-grading",
            ],
            "adopted_guidance": [
                "keep prepared candidate evaluation separate from serving",
                "apply explicit user dislikes and constraints before final ranking",
                "treat this artifact as reproducible shadow evidence only",
            ],
        },
        "non_claims": [
            "not_recommendation_serving",
            "not_proactive_sending",
            "not_runtime_activation_evidence",
            "not_manager_context_packet_input",
            "not_durable_memory_truth",
        ],
        **dict(FALSE_FLAGS),
    }


def _evaluate_candidate(
    candidate: Mapping[str, Any],
    memory_summary_projection: Mapping[str, Any],
) -> dict[str, Any]:
    memory = _memory_index(memory_summary_projection)
    source_refs = [str(ref) for ref in candidate.get("source_refs", [])]
    negative_match = _matches_any_ref(source_refs, memory["negative_ids"])
    quality = evaluate_recommendation_candidate_quality(
        quality_input_from_prepared_candidate(
            candidate,
            violates_negative_preference=negative_match,
        )
    )
    quality_tier = quality.quality_tier
    proactive_intensity = quality.proactive_intensity
    signals = list(quality.quality_signals)
    rejection_reasons: list[str] = []

    if _matches_any_ref(source_refs, memory["positive_ids"]):
        signals.append("memory_positive_summary_match")
    if _matches_any_ref(source_refs, memory["golden_order_ids"]):
        signals.append("memory_golden_order_projection_match")
    if negative_match:
        rejection_reasons.append("negative_preference_blocker")

    confidence_posture = str(memory["confidence_posture"])
    if confidence_posture != "fresh":
        signals.append("memory_summary_not_fresh")
        if quality.passed and quality_tier == "high":
            quality_tier = "medium"
            proactive_intensity = "offer"

    return {
        "candidate_id": quality.candidate_id,
        "quality_gate_passed": quality.passed,
        "quality_tier": quality_tier,
        "proactive_intensity": proactive_intensity,
        "presentation_posture": _presentation_posture(
            passed=quality.passed,
            quality_tier=quality_tier,
        ),
        "disqualifier_flags": list(quality.disqualifier_flags),
        "quality_signals": _dedupe(signals),
        "memory_confidence_posture": confidence_posture,
        "memory_rejection_reasons": rejection_reasons,
        "runtime_effect_allowed": False,
        "recommendation_served": False,
        "intake_handoff_created": False,
    }


def _memory_index(memory_summary_projection: Mapping[str, Any]) -> dict[str, Any]:
    profile = _mapping(memory_summary_projection.get("preference_profile_summary"))
    golden = _mapping(memory_summary_projection.get("golden_order_summary"))
    positive_ids = {str(item) for item in profile.get("accepted_shadow_candidate_ids", [])}
    positive_ids.update(
        str(item.get("candidate_id"))
        for item in profile.get("preference_summaries", [])
        if isinstance(item, Mapping) and item.get("candidate_id")
    )
    negative_ids = {str(item) for item in profile.get("negative_preference_blockers", [])}
    golden_ids = {
        str(item.get("candidate_id"))
        for item in golden.get("orders", [])
        if isinstance(item, Mapping) and item.get("candidate_id")
    }
    return {
        "positive_ids": positive_ids,
        "negative_ids": negative_ids,
        "golden_order_ids": golden_ids,
        "confidence_posture": _confidence_posture(profile, positive_ids),
    }


def _matches_any_ref(source_refs: list[str], candidate_ids: set[str]) -> bool:
    return any(
        ref == candidate_id or ref.endswith(f":{candidate_id}")
        for ref in source_refs
        for candidate_id in candidate_ids
    )


def _confidence_posture(profile: Mapping[str, Any], positive_ids: set[str]) -> str:
    freshness = str(profile.get("freshness_posture") or "").lower()
    if freshness and freshness != "fresh":
        return freshness
    if not positive_ids:
        return "sparse"
    return "fresh"


def _presentation_posture(*, passed: bool, quality_tier: str) -> str:
    if not passed:
        return "silent"
    if quality_tier == "high":
        return "shadow_activation_candidate"
    return "low_friction_offer_only"


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_shadow_summary_consumer_quality_report",
]
