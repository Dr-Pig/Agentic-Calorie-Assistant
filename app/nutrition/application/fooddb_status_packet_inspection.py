from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_integration_readiness_matrix import build_fooddb_integration_readiness_matrix

_EXPECTED_STATUS_PACKET = "accurate_intake_fooddb_evidence_status_packet_v1"
_EXPECTED_LIVE_RUNNER = "accurate_intake_grokfast_fooddb_live_runner_readiness_packet_v1"
_EXPECTED_CONTRACT_HANDOFF = "accurate_intake_fooddb_manager_contract_handoff_v1"
_EXPECTED_LIVE_RUNNER_NEXT = "run_explicit_grokfast_fooddb_packet_live_diagnostic"
_ALLOWED_NEXT_SLICES = {
    "await_manager_contract_owner_repair",
    "common_serving_anchor_expansion",
    "grokfast_fooddb_packet_live_diagnostic",
    "grokfast_websearch_packet_live_diagnostic",
    "inspect_contract_handoff_status",
    "listed_component_anchor_expansion",
    "manager_fooddb_packet_seam_smoke",
    "packet_to_mutation_guard_hardening",
    "repair_artifact_alignment_required",
}


def build_fooddb_status_packet_inspection(
    *,
    fooddb_status_packet: dict[str, Any],
    live_runner_readiness_artifact: dict[str, Any] | None = None,
    contract_handoff_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = _status_packet_blockers(fooddb_status_packet)
    next_safe_slice = _safe_next_slice(fooddb_status_packet)
    live_runner_status = None
    live_runner_next_slice = None
    contract_handoff_status = None
    contract_handoff_next_step = None

    if live_runner_readiness_artifact is not None:
        live_runner_status = str(live_runner_readiness_artifact.get("status") or "").strip() or None
        live_runner_next_slice = (
            str(live_runner_readiness_artifact.get("next_required_slice") or "").strip() or None
        )
        blockers.extend(_live_runner_blockers(live_runner_readiness_artifact))
    if contract_handoff_artifact is not None:
        contract_handoff_status = str(contract_handoff_artifact.get("status") or "").strip() or None
        contract_handoff_next_step = (
            str(contract_handoff_artifact.get("selected_next_step") or "").strip() or None
        )
        blockers.extend(_contract_handoff_blockers(contract_handoff_artifact))

    if next_safe_slice == "grokfast_fooddb_packet_live_diagnostic":
        if live_runner_status and live_runner_status != "pass":
            blockers.append("live_runner_readiness_not_clear_for_fooddb_live_diagnostic")
        if live_runner_next_slice and live_runner_next_slice != _EXPECTED_LIVE_RUNNER_NEXT:
            blockers.append("live_runner_next_slice_mismatch")
    elif next_safe_slice == "grokfast_websearch_packet_live_diagnostic":
        if contract_handoff_status != "fooddb_contract_unblocked":
            blockers.append("contract_handoff_not_unblocked_for_websearch_live_diagnostic")
    elif next_safe_slice == "await_manager_contract_owner_repair":
        if contract_handoff_status != "ready_for_manager_contract_owner":
            blockers.append("contract_handoff_not_ready_for_manager_owner")
        if contract_handoff_artifact is not None and contract_handoff_artifact.get("handoff_ready") is not True:
            blockers.append("contract_handoff_ready_flag_missing")
    elif next_safe_slice == "repair_artifact_alignment_required":
        if contract_handoff_status and contract_handoff_status != "blocked_contract_handoff_alignment":
            blockers.append("contract_handoff_alignment_status_mismatch")

    integration_matrix = build_fooddb_integration_readiness_matrix()
    return {
        "artifact_type": "accurate_intake_fooddb_status_packet_inspection_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "deterministic_fooddb_status_packet_inspection_only",
        "claim_scope": "fooddb_status_packet_alignment_without_runtime_truth",
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "status_packet_next_required_slice": next_safe_slice,
            "live_runner_status": live_runner_status,
            "live_runner_next_required_slice": live_runner_next_slice,
            "contract_handoff_status": contract_handoff_status,
            "contract_handoff_selected_next_step": contract_handoff_next_step,
            "integration_edge_count": len(integration_matrix["check_edges"]),
            "next_safe_slice": next_safe_slice,
        },
        "source_refs": {
            "fooddb_status_packet_type": fooddb_status_packet.get("artifact_type"),
            "live_runner_readiness_type": None
            if live_runner_readiness_artifact is None
            else live_runner_readiness_artifact.get("artifact_type"),
            "contract_handoff_type": None
            if contract_handoff_artifact is None
            else contract_handoff_artifact.get("artifact_type"),
            "integration_matrix_type": integration_matrix["artifact_type"],
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _status_packet_blockers(artifact: dict[str, Any]) -> list[str]:
    return _artifact_boundary_blockers(
        artifact,
        expected_type=_EXPECTED_STATUS_PACKET,
        mutation_key="mutation_changed",
        live_keys=("live_provider_used", "live_websearch_used"),
        prefix="fooddb_status_packet",
    )


def _live_runner_blockers(artifact: dict[str, Any]) -> list[str]:
    return _artifact_boundary_blockers(
        artifact,
        expected_type=_EXPECTED_LIVE_RUNNER,
        mutation_key="runtime_mutation_allowed",
        live_keys=("live_provider_used", "live_websearch_used"),
        prefix="live_runner_readiness",
    )


def _contract_handoff_blockers(artifact: dict[str, Any]) -> list[str]:
    blockers = _artifact_boundary_blockers(
        artifact,
        expected_type=_EXPECTED_CONTRACT_HANDOFF,
        mutation_key="runtime_mutation_attempted",
        live_keys=(),
        prefix="contract_handoff",
    )
    if artifact.get("readiness_claimed") is not False:
        blockers.append("contract_handoff_claimed_readiness")
    return blockers


def _artifact_boundary_blockers(
    artifact: dict[str, Any],
    *,
    expected_type: str,
    mutation_key: str,
    live_keys: tuple[str, ...],
    prefix: str,
) -> list[str]:
    if str(artifact.get("artifact_type") or "") != expected_type:
        return [f"unsupported_{prefix}_artifact"]
    blockers: list[str] = []
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append(f"{prefix}_changed_runtime_truth")
    if artifact.get(mutation_key) is not False:
        blockers.append(f"{prefix}_changed_runtime_mutation")
    if "shared_contract_changed" in artifact and artifact.get("shared_contract_changed") is not False:
        blockers.append(f"{prefix}_changed_shared_contract")
    for key in live_keys:
        if key in artifact and artifact.get(key) is not False:
            blockers.append(f"{prefix}_used_{key.removesuffix('_used')}")
    return blockers


def _safe_next_slice(fooddb_status_packet: dict[str, Any]) -> str:
    next_required_slices = list(fooddb_status_packet.get("next_required_slices") or [])
    text = str(next_required_slices[0] or "").strip() if next_required_slices else ""
    return text if text in _ALLOWED_NEXT_SLICES else "inspect_fooddb_status_packet"


__all__ = ["build_fooddb_status_packet_inspection"]
