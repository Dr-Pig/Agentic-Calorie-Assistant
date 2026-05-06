from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_manager_contract_handoff import build_fooddb_manager_contract_handoff
from .fooddb_manager_contract_handoff_proof import (
    handoff_proof,
    safe_fooddb_handoff_next_slice,
    unblocked_handoff_shape_blockers,
)

_EXPECTED_HANDOFF = "accurate_intake_fooddb_manager_contract_handoff_v1"


def build_fooddb_manager_contract_handoff_inspection(
    *,
    manager_contract_handoff_artifact: dict[str, Any],
    live_diagnostic_report: dict[str, Any] | None = None,
    contract_probe_artifact: dict[str, Any] | None = None,
    repair_pack_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = _handoff_boundary_blockers(manager_contract_handoff_artifact)
    source_chain_verified = False
    if all(
        isinstance(artifact, dict)
        for artifact in (
            live_diagnostic_report,
            contract_probe_artifact,
            repair_pack_artifact,
        )
    ):
        source_chain_verified = True
        try:
            derived = build_fooddb_manager_contract_handoff(
                live_diagnostic_report=live_diagnostic_report,  # type: ignore[arg-type]
                contract_probe_artifact=contract_probe_artifact,  # type: ignore[arg-type]
                repair_pack_artifact=repair_pack_artifact,  # type: ignore[arg-type]
            )
        except ValueError:
            blockers.append("manager_contract_handoff_source_artifacts_invalid")
        else:
            if handoff_proof(manager_contract_handoff_artifact) != handoff_proof(derived):
                blockers.append("manager_contract_handoff_derivation_mismatch")
    elif any(
        artifact is not None
        for artifact in (live_diagnostic_report, contract_probe_artifact, repair_pack_artifact)
    ):
        blockers.append("manager_contract_handoff_source_artifacts_incomplete")

    status = str(manager_contract_handoff_artifact.get("status") or "")
    if status == "fooddb_contract_unblocked":
        blockers.extend(unblocked_handoff_shape_blockers(manager_contract_handoff_artifact))
    if status == "ready_for_manager_contract_owner" and manager_contract_handoff_artifact.get("handoff_ready") is not True:
        blockers.append("manager_contract_handoff_ready_flag_missing")

    next_safe_slice = _next_safe_slice(manager_contract_handoff_artifact)
    summary = dict(manager_contract_handoff_artifact.get("summary") or {})
    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_handoff_inspection_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "deterministic_fooddb_manager_contract_handoff_inspection_only",
        "claim_scope": "fooddb_manager_contract_handoff_alignment_without_runtime_truth",
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "readiness_claimed": False,
        "summary": {
            "handoff_status": status or "unknown",
            "live_seam_status": str(summary.get("live_seam_status") or "unknown"),
            "handoff_ready": manager_contract_handoff_artifact.get("handoff_ready") is True,
            "selected_next_step": safe_fooddb_handoff_next_slice(
                manager_contract_handoff_artifact.get("selected_next_step")
            ),
            "source_chain_verified": source_chain_verified,
            "next_safe_slice": next_safe_slice,
        },
        "source_refs": {
            "manager_contract_handoff_type": manager_contract_handoff_artifact.get("artifact_type"),
            "live_diagnostic_report_type": None
            if live_diagnostic_report is None
            else live_diagnostic_report.get("artifact_type"),
            "contract_probe_type": None
            if contract_probe_artifact is None
            else contract_probe_artifact.get("artifact_type"),
            "repair_pack_type": None
            if repair_pack_artifact is None
            else repair_pack_artifact.get("artifact_type"),
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _handoff_boundary_blockers(artifact: dict[str, Any]) -> list[str]:
    if str(artifact.get("artifact_type") or "") != _EXPECTED_HANDOFF:
        return ["unsupported_manager_contract_handoff_artifact"]
    blockers: list[str] = []
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append("manager_contract_handoff_changed_runtime_truth")
    if artifact.get("runtime_mutation_attempted") is not False:
        blockers.append("manager_contract_handoff_attempted_runtime_mutation")
    if artifact.get("shared_contract_changed") is not False:
        blockers.append("manager_contract_handoff_changed_shared_contract")
    if artifact.get("readiness_claimed") is not False:
        blockers.append("manager_contract_handoff_claimed_readiness")
    return blockers


def _next_safe_slice(artifact: dict[str, Any]) -> str:
    selected_next = safe_fooddb_handoff_next_slice(artifact.get("selected_next_step"))
    if selected_next:
        return selected_next
    status = str(artifact.get("status") or "")
    defaults = {
        "blocked_contract_handoff_alignment": "repair_artifact_alignment_required",
        "fooddb_contract_unblocked": "grokfast_websearch_packet_live_diagnostic",
        "insufficient_contract_handoff_evidence": "inspect_fooddb_live_failure_taxonomy",
        "ready_for_manager_contract_owner": "tighten_fooddb_manager_contract_prompt_or_transport",
        "return_to_fooddb_packet_boundary": "narrow_fooddb_packet_boundary_or_prompt_probe",
    }
    return defaults.get(status, "inspect_contract_handoff_status")


__all__ = ["build_fooddb_manager_contract_handoff_inspection"]
