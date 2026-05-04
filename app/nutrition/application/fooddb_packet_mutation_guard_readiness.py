from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Sequence

from .fooddb_manager_packet_smoke import build_fooddb_manager_packet_smoke
from .fooddb_retrieval_policy import IndexedFoodRecord
from .tool_evidence_result import build_tool_evidence_result


REQUIRED_TOOL_RESULT_FLAGS = {
    "runtime_mutation_allowed": False,
    "runtime_truth_changed": False,
    "manager_context_changed": False,
    "read_model_only": True,
    "source_implementation_visible": False,
}


def build_fooddb_packet_mutation_guard_readiness(
    *,
    retrieval_records: Sequence[IndexedFoodRecord],
) -> dict[str, Any]:
    packet_artifact = build_fooddb_manager_packet_smoke(
        retrieval_records=tuple(retrieval_records),
    )
    packets = tuple(
        case["manager_evidence_packet"]
        for case in packet_artifact["cases"]
        if isinstance(case.get("manager_evidence_packet"), dict)
    )
    tool_result = build_tool_evidence_result(
        tool_name="lookup_food_evidence",
        tool_call_id="tool-fooddb-packet-mutation-guard-readiness",
        evidence_packets=packets,
        index_adapter={
            "adapter_kind": "local_small_anchor_index",
            "storage_backend": "local_json",
            "record_count": len(retrieval_records),
            "index_policy_version": "food_evidence_index_port_v1",
        },
        trace_context={
            "packet_artifact_type": packet_artifact["artifact_type"],
            "packet_claim_scope": packet_artifact["claim_scope"],
        },
    )
    checks = _readiness_checks(packet_artifact=packet_artifact, tool_result=tool_result)
    negative_checks = _negative_mutation_authority_checks(packets)
    all_checks = [*checks, *negative_checks]
    pass_count = sum(1 for check in all_checks if check["status"] == "pass")

    return {
        "artifact_type": "accurate_intake_fooddb_packet_mutation_guard_readiness",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "packet_to_mutation_guard_contract_readiness",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "packet_artifact_type": packet_artifact["artifact_type"],
        "tool_evidence_result_type": tool_result["result_type"],
        "checks": all_checks,
        "summary": {
            "check_count": len(all_checks),
            "pass_count": pass_count,
            "fail_count": len(all_checks) - pass_count,
            "packet_count": tool_result["trace"]["packet_count"],
            "compact_packet_pass_count": tool_result["trace"]["compact_packet_pass_count"],
            "packet_to_mutation_guard_status": "contract_backed"
            if pass_count == len(all_checks)
            else "draft",
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_mutation_authority_change",
            "no_packetizer_format_change",
            "no_manager_context_change",
            "no_product_loop_integration",
            "no_live_provider_call",
            "no_readiness_claim",
        ],
    }


def _readiness_checks(
    *,
    packet_artifact: dict[str, Any],
    tool_result: dict[str, Any],
) -> list[dict[str, Any]]:
    cases = packet_artifact.get("cases") or []
    packets = tool_result.get("evidence_packets") or []
    return [
        _check(
            check_id="tool_result_is_read_only",
            passed=all(tool_result.get(key) is expected for key, expected in REQUIRED_TOOL_RESULT_FLAGS.items()),
            evidence="ToolEvidenceResult flags deny mutation, truth change, manager context change, and source implementation visibility.",
        ),
        _check(
            check_id="tool_result_declares_runtime_mutation_forbidden",
            passed="runtime_mutation" in set(tool_result.get("manager_must_not_use_for") or []),
            evidence="Manager-facing tool result keeps runtime mutation in manager_must_not_use_for.",
        ),
        _check(
            check_id="all_packets_deny_truth_selection_and_mutation",
            passed=all(
                isinstance(packet, dict)
                and packet.get("runtime_mutation_allowed") is False
                and packet.get("truth_selection_forbidden") is True
                for packet in packets
            ),
            evidence="Every compact packet denies runtime mutation and truth selection authority.",
        ),
        _check(
            check_id="bare_basket_packet_stays_followup_only",
            passed=_bare_basket_packet_stays_followup_only(cases),
            evidence="Bare basket cases carry no evidence_items and preserve followup/no-mutation posture.",
        ),
        _check(
            check_id="packet_projection_preserves_case_count",
            passed=len(packets) == len(cases) == tool_result["trace"]["packet_count"],
            evidence="ToolEvidenceResult projects one read-only packet per deterministic smoke case.",
        ),
        _check(
            check_id="source_implementation_hidden_from_manager",
            passed=tool_result.get("source_implementation_visible") is False
            and tool_result["trace"].get("source_implementation_manager_visible") is False,
            evidence="Adapter diagnostics are trace-local and hidden from manager-facing packets.",
        ),
    ]


def _negative_mutation_authority_checks(packets: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    if not packets:
        return [
            _check(
                check_id="negative_mutation_shortcut_rejected",
                passed=False,
                evidence="No packet available for negative mutation shortcut check.",
            )
        ]

    mutation_shortcut = deepcopy(packets[0])
    mutation_shortcut["runtime_mutation_allowed"] = True

    truth_selection_shortcut = deepcopy(packets[0])
    truth_selection_shortcut["truth_selection_forbidden"] = False

    return [
        _check(
            check_id="negative_mutation_shortcut_rejected",
            passed=_tool_result_rejects_packet(mutation_shortcut),
            evidence="ToolEvidenceResult rejects compact-looking packets that set runtime_mutation_allowed=true.",
        ),
        _check(
            check_id="negative_truth_selection_shortcut_rejected",
            passed=_tool_result_rejects_packet(truth_selection_shortcut),
            evidence="ToolEvidenceResult rejects compact-looking packets that allow deterministic truth selection.",
        ),
    ]


def _bare_basket_packet_stays_followup_only(cases: list[Any]) -> bool:
    bare_cases = [
        case
        for case in cases
        if isinstance(case, dict) and case.get("case_family") == "composition_unknown_self_selected_basket"
    ]
    return bool(bare_cases) and all(
        isinstance(case.get("manager_evidence_packet"), dict)
        and case["manager_evidence_packet"].get("retrieval_boundary")
        == "bare_basket_ask_followup_no_estimate"
        and case["manager_evidence_packet"].get("evidence_items") == []
        and case["manager_evidence_packet"].get("runtime_mutation_allowed") is False
        for case in bare_cases
    )


def _tool_result_rejects_packet(packet: dict[str, Any]) -> bool:
    try:
        build_tool_evidence_result(
            tool_name="lookup_food_evidence",
            tool_call_id="tool-fooddb-packet-negative-check",
            evidence_packets=(packet,),
            index_adapter={"adapter_kind": "local_small_anchor_index"},
        )
    except ValueError:
        return True
    return False


def _check(*, check_id: str, passed: bool, evidence: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "REQUIRED_TOOL_RESULT_FLAGS",
    "build_fooddb_packet_mutation_guard_readiness",
]
