from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .exact_evidence_lane_status_packet import build_exact_evidence_lane_status_packet
from .websearch_candidate_lane_status_packet import build_websearch_candidate_lane_status_packet

_INSPECT_WEBSEARCH_STATUS = "inspect_websearch_status_packet"
_NARROW_EXPANSION = "websearch_candidate_pipeline_narrow_expansion"
_EXPECTED_CANDIDATE_ARTIFACT = "accurate_intake_websearch_candidate_lane_status_packet_v1"
_EXPECTED_EXACT_ARTIFACT = "accurate_intake_exact_evidence_lane_status_packet_v1"
_EXPECTED_HANDOFF_ARTIFACT = "accurate_intake_websearch_manager_contract_handoff_v1"
_ALLOWED_CANDIDATE_NEXT_SLICES = {
    "await_manager_contract_owner_repair",
    "grokfast_fooddb_packet_live_diagnostic",
    "grokfast_websearch_packet_live_diagnostic",
    "inspect_fooddb_status_packet",
    "inspect_websearch_manager_contract_handoff",
    _INSPECT_WEBSEARCH_STATUS,
}
_ALLOWED_EXACT_NEXT_SLICES = {
    "grokfast_websearch_packet_live_diagnostic",
    "inspect_websearch_exact_candidate_chain_status",
    _INSPECT_WEBSEARCH_STATUS,
}
_ALLOWED_HANDOFF_STATUSES = {
    "blocked_contract_handoff_alignment",
    "insufficient_contract_handoff_evidence",
    "ready_for_manager_contract_owner",
    "return_to_websearch_packet_boundary",
    "websearch_contract_unblocked",
}


def build_websearch_evidence_status_packet(
    *,
    candidate_lane_status_packet: dict[str, Any] | None = None,
    exact_lane_status_packet: dict[str, Any] | None = None,
    manager_contract_handoff_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    candidate_lane = (
        build_websearch_candidate_lane_status_packet()
        if candidate_lane_status_packet is None
        else candidate_lane_status_packet
    )
    _compact_candidate_lane(candidate_lane)
    exact_lane = (
        build_exact_evidence_lane_status_packet(websearch_status_packet=candidate_lane)
        if exact_lane_status_packet is None
        else exact_lane_status_packet
    )
    candidate_gate = _compact_candidate_lane(candidate_lane)
    exact_gate = _compact_exact_lane(exact_lane)
    handoff_gate = _compact_handoff(manager_contract_handoff_artifact)
    next_required_slices = _next_required_slices(
        candidate_gate=candidate_gate,
        exact_gate=exact_gate,
        handoff_gate=handoff_gate,
    )
    status = "pass" if candidate_gate["next_required_slice"] == _INSPECT_WEBSEARCH_STATUS else "blocked_on_candidate_lane"

    return {
        "artifact_type": "accurate_intake_websearch_evidence_status_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_websearch_evidence_status_only",
        "claim_scope": "websearch_candidate_exact_live_status_consolidation",
        "status": status,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "candidate_lane_status": candidate_gate["status"],
            "candidate_lane_next_required_slice": candidate_gate["next_required_slice"],
            "exact_lane_status": exact_gate["status"],
            "exact_lane_next_required_slice": exact_gate["next_required_slice"],
            "manager_contract_handoff_status": handoff_gate["status"],
            "manager_contract_selected_next_step": handoff_gate["selected_next_step"],
            "live_seam_status": handoff_gate["live_seam_status"],
        },
        "candidate_lane_gate": candidate_gate,
        "exact_lane_gate": exact_gate,
        "manager_contract_handoff_gate": handoff_gate,
        "next_required_slices": next_required_slices,
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _compact_candidate_lane(artifact: dict[str, Any]) -> dict[str, Any]:
    if str(artifact.get("artifact_type") or "") != _EXPECTED_CANDIDATE_ARTIFACT:
        raise ValueError("unsupported_websearch_evidence_status_candidate_lane")
    next_required_slices = list(artifact.get("next_required_slices") or [])
    next_required_slice = _safe_candidate_next_slice(
        next_required_slices[0] if next_required_slices else None
    )
    return {
        "status": str(artifact.get("classification") or "unknown"),
        "next_required_slice": next_required_slice,
    }


def _compact_exact_lane(artifact: dict[str, Any]) -> dict[str, Any]:
    if str(artifact.get("artifact_type") or "") != _EXPECTED_EXACT_ARTIFACT:
        raise ValueError("unsupported_websearch_evidence_status_exact_lane")
    next_required_slices = list(artifact.get("next_required_slices") or [])
    next_required_slice = _safe_exact_next_slice(
        next_required_slices[0] if next_required_slices else None
    )
    summary = dict(artifact.get("summary") or {})
    return {
        "status": str(summary.get("exact_candidate_chain_status") or "unknown"),
        "next_required_slice": next_required_slice,
    }


def _compact_handoff(artifact: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifact, dict):
        return {
            "status": "not_provided",
            "selected_next_step": None,
            "live_seam_status": "not_provided",
        }
    if str(artifact.get("artifact_type") or "") != _EXPECTED_HANDOFF_ARTIFACT:
        raise ValueError("unsupported_websearch_evidence_status_handoff")
    summary = dict(artifact.get("summary") or {})
    status = str(artifact.get("status") or "").strip()
    if status not in _ALLOWED_HANDOFF_STATUSES:
        status = "blocked_contract_handoff_alignment"
    selected_next_step = str(artifact.get("selected_next_step") or "").strip() or None
    return {
        "status": status,
        "selected_next_step": selected_next_step,
        "live_seam_status": str(summary.get("live_seam_status") or "unknown"),
    }


def _next_required_slices(
    *,
    candidate_gate: dict[str, Any],
    exact_gate: dict[str, Any],
    handoff_gate: dict[str, Any],
) -> list[str]:
    candidate_next = candidate_gate["next_required_slice"]
    if candidate_next != _INSPECT_WEBSEARCH_STATUS:
        return [candidate_next]
    exact_next = exact_gate["next_required_slice"]
    if exact_next and exact_next != "grokfast_websearch_packet_live_diagnostic":
        return [exact_next]
    if (
        exact_next == "grokfast_websearch_packet_live_diagnostic"
        and handoff_gate["status"] == "websearch_contract_unblocked"
    ):
        return [_NARROW_EXPANSION]
    if exact_next:
        return [exact_next]
    return [_INSPECT_WEBSEARCH_STATUS]


def _safe_candidate_next_slice(value: Any) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_CANDIDATE_NEXT_SLICES:
        return text
    return _INSPECT_WEBSEARCH_STATUS


def _safe_exact_next_slice(value: Any) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_EXACT_NEXT_SLICES:
        return text
    return _INSPECT_WEBSEARCH_STATUS


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_evidence_status_packet"]
