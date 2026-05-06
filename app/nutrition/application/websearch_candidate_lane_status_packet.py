from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .tool_evidence_result import build_tool_evidence_result
from .web_search_candidate_producer import MAX_WEBSEARCH_RESULTS_HARD_CAP
from .websearch_candidate_packet_smoke import build_websearch_candidate_packet_smoke
from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic
from .websearch_candidate_lane_handoff_gate import compact_websearch_manager_contract_gate
from .websearch_manager_packet_smoke import build_websearch_manager_packet_projection
from .websearch_source_adapter_guard import build_websearch_source_adapter_guard
from .websearch_source_policy import build_websearch_source_policy_artifact


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
    live_diagnostic_report: dict[str, Any] | None = None,
    contract_probe_artifact: dict[str, Any] | None = None,
    repair_pack_artifact: dict[str, Any] | None = None,
    preflight_artifact: dict[str, Any] | None = None,
    source_adapter_guard_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_policy = build_websearch_source_policy_artifact()
    source_adapter_guard = (
        build_websearch_source_adapter_guard()
        if source_adapter_guard_artifact is None
        else source_adapter_guard_artifact
    )
    candidate_pipeline = build_websearch_candidate_pipeline_diagnostic()
    candidate_packet_artifact = build_websearch_candidate_packet_smoke()
    tool_evidence_artifact = _build_tool_evidence_artifact(candidate_packet_artifact)
    manager_projection = build_websearch_manager_packet_projection(
        tool_evidence_artifact=tool_evidence_artifact
    )
    upstream_gate = _compact_fooddb_gate(fooddb_status_packet)
    manager_contract_gate = compact_websearch_manager_contract_gate(
        manager_contract_handoff_artifact=manager_contract_handoff_artifact,
        live_diagnostic_report=live_diagnostic_report,
        contract_probe_artifact=contract_probe_artifact,
        repair_pack_artifact=repair_pack_artifact,
        preflight_artifact=preflight_artifact,
    )
    source_adapter_gate = _compact_source_adapter_gate(source_adapter_guard)

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
            "source_adapter_guard_status": source_adapter_gate["status"],
            "source_adapter_guard_case_count": source_adapter_gate["case_count"],
            "source_adapter_guard_max_results_hard_cap": source_adapter_gate[
                "max_results_hard_cap"
            ],
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
        "source_adapter_gate": source_adapter_gate,
        "upstream_gate": upstream_gate,
        "manager_contract_gate": manager_contract_gate,
        "next_required_slices": _next_required_slices(
            source_adapter_gate=source_adapter_gate,
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


def _compact_source_adapter_gate(source_adapter_guard: dict[str, Any]) -> dict[str, Any]:
    if (
        str(source_adapter_guard.get("artifact_type") or "")
        != "accurate_intake_websearch_source_adapter_guard_v1"
    ):
        raise ValueError("unsupported_websearch_status_source_adapter_guard")
    summary = dict(source_adapter_guard.get("summary") or {})
    blockers = list(source_adapter_guard.get("blockers") or [])
    status = str(source_adapter_guard.get("status") or "blocked")
    case_count = _safe_non_negative_int(summary.get("case_count"))
    truth_field_leak_count = _safe_non_negative_int(summary.get("truth_field_leak_count"))
    max_results_hard_cap = _safe_non_negative_int(summary.get("max_results_hard_cap"))
    blocked = (
        status != "pass"
        or bool(blockers)
        or case_count <= 0
        or truth_field_leak_count != 0
        or max_results_hard_cap != MAX_WEBSEARCH_RESULTS_HARD_CAP
        or source_adapter_guard.get("live_provider_used") is not False
        or source_adapter_guard.get("live_websearch_used") is not False
        or source_adapter_guard.get("readiness_claimed") is not False
        or source_adapter_guard.get("runtime_truth_changed") is not False
        or source_adapter_guard.get("mutation_changed") is not False
    )
    return {
        "status": "pass" if not blocked else "blocked_on_source_adapter_guard",
        "next_required_slice": (
            "inspect_websearch_source_adapter_guard"
            if blocked
            else "websearch_candidate_lane_status_packet"
        ),
        "blocked": blocked,
        "case_count": case_count,
        "truth_field_leak_count": truth_field_leak_count,
        "max_results_hard_cap": max_results_hard_cap,
    }


def _safe_fooddb_next_slice(value: Any) -> str | None:
    text = str(value or "").strip()
    if text in _ALLOWED_FOODDB_NEXT_SLICES:
        return text
    return "inspect_fooddb_status_packet"


def _next_required_slices(
    *,
    source_adapter_gate: dict[str, Any],
    upstream_gate: dict[str, Any],
    manager_contract_gate: dict[str, Any],
) -> list[str]:
    if source_adapter_gate["blocked"]:
        return [
            str(
                source_adapter_gate["next_required_slice"]
                or "inspect_websearch_source_adapter_guard"
            )
        ]
    if upstream_gate["blocked"]:
        return [str(upstream_gate["next_required_slice"] or "inspect_fooddb_status_packet")]
    if manager_contract_gate["blocked"]:
        return [str(manager_contract_gate["next_required_slice"] or "inspect_websearch_manager_contract_handoff")]
    return ["grokfast_websearch_packet_live_diagnostic"]


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


__all__ = ["build_websearch_candidate_lane_status_packet"]
