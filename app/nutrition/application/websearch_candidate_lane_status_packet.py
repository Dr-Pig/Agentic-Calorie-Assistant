from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .tool_evidence_result import build_tool_evidence_result
from .websearch_candidate_packet_smoke import build_websearch_candidate_packet_smoke
from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic
from .websearch_manager_packet_smoke import build_websearch_manager_packet_projection
from .websearch_source_policy import build_websearch_source_policy_artifact


def build_websearch_candidate_lane_status_packet(
    *,
    fooddb_status_packet: dict[str, Any] | None = None,
    live_diagnostic_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_policy = build_websearch_source_policy_artifact()
    candidate_pipeline = build_websearch_candidate_pipeline_diagnostic()
    candidate_packet_artifact = build_websearch_candidate_packet_smoke()
    tool_evidence_artifact = _build_tool_evidence_artifact(candidate_packet_artifact)
    manager_projection = build_websearch_manager_packet_projection(
        tool_evidence_artifact=tool_evidence_artifact
    )
    upstream_gate = _compact_fooddb_gate(fooddb_status_packet)
    live_diagnostic_gate = _compact_live_diagnostic_gate(
        live_diagnostic_report=live_diagnostic_report,
        upstream_gate=upstream_gate,
    )

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
            "grokfast_websearch_seam_status": live_diagnostic_gate["status"],
            "grokfast_websearch_can_expand": live_diagnostic_gate["can_expand"],
            "grokfast_websearch_next_required_slice": live_diagnostic_gate[
                "next_required_slice"
            ],
        },
        "upstream_gate": upstream_gate,
        "live_diagnostic_gate": live_diagnostic_gate,
        "next_required_slices": _next_required_slices(
            upstream_gate=upstream_gate,
            live_diagnostic_gate=live_diagnostic_gate,
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
    next_required_slice = str(next_required_slices[0] or "").strip() if next_required_slices else None
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


def _compact_live_diagnostic_gate(
    *,
    live_diagnostic_report: dict[str, Any] | None,
    upstream_gate: dict[str, Any],
) -> dict[str, Any]:
    if upstream_gate["blocked"]:
        return {
            "status": "not_checked_upstream_blocked",
            "next_required_slice": upstream_gate["next_required_slice"],
            "blocked": True,
            "can_expand": False,
        }
    if not isinstance(live_diagnostic_report, dict):
        return {
            "status": "not_provided",
            "next_required_slice": "run_explicit_grokfast_websearch_packet_live_diagnostic",
            "blocked": True,
            "can_expand": False,
        }
    if (
        str(live_diagnostic_report.get("artifact_type") or "")
        != "accurate_intake_websearch_live_diagnostic_report"
    ):
        raise ValueError("unsupported_websearch_status_live_diagnostic_report")
    if (
        live_diagnostic_report.get("source_live_websearch_used") is True
        or live_diagnostic_report.get("live_websearch_used") is True
        or live_diagnostic_report.get("runtime_truth_changed") is True
        or live_diagnostic_report.get("readiness_claimed") is True
    ):
        return {
            "status": "unsupported_live_diagnostic_boundary",
            "next_required_slice": "inspect_websearch_live_diagnostic_report",
            "blocked": True,
            "can_expand": False,
        }
    if (
        live_diagnostic_report.get("provider_contract_blocked") is True
        or live_diagnostic_report.get("provider_runtime_residual_blocked") is True
        or live_diagnostic_report.get("candidate_boundary_blocked") is True
    ):
        return {
            "status": "blocked_live_diagnostic_report",
            "next_required_slice": str(
                live_diagnostic_report.get("next_recommended_slice")
                or "inspect_websearch_live_diagnostic_report"
            ),
            "blocked": True,
            "can_expand": False,
        }
    can_expand = live_diagnostic_report.get("can_expand_websearch_candidate_pipeline") is True
    seam_status = str(live_diagnostic_report.get("seam_status") or "").strip()
    if seam_status == "live_diagnostic_pass" and can_expand:
        return {
            "status": seam_status,
            "next_required_slice": "websearch_live_search_preflight_or_candidate_source_adapter",
            "blocked": False,
            "can_expand": True,
        }
    return {
        "status": seam_status or "live_diagnostic_report_blocked",
        "next_required_slice": str(
            live_diagnostic_report.get("next_recommended_slice")
            or "inspect_websearch_live_diagnostic_report"
        ),
        "blocked": True,
        "can_expand": False,
    }


def _next_required_slices(
    *,
    upstream_gate: dict[str, Any],
    live_diagnostic_gate: dict[str, Any],
) -> list[str]:
    if upstream_gate["blocked"]:
        return [str(upstream_gate["next_required_slice"] or "inspect_fooddb_status_packet")]
    if live_diagnostic_gate["blocked"]:
        return [
            str(
                live_diagnostic_gate["next_required_slice"]
                or "run_explicit_grokfast_websearch_packet_live_diagnostic"
            )
        ]
    return ["websearch_live_search_preflight_or_candidate_source_adapter"]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_websearch_candidate_lane_status_packet"]
