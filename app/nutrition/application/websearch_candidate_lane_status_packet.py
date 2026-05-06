from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .tool_evidence_result import build_tool_evidence_result
from .websearch_candidate_packet_smoke import build_websearch_candidate_packet_smoke
from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic
from .websearch_manager_packet_smoke import build_websearch_manager_packet_projection
from .websearch_source_policy import build_websearch_source_policy_artifact


_ALLOWED_MANAGER_CONTRACT_NEXT_SLICES = {
    "inspect_websearch_manager_contract_handoff",
    "narrow_websearch_packet_boundary_or_prompt_probe",
    "tighten_websearch_manager_contract_prompt_or_transport",
    "websearch_candidate_pipeline_narrow_expansion",
}
_ALLOWED_FOODDB_NEXT_SLICES = {
    "await_manager_contract_owner_repair",
    "common_serving_anchor_expansion",
    "grokfast_fooddb_packet_live_diagnostic",
    "grokfast_websearch_packet_live_diagnostic",
    "inspect_fooddb_status_packet",
    "manager_fooddb_packet_seam_smoke",
}


def build_websearch_candidate_lane_status_packet(
    *,
    fooddb_status_packet: dict[str, Any] | None = None,
    manager_contract_handoff_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_policy = build_websearch_source_policy_artifact()
    candidate_pipeline = build_websearch_candidate_pipeline_diagnostic()
    candidate_packet_artifact = build_websearch_candidate_packet_smoke()
    tool_evidence_artifact = _build_tool_evidence_artifact(candidate_packet_artifact)
    manager_projection = build_websearch_manager_packet_projection(
        tool_evidence_artifact=tool_evidence_artifact
    )
    upstream_gate = _compact_fooddb_gate(fooddb_status_packet)
    manager_contract_gate = _compact_manager_contract_gate(manager_contract_handoff_artifact)

    return {
        "artifact_type": "accurate_intake_websearch_candidate_lane_status_packet_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_websearch_candidate_lane_status_only",
        "claim_scope": "websearch_candidate_lane_readiness_without_live_probe",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "source_policy_max_search_attempts": source_policy["max_search_attempts"],
            "source_policy_max_results": source_policy["rate_policy"]["max_results"],
            "pipeline_case_count": candidate_pipeline["summary"]["case_count"],
            "extract_candidate_allowed_count": candidate_pipeline["summary"][
                "extract_candidate_allowed_count"
            ],
            "candidate_packet_case_count": candidate_packet_artifact["summary"]["case_count"],
            "candidate_only_packet_count": candidate_packet_artifact["summary"]["candidate_only_count"],
            "manager_projection_case_count": manager_projection["summary"]["case_count"],
            "manager_projection_compact_count": sum(
                1 for case in manager_projection["cases"] if case["compact_manager_packet"] is True
            ),
            "upstream_fooddb_gate_status": upstream_gate["status"],
            "upstream_fooddb_next_required_slice": upstream_gate["next_required_slice"],
            "manager_contract_gate_status": manager_contract_gate["status"],
            "manager_contract_next_required_slice": manager_contract_gate["next_required_slice"],
        },
        "upstream_gate": upstream_gate,
        "manager_contract_gate": manager_contract_gate,
        "next_required_slices": _next_required_slices(
            upstream_gate=upstream_gate,
            manager_contract_gate=manager_contract_gate,
        ),
        "non_claims": [
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_readiness_claim",
        ],
    }


def _build_tool_evidence_artifact(packet_artifact: dict[str, Any]) -> dict[str, Any]:
    packets = tuple(case["websearch_candidate_packet"] for case in packet_artifact["cases"])
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id="tool-call-websearch-lane-status",
        evidence_packets=packets,
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
            "live_websearch_used": False,
        },
    )
    return {
        "artifact_type": "accurate_intake_websearch_tool_evidence_result_smoke",
        "tool_evidence_result": tool_result,
    }


def _compact_fooddb_gate(fooddb_status_packet: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(fooddb_status_packet, dict):
        return {
            "status": "not_provided",
            "next_required_slice": "inspect_fooddb_status_packet",
            "blocked": True,
        }
    if (
        str(fooddb_status_packet.get("artifact_type") or "")
        != "accurate_intake_fooddb_evidence_status_packet_v1"
    ):
        raise ValueError("unsupported_websearch_status_fooddb_packet")
    next_required_slices = list(fooddb_status_packet.get("next_required_slices") or [])
    next_required_slice = (
        _safe_fooddb_next_slice(next_required_slices[0]) if next_required_slices else None
    )
    allowed_next_slice = next_required_slice == "grokfast_websearch_packet_live_diagnostic"
    blocked = not allowed_next_slice
    return {
        "status": (
            "clear_for_websearch_lane"
            if allowed_next_slice
            else "blocked_on_fooddb_upstream_gate"
        ),
        "next_required_slice": next_required_slice,
        "blocked": blocked,
    }


def _safe_fooddb_next_slice(value: Any) -> str | None:
    text = str(value or "").strip()
    if text in _ALLOWED_FOODDB_NEXT_SLICES:
        return text
    return "inspect_fooddb_status_packet"


def _compact_manager_contract_gate(
    manager_contract_handoff_artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(manager_contract_handoff_artifact, dict):
        return {
            "status": "not_provided",
            "next_required_slice": "inspect_websearch_manager_contract_handoff",
            "blocked": True,
        }
    if (
        str(manager_contract_handoff_artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_manager_contract_handoff_v1"
    ):
        raise ValueError("unsupported_websearch_status_manager_contract_handoff")
    status = str(manager_contract_handoff_artifact.get("status") or "")
    selected_next_step = _safe_manager_contract_next_slice(
        manager_contract_handoff_artifact.get("selected_next_step")
    )
    if status == "websearch_contract_unblocked":
        return {
            "status": "clear_for_websearch_lane",
            "next_required_slice": selected_next_step or None,
            "blocked": False,
        }
    if status == "ready_for_manager_contract_owner":
        return {
            "status": "blocked_on_manager_contract_owner",
            "next_required_slice": selected_next_step or "tighten_websearch_manager_contract_prompt_or_transport",
            "blocked": True,
        }
    if status == "return_to_websearch_packet_boundary":
        return {
            "status": "blocked_on_websearch_packet_boundary",
            "next_required_slice": selected_next_step or "narrow_websearch_packet_boundary_or_prompt_probe",
            "blocked": True,
        }
    return {
        "status": "blocked_on_manager_contract_handoff",
        "next_required_slice": selected_next_step or "inspect_websearch_manager_contract_handoff",
        "blocked": True,
    }


def _safe_manager_contract_next_slice(value: Any) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_MANAGER_CONTRACT_NEXT_SLICES:
        return text
    return ""


def _next_required_slices(
    *,
    upstream_gate: dict[str, Any],
    manager_contract_gate: dict[str, Any],
) -> list[str]:
    if upstream_gate["blocked"]:
        return [str(upstream_gate["next_required_slice"] or "inspect_fooddb_status_packet")]
    if manager_contract_gate["blocked"]:
        return [str(manager_contract_gate["next_required_slice"] or "inspect_websearch_manager_contract_handoff")]
    return ["grokfast_websearch_packet_live_diagnostic"]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_candidate_lane_status_packet"]
