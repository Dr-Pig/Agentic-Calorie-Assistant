from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .websearch_integration_readiness_matrix import (
    build_websearch_integration_readiness_matrix,
)

_EXPECTED_STATUS_PACKET = "accurate_intake_websearch_evidence_status_packet_v1"
_EXPECTED_ROUTER_READINESS = "accurate_intake_food_evidence_retriever_router_readiness_v1"
_EXPECTED_EXACT_CHAIN = "accurate_intake_websearch_exact_candidate_chain_status_v1"
_EXPECTED_LIVE_RUNNER_READINESS = "accurate_intake_websearch_live_runner_readiness_packet_v1"
_ALLOWED_NEXT_SLICES = {
    "grokfast_fooddb_packet_live_diagnostic",
    "inspect_fooddb_status_packet",
    "inspect_websearch_exact_candidate_chain_status",
    "inspect_websearch_manager_contract_handoff",
    "inspect_websearch_status_packet",
    "websearch_candidate_pipeline_narrow_expansion",
}


def build_websearch_status_packet_inspection(
    *,
    websearch_status_packet: dict[str, Any],
    router_readiness_artifact: dict[str, Any] | None = None,
    exact_candidate_chain_status_artifact: dict[str, Any] | None = None,
    live_runner_readiness_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = _status_packet_blockers(websearch_status_packet)
    next_safe_slice = _safe_next_slice(websearch_status_packet)
    router_next_slice = None
    live_runner_next_slice = None

    if router_readiness_artifact is not None:
        router_next_slice = str(
            dict(router_readiness_artifact.get("summary") or {}).get("next_required_slice") or ""
        ).strip() or None
        blockers.extend(_router_blockers(router_readiness_artifact, expected_next="inspect_websearch_status_packet"))
    if exact_candidate_chain_status_artifact is not None:
        blockers.extend(_artifact_boundary_blockers(
            exact_candidate_chain_status_artifact,
            expected_type=_EXPECTED_EXACT_CHAIN,
            runtime_mutation_key="runtime_mutation_allowed",
            live_keys=("live_websearch_used", "live_extract_used", "live_provider_used"),
            prefix="exact_candidate_chain_status",
        ))
    if live_runner_readiness_artifact is not None:
        live_runner_next_slice = str(live_runner_readiness_artifact.get("next_required_slice") or "").strip() or None
        blockers.extend(_artifact_boundary_blockers(
            live_runner_readiness_artifact,
            expected_type=_EXPECTED_LIVE_RUNNER_READINESS,
            runtime_mutation_key="runtime_mutation_allowed",
            live_keys=("live_websearch_used", "live_extract_used", "live_provider_used"),
            prefix="live_runner_readiness",
        ))

    if next_safe_slice == "websearch_candidate_pipeline_narrow_expansion":
        if router_next_slice and router_next_slice != "inspect_websearch_status_packet":
            blockers.append("router_readiness_next_slice_mismatch")
        if exact_candidate_chain_status_artifact is not None and exact_candidate_chain_status_artifact.get("status") != "pass":
            blockers.append("exact_candidate_chain_status_not_clear_for_narrow_expansion")
        if live_runner_readiness_artifact is not None and live_runner_readiness_artifact.get("status") != "pass":
            blockers.append("live_runner_readiness_not_clear_for_narrow_expansion")

    integration_matrix = build_websearch_integration_readiness_matrix()
    return {
        "artifact_type": "accurate_intake_websearch_status_packet_inspection_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "deterministic_websearch_status_packet_inspection_only",
        "claim_scope": "websearch_status_packet_alignment_without_runtime_truth",
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
            "router_next_required_slice": router_next_slice,
            "live_runner_next_required_slice": live_runner_next_slice,
            "integration_edge_count": len(integration_matrix["check_edges"]),
            "next_safe_slice": next_safe_slice,
        },
        "source_refs": {
            "websearch_status_packet_type": websearch_status_packet.get("artifact_type"),
            "router_readiness_type": None if router_readiness_artifact is None else router_readiness_artifact.get("artifact_type"),
            "exact_candidate_chain_status_type": None if exact_candidate_chain_status_artifact is None else exact_candidate_chain_status_artifact.get("artifact_type"),
            "live_runner_readiness_type": None if live_runner_readiness_artifact is None else live_runner_readiness_artifact.get("artifact_type"),
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


def _status_packet_blockers(websearch_status_packet: dict[str, Any]) -> list[str]:
    blockers = _artifact_boundary_blockers(
        websearch_status_packet,
        expected_type=_EXPECTED_STATUS_PACKET,
        runtime_mutation_key="mutation_changed",
        live_keys=("live_provider_used", "live_websearch_used"),
        prefix="websearch_status_packet",
    )
    summary = dict(websearch_status_packet.get("summary") or {})
    candidate_next = str(summary.get("candidate_lane_next_required_slice") or "").strip()
    if candidate_next != "inspect_websearch_status_packet":
        blockers.append("websearch_status_packet_candidate_lane_not_clear_for_inspection")
    return blockers


def _router_blockers(router_artifact: dict[str, Any], *, expected_next: str) -> list[str]:
    blockers = _artifact_boundary_blockers(
        router_artifact,
        expected_type=_EXPECTED_ROUTER_READINESS,
        runtime_mutation_key="mutation_changed",
        live_keys=("live_provider_used", "live_websearch_used"),
        prefix="router_readiness",
    )
    summary = dict(router_artifact.get("summary") or {})
    if str(summary.get("next_required_slice") or "").strip() != expected_next:
        blockers.append("router_readiness_next_slice_mismatch")
    return blockers


def _artifact_boundary_blockers(
    artifact: dict[str, Any],
    *,
    expected_type: str,
    runtime_mutation_key: str,
    live_keys: tuple[str, ...],
    prefix: str,
) -> list[str]:
    blockers: list[str] = []
    if str(artifact.get("artifact_type") or "") != expected_type:
        return [f"unsupported_{prefix}_artifact"]
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append(f"{prefix}_changed_runtime_truth")
    if artifact.get(runtime_mutation_key) is not False:
        blockers.append(f"{prefix}_changed_runtime_mutation")
    if artifact.get("shared_contract_changed") is not False:
        blockers.append(f"{prefix}_changed_shared_contract")
    if artifact.get("manager_context_changed") is not False:
        blockers.append(f"{prefix}_changed_manager_context")
    if artifact.get("readiness_claimed") is not False:
        blockers.append(f"{prefix}_claimed_readiness")
    for key in live_keys:
        if artifact.get(key) is not False:
            blockers.append(f"{prefix}_used_{key.removesuffix('_used')}")
    return blockers


def _safe_next_slice(websearch_status_packet: dict[str, Any]) -> str:
    next_required_slices = list(websearch_status_packet.get("next_required_slices") or [])
    text = str(next_required_slices[0] or "").strip() if next_required_slices else ""
    return text if text in _ALLOWED_NEXT_SLICES else "inspect_websearch_status_packet"


__all__ = ["build_websearch_status_packet_inspection"]
