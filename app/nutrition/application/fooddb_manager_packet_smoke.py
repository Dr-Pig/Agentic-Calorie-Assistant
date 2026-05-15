from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .food_evidence_packet_builder import (
    build_food_evidence_recall_packet,
    is_compact_food_evidence_packet,
)
from .fooddb_retrieval_policy import IndexedFoodRecord, retrieve_fooddb_candidates
from .tool_evidence_result import build_tool_evidence_result


@dataclass(frozen=True)
class FoodDBPacketSmokeCase:
    case_id: str
    raw_input: str
    expected_behavior: str
    case_family: str
    retrieval_query_text: str | None = None
    listed_components: tuple[str, ...] = ()


FOODDB_PACKET_SMOKE_CASES: tuple[FoodDBPacketSmokeCase, ...] = (
    FoodDBPacketSmokeCase(
        case_id="boba_large_half_sugar",
        raw_input="\u5927\u676f\u534a\u7cd6\u73cd\u5976",
        expected_behavior="estimate_from_packet_with_uncertainty",
        case_family="common_commercial_drink",
    ),
    FoodDBPacketSmokeCase(
        case_id="boba_typo",
        raw_input="\u73cd\u73e0\u4e43\u8336",
        expected_behavior="estimate_or_confirm_from_fuzzy_packet",
        case_family="common_commercial_drink",
    ),
    FoodDBPacketSmokeCase(
        case_id="bare_luwei",
        raw_input="\u6211\u5403\u6ef7\u5473",
        expected_behavior="ask_followup_no_mutation",
        case_family="composition_unknown_self_selected_basket",
    ),
    FoodDBPacketSmokeCase(
        case_id="listed_luwei_components",
        raw_input="\u6ef7\u5473\u6709\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",
        expected_behavior="estimate_listed_components_only",
        case_family="listed_ingredient_basket",
        listed_components=("\u8c46\u5e72", "\u6d77\u5e36", "\u8ca2\u4e38"),
    ),
    FoodDBPacketSmokeCase(
        case_id="chicken_bento_less_rice",
        raw_input="\u96de\u817f\u4fbf\u7576\u5c11\u98ef",
        expected_behavior="generic_range_estimate_with_followup_hints",
        case_family="common_commercial_meal",
    ),
)


def build_fooddb_manager_packet_smoke(
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
    approved_packet_ready_artifact: dict[str, Any] | None = None,
    cases: tuple[FoodDBPacketSmokeCase, ...] = FOODDB_PACKET_SMOKE_CASES,
) -> dict[str, Any]:
    case_results = [_case_result(case, retrieval_records=retrieval_records) for case in cases]
    approved_cases = _approved_packet_ready_cases(approved_packet_ready_artifact)
    compact_pass_count = sum(
        1
        for item in case_results
        if is_compact_food_evidence_packet(item["manager_evidence_packet"])
    )
    approved_lane_counts = _approved_lane_counts(approved_cases)
    return {
        "artifact_type": "accurate_intake_fooddb_manager_packet_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "deterministic_fooddb_manager_packet_smoke",
        "runtime_truth_changed": False,
        "live_provider_used": False,
        "manager_context_changed": False,
        "runtime_packetizer_contract_changed": False,
        "manager_recall_packet_shape_changed": True,
        "packetizer_format_changed": False,
        "product_loop_integration_claimed": False,
        "cases": case_results,
        "approved_packet_ready_cases": approved_cases,
        "summary": {
            "case_count": len(case_results),
            "compact_packet_pass_count": compact_pass_count,
            "approved_packet_ready_case_count": len(approved_cases),
            "approved_packet_ready_lane_counts": approved_lane_counts,
            "raw_source_rows_included": False,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
            "compact_packet_structural_leak_check": "enabled",
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_live_provider_call",
            "no_manager_context_change",
            "no_runtime_packetizer_contract_change",
            "no_product_loop_integration",
            "no_readiness_claim",
        ],
    }


