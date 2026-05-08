from __future__ import annotations

from typing import Any

from app.composition.current_shell_compatibility_ids import (
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_ARTIFACT_TYPE,
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS,
    LEGACY_CURRENT_METADATA_ARTIFACT_TYPES,
    LEGACY_CURRENT_METADATA_READY_STATUSES,
    matches_alias,
)

EXPECTED_CURRENT_METADATA_ARTIFACT_TYPE = (
    CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_ARTIFACT_TYPE
)
EXPECTED_CURRENT_METADATA_STATUS = CURRENT_SHELL_COMPATIBILITY_CURRENT_METADATA_READY_STATUS

FORBIDDEN_METADATA_FLAGS = (
    "ready_for_live_diagnostic_decision",
    "ready_for_fdb_integration",
    "live_llm_invoked",
    "web_tavily_used",
    "websearch_evidence_used",
    "fooddb_evidence_used",
    "real_fooddb_pass_claimed",
    "dogfood_pass",
    "product_readiness_claimed",
    "private_self_use_approved",
    "runtime_truth_changed",
    "mutation_changed",
    "manager_context_packet_schema_changed",
)


def _claim_is_true(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, int | float):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return bool(value)


def current_metadata_freshness_blockers(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not payload:
        return ["current_metadata_freshness_pack.missing"]
    if payload.get("artifact_type") in {
        "missing_current_shell_compatibility_current_metadata_freshness_pack",
        "missing_pl_ce_current_metadata_freshness_pack",
        "missing_pl_ce_current_metadata_input",
    }:
        return ["current_metadata_freshness_pack.missing"]
    if payload.get("artifact_type") in {
        "invalid_missing_current_shell_compatibility_current_metadata_freshness_pack",
        "invalid_missing_current_shell_compatibility_current_metadata_freshness_pack_shape",
        "invalid_pl_ce_current_metadata_freshness_pack",
        "invalid_pl_ce_current_metadata_input",
    }:
        return ["current_metadata_freshness_pack.invalid"]
    if not matches_alias(
        payload.get("artifact_type"),
        EXPECTED_CURRENT_METADATA_ARTIFACT_TYPE,
        *LEGACY_CURRENT_METADATA_ARTIFACT_TYPES,
    ):
        blockers.append(
            f"current_metadata_freshness_pack.unexpected_artifact_type:{payload.get('artifact_type')}"
        )
    if payload.get("artifact_schema_version") != "1.0":
        blockers.append("current_metadata_freshness_pack.missing_artifact_schema_version")
    if not matches_alias(
        payload.get("status"),
        EXPECTED_CURRENT_METADATA_STATUS,
        *LEGACY_CURRENT_METADATA_READY_STATUSES,
    ):
        blockers.append(f"current_metadata_freshness_pack.unexpected_status:{payload.get('status')}")
    if payload.get("blockers") != []:
        blockers.append("current_metadata_freshness_pack.upstream_blockers_present")
    if payload.get("metadata_only") is not True:
        blockers.append("current_metadata_freshness_pack.metadata_only_not_true")
    if payload.get("source_status_only") is not True:
        blockers.append("current_metadata_freshness_pack.source_status_only_not_true")
    if payload.get("ready_for_serial_handoff") is not True:
        blockers.append("current_metadata_freshness_pack.ready_for_serial_handoff_not_true")
    for flag in FORBIDDEN_METADATA_FLAGS:
        if _claim_is_true(payload.get(flag)):
            blockers.append(f"current_metadata_freshness_pack.{flag}")
    return blockers


def current_metadata_freshness_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": payload.get("artifact_type", "not_available"),
        "status": payload.get("status", "not_available"),
        "source_artifact_path": payload.get("_source_artifact_path", "not_available"),
        "fresh_artifact_count": payload.get("fresh_artifact_count", "not_available"),
        "required_artifact_count": payload.get("required_artifact_count", "not_available"),
    }


__all__ = [
    "current_metadata_freshness_blockers",
    "current_metadata_freshness_summary",
]
