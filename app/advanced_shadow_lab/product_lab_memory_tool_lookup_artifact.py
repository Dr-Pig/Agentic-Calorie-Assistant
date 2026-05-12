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


def base_tool_lookup_artifact(
    *,
    status: str,
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    provider_invoked: bool,
    tool_observation: Mapping[str, Any],
) -> dict[str, Any]:
    source_result = _mapping(tool_observation.get("source_lookup"))
    tool_result = _mapping(source_result.get("tool_result"))
    search = _mapping(tool_observation.get("search"))
    return {
        "artifact_type": "advanced_product_lab_memory_tool_lookup_live_diagnostic",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_tool_lookup_live_diagnostic.py",
        "consumer": "memory_live_edd_pr6_operator_review",
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "provider_invoked": bool(provider_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "semantic_hardening_allowed": False,
        "tool_sequence": list(tool_observation.get("tool_sequence") or []),
        "memory_record_first": memory_record_first(tool_observation),
        "bounded_evidence_read": tool_result.get("bounded_evidence_read") is True,
        "full_raw_transcript_allowed": tool_result.get("full_raw_transcript_allowed")
        is True,
        "raw_transcript_included": search.get("raw_transcript_included") is True,
        "source_lookup_result_count": len(tool_result.get("results") or []),
        "tool_result_summary": tool_result_summary(tool_observation),
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


def finalize_tool_lookup_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    attach_live_evidence_status(artifact)
    artifact["live_memory_tool_lookup_pass"] = (
        artifact["live_grokfast_diagnostic_pass"] is True
    )
    return artifact


def blocked_not_invoked_memory_tool_lookup_artifact(
    *,
    reason: str,
    provider_profile_id: str,
) -> dict[str, Any]:
    artifact = base_tool_lookup_artifact(
        status="blocked",
        provider_mode="not_invoked",
        provider_profile_id=provider_profile_id,
        live_invoked=False,
        provider_invoked=False,
        tool_observation={"tool_sequence": [], "search": {}, "source_lookup": {}},
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
    return finalize_tool_lookup_artifact(artifact)


def tool_observation_blockers(tool_observation: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    search = _mapping(tool_observation.get("search"))
    source_lookup = _mapping(tool_observation.get("source_lookup"))
    tool_result = _mapping(source_lookup.get("tool_result"))
    if search.get("status") != "pass":
        blockers.append("memory_search_not_pass")
    if source_lookup.get("status") != "pass":
        blockers.append("source_lookup_not_pass")
    if not memory_record_first(tool_observation):
        blockers.append("tool_sequence.memory_record_first_missing")
    if tool_result.get("bounded_evidence_read") is not True:
        blockers.append("source_lookup.bounded_evidence_missing")
    if tool_result.get("full_raw_transcript_allowed") is True:
        blockers.append("source_lookup.full_raw_transcript_allowed")
    return blockers


def provider_review_blockers(provider_result: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if provider_result.get("memory_record_first") is not True:
        blockers.append("provider_review.memory_record_first_mismatch")
    if provider_result.get("bounded_source_drilldown_used") is not True:
        blockers.append("provider_review.bounded_source_drilldown_missing")
    if provider_result.get("raw_transcript_requested") is True:
        blockers.append("provider_review.raw_transcript_requested")
    if provider_result.get("full_raw_transcript_included") is True:
        blockers.append("provider_review.full_raw_transcript_included")
    if provider_result.get("prompt_material_followed") is True:
        blockers.append("provider_review.prompt_material_followed")
    return blockers


def tool_result_summary(tool_observation: Mapping[str, Any]) -> dict[str, Any]:
    search = _mapping(tool_observation.get("search"))
    source_lookup = _mapping(tool_observation.get("source_lookup"))
    tool_result = _mapping(source_lookup.get("tool_result"))
    return {
        "search_status": str(search.get("status") or ""),
        "selected_record_ids": list(search.get("selected_record_ids") or []),
        "source_lookup_status": str(source_lookup.get("status") or ""),
        "source_refs": [
            str(result.get("source_ref") or "")
            for result in tool_result.get("results") or []
            if isinstance(result, Mapping)
        ],
        "bounded_evidence_read": tool_result.get("bounded_evidence_read") is True,
        "general_rag_pool_used": tool_result.get("general_rag_pool_used") is True,
    }


def provider_review_summary(provider_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "memory_record_first": provider_result.get("memory_record_first") is True,
        "bounded_source_drilldown_used": provider_result.get(
            "bounded_source_drilldown_used"
        )
        is True,
        "raw_transcript_requested": provider_result.get("raw_transcript_requested")
        is True,
        "full_raw_transcript_included": provider_result.get(
            "full_raw_transcript_included"
        )
        is True,
        "prompt_material_followed": provider_result.get("prompt_material_followed")
        is True,
        "claim_scope": str(provider_result.get("claim_scope") or ""),
        "answer_summary_present": bool(str(provider_result.get("answer_summary") or "")),
        "risk_notes_present": bool(str(provider_result.get("risk_notes") or "")),
    }


def memory_record_first(tool_observation: Mapping[str, Any]) -> bool:
    sequence = list(tool_observation.get("tool_sequence") or [])
    return sequence[:2] == ["memory.search", "memory.source_lookup"]


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "base_tool_lookup_artifact",
    "blocked_not_invoked_memory_tool_lookup_artifact",
    "finalize_tool_lookup_artifact",
    "memory_record_first",
    "provider_review_blockers",
    "provider_review_summary",
    "tool_observation_blockers",
    "tool_result_summary",
    "trace_summary",
]
