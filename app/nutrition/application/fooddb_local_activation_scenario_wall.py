from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .food_evidence_packet_builder import (
    build_food_evidence_recall_packet,
    is_compact_food_evidence_packet,
)
from .fooddb_retrieval_policy import IndexedFoodRecord, retrieve_fooddb_candidates


@dataclass(frozen=True)
class FoodDBActivationScenarioCase:
    turn_id: str
    packet_posture: str
    evidence_queries: tuple[str, ...] = ()
    required_anchor_ids: tuple[str, ...] = ()
    required_modifier_compatibility: tuple[tuple[str, str], ...] = ()
    expected_retrieval_boundary: str | None = None


FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES: tuple[FoodDBActivationScenarioCase, ...] = (
    FoodDBActivationScenarioCase(
        turn_id="breakfast_tea_egg_latte",
        packet_posture="fooddb_packet_required",
        evidence_queries=("\u8336\u8449\u86cb", "\u62ff\u9435"),
        required_anchor_ids=("single_item_tea_egg", "custom_drink_latte"),
    ),
    FoodDBActivationScenarioCase(
        turn_id="lunch_chicken_bento",
        packet_posture="fooddb_packet_required",
        evidence_queries=("\u96de\u817f\u4fbf\u7576",),
        required_anchor_ids=("generic_meal_chicken_bento",),
    ),
    FoodDBActivationScenarioCase(
        turn_id="lunch_rice_less_correction",
        packet_posture="fooddb_packet_required",
        evidence_queries=("\u96de\u817f\u4fbf\u7576\u5c11\u98ef",),
        required_anchor_ids=("generic_meal_chicken_bento",),
        required_modifier_compatibility=(("rice_portion", "compatible_via_normalized_equivalent"),),
    ),
    FoodDBActivationScenarioCase(
        turn_id="bubble_tea_first_value",
        packet_posture="fooddb_packet_required",
        evidence_queries=("\u73cd\u5976",),
        required_anchor_ids=("custom_drink_boba_milk_tea",),
    ),
    FoodDBActivationScenarioCase(
        turn_id="bubble_tea_half_sugar_large_refinement",
        packet_posture="fooddb_packet_required",
        evidence_queries=("\u5927\u676f\u534a\u7cd6\u73cd\u5976",),
        required_anchor_ids=("custom_drink_boba_milk_tea",),
        required_modifier_compatibility=(
            ("cup_size", "compatible"),
            ("sugar_level", "compatible"),
        ),
    ),
    FoodDBActivationScenarioCase(
        turn_id="dinner_luwei_bare_draft",
        packet_posture="followup_no_mutation_no_fooddb_estimate",
        evidence_queries=("\u6211\u5403\u6ef7\u5473",),
        expected_retrieval_boundary="bare_basket_ask_followup_no_estimate",
    ),
    FoodDBActivationScenarioCase(
        turn_id="dinner_luwei_listed_commit",
        packet_posture="fooddb_packet_required",
        evidence_queries=("\u6ef7\u5473\u6709\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",),
        required_anchor_ids=(
            "listed_item_kelp",
            "listed_item_meatball",
            "listed_item_tofu_dried",
        ),
        expected_retrieval_boundary="listed_basket_component_recall",
    ),
    FoodDBActivationScenarioCase(
        turn_id="dinner_remove_gongwan",
        packet_posture="target_evidence_only_no_fooddb_lookup",
    ),
    FoodDBActivationScenarioCase(
        turn_id="today_consumed_remaining_query",
        packet_posture="read_only_query_no_fooddb_lookup",
    ),
)


