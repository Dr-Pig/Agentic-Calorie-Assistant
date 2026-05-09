from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_recommendation_prompt_bridge"
)
SUPPORTED_REPORT = "recommendation_shadow_summary_consumer_quality_report"
SUPPORTED_POOL_DECISIONS = {
    "offer",
    "primary_plus_backup",
    "silent_no_qualified_candidate",
}
CLAIM_FLAGS = (
    "recommendation_served",
    "proactive_sent",
    "live_search_used",
    "ranking_llm_invoked",
    "intake_handoff_created",
    "mutation_changed",
    "meal_thread_mutated",
    "day_budget_mutated",
    "body_plan_mutated",
    "durable_memory_written",
    "manager_context_packet_changed",
    "manager_context_injected",
)
NO_RECOMMENDATION_PROMPT_REVIEW = {
    "source_report_used": False,
    "status": "not_evaluated",
    "recommendation_pool_decision": "not_evaluated",
    "prompt_posture": "not_applicable",
    "suppression_reasons": [],
    "blockers": [],
    "actual_candidates_included": False,
    "candidate_ids_exposed": False,
    "runtime_effect_allowed": False,
    "recommendation_served": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "scheduler_activation_allowed": False,
    "manager_context_injected": False,
}


def build_recommendation_prompt_no_send_review(
    recommendation_quality_report: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = _report_blockers(recommendation_quality_report)
    pool_decision = str(recommendation_quality_report.get("pool_decision") or "blocked")
    if blockers:
        return _review(
            status="blocked",
            pool_decision="blocked",
            prompt_posture="not_applicable",
            suppression_reasons=[],
            blockers=blockers,
            reviewer_next_step="fix_recommendation_quality_report_before_review",
        )
    if pool_decision == "silent_no_qualified_candidate":
        return _review(
            status="suppressed",
            pool_decision=pool_decision,
            prompt_posture="silent",
            suppression_reasons=["recommendation_pool_silent_no_qualified_candidate"],
            blockers=[],
            reviewer_next_step="keep_silent_until_qualified_recommendation_pool",
        )
    return _review(
        status="candidate_for_human_review",
        pool_decision=pool_decision,
        prompt_posture="invitation_only",
        suppression_reasons=[],
        blockers=[],
        reviewer_next_step="review_invitation_posture_without_serving_candidates",
    )


def _review(
    *,
    status: str,
    pool_decision: str,
    prompt_posture: str,
    suppression_reasons: list[str],
    blockers: list[str],
    reviewer_next_step: str,
) -> dict[str, Any]:
    return {
        **dict(NO_RECOMMENDATION_PROMPT_REVIEW),
        "source_report_used": True,
        "status": status,
        "recommendation_pool_decision": pool_decision,
        "prompt_posture": prompt_posture,
        "suppression_reasons": suppression_reasons,
        "blockers": blockers,
        "review_decision": {
            "status": status
            if status != "suppressed"
            else "suppressed_context_or_data",
            "reviewer_next_step": reviewer_next_step,
        },
    }


def _report_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if report.get("artifact_type") != SUPPORTED_REPORT:
        blockers.append("recommendation_quality_report.unsupported_artifact_type")
    if report.get("status") != "pass":
        blockers.append("recommendation_quality_report.status_not_pass")
    if report.get("pool_decision") not in SUPPORTED_POOL_DECISIONS:
        blockers.append("recommendation_quality_report.unsupported_pool_decision")
    for flag in CLAIM_FLAGS:
        if report.get(flag) is True:
            blockers.append(f"recommendation_quality_report.{flag}")
    return blockers


__all__ = [
    "NO_RECOMMENDATION_PROMPT_REVIEW",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_prompt_no_send_review",
]
