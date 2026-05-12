from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_record_live_evidence import (
    attach_live_evidence_status,
)
from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS


NON_CLAIMS = [
    "not_product_readiness_evidence",
    "not_mainline_runtime_activation",
    "not_durable_product_memory",
    "not_canonical_mutation",
    "not_memory_promotion",
]


def memory_feedback_artifact(
    *,
    status: str,
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    provider_invoked: bool,
    case_reports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_feedback_live_diagnostic",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_feedback_live_diagnostic.py",
        "consumer": "memory_live_edd_pr8_operator_review",
        "case_count": len(case_reports),
        "case_reports": [dict(report) for report in case_reports],
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "provider_invoked": bool(provider_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "semantic_hardening_allowed": False,
        "confirmed_memory_promoted": any(
            report.get("confirmed_memory_promoted") is True for report in case_reports
        ),
        "durable_product_memory_written": any(
            report.get("durable_product_memory_written") is True
            for report in case_reports
        ),
        "proactive_delivery_enabled": any(
            report.get("proactive_delivery_enabled") is True for report in case_reports
        ),
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **NON_MUTATION_FLAGS,
    }


def finalize_memory_feedback_artifact(artifact: dict[str, Any]) -> None:
    attach_live_evidence_status(artifact)
    artifact["live_memory_feedback_projection_pass"] = (
        artifact["live_grokfast_diagnostic_pass"] is True
    )


def blocked_not_invoked_memory_feedback_artifact(
    *,
    reason: str,
    provider_profile_id: str,
) -> dict[str, Any]:
    artifact = memory_feedback_artifact(
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
    finalize_memory_feedback_artifact(artifact)
    return artifact


def case_blockers(case_reports: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"case:{report.get('case_id')}.blocked"
        for report in case_reports
        if report.get("status") != "pass"
    ]


def provider_review_blockers(provider_result: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if provider_result.get("confirmed_memory_promoted") is True:
        blockers.append("provider_review.confirmed_memory_promoted")
    if provider_result.get("durable_memory_written") is True:
        blockers.append("provider_review.durable_memory_written")
    if provider_result.get("canonical_mutation_allowed") is True:
        blockers.append("provider_review.canonical_mutation_allowed")
    if provider_result.get("validator_required_for_confirm") is not True:
        blockers.append("provider_review.validator_required_for_confirm_missing")
    return blockers


def provider_review_summary(provider_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "confirmed_memory_promoted": provider_result.get("confirmed_memory_promoted")
        is True,
        "durable_memory_written": provider_result.get("durable_memory_written") is True,
        "canonical_mutation_allowed": provider_result.get("canonical_mutation_allowed")
        is True,
        "validator_required_for_confirm": provider_result.get(
            "validator_required_for_confirm"
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


__all__ = [
    "blocked_not_invoked_memory_feedback_artifact",
    "case_blockers",
    "finalize_memory_feedback_artifact",
    "memory_feedback_artifact",
    "provider_review_blockers",
    "provider_review_summary",
    "trace_summary",
]
