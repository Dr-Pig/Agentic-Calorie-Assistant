from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_record_live_evidence import (
    attach_live_evidence_status,
)
from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS


def proactive_feedback_artifact(
    *,
    status: str,
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    provider_invoked: bool,
    case_reports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_proactive_feedback_live_diagnostic",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_proactive_feedback_live_diagnostic.py",
        "consumer": "memory_live_edd_pr9_operator_review",
        "case_count": len(case_reports),
        "case_reports": [dict(report) for report in case_reports],
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "provider_invoked": bool(provider_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "semantic_hardening_allowed": False,
        "proactive_delivery_enabled": any(
            report.get("proactive_delivery_enabled") is True for report in case_reports
        ),
        "scheduler_delivery_allowed": any(
            report.get("scheduler_delivery_allowed") is True for report in case_reports
        ),
        "durable_product_memory_written": any(
            report.get("durable_product_memory_written") is True for report in case_reports
        ),
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        **NON_MUTATION_FLAGS,
    }


def finalize_proactive_feedback_artifact(artifact: dict[str, Any]) -> None:
    attach_live_evidence_status(artifact)
    artifact["live_proactive_feedback_projection_pass"] = (
        artifact["live_grokfast_diagnostic_pass"] is True
    )


def blocked_not_invoked_proactive_feedback_artifact(
    *,
    reason: str,
    provider_profile_id: str,
) -> dict[str, Any]:
    artifact = proactive_feedback_artifact(
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
    finalize_proactive_feedback_artifact(artifact)
    return artifact


def case_blockers(case_reports: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"case:{report.get('case_id')}.blocked"
        for report in case_reports
        if report.get("status") != "pass"
    ]


def provider_review_blockers(provider_result: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if provider_result.get("proactive_delivery_enabled") is True:
        blockers.append("provider_review.proactive_delivery_enabled")
    if provider_result.get("scheduler_delivery_allowed") is True:
        blockers.append("provider_review.scheduler_delivery_allowed")
    if provider_result.get("dismissal_path_present") is not True:
        blockers.append("provider_review.dismissal_path_missing")
    if provider_result.get("reopen_modify_path_present") is not True:
        blockers.append("provider_review.reopen_modify_path_missing")
    return blockers


def provider_review_summary(provider_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "proactive_delivery_enabled": provider_result.get("proactive_delivery_enabled")
        is True,
        "scheduler_delivery_allowed": provider_result.get("scheduler_delivery_allowed")
        is True,
        "dismissal_path_present": provider_result.get("dismissal_path_present") is True,
        "reopen_modify_path_present": provider_result.get("reopen_modify_path_present")
        is True,
        "claim_scope": str(provider_result.get("claim_scope") or ""),
    }


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


__all__ = [
    "blocked_not_invoked_proactive_feedback_artifact",
    "case_blockers",
    "finalize_proactive_feedback_artifact",
    "proactive_feedback_artifact",
    "provider_review_blockers",
    "provider_review_summary",
    "trace_summary",
]
