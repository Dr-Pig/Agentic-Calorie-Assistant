from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_live_failure_taxonomy"
)
NON_CLAIMS = [
    "not_product_truth_change",
    "not_prompt_hardening_approval",
    "not_schema_hardening_approval",
    "not_mainline_activation",
]
FAILURE_RULES = {
    "provider_review.durable_product_memory_written": (
        "activation_boundary_claim_drift",
        "live_provider_review_contract",
        "clarify_activation_boundary_payload_or_add_holdout",
    ),
    "provider_review.canonical_mutation_allowed": (
        "activation_boundary_claim_drift",
        "live_provider_review_contract",
        "clarify_activation_boundary_payload_or_add_holdout",
    ),
    "provider_review.mainline_activation_enabled": (
        "activation_boundary_claim_drift",
        "live_provider_review_contract",
        "clarify_activation_boundary_payload_or_add_holdout",
    ),
    "provider_review.scheduler_delivery_allowed": (
        "delivery_claim_drift",
        "live_provider_review_contract",
        "clarify_delivery_boundary_payload_or_add_holdout",
    ),
    "provider_review.raw_transcript_requested": (
        "retrieval_safety_claim_drift",
        "memory_tool_lookup_contract",
        "add_retrieval_safety_holdout",
    ),
    "provider_review.full_raw_transcript_included": (
        "retrieval_safety_claim_drift",
        "memory_tool_lookup_contract",
        "add_retrieval_safety_holdout",
    ),
    "provider_review.blocked_candidate_selected": (
        "recommendation_guard_claim_drift",
        "recommendation_blocker_contract",
        "add_recommendation_blocker_holdout",
    ),
    "provider_review.rescue_commit_requested": (
        "rescue_mutation_claim_drift",
        "rescue_memory_context_contract",
        "add_rescue_no_mutation_holdout",
    ),
    "provider_review.proactive_delivery_enabled": (
        "proactive_control_claim_drift",
        "proactive_feedback_contract",
        "add_proactive_control_holdout",
    ),
}


def build_live_failure_taxonomy_report(
    diagnostic_artifacts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    records = [
        record
        for artifact in diagnostic_artifacts
        for record in _failure_records(artifact)
    ]
    blockers = [
        f"unclassified_failure:{record['blocker']}"
        for record in records
        if record["failure_family"] == "unclassified_live_failure"
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_live_failure_taxonomy",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_live_failure_taxonomy.py",
        "consumer": "memory_live_edd_pr13_operator_review",
        "diagnostic_artifact_count": len(diagnostic_artifacts),
        "failure_count": len(records),
        "unclassified_failure_count": len(blockers),
        "failure_records": records,
        "summary": dict(Counter(record["failure_family"] for record in records)),
        "milestone_statuses": _milestone_statuses(diagnostic_artifacts),
        "next_allowed_slices": ["live_edd_decision_pack"] if not blockers else [],
        "blockers": blockers,
        "live_failures_create_attribution_only": True,
        "semantic_hardening_allowed": False,
        "prompt_hardening_allowed": False,
        "schema_hardening_allowed": False,
        "product_truth_changed": False,
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _failure_records(artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for blocker in artifact.get("blockers") or []:
        records.append(_record(artifact, str(blocker)))
    if artifact.get("status") == "provider_error" and not records:
        records.append(_provider_error_record(artifact))
    return records


def _record(artifact: Mapping[str, Any], blocker: str) -> dict[str, Any]:
    family, owner, next_slice = FAILURE_RULES.get(
        blocker,
        (
            "unclassified_live_failure",
            "operator_review_required",
            "classify_live_failure_before_hardening",
        ),
    )
    return {
        "source_artifact_type": str(artifact.get("artifact_type") or ""),
        "source_status": str(artifact.get("status") or ""),
        "blocker": blocker,
        "failure_family": family,
        "attribution_owner": owner,
        "next_safe_slice": next_slice,
        "semantic_hardening_allowed": False,
    }


def _provider_error_record(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_artifact_type": str(artifact.get("artifact_type") or ""),
        "source_status": "provider_error",
        "blocker": "provider_error",
        "failure_family": "provider_transport_or_parse_failure",
        "attribution_owner": "provider_adapter_or_transport",
        "next_safe_slice": "inspect_provider_error_trace",
        "semantic_hardening_allowed": False,
    }


def _milestone_statuses(
    diagnostic_artifacts: list[Mapping[str, Any]],
) -> dict[str, str]:
    return {
        str(artifact.get("artifact_type") or ""): str(
            artifact.get("live_milestone_status") or ""
        )
        for artifact in diagnostic_artifacts
        if artifact.get("artifact_type")
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_live_failure_taxonomy_report"]
