from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_memory_record_provider_summary import (
    provider_contract_summary,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_memory_record_closure_pack"
)
CAPABILITY_ORDER = [
    "long_term_memory",
    "recommendation",
    "rescue",
    "calibration",
    "proactive",
    "chat_surface",
]
STAGE_TYPES = {
    "memory_record_dogfood_summary": "advanced_product_lab_memory_record_dogfood_summary",
    "memory_record_readiness": "advanced_product_lab_memory_record_readiness_report",
    "integrated_e2e": "advanced_product_lab_memory_record_integrated_e2e_artifact",
    "provider_contract_diagnostic": (
        "advanced_product_lab_memory_record_live_diagnostic_artifact"
    ),
    "negative_preference_holdout": "advanced_product_lab_memory_record_holdout_report",
}
CLAIM_FALSE_FIELDS = [
    "mainline_activation_enabled",
    "mainline_runtime_connected",
    "durable_product_memory_written",
    "canonical_product_mutation_allowed",
    "production_scheduler_delivery_allowed",
    "manager_context_packet_changed",
    "manager_context_injected",
    "user_facing_behavior_changed",
]
NON_CLAIMS = [
    "not_mainline_runtime_activation",
    "not_self_use_v1_activation",
    "not_production_scheduler_delivery",
    "not_canonical_mutation",
    "not_durable_product_memory",
]


def build_memory_record_closure_pack(
    *,
    summary_artifact: Mapping[str, Any],
    readiness_report: Mapping[str, Any],
    integrated_e2e_artifact: Mapping[str, Any],
    live_diagnostic_artifact: Mapping[str, Any],
    holdout_report: Mapping[str, Any],
    source_summary_path: str | Path | None = None,
    source_readiness_path: str | Path | None = None,
    source_integrated_e2e_path: str | Path | None = None,
    source_live_diagnostic_path: str | Path | None = None,
    source_holdout_path: str | Path | None = None,
) -> dict[str, Any]:
    stage_artifacts = {
        "memory_record_dogfood_summary": summary_artifact,
        "memory_record_readiness": readiness_report,
        "integrated_e2e": integrated_e2e_artifact,
        "provider_contract_diagnostic": live_diagnostic_artifact,
        "negative_preference_holdout": holdout_report,
    }
    blockers = _blockers(stage_artifacts)
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_memory_record_closure_pack",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_record_closure_pack.py",
        "consumer": "advanced_product_lab_activation_wall_audit",
        "retirement_trigger": "approved_advanced_product_lab_activation_plan",
        "stage_statuses": _stage_statuses(stage_artifacts),
        "stage_artifact_types": _stage_artifact_types(stage_artifacts),
        "source_paths": {
            "summary": str(source_summary_path or ""),
            "readiness": str(source_readiness_path or ""),
            "integrated_e2e": str(source_integrated_e2e_path or ""),
            "live_diagnostic": str(source_live_diagnostic_path or ""),
            "holdout": str(source_holdout_path or ""),
        },
        "capabilities_closed": _capabilities_closed(readiness_report, status),
        "provider_contract_diagnostic": provider_contract_summary(
            live_diagnostic_artifact
        ),
        "holdout_case_count": int(holdout_report.get("holdout_case_count") or 0),
        "blockers": blockers,
        "next_allowed_slices": [
            "activation_wall_audit",
            "lab_debt_retirement_plan",
        ]
        if status == "pass"
        else [],
        "lab_enabled": True,
        "lab_product_loop_closed": status == "pass",
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _blockers(stage_artifacts: Mapping[str, Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for stage, artifact in stage_artifacts.items():
        expected_type = STAGE_TYPES[stage]
        if artifact.get("artifact_type") != expected_type:
            blockers.append(f"{stage}.artifact_type_mismatch")
        if stage != "memory_record_dogfood_summary" and artifact.get("status") != "pass":
            blockers.append(f"{stage}.status_{artifact.get('status')}")
            blockers.extend(f"{stage}.{item}" for item in artifact.get("blockers") or [])
    for stage, artifact in stage_artifacts.items():
        blockers.extend(_claim_drift_blockers(stage, artifact))
    if _missing_capabilities(stage_artifacts["memory_record_readiness"]):
        blockers.append("memory_record_readiness.capabilities_not_closed")
    return blockers


def _claim_drift_blockers(stage: str, artifact: Mapping[str, Any]) -> list[str]:
    return [
        f"{stage}.{field}.claim_drift"
        for field in CLAIM_FALSE_FIELDS
        if artifact.get(field) is True
    ]


def _missing_capabilities(readiness_report: Mapping[str, Any]) -> list[str]:
    capability_readiness = readiness_report.get("capability_readiness") or {}
    if not isinstance(capability_readiness, Mapping):
        return list(CAPABILITY_ORDER)
    return [
        capability
        for capability in CAPABILITY_ORDER
        if not str(capability_readiness.get(capability) or "").startswith("ready_")
    ]


def _capabilities_closed(
    readiness_report: Mapping[str, Any],
    status: str,
) -> list[str]:
    if status != "pass":
        return []
    missing = set(_missing_capabilities(readiness_report))
    return [capability for capability in CAPABILITY_ORDER if capability not in missing]


def _stage_statuses(stage_artifacts: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for stage, artifact in stage_artifacts.items():
        if stage == "memory_record_dogfood_summary":
            statuses[stage] = "pass" if _summary_closed(artifact) else "blocked"
        else:
            statuses[stage] = str(artifact.get("status") or "missing")
    return statuses


def _summary_closed(summary_artifact: Mapping[str, Any]) -> bool:
    return (
        summary_artifact.get("artifact_type")
        == STAGE_TYPES["memory_record_dogfood_summary"]
        and summary_artifact.get("advanced_product_lab_product_loop_closed") is True
    )


def _stage_artifact_types(
    stage_artifacts: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    return {
        stage: str(artifact.get("artifact_type") or "")
        for stage, artifact in stage_artifacts.items()
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_memory_record_closure_pack",
]
