from __future__ import annotations

from typing import Any

from .food_evidence_packet_builder import (
    build_food_evidence_recall_packet,
    is_compact_food_evidence_packet,
)
from .fooddb_local_activation_scenario_cases import FoodDBActivationScenarioCase
from .fooddb_retrieval_policy import IndexedFoodRecord, retrieve_fooddb_candidates


NO_LOOKUP_POSTURES = {
    "target_evidence_only_no_fooddb_lookup",
    "read_only_query_no_fooddb_lookup",
}


def build_case_result(
    case: FoodDBActivationScenarioCase,
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    query_results = [
        _query_result(case.turn_id, index, query, retrieval_records)
        for index, query in enumerate(case.evidence_queries, start=1)
    ]
    checks = _case_checks(case, query_results)
    return {
        "turn_id": case.turn_id,
        "packet_posture": case.packet_posture,
        "runner_inferred_semantics": False,
        "status": "pass"
        if all(check["status"] == "pass" for check in checks)
        else "fail",
        "evidence_queries": query_results,
        "checks": checks,
    }


def _query_result(
    turn_id: str,
    query_index: int,
    query: str,
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    retrieval_result = retrieve_fooddb_candidates(
        query, retrieval_records=retrieval_records, limit=8
    )
    packet = build_food_evidence_recall_packet(
        packet_id=f"{turn_id}:{query_index}",
        raw_user_input=query,
        retrieval_result=retrieval_result,
        manager_expected_behavior="scenario_wall_evidence_only",
        packet_type="fooddb_manager_evidence_packet_v1",
    )
    return {
        "query": query,
        "retrieval_boundary": retrieval_result["retrieval_boundary"],
        "manager_evidence_packet": packet,
    }


def _case_checks(
    case: FoodDBActivationScenarioCase, query_results: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    if case.packet_posture in NO_LOOKUP_POSTURES:
        return [
            _check(
                "no_fooddb_lookup_required",
                not query_results,
                {"packet_posture": case.packet_posture},
            )
        ]
    checks = [
        _check(
            "compact_packets_only",
            all(
                is_compact_food_evidence_packet(result["manager_evidence_packet"])
                for result in query_results
            ),
            {"query_count": len(query_results)},
        ),
        _check(
            "packets_do_not_authorize_mutation",
            all(
                result["manager_evidence_packet"].get("runtime_mutation_allowed")
                is False
                and result["manager_evidence_packet"].get("truth_selection_forbidden")
                is True
                for result in query_results
            ),
            {"query_count": len(query_results)},
        ),
    ]
    if case.expected_retrieval_boundary:
        checks.append(_expected_retrieval_boundary_check(case, query_results))
    if case.packet_posture == "followup_no_mutation_no_fooddb_estimate":
        checks.append(_followup_no_mutation_check(query_results))
    if case.required_anchor_ids:
        checks.append(_required_anchors_check(case, query_results))
    if case.required_modifier_compatibility:
        checks.append(_required_modifier_check(case, query_results))
    return checks


def _expected_retrieval_boundary_check(
    case: FoodDBActivationScenarioCase,
    query_results: list[dict[str, Any]],
) -> dict[str, Any]:
    actual = [result["retrieval_boundary"] for result in query_results]
    return _check(
        "expected_retrieval_boundary",
        all(boundary == case.expected_retrieval_boundary for boundary in actual),
        {"expected": case.expected_retrieval_boundary, "actual": actual},
    )


def _followup_no_mutation_check(query_results: list[dict[str, Any]]) -> dict[str, Any]:
    packets = [result["manager_evidence_packet"] for result in query_results]
    return _check(
        "followup_no_mutation_without_fooddb_estimate",
        all(
            packet.get("evidence_items") == []
            and packet.get("runtime_mutation_allowed") is False
            and bool(packet.get("followup_hints"))
            for packet in packets
        ),
        {
            "evidence_item_counts": [
                len(packet.get("evidence_items") or []) for packet in packets
            ],
            "followup_hint_counts": [
                len(packet.get("followup_hints") or []) for packet in packets
            ],
        },
    )


def _required_anchors_check(
    case: FoodDBActivationScenarioCase,
    query_results: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor_ids = _packet_anchor_ids(query_results)
    return _check(
        "required_runtime_anchor_ids_present",
        all(anchor_id in anchor_ids for anchor_id in case.required_anchor_ids),
        {
            "required_anchor_ids": list(case.required_anchor_ids),
            "actual_anchor_ids": sorted(anchor_ids),
        },
    )


def _required_modifier_check(
    case: FoodDBActivationScenarioCase,
    query_results: list[dict[str, Any]],
) -> dict[str, Any]:
    compatibility = _packet_modifier_compatibility(query_results)
    return _check(
        "required_modifier_compatibility_present",
        all(
            compatibility.get(name) == expected
            for name, expected in case.required_modifier_compatibility
        ),
        {
            "required_modifier_compatibility": dict(
                case.required_modifier_compatibility
            ),
            "actual_modifier_compatibility": compatibility,
        },
    )


def _packet_anchor_ids(query_results: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("anchor_id") or "")
        for result in query_results
        for item in result["manager_evidence_packet"].get("evidence_items") or []
        if str(item.get("anchor_id") or "")
    }


def _packet_modifier_compatibility(
    query_results: list[dict[str, Any]],
) -> dict[str, str]:
    combined: dict[str, str] = {}
    for result in query_results:
        for item in result["manager_evidence_packet"].get("evidence_items") or []:
            for name, status in (item.get("modifier_compatibility") or {}).items():
                combined[str(name)] = str(status)
    return combined


def _check(check_id: str, passed: bool, details: dict[str, Any]) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "details": details,
    }


__all__ = ["build_case_result"]
