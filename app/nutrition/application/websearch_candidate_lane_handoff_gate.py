from __future__ import annotations

from typing import Any

from .websearch_candidate_lane_handoff_proof import (
    handoff_proof,
    safe_manager_contract_next_slice,
    unblocked_handoff_shape_blockers,
)
from .websearch_candidate_lane_source_chain_guard import source_chain_blockers
from .websearch_manager_contract_handoff import build_websearch_manager_contract_handoff


def compact_websearch_manager_contract_gate(
    *,
    manager_contract_handoff_artifact: dict[str, Any] | None,
    live_diagnostic_report: dict[str, Any] | None = None,
    contract_probe_artifact: dict[str, Any] | None = None,
    repair_pack_artifact: dict[str, Any] | None = None,
    preflight_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(manager_contract_handoff_artifact, dict):
        return _gate("not_provided", "inspect_websearch_manager_contract_handoff", True)
    if (
        str(manager_contract_handoff_artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_manager_contract_handoff_v1"
    ):
        raise ValueError("unsupported_websearch_status_manager_contract_handoff")

    status = str(manager_contract_handoff_artifact.get("status") or "")
    selected_next_step = safe_manager_contract_next_slice(
        manager_contract_handoff_artifact.get("selected_next_step")
    )
    if status == "websearch_contract_unblocked":
        blockers = _verified_unblocked_handoff_blockers(
            manager_contract_handoff_artifact=manager_contract_handoff_artifact,
            live_diagnostic_report=live_diagnostic_report,
            contract_probe_artifact=contract_probe_artifact,
            repair_pack_artifact=repair_pack_artifact,
            preflight_artifact=preflight_artifact,
        )
        if blockers:
            return _gate(
                "blocked_on_manager_contract_handoff",
                "inspect_websearch_manager_contract_handoff",
                True,
                blockers,
            )
        return _gate("clear_for_websearch_lane", selected_next_step or None, False)
    if status == "ready_for_manager_contract_owner":
        return _gate(
            "blocked_on_manager_contract_owner",
            selected_next_step or "tighten_websearch_manager_contract_prompt_or_transport",
            True,
        )
    if status == "return_to_websearch_packet_boundary":
        return _gate(
            "blocked_on_websearch_packet_boundary",
            selected_next_step or "narrow_websearch_packet_boundary_or_prompt_probe",
            True,
        )
    return _gate(
        "blocked_on_manager_contract_handoff",
        selected_next_step or "inspect_websearch_manager_contract_handoff",
        True,
    )


def _verified_unblocked_handoff_blockers(
    *,
    manager_contract_handoff_artifact: dict[str, Any],
    live_diagnostic_report: dict[str, Any] | None,
    contract_probe_artifact: dict[str, Any] | None,
    repair_pack_artifact: dict[str, Any] | None,
    preflight_artifact: dict[str, Any] | None,
) -> list[str]:
    blockers = unblocked_handoff_shape_blockers(manager_contract_handoff_artifact)
    if not all(
        isinstance(artifact, dict)
        for artifact in (
            live_diagnostic_report,
            contract_probe_artifact,
            repair_pack_artifact,
            preflight_artifact,
        )
    ):
        blockers.append("manager_contract_handoff_source_artifacts_missing")
        return blockers
    blockers.extend(
        source_chain_blockers(
            contract_probe_artifact=contract_probe_artifact,  # type: ignore[arg-type]
            repair_pack_artifact=repair_pack_artifact,  # type: ignore[arg-type]
            manager_contract_handoff_artifact=manager_contract_handoff_artifact,
        )
    )
    try:
        derived = build_websearch_manager_contract_handoff(
            live_diagnostic_report=live_diagnostic_report,  # type: ignore[arg-type]
            contract_probe_artifact=contract_probe_artifact,  # type: ignore[arg-type]
            repair_pack_artifact=repair_pack_artifact,  # type: ignore[arg-type]
            preflight_artifact=preflight_artifact,  # type: ignore[arg-type]
        )
    except ValueError:
        blockers.append("manager_contract_handoff_source_artifacts_invalid")
        return blockers
    if handoff_proof(manager_contract_handoff_artifact) != handoff_proof(derived):
        blockers.append("manager_contract_handoff_derivation_mismatch")
    return blockers


def _gate(
    status: str,
    next_required_slice: str | None,
    blocked: bool,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "next_required_slice": next_required_slice,
        "blocked": blocked,
        "blockers": sorted(set(blockers or [])),
    }


__all__ = ["compact_websearch_manager_contract_gate"]