def build_fooddb_local_activation_scenario_wall(
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
    activation_wall_artifact: dict[str, Any] | None = None,
    cases: tuple[FoodDBActivationScenarioCase, ...] = FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES,
) -> dict[str, Any]:
    case_results = [_case_result(case, retrieval_records=retrieval_records) for case in cases]
    blockers = [
        f"{case['turn_id']}:{check['check_id']}"
        for case in case_results
        for check in case["checks"]
        if check["status"] != "pass"
    ]
    activation_wall_status = _activation_wall_status(activation_wall_artifact)
    if activation_wall_status != "pass":
        blockers.append(f"activation_wall_status:{activation_wall_status}")
    status = "pass" if not blockers else "blocked"
    upstream_next_required = _activation_wall_upstream_next_required(activation_wall_artifact)
    return {
        "artifact_type": "accurate_intake_fooddb_local_activation_scenario_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_fooddb_local_activation_scenario_wall_only",
        "claim_scope": "fooddb_real_packet_scenario_wall_without_runtime_mutation",
        "status": status,
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "runner_inferred_semantics": False,
        "activation_wall_status": activation_wall_status,
        "upstream_next_required_slices": upstream_next_required,
        "summary": {
            "scenario_turn_count": len(case_results),
            "fooddb_packet_required_turn_count": sum(
                1 for case in case_results if case["packet_posture"] == "fooddb_packet_required"
            ),
            "fooddb_packet_pass_turn_count": sum(
                1
                for case in case_results
                if case["packet_posture"] == "fooddb_packet_required" and case["status"] == "pass"
            ),
            "no_fooddb_lookup_turn_count": sum(
                1
                for case in case_results
                if case["packet_posture"]
                in {
                    "target_evidence_only_no_fooddb_lookup",
                    "read_only_query_no_fooddb_lookup",
                }
            ),
            "followup_no_mutation_turn_count": sum(
                1
                for case in case_results
                if case["packet_posture"] == "followup_no_mutation_no_fooddb_estimate"
            ),
        },
        "cases": case_results,
        "next_required_slice": _next_required_slice(
            status=status,
            upstream_next_required=upstream_next_required,
        ),
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_readiness_claim",
        ],
    }


