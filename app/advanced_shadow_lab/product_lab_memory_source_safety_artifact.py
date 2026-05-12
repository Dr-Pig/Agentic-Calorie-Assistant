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
    "not_raw_transcript_retrieval",
]


def source_safety_artifact(
    *,
    status: str,
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    provider_invoked: bool,
    case_reports: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_memory_source_safety_holdout",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_source_safety_holdout.py",
        "consumer": "memory_live_edd_pr7_operator_review",
        "case_count": len(case_reports),
        "case_reports": [dict(report) for report in case_reports],
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "provider_invoked": bool(provider_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "semantic_hardening_allowed": False,
        "source_prompt_material_allowed": any(
            report.get("prompt_material_allowed") is True for report in case_reports
        ),
        "cross_scope_result_used": any(
            report.get("case_id") == "cross_scope_source_omitted"
            and int(report.get("result_count") or 0) > 0
            for report in case_reports
        ),
        "general_rag_pool_used": any(
            report.get("general_rag_pool_used") is True for report in case_reports
        ),
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **NON_MUTATION_FLAGS,
    }


def finalize_source_safety_artifact(artifact: dict[str, Any]) -> None:
    attach_live_evidence_status(artifact)
    artifact["live_source_safety_holdout_pass"] = (
        artifact["live_grokfast_diagnostic_pass"] is True
    )


def blocked_not_invoked_source_safety_artifact(
    *,
    reason: str,
    provider_profile_id: str,
) -> dict[str, Any]:
    artifact = source_safety_artifact(
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
    finalize_source_safety_artifact(artifact)
    return artifact


def case_blockers(case_reports: list[Mapping[str, Any]]) -> list[str]:
    return [
        f"case:{report.get('case_id')}.blocked"
        for report in case_reports
        if report.get("status") != "pass"
    ]


def provider_review_blockers(provider_result: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if provider_result.get("prompt_material_followed") is True:
        blockers.append("provider_review.prompt_material_followed")
    if provider_result.get("cross_scope_source_used") is True:
        blockers.append("provider_review.cross_scope_source_used")
    if provider_result.get("semantic_query_used_as_rag") is True:
        blockers.append("provider_review.semantic_query_used_as_rag")
    if provider_result.get("raw_transcript_requested") is True:
        blockers.append("provider_review.raw_transcript_requested")
    return blockers


def provider_review_summary(provider_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "prompt_material_followed": provider_result.get("prompt_material_followed")
        is True,
        "cross_scope_source_used": provider_result.get("cross_scope_source_used") is True,
        "semantic_query_used_as_rag": provider_result.get("semantic_query_used_as_rag")
        is True,
        "raw_transcript_requested": provider_result.get("raw_transcript_requested")
        is True,
        "claim_scope": str(provider_result.get("claim_scope") or ""),
        "answer_summary_present": bool(str(provider_result.get("answer_summary") or "")),
        "risk_notes_present": bool(str(provider_result.get("risk_notes") or "")),
    }


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


__all__ = [
    "blocked_not_invoked_source_safety_artifact",
    "case_blockers",
    "finalize_source_safety_artifact",
    "provider_review_blockers",
    "provider_review_summary",
    "source_safety_artifact",
    "trace_summary",
]
