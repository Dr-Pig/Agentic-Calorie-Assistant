from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_memory_record_readiness"
)

CAPABILITIES = [
    "long_term_memory",
    "recommendation",
    "rescue",
    "calibration",
    "proactive",
    "chat_surface",
]
REQUIRED_TRUE_FIELDS = [
    "advanced_product_lab_product_loop_closed",
    "memory_record_session_replay_enabled",
    "memory_record_context_pack_used",
    "lab_memory_store_written",
    "lab_memory_context_injected",
    "product_outputs_applied_to_chat_surface",
    "product_recommendation_intake_handoff_created",
    "product_rescue_commit_handoff_created",
    "product_proactive_delivery_packet_ready",
]
CLAIM_FALSE_FIELDS = [
    "mainline_activation_enabled",
    "mainline_runtime_connected",
    "durable_product_memory_written",
    "canonical_product_mutation_allowed",
    "production_db_migration_allowed",
    "production_scheduler_delivery_allowed",
    "manager_context_packet_changed",
    "manager_context_injected",
    "user_facing_behavior_changed",
]
NEXT_ALLOWED_SLICES = [
    "memory_record_integrated_lab_e2e_chain",
    "memory_record_env_gated_grokfast_diagnostic",
    "simulated_dogfood_holdout_expansion",
]
NON_CLAIMS = [
    "not_mainline_runtime_activation",
    "not_self_use_v1_activation",
    "not_production_scheduler_delivery",
    "not_canonical_mutation",
    "not_durable_product_memory",
]


def build_memory_record_readiness_report(
    summary: Mapping[str, Any],
    *,
    source_summary_path: str | Path | None = None,
) -> dict[str, Any]:
    blockers = _blockers(summary)
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_memory_record_readiness_report",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_record_readiness.py",
        "consumer": "advanced_product_lab_integrated_e2e_and_live_diagnostic",
        "retirement_trigger": "approved_advanced_product_lab_activation_plan",
        "source_summary_artifact_type": str(summary.get("artifact_type") or ""),
        "source_summary_path": str(source_summary_path or ""),
        "session_id": str(summary.get("session_id") or ""),
        "turn_count": int(summary.get("turn_count") or 0),
        "stage_trace": _stage_trace(summary),
        "capability_readiness": _capability_readiness(summary, status),
        "next_allowed_slices": list(NEXT_ALLOWED_SLICES) if status == "pass" else [],
        "blockers": blockers,
        "lab_enabled": True,
        "lab_user_facing_behavior_changed": bool(
            summary.get("lab_user_facing_behavior_changed")
        ),
        "mainline_user_facing_behavior_changed": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _blockers(summary: Mapping[str, Any]) -> list[str]:
    blockers = [
        f"{field}.missing_or_false"
        for field in REQUIRED_TRUE_FIELDS
        if summary.get(field) is not True
    ]
    blockers.extend(
        f"{field}.claim_drift"
        for field in CLAIM_FALSE_FIELDS
        if summary.get(field) is True
    )
    missing_capabilities = [
        capability
        for capability in CAPABILITIES
        if capability not in set(summary.get("product_runtime_capabilities_exercised") or [])
    ]
    blockers.extend(f"capability.{name}.missing" for name in missing_capabilities)
    return blockers


def _stage_trace(summary: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        _stage("memory_record_session_replay", summary),
        _stage("memory_record_operator_summary", summary),
        _stage("advanced_product_lab_closure", summary),
    ]


def _stage(name: str, summary: Mapping[str, Any]) -> dict[str, str]:
    stage_checks = {
        "memory_record_session_replay": "memory_record_session_replay_enabled",
        "memory_record_operator_summary": "operator_review_artifact_written",
        "advanced_product_lab_closure": "advanced_product_lab_product_loop_closed",
    }
    field = stage_checks[name]
    return {"stage": name, "status": "pass" if summary.get(field) is True else "blocked"}


def _capability_readiness(
    summary: Mapping[str, Any],
    status: str,
) -> dict[str, str]:
    exercised = set(summary.get("product_runtime_capabilities_exercised") or [])
    return {
        capability: _capability_status(capability, exercised, status)
        for capability in CAPABILITIES
    }


def _capability_status(capability: str, exercised: set[object], status: str) -> str:
    if capability not in exercised:
        return "missing"
    if status != "pass":
        return "blocked_by_memory_record_readiness"
    return "ready_for_integrated_lab_e2e"


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_memory_record_readiness_report",
]
