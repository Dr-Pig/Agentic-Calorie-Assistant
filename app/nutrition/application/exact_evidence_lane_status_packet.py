from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .exact_evidence_lane_policy import build_exact_evidence_lane_policy_artifact

_ALLOWED_WEBSEARCH_GATE_STATUSES = {"clear_for_websearch_lane"}
_ALLOWED_WEBSEARCH_NEXT_SLICES = {
    "await_manager_contract_owner_repair",
    "grokfast_websearch_packet_live_diagnostic",
    "inspect_websearch_manager_contract_handoff",
    "inspect_websearch_status_packet",
    "narrow_websearch_packet_boundary_or_prompt_probe",
    "tighten_websearch_manager_contract_prompt_or_transport",
    "websearch_candidate_pipeline_narrow_expansion",
}


def build_exact_evidence_lane_status_packet(
    *,
    websearch_status_packet: dict[str, Any] | None = None,
    exact_candidate_chain_status_packet: dict[str, Any] | None = None,
) -> dict[str, Any]:
    lane_policy = build_exact_evidence_lane_policy_artifact()
    upstream_gate = _compact_websearch_gate(websearch_status_packet)
    exact_chain_gate = _compact_exact_candidate_chain_gate(
        exact_candidate_chain_status_packet
    )
    summary = lane_policy["summary"]

    return {
        "artifact_type": "accurate_intake_exact_evidence_lane_status_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_exact_evidence_lane_status_only",
        "claim_scope": "exact_evidence_lane_readiness_without_live_probe",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "local_exact_preferred_count": summary["local_exact_preferred_count"],
            "websearch_candidate_review_count": summary["websearch_candidate_review_count"],
            "no_exact_evidence_count": summary["no_exact_evidence_count"],
            "exact_card_staging_candidate_count": summary["exact_card_staging_candidate_count"],
            "upstream_websearch_gate_status": upstream_gate["status"],
            "upstream_websearch_next_required_slice": upstream_gate["next_required_slice"],
            "exact_candidate_chain_status": exact_chain_gate["status"],
            "exact_candidate_chain_next_required_slice": exact_chain_gate["next_required_slice"],
        },
        "upstream_gate": upstream_gate,
        "exact_candidate_chain_gate": exact_chain_gate,
        "next_required_slices": _next_required_slices(upstream_gate, exact_chain_gate),
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_packet_ready_truth",
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_readiness_claim",
        ],
    }


def _compact_websearch_gate(websearch_status_packet: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(websearch_status_packet, dict):
        return {
            "status": "not_provided",
            "next_required_slice": "inspect_websearch_status_packet",
            "blocked": True,
        }
    if (
        str(websearch_status_packet.get("artifact_type") or "")
        != "accurate_intake_websearch_candidate_lane_status_packet_v1"
    ):
        raise ValueError("unsupported_exact_lane_websearch_status_packet")
    upstream_gate = websearch_status_packet.get("upstream_gate")
    if not isinstance(upstream_gate, dict):
        return {
            "status": "blocked_websearch_gate_alignment",
            "next_required_slice": "inspect_websearch_status_packet",
            "blocked": True,
        }
    upstream_status = str(upstream_gate.get("status") or "").strip()
    next_required_slices = list(websearch_status_packet.get("next_required_slices") or [])
    next_required_slice = (
        _safe_websearch_next_slice(next_required_slices[0]) if next_required_slices else None
    )
    allowed_next_slice = next_required_slice == "grokfast_websearch_packet_live_diagnostic"
    allowed_upstream_status = upstream_status in _ALLOWED_WEBSEARCH_GATE_STATUSES
    aligned = allowed_next_slice and allowed_upstream_status
    blocked = not aligned
    if blocked and allowed_next_slice and not allowed_upstream_status:
        next_required_slice = "inspect_websearch_status_packet"
    return {
        "status": (
            "clear_for_exact_websearch_followthrough"
            if aligned
            else "blocked_on_websearch_upstream_gate"
            if next_required_slice
            else "blocked_websearch_gate_alignment"
        ),
        "next_required_slice": next_required_slice,
        "blocked": blocked,
    }


def _compact_exact_candidate_chain_gate(
    chain_status_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(chain_status_packet, dict):
        return {
            "status": "not_provided",
            "next_required_slice": "inspect_websearch_exact_candidate_chain_status",
            "blocked": True,
        }
    if (
        str(chain_status_packet.get("artifact_type") or "")
        != "accurate_intake_websearch_exact_candidate_chain_status_v1"
    ):
        raise ValueError("unsupported_exact_lane_candidate_chain_status_packet")
    if (
        chain_status_packet.get("status") == "pass"
        and chain_status_packet.get("ready_for_live_diagnostic") is True
        and chain_status_packet.get("ready_for_runtime_truth") is False
        and chain_status_packet.get("runtime_truth_changed") is False
        and chain_status_packet.get("runtime_mutation_allowed") is False
        and chain_status_packet.get("live_websearch_used") is False
        and chain_status_packet.get("live_extract_used") is False
        and chain_status_packet.get("live_provider_used") is False
        and chain_status_packet.get("readiness_claimed") is False
    ):
        return {
            "status": "clear_for_websearch_exact_candidate_chain",
            "next_required_slice": chain_status_packet.get("next_required_slice"),
            "blocked": False,
        }
    return {
        "status": "blocked_on_websearch_exact_candidate_chain",
        "next_required_slice": "inspect_websearch_exact_candidate_chain_status",
        "blocked": True,
    }


def _next_required_slices(
    upstream_gate: dict[str, Any],
    exact_chain_gate: dict[str, Any],
) -> list[str]:
    if upstream_gate["blocked"]:
        return [str(upstream_gate["next_required_slice"] or "inspect_websearch_status_packet")]
    if exact_chain_gate["blocked"]:
        return [
            str(
                exact_chain_gate["next_required_slice"]
                or "inspect_websearch_exact_candidate_chain_status"
            )
        ]
    return ["grokfast_websearch_packet_live_diagnostic"]


def _safe_websearch_next_slice(value: Any) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_WEBSEARCH_NEXT_SLICES:
        return text
    return "inspect_websearch_status_packet"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_exact_evidence_lane_status_packet"]