def _case_result(
    case: FoodDBPacketSmokeCase,
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    retrieval_query_text = case.retrieval_query_text or case.raw_input
    retrieval_result = retrieve_fooddb_candidates(
        retrieval_query_text, retrieval_records=retrieval_records, limit=8,
        listed_components=list(case.listed_components) or None,
    )
    packet = _manager_evidence_packet(case=case, retrieval_result=retrieval_result, retrieval_query_text=retrieval_query_text)
    return {
        "case_id": case.case_id,
        "raw_user_input": case.raw_input,
        "retrieval_query_text": retrieval_query_text,
        "case_family": case.case_family,
        "manager_expected_behavior": case.expected_behavior,
        "manager_evidence_packet": packet,
    }


def _manager_evidence_packet(
    *,
    case: FoodDBPacketSmokeCase,
    retrieval_result: dict[str, Any],
    retrieval_query_text: str,
) -> dict[str, Any]:
    packet = build_food_evidence_recall_packet(
        packet_id=case.case_id,
        raw_user_input=case.raw_input,
        retrieval_result=retrieval_result,
        manager_expected_behavior=case.expected_behavior,
        packet_type="fooddb_manager_evidence_packet_v1",
    )
    packet["case_id"] = case.case_id
    packet["retrieval_query_text"] = retrieval_query_text
    return packet


def _approved_packet_ready_cases(
    approved_packet_ready_artifact: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not approved_packet_ready_artifact:
        return []
    return [
        _approved_packet_ready_case(item)
        for item in approved_packet_ready_artifact.get("packet_ready_items") or []
    ]


def _approved_packet_ready_case(item: dict[str, Any]) -> dict[str, Any]:
    source_lane = str(item.get("source_lane") or "").strip()
    item_id = str(item.get("item_id") or "").strip()
    packet = _approved_manager_evidence_packet(item)
    tool_result = build_tool_evidence_result(
        tool_name="fooddb.get_approved_packet_ready_evidence",
        tool_call_id=f"tool-approved-{source_lane}-{item_id}",
        evidence_packets=(packet,),
        trace_context={
            "live_provider_used": False,
            "packet_artifact_type": "accurate_intake_approved_packet_ready_fooddb_artifact",
            "packet_claim_scope": "minimal_fooddb_packet_ready_macro_handoff",
        },
    )
    return {
        "case_id": f"approved_packet_ready:{source_lane}:{item_id}",
        "source_lane": source_lane,
        "item_id": item_id,
        "manager_evidence_packet": packet,
        "tool_result_envelope": tool_result,
        "final_response_basis": _final_response_basis(item),
    }


def _approved_manager_evidence_packet(item: dict[str, Any]) -> dict[str, Any]:
    source_lane = str(item.get("source_lane") or "").strip()
    item_id = str(item.get("item_id") or "").strip()
    packet = {
        "packet_type": "fooddb_manager_evidence_packet_v1",
        "packet_id": f"approved_packet_ready:{source_lane}:{item_id}",
        "raw_user_input": str(item.get("canonical_name") or item_id),
        "retrieval_scope": "approved_packet_ready_artifact",
        "retrieval_boundary": "approved_packet_ready_support_only",
        "runtime_mutation_allowed": False,
        "truth_selection_forbidden": True,
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "full_fooddb_included": False,
        "modifier_hints": {},
        "candidate_terms": [str(item.get("canonical_name") or item_id)],
        "evidence_items": [_approved_evidence_item(item)],
        "rejected_candidate_count": 0,
        "ambiguity_reason": None,
        "followup_hints": [],
        "vector_search_policy": None,
        "ranking_policy": "approved_packet_ready_single_item",
        "manager_may_use_for": [
            "grounded_food_evidence",
            "macro_visibility_honesty",
            "followup_or_uncertainty_decision",
        ],
        "manager_must_not_use_for": [
            "runtime_mutation",
            "creating_fooddb_truth",
            "inventing_source",
            "inventing_macro",
        ],
    }
    return packet


def _approved_evidence_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_lane": item.get("source_lane"),
        "item_id": item.get("item_id"),
        "canonical_name": item.get("canonical_name"),
        "runtime_role": item.get("runtime_role"),
        "runtime_truth_allowed": item.get("runtime_truth_allowed"),
        "runtime_usage_boundary": item.get("runtime_usage_boundary"),
        "serving_basis": item.get("serving_basis"),
        "portion_basis": item.get("portion_basis") or {},
        "kcal_point": item.get("kcal_point"),
        "kcal_range": item.get("kcal_range"),
        "protein_g": item.get("protein_g"),
        "carbs_g": item.get("carbs_g"),
        "fat_g": item.get("fat_g"),
        "macro_visibility_status": item.get("macro_visibility_status"),
        "macro_source_basis": item.get("macro_source_basis"),
        "macro_confidence": item.get("macro_confidence"),
        "source_provenance": _compact_source_provenance(item.get("source_provenance")),
        "approval_metadata": _compact_approval_metadata(item.get("approval_metadata")),
    }


def _final_response_basis(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "basis_type": "allowed_facts_from_approved_packet_ready_tool_result",
        "source_lane": item.get("source_lane"),
        "item_id": item.get("item_id"),
        "kcal_basis": {
            "kcal_point": item.get("kcal_point"),
            "kcal_range": item.get("kcal_range"),
        },
        "macro_basis": _macro_basis(item),
        "packet_is_not_mutation_authority": True,
        "forbidden_claims": [
            "logged_status",
            "runtime_mutation",
            "fooddb_truth_created",
            "invented_macro",
        ],
    }


def _macro_basis(item: dict[str, Any]) -> dict[str, Any]:
    visible = str(item.get("macro_visibility_status") or "") == "visible"
    if not visible:
        return {
            "macro_visibility_status": item.get("macro_visibility_status"),
            "allowed_macro_claims": {},
        }
    return {
        "macro_visibility_status": "visible",
        "allowed_macro_claims": {
            "protein_g": item.get("protein_g"),
            "carbs_g": item.get("carbs_g"),
            "fat_g": item.get("fat_g"),
        },
    }


def _approved_lane_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    lanes = {
        "exact_item_card": 0,
        "generic_common_serving": 0,
        "listed_component": 0,
    }
    for case in cases:
        lane = str(case.get("source_lane") or "").strip()
        if lane in lanes:
            lanes[lane] += 1
    return lanes


def _compact_source_provenance(value: Any) -> dict[str, Any]:
    source = value if isinstance(value, dict) else {}
    allowed_keys = ("source_id", "source_file", "source_url")
    return {key: source.get(key) for key in allowed_keys if source.get(key) is not None}


def _compact_approval_metadata(value: Any) -> dict[str, Any]:
    approval = value if isinstance(value, dict) else {}
    allowed_keys = (
        "approval_mode",
        "approval_scope",
        "policy_version",
        "runtime_truth_allowed",
    )
    return {key: approval.get(key) for key in allowed_keys if key in approval}


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "FOODDB_PACKET_SMOKE_CASES",
    "FoodDBPacketSmokeCase",
    "build_fooddb_manager_packet_smoke",
]
