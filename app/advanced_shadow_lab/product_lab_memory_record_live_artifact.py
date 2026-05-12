from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.model_profiles import advanced_lab_model_profile_policy
from app.shared.infra.json_artifacts import write_json_artifact


ARTIFACT_TYPE = "advanced_product_lab_memory_record_live_diagnostic_artifact"
NON_CLAIMS = [
    "not_user_facing_activation",
    "not_mainline_runtime_activation",
    "not_scheduler_delivery",
    "not_durable_product_memory",
    "not_canonical_mutation",
    "not_product_readiness_evidence",
    "not_kimi_activation",
]


def base_live_artifact(
    *,
    status: str,
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    source_integrated_e2e_path: str | Path | None,
    integrated_e2e_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_record_live_diagnostic.py",
        "consumer": "advanced_product_lab_operator_review",
        "retirement_trigger": "approved_advanced_product_lab_activation_plan",
        "source_integrated_e2e_path": str(source_integrated_e2e_path or ""),
        "source_integrated_e2e_status": str(integrated_e2e_artifact.get("status") or ""),
        "source_memory_record_ids": list(
            integrated_e2e_artifact.get("source_memory_record_ids") or []
        ),
        "source_memory_record_summary_drives_chain": bool(
            integrated_e2e_artifact.get("memory_record_summary_drives_chain")
        ),
        "source_journey_terminal_evidence_count": int(
            integrated_e2e_artifact.get("journey_terminal_evidence_count") or 0
        ),
        "model_input_policy": model_input_policy(),
        "model_profile_policy": advanced_lab_model_profile_policy(),
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "live_invoked": bool(live_invoked),
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "production_db_migration_allowed": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "user_facing_behavior_changed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def blocked_not_invoked_artifact(
    *,
    output_path: Path,
    provider_profile_id: str,
    reason: str,
) -> dict[str, Any]:
    artifact = base_live_artifact(
        status="blocked",
        provider_mode="not_invoked",
        provider_profile_id=provider_profile_id,
        live_invoked=False,
        source_integrated_e2e_path=None,
        integrated_e2e_artifact={},
    )
    artifact.update(
        {
            "live_provider_used": False,
            "provider_invoked": False,
            "provider_readiness": {},
            "provider_trace_summary": {
                "stage": "not_invoked",
                "provider": "not_invoked",
                "usage_present": False,
            },
            "provider_error": {},
            "model_output_summary": {
                "diagnostic_notes_present": False,
                "risk_notes_present": False,
                "claim_scope": "",
            },
            "output_guard": {"status": "not_invoked", "blockers": []},
            "blockers": [reason],
        }
    )
    write_json_artifact(output_path, artifact)
    return artifact


def input_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != (
        "advanced_product_lab_memory_record_integrated_e2e_artifact"
    ):
        blockers.append("integrated_e2e.unsupported_artifact_type")
    if artifact.get("status") != "pass":
        blockers.append("integrated_e2e.status_not_pass")
    if artifact.get("memory_record_summary_drives_chain") is not True:
        blockers.append("integrated_e2e.memory_record_summary_not_driving_chain")
    for flag in (
        "mainline_activation_enabled",
        "mainline_runtime_connected",
        "durable_product_memory_written",
        "canonical_product_mutation_allowed",
        "user_facing_behavior_changed",
        "manager_context_packet_changed",
    ):
        if artifact.get(flag) is True:
            blockers.append(f"integrated_e2e.{flag}")
    return blockers


def model_input_policy() -> dict[str, Any]:
    return {
        "claim_scope_required": "diagnostic_only",
        "lab_user_facing_output_allowed": True,
        "outside_lab_delivery_allowed": False,
        "mutation_or_commit_allowed": False,
    }


def model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "diagnostic_notes_present": bool(
            str(output.get("diagnostic_notes") or "").strip()
        ),
        "risk_notes_present": bool(str(output.get("risk_notes") or "").strip()),
        "claim_scope": str(output.get("claim_scope") or ""),
    }


def trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


__all__ = [
    "ARTIFACT_TYPE",
    "base_live_artifact",
    "blocked_not_invoked_artifact",
    "input_blockers",
    "model_input_policy",
    "model_output_summary",
    "trace_summary",
]
