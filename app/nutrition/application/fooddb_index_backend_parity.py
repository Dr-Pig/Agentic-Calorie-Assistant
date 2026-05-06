from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .food_evidence_index_port import FoodEvidenceIndexPort
from .food_evidence_packet_builder import build_food_evidence_recall_packet
from .food_evidence_retriever_execution_scope import records_for_query
from .fooddb_retrieval_policy import retrieve_fooddb_candidates
from .tool_evidence_result import build_tool_evidence_result


@dataclass(frozen=True)
class BackendParityCase:
    case_id: str
    query: str
    expected_top_anchor_id: str


DEFAULT_BACKEND_PARITY_CASES = (
    BackendParityCase(
        case_id="boba_alias",
        query="boba",
        expected_top_anchor_id="custom_drink_boba_milk_tea",
    ),
    BackendParityCase(
        case_id="chicken_bento_alias",
        query="\u96de\u817f\u4fbf\u7576",
        expected_top_anchor_id="generic_meal_chicken_bento",
    ),
    BackendParityCase(
        case_id="kelp_component",
        query="\u6d77\u5e36",
        expected_top_anchor_id="listed_item_kelp",
    ),
    BackendParityCase(
        case_id="latte_alias",
        query="\u62ff\u9435",
        expected_top_anchor_id="custom_drink_latte",
    ),
)


def build_fooddb_index_backend_parity(
    *,
    local_index: FoodEvidenceIndexPort,
    sqlite_index: FoodEvidenceIndexPort,
    supabase_index: FoodEvidenceIndexPort,
    cases: tuple[BackendParityCase, ...] = DEFAULT_BACKEND_PARITY_CASES,
) -> dict[str, Any]:
    backends = (
        ("local_json", local_index),
        ("sqlite_fts", sqlite_index),
        ("supabase_rows", supabase_index),
    )
    case_results = [
        _case_result(case=case, backends=backends)
        for case in cases
    ]
    blockers = []
    if not cases:
        blockers.append("backend_parity_case_suite_empty")
    blockers.extend(
        f"backend_parity_case_failed:{case['case_id']}"
        for case in case_results
        if case["status"] != "pass"
    )
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_fooddb_index_backend_parity_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_backend_parity_only",
        "claim_scope": "fooddb_index_dependency_inversion_parity",
        "status": "pass" if clear else "blocked",
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "case_count": len(case_results),
            "pass_count": sum(1 for case in case_results if case["status"] == "pass"),
            "fail_count": sum(1 for case in case_results if case["status"] != "pass"),
            "backend_count": len(backends),
            "backend_labels": [label for label, _index in backends],
        },
        "cases": case_results,
        "dependency_inversion": {
            "stable_application_contract": "FoodEvidenceIndexPort -> IndexedFoodRecord",
            "parity_backends": [label for label, _index in backends],
            "manager_visible_backend": False,
            "deterministic_role": "validate backend parity and compact packet boundary",
            "deterministic_does_not_own": [
                "user_intent",
                "workflow_effect",
                "final_action",
                "mutation_legality",
                "nutrition_truth_promotion",
            ],
        },
        "next_required_slice": (
            "grokfast_fooddb_packet_live_diagnostic"
            if clear
            else "inspect_fooddb_index_backend_parity_blockers"
        ),
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_supabase_connection",
            "no_readiness_claim",
        ],
    }


