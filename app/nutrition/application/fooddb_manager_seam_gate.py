from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_manager_packet_smoke import build_fooddb_manager_packet_smoke
from .fooddb_retrieval_policy import build_runtime_retrieval_records_from_small_anchor_payload
from .grokfast_fooddb_packet_smoke import (
    build_fixture_manager_outputs,
    build_grokfast_fooddb_packet_diagnostic,
    build_packet_artifact_from_tool_evidence_result,
)
from .tool_evidence_result import build_tool_evidence_result


def build_fooddb_manager_seam_gate(*, small_anchor_payload: dict[str, Any]) -> dict[str, Any]:
    records = build_runtime_retrieval_records_from_small_anchor_payload(small_anchor_payload)
    packet_artifact = build_fooddb_manager_packet_smoke(retrieval_records=records)
    packets = tuple(
        case["manager_evidence_packet"]
        for case in packet_artifact["cases"]
        if isinstance(case.get("manager_evidence_packet"), dict)
    )
    tool_result = build_tool_evidence_result(
        tool_name="lookup_food_evidence",
        tool_call_id="tool-fooddb-manager-seam-gate",
        evidence_packets=packets,
        index_adapter={
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
            "record_count": len(records),
            "index_policy_version": "food_evidence_index_port_v1",
        },
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
        },
    )
    projected_packet_artifact = build_packet_artifact_from_tool_evidence_result(
        tool_evidence_artifact={
            "artifact_type": "accurate_intake_tool_evidence_result_smoke",
            "tool_evidence_result": tool_result,
        }
    )
    diagnostic = build_grokfast_fooddb_packet_diagnostic(
        packet_artifact=projected_packet_artifact,
        manager_outputs=build_fixture_manager_outputs(packet_artifact=projected_packet_artifact),
        live_provider_used=False,
    )
    checks = _checks(
        packet_artifact=packet_artifact,
        projected_packet_artifact=projected_packet_artifact,
        tool_result=tool_result,
        diagnostic=diagnostic,
    )
    pass_count = sum(1 for check in checks if check["status"] == "pass")
    status = "pass" if pass_count == len(checks) else "fail"

    return {
        "artifact_type": "accurate_intake_fooddb_manager_seam_gate",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "deterministic_manager_fooddb_packet_seam_gate",
        "status": status,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "tool_evidence_result_type": tool_result["result_type"],
        "diagnostic_artifact_type": diagnostic["artifact_type"],
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "pass_count": pass_count,
            "fail_count": len(checks) - pass_count,
            "packet_case_count": packet_artifact["summary"]["case_count"],
            "compact_packet_pass_count": packet_artifact["summary"]["compact_packet_pass_count"],
            "tool_packet_count": tool_result["trace"]["packet_count"],
            "diagnostic_pass_count": diagnostic["summary"]["pass_count"],
            "diagnostic_fail_count": diagnostic["summary"]["fail_count"],
            "next_allowed_slice": _next_allowed_slice(status),
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_mutation_authority_change",
            "no_packetizer_format_change",
            "no_manager_context_change",
            "no_product_loop_integration",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_readiness_claim",
        ],
    }


def _checks(
    *,
    packet_artifact: dict[str, Any],
    projected_packet_artifact: dict[str, Any],
    tool_result: dict[str, Any],
    diagnostic: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check(
            check_id="deterministic_packets_are_compact",
            passed=packet_artifact["summary"]["case_count"]
            == packet_artifact["summary"]["compact_packet_pass_count"],
            evidence="FoodDB manager packet smoke produced compact packets for every case.",
        ),
        _check(
            check_id="tool_result_remains_read_only",
            passed=tool_result.get("runtime_mutation_allowed") is False
            and tool_result.get("runtime_truth_changed") is False
            and tool_result.get("manager_context_changed") is False
            and tool_result.get("read_model_only") is True,
            evidence="ToolEvidenceResult is read-only and denies runtime mutation authority.",
        ),
        _check(
            check_id="tool_projection_hides_backend",
            passed=projected_packet_artifact["summary"]["tool_evidence_result_used"] is True
            and projected_packet_artifact["summary"]["source_implementation_visible"] is False,
            evidence="Manager packet projection uses ToolEvidenceResult without exposing index backend.",
        ),
        _check(
            check_id="fixture_manager_uses_packet_without_invention",
            passed=diagnostic["status"] == "pass"
            and diagnostic["summary"]["pass_count"] == diagnostic["summary"]["case_count"]
            and diagnostic["summary"]["fail_count"] == 0,
            evidence="Fixture manager outputs pass packet-use and no-invented-source diagnostics.",
        ),
        _check(
            check_id="live_provider_not_used",
            passed=diagnostic.get("live_provider_used") is False,
            evidence="This seam gate is deterministic; live GrokFast remains a later diagnostic slice.",
        ),
    ]


def _check(*, check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
    }


def _next_allowed_slice(status: str) -> str:
    if status == "pass":
        return "grokfast_fooddb_packet_live_diagnostic"
    return "fooddb_manager_packet_seam_smoke"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_manager_seam_gate"]
