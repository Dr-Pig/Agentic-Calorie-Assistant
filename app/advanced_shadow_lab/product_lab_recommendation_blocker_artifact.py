from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_record_live_evidence import (
    attach_live_evidence_status,
)
from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS


def recommendation_blocker_artifact(
    *,
    status: str,
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    provider_invoked: bool,
    case_reports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_blocker_live_diagnostic",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_recommendation_blocker_live_diagnostic.py",
        "consumer": "memory_live_edd_pr10_operator_review",
        "case_count": len(case_reports),
        "case_reports": [dict(report) for report in case_reports],
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "provider_invoked": bool(provider_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "semantic_hardening_allowed": False,
        "lab_recommendation_served": any(
            report.get("lab_recommendation_served") is True for report in case_reports
        ),
        "blocked_candidate_selected": any(_blocked_selected(report) for report in case_reports),
        "negative_block_before_offer": all(_negative_block_ok(report) for report in case_reports),
        "positive_memory_boost_observed": any(
            report.get("primary_source_type") == "memory_golden_order"
            for report in case_reports
        ),
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "production_scheduler_delivery_allowed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        **NON_MUTATION_FLAGS,
    }


def finalize_recommendation_blocker_artifact(artifact: dict[str, Any]) -> None:
    attach_live_evidence_status(artifact)
    artifact["live_recommendation_blocker_diagnostic_pass"] = (
        artifact["live_grokfast_diagnostic_pass"] is True
    )


def blocked_not_invoked_recommendation_blocker_artifact(
    *,
    reason: str,
    provider_profile_id: str,
) -> dict[str, Any]:
    artifact = recommendation_blocker_artifact(
        status="blocked",
        provider_mode="not_invoked",
        provider_profile_id=provider_profile_id,
        live_invoked=False,
        provider_invoked=False,
        case_reports=[],
    )
    artifact.update(
        {
            "provider_readiness": {},
            "provider_trace_summary": {"stage": "not_invoked", "provider": "not_invoked"},
            "provider_error": {},
            "provider_review_summary": {},
            "blockers": [reason],
        }
    )
    finalize_recommendation_blocker_artifact(artifact)
    return artifact


def case_blockers(case_reports: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"case:{report.get('case_id')}.blocked"
        for report in case_reports
        if report.get("status") != "pass"
    ]


def provider_review_blockers(provider_result: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if provider_result.get("blocker_respected") is not True:
        blockers.append("provider_review.blocker_respected_missing")
    if provider_result.get("blocked_candidate_selected") is True:
        blockers.append("provider_review.blocked_candidate_selected")
    if provider_result.get("offer_synthesis_after_guard") is not True:
        blockers.append("provider_review.offer_synthesis_after_guard_missing")
    if provider_result.get("claim_scope") != "diagnostic_only":
        blockers.append("provider_review.claim_scope_not_diagnostic")
    return blockers


def provider_review_summary(provider_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "blocker_respected": provider_result.get("blocker_respected") is True,
        "blocked_candidate_selected": provider_result.get("blocked_candidate_selected")
        is True,
        "positive_boost_observed": provider_result.get("positive_boost_observed") is True,
        "offer_synthesis_after_guard": provider_result.get(
            "offer_synthesis_after_guard"
        )
        is True,
        "claim_scope": str(provider_result.get("claim_scope") or ""),
    }


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def _negative_block_ok(report: Mapping[str, Any]) -> bool:
    if not report.get("blocked_candidate_id"):
        return True
    return report.get("blocked_candidate_reason_codes") == ["confirmed_negative_preference"]


def _blocked_selected(report: Mapping[str, Any]) -> bool:
    blocked = str(report.get("blocked_candidate_id") or "")
    return bool(blocked) and report.get("primary_candidate_id") == blocked


__all__ = [
    "blocked_not_invoked_recommendation_blocker_artifact",
    "case_blockers",
    "finalize_recommendation_blocker_artifact",
    "provider_review_blockers",
    "provider_review_summary",
    "recommendation_blocker_artifact",
    "trace_summary",
]