def _case_result(
    case: FoodDBActivationScenarioCase,
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    query_results = [
        _query_result(
            turn_id=case.turn_id,
            query_index=index,
            query=query,
            retrieval_records=retrieval_records,
        )
        for index, query in enumerate(case.evidence_queries, start=1)
    ]
    checks = _case_checks(case=case, query_results=query_results)
    return {
        "turn_id": case.turn_id,
        "packet_posture": case.packet_posture,
        "runner_inferred_semantics": False,
        "status": "pass" if all(check["status"] == "pass" for check in checks) else "fail",
        "evidence_queries": query_results,
        "checks": checks,
    }


def _query_result(
    *,
    turn_id: str,
    query_index: int,
    query: str,
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    retrieval_result = retrieve_fooddb_candidates(query, retrieval_records=retrieval_records, limit=8)
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
    *,
    case: FoodDBActivationScenarioCase,
    query_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if case.packet_posture in {
        "target_evidence_only_no_fooddb_lookup",
        "read_only_query_no_fooddb_lookup",
    }:
        return [
            _check(
                check_id="no_fooddb_lookup_required",
                passed=not query_results,
                details={"packet_posture": case.packet_posture},
            )
        ]
    checks = [
        _check(
            check_id="compact_packets_only",
            passed=all(
                is_compact_food_evidence_packet(result["manager_evidence_packet"])
                for result in query_results
            ),
            details={"query_count": len(query_results)},
        ),
        _check(
            check_id="packets_do_not_authorize_mutation",
            passed=all(
                result["manager_evidence_packet"].get("runtime_mutation_allowed") is False
                and result["manager_evidence_packet"].get("truth_selection_forbidden") is True
                for result in query_results
            ),
            details={"query_count": len(query_results)},
        ),
    ]
    if case.expected_retrieval_boundary:
        checks.append(
            _check(
                check_id="expected_retrieval_boundary",
                passed=all(
                    result["retrieval_boundary"] == case.expected_retrieval_boundary
                    for result in query_results
                ),
                details={
                    "expected": case.expected_retrieval_boundary,
                    "actual": [result["retrieval_boundary"] for result in query_results],
                },
            )
        )
    if case.packet_posture == "followup_no_mutation_no_fooddb_estimate":
        checks.append(_followup_no_mutation_check(query_results))
    if case.required_anchor_ids:
        checks.append(_required_anchors_check(case=case, query_results=query_results))
    if case.required_modifier_compatibility:
        checks.append(_required_modifier_check(case=case, query_results=query_results))
    return checks


def _followup_no_mutation_check(query_results: list[dict[str, Any]]) -> dict[str, Any]:
    packets = [result["manager_evidence_packet"] for result in query_results]
    return _check(
        check_id="followup_no_mutation_without_fooddb_estimate",
        passed=all(
            packet.get("evidence_items") == []
            and packet.get("runtime_mutation_allowed") is False
            and bool(packet.get("followup_hints"))
            for packet in packets
        ),
        details={
            "evidence_item_counts": [len(packet.get("evidence_items") or []) for packet in packets],
            "followup_hint_counts": [len(packet.get("followup_hints") or []) for packet in packets],
        },
    )


def _required_anchors_check(
    *,
    case: FoodDBActivationScenarioCase,
    query_results: list[dict[str, Any]],
) -> dict[str, Any]:
    anchor_ids = _packet_anchor_ids(query_results)
    return _check(
        check_id="required_runtime_anchor_ids_present",
        passed=all(anchor_id in anchor_ids for anchor_id in case.required_anchor_ids),
        details={
            "required_anchor_ids": list(case.required_anchor_ids),
            "actual_anchor_ids": sorted(anchor_ids),
        },
    )


def _required_modifier_check(
    *,
    case: FoodDBActivationScenarioCase,
    query_results: list[dict[str, Any]],
) -> dict[str, Any]:
    compatibility = _packet_modifier_compatibility(query_results)
    return _check(
        check_id="required_modifier_compatibility_present",
        passed=all(
            compatibility.get(name) == expected
            for name, expected in case.required_modifier_compatibility
        ),
        details={
            "required_modifier_compatibility": dict(case.required_modifier_compatibility),
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


def _packet_modifier_compatibility(query_results: list[dict[str, Any]]) -> dict[str, str]:
    combined: dict[str, str] = {}
    for result in query_results:
        for item in result["manager_evidence_packet"].get("evidence_items") or []:
            for name, status in (item.get("modifier_compatibility") or {}).items():
                combined[str(name)] = str(status)
    return combined


def _check(
    *,
    check_id: str,
    passed: bool,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "status": "pass" if passed else "fail",
        "details": details,
    }


def _activation_wall_status(activation_wall_artifact: dict[str, Any] | None) -> str:
    if not isinstance(activation_wall_artifact, dict):
        return "not_provided"
    if activation_wall_artifact.get("artifact_type") != "accurate_intake_fooddb_activation_wall_v1":
        return "unsupported_activation_wall_artifact"
    return str(activation_wall_artifact.get("status") or "unknown")


def _activation_wall_upstream_next_required(
    activation_wall_artifact: dict[str, Any] | None,
) -> list[str]:
    if not isinstance(activation_wall_artifact, dict):
        return ["not_provided"]
    return [
        str(slice_id)
        for slice_id in activation_wall_artifact.get("upstream_next_required_slices") or []
        if str(slice_id).strip()
    ]


def _next_required_slice(
    *,
    status: str,
    upstream_next_required: list[str],
) -> str:
    if status != "pass":
        if "not_provided" in upstream_next_required:
            return "build_fooddb_activation_wall_first"
        return "inspect_fooddb_local_activation_scenario_wall_blockers"
    if upstream_next_required:
        return upstream_next_required[0]
    return "grokfast_fooddb_activation_packet_seam_rerun"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "FOODDB_LOCAL_ACTIVATION_SCENARIO_CASES",
    "FoodDBActivationScenarioCase",
    "build_fooddb_local_activation_scenario_wall",
]
