from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_record_live_evidence import (
    attach_live_evidence_status,
)
from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS


def rescue_memory_context_artifact(
    *,
    status: str,
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    provider_invoked: bool,
    case_reports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_rescue_memory_context_live_diagnostic",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_rescue_memory_context_live_diagnostic.py",
        "consumer": "memory_live_edd_pr11_operator_review",
        "case_count": len(case_reports),
        "case_reports": [dict(report) for report in case_reports],
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "provider_invoked": bool(provider_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "semantic_hardening_allowed": False,
        "memory_context_used": any(
            report.get("memory_summary_projection_used") is True for report in case_reports
        ),
        "claim_drift_rejected": any(
            report.get("claim_boundary_blocked") is True for report in case_reports
        ),
        "proposal_presented_to_lab": any(
            report.get("proposal_presented_to_lab") is True for report in case_reports
        ),
        "rescue_commit_requested": _any_true(case_reports, "canonical_commit_requested"),
        "meal_or_budget_truth_mutated": any(_mutated(report) for report in case_reports),
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "production_scheduler_delivery_allowed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        **NON_MUTATION_FLAGS,
    }


def finalize_rescue_memory_context_artifact(artifact: dict[str, Any]) -> None:
    attach_live_evidence_status(artifact)
    artifact["live_rescue_memory_context_diagnostic_pass"] = (
        artifact["live_grokfast_diagnostic_pass"] is True
    )


def blocked_not_invoked_rescue_memory_context_artifact(
    *,
    reason: str,
    provider_profile_id: str,
) -> dict[str, Any]:
    artifact = rescue_memory_context_artifact(
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
    finalize_rescue_memory_context_artifact(artifact)
    return artifact


def case_blockers(case_reports: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"case:{report.get('case_id')}.blocked"
        for report in case_reports
        if report.get("status") != "pass"
    ]


def provider_review_blockers(provider_result: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if provider_result.get("memory_context_used") is not True:
        blockers.append("provider_review.memory_context_used_missing")
    if provider_result.get("meal_or_budget_truth_mutated") is True:
        blockers.append("provider_review.meal_or_budget_truth_mutated")
    if provider_result.get("rescue_commit_requested") is True:
        blockers.append("provider_review.rescue_commit_requested")
    if provider_result.get("claim_boundary_respected") is not True:
        blockers.append("provider_review.claim_boundary_respected_missing")
    if provider_result.get("claim_scope") != "diagnostic_only":
        blockers.append("provider_review.claim_scope_not_diagnostic")
    return blockers


def provider_review_summary(provider_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "memory_context_used": provider_result.get("memory_context_used") is True,
        "meal_or_budget_truth_mutated": provider_result.get(
            "meal_or_budget_truth_mutated"
        )
        is True,
        "rescue_commit_requested": provider_result.get("rescue_commit_requested") is True,
        "claim_boundary_respected": provider_result.get("claim_boundary_respected")
        is True,
        "claim_scope": str(provider_result.get("claim_scope") or ""),
    }


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def _any_true(reports: list[Mapping[str, Any]], key: str) -> bool:
    return any(report.get(key) is True for report in reports)


def _mutated(report: Mapping[str, Any]) -> bool:
    return any(
        report.get(flag) is True
        for flag in ("ledger_entry_created", "day_budget_mutated", "body_plan_mutated", "meal_thread_mutated")
    )


__all__ = [
    "blocked_not_invoked_rescue_memory_context_artifact",
    "case_blockers",
    "finalize_rescue_memory_context_artifact",
    "provider_review_blockers",
    "provider_review_summary",
    "rescue_memory_context_artifact",
    "trace_summary",
]