def _case_result(
    *,
    case: BackendParityCase,
    backends: tuple[tuple[str, FoodEvidenceIndexPort], ...],
) -> dict[str, Any]:
    backend_results = [
        _backend_result(case=case, backend_label=label, index=index)
        for label, index in backends
    ]
    anchor_sets = [tuple(result["accepted_anchor_ids"]) for result in backend_results]
    first_anchor_set = anchor_sets[0] if anchor_sets else ()
    parity_passed = all(anchor_set == first_anchor_set for anchor_set in anchor_sets)
    evidence_signatures = [
        tuple(result["manager_visible_evidence_item_signatures"])
        for result in backend_results
    ]
    first_signature = evidence_signatures[0] if evidence_signatures else ()
    evidence_payload_parity_passed = all(
        signature == first_signature for signature in evidence_signatures
    )
    expected_top_passed = all(
        result["top_anchor_id"] == case.expected_top_anchor_id
        for result in backend_results
    )
    boundary_passed = all(result["manager_visible_boundary_passed"] for result in backend_results)
    return {
        "case_id": case.case_id,
        "query": case.query,
        "expected_top_anchor_id": case.expected_top_anchor_id,
        "status": (
            "pass"
            if parity_passed
            and evidence_payload_parity_passed
            and expected_top_passed
            and boundary_passed
            else "fail"
        ),
        "checks": {
            "accepted_anchor_parity": parity_passed,
            "manager_visible_evidence_payload_parity": evidence_payload_parity_passed,
            "expected_top_anchor": expected_top_passed,
            "manager_visible_boundary": boundary_passed,
        },
        "backend_results": backend_results,
    }


def _backend_result(
    *,
    case: BackendParityCase,
    backend_label: str,
    index: FoodEvidenceIndexPort,
) -> dict[str, Any]:
    records = records_for_query(index=index, query=case.query)
    retrieval_result = retrieve_fooddb_candidates(case.query, retrieval_records=records)
    packet = build_food_evidence_recall_packet(
        packet_id=f"index-parity:{case.case_id}",
        raw_user_input=case.query,
        retrieval_result=retrieval_result,
    )
    tool_result = build_tool_evidence_result(
        tool_name="lookup_food_evidence",
        tool_call_id=f"tool-{case.case_id}",
        evidence_packets=(packet,),
        trace_context={
            "packet_artifact_type": "inline_index_parity_packet",
            "packet_claim_scope": "deterministic_fooddb_index_parity",
        },
    )
    accepted_anchor_ids = [
        item.get("anchor_id")
        for item in packet.get("evidence_items", [])
        if item.get("anchor_id")
    ]
    return {
        "backend_label": backend_label,
        "record_count_used": len(records),
        "accepted_anchor_ids": accepted_anchor_ids,
        "top_anchor_id": accepted_anchor_ids[0] if accepted_anchor_ids else None,
        "manager_visible_evidence_item_signatures": _evidence_item_signatures(tool_result),
        "tool_result_runtime_mutation_allowed": tool_result["runtime_mutation_allowed"],
        "tool_result_source_implementation_visible": tool_result["source_implementation_visible"],
        "manager_visible_boundary_passed": _manager_visible_boundary_passed(tool_result),
    }


def _evidence_item_signatures(tool_result: dict[str, Any]) -> list[dict[str, Any]]:
    signatures: list[dict[str, Any]] = []
    for packet in tool_result.get("evidence_packets") or []:
        if not isinstance(packet, dict):
            continue
        for item in packet.get("evidence_items") or []:
            if not isinstance(item, dict):
                continue
            signatures.append(
                {
                    "anchor_id": item.get("anchor_id"),
                    "canonical_name": item.get("canonical_name"),
                    "runtime_role": item.get("runtime_role"),
                    "runtime_truth_allowed": item.get("runtime_truth_allowed"),
                    "kcal_point": item.get("kcal_point"),
                    "kcal_range": item.get("kcal_range"),
                    "serving_basis": item.get("serving_basis"),
                    "portion_basis": item.get("portion_basis"),
                    "runtime_usage_boundary": item.get("runtime_usage_boundary"),
                    "source_provenance": item.get("source_provenance"),
                    "approval_metadata": item.get("approval_metadata"),
                    "modifier_compatibility": item.get("modifier_compatibility"),
                }
            )
    return signatures


def _manager_visible_boundary_passed(tool_result: dict[str, Any]) -> bool:
    text = str(tool_result).lower()
    forbidden_tokens = (
        "adapter_kind",
        "index_adapter",
        "local_json",
        "sqlite_fts",
        "supabase",
    )
    return (
        tool_result.get("runtime_mutation_allowed") is False
        and tool_result.get("source_implementation_visible") is False
        and not any(token in text for token in forbidden_tokens)
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "BackendParityCase",
    "DEFAULT_BACKEND_PARITY_CASES",
    "build_fooddb_index_backend_parity",
]
