from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_memory_record_live_evidence import (
    attach_live_evidence_status,
)
from app.memory.application.memory_feedback_contract import NON_MUTATION_FLAGS


def integrated_live_e2e_artifact(
    *,
    status: str,
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    provider_invoked: bool,
    case_bundle: Mapping[str, Any],
) -> dict[str, Any]:
    turn = _mapping(case_bundle.get("product_lab_turn_summary"))
    return {
        "artifact_type": "advanced_product_lab_integrated_live_e2e",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_integrated_live_e2e.py",
        "consumer": "memory_live_edd_pr12_operator_review",
        "component_statuses": dict(_mapping(case_bundle.get("component_statuses"))),
        "component_summaries": dict(_mapping(case_bundle.get("component_summaries"))),
        "product_lab_turn_summary": dict(turn),
        "integrated_loop_closed": integrated_loop_closed(case_bundle),
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "provider_invoked": bool(provider_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "semantic_hardening_allowed": False,
        "lab_enabled": True,
        "lab_user_facing_behavior_changed": turn.get("lab_user_facing_behavior_changed")
        is True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "production_scheduler_delivery_allowed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        **NON_MUTATION_FLAGS,
    }


def finalize_integrated_live_e2e_artifact(artifact: dict[str, Any]) -> None:
    attach_live_evidence_status(artifact)
    artifact["live_integrated_e2e_pass"] = (
        artifact["live_grokfast_diagnostic_pass"] is True
    )


def blocked_not_invoked_integrated_live_e2e_artifact(
    *,
    reason: str,
    provider_profile_id: str,
) -> dict[str, Any]:
    artifact = integrated_live_e2e_artifact(
        status="blocked",
        provider_mode="not_invoked",
        provider_profile_id=provider_profile_id,
        live_invoked=False,
        provider_invoked=False,
        case_bundle={},
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
    finalize_integrated_live_e2e_artifact(artifact)
    return artifact


def case_bundle_blockers(case_bundle: Mapping[str, Any]) -> list[str]:
    statuses = _mapping(case_bundle.get("component_statuses"))
    return [
        f"component:{name}.status_{status}"
        for name, status in statuses.items()
        if status != "pass"
    ]


def provider_review_blockers(provider_result: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if provider_result.get("integrated_loop_closed") is not True:
        blockers.append("provider_review.integrated_loop_not_closed")
    if provider_result.get("mainline_activation_enabled") is True:
        blockers.append("provider_review.mainline_activation_enabled")
    if provider_result.get("canonical_mutation_allowed") is True:
        blockers.append("provider_review.canonical_mutation_allowed")
    if provider_result.get("durable_product_memory_written") is True:
        blockers.append("provider_review.durable_product_memory_written")
    if provider_result.get("scheduler_delivery_allowed") is True:
        blockers.append("provider_review.scheduler_delivery_allowed")
    if provider_result.get("claim_scope") != "diagnostic_only":
        blockers.append("provider_review.claim_scope_not_diagnostic")
    return blockers


def provider_review_summary(provider_result: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "integrated_loop_closed": provider_result.get("integrated_loop_closed") is True,
        "mainline_activation_enabled": provider_result.get("mainline_activation_enabled")
        is True,
        "canonical_mutation_allowed": provider_result.get("canonical_mutation_allowed")
        is True,
        "durable_product_memory_written": provider_result.get(
            "durable_product_memory_written"
        )
        is True,
        "scheduler_delivery_allowed": provider_result.get("scheduler_delivery_allowed")
        is True,
        "claim_scope": str(provider_result.get("claim_scope") or ""),
    }


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def integrated_loop_closed(case_bundle: Mapping[str, Any]) -> bool:
    statuses = _mapping(case_bundle.get("component_statuses"))
    return bool(statuses) and all(status == "pass" for status in statuses.values())


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "blocked_not_invoked_integrated_live_e2e_artifact",
    "case_bundle_blockers",
    "finalize_integrated_live_e2e_artifact",
    "integrated_live_e2e_artifact",
    "provider_review_blockers",
    "provider_review_summary",
    "trace_summary",
]
