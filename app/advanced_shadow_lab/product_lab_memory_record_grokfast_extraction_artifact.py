from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_memory_record_live_evidence import (
    attach_live_evidence_status,
)


ARTIFACT_TYPE = "advanced_product_lab_memory_record_grokfast_extraction_diagnostic"
NON_CLAIMS = [
    "not_product_readiness_evidence",
    "not_mainline_runtime_activation",
    "not_durable_product_memory",
    "not_canonical_mutation",
    "not_semantic_hardening",
]


def base_extraction_artifact(
    *,
    status: str,
    cases: list[Mapping[str, Any]],
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
) -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_record_grokfast_extraction.py",
        "consumer": "memory_live_edd_pr4_operator_review",
        "case_count": len(cases),
        "case_ids": [str(case.get("case_id") or "") for case in cases],
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "semantic_hardening_allowed": False,
        "provider_semantics_owner": False,
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def finalize_extraction_live_status(artifact: dict[str, Any]) -> None:
    attach_live_evidence_status(artifact)
    artifact["live_grokfast_extraction_pass"] = (
        artifact["live_grokfast_diagnostic_pass"] is True
    )


def empty_grade_summary(cases: list[Mapping[str, Any]]) -> dict[str, int]:
    return {"case_count": len(cases), "passed_case_count": 0, "failed_case_count": 0}


def model_output_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "case_result_count": len(result.get("case_results") or []),
        "diagnostic_notes_present": bool(str(result.get("diagnostic_notes") or "")),
        "risk_notes_present": bool(str(result.get("risk_notes") or "")),
        "claim_scope": str(result.get("claim_scope") or ""),
    }


def trace_summary(traces: list[Mapping[str, Any]]) -> dict[str, Any]:
    first = traces[0] if traces else {}
    return {
        "stage": str(first.get("stage") or ""),
        "provider": str(first.get("provider") or ""),
        "call_count": len(traces),
        "usage_present": any(isinstance(trace.get("usage"), Mapping) for trace in traces),
    }
