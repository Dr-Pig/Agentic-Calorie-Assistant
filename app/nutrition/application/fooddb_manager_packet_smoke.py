from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .fooddb_retrieval_policy import IndexedFoodRecord, retrieve_fooddb_candidates


@dataclass(frozen=True)
class FoodDBPacketSmokeCase:
    case_id: str
    raw_input: str
    expected_behavior: str
    case_family: str


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
    cases: tuple[FoodDBPacketSmokeCase, ...] = FOODDB_PACKET_SMOKE_CASES,
) -> dict[str, Any]:
    case_results = [_case_result(case, retrieval_records=retrieval_records) for case in cases]
    compact_pass_count = sum(1 for item in case_results if _is_compact_packet(item["manager_evidence_packet"]))
    return {
        "artifact_type": "accurate_intake_fooddb_manager_packet_smoke",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "deterministic_fooddb_manager_packet_smoke",
        "runtime_truth_changed": False,
        "live_provider_used": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "product_loop_integration_claimed": False,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "compact_packet_pass_count": compact_pass_count,
            "raw_source_rows_included": False,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_live_provider_call",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_product_loop_integration",
            "no_readiness_claim",
        ],
    }


def _case_result(
    case: FoodDBPacketSmokeCase,
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
) -> dict[str, Any]:
    retrieval_result = retrieve_fooddb_candidates(case.raw_input, retrieval_records=retrieval_records, limit=8)
    packet = _manager_evidence_packet(case=case, retrieval_result=retrieval_result)
    return {
        "case_id": case.case_id,
        "raw_user_input": case.raw_input,
        "case_family": case.case_family,
        "manager_expected_behavior": case.expected_behavior,
        "manager_evidence_packet": packet,
    }


def _manager_evidence_packet(
    *,
    case: FoodDBPacketSmokeCase,
    retrieval_result: dict[str, Any],
) -> dict[str, Any]:
    evidence_items = [_compact_candidate(item) for item in retrieval_result.get("accepted_candidates") or []]
    return {
        "packet_type": "fooddb_manager_evidence_packet_v1",
        "case_id": case.case_id,
        "raw_user_input": case.raw_input,
        "retrieval_scope": retrieval_result.get("retrieval_scope"),
        "retrieval_boundary": retrieval_result.get("retrieval_boundary"),
        "manager_expected_behavior": case.expected_behavior,
        "runtime_mutation_allowed": False,
        "truth_selection_forbidden": True,
        "raw_source_rows_included": False,
        "candidate_only_records_included": False,
        "full_fooddb_included": False,
        "modifier_hints": (retrieval_result.get("normalized_query") or {}).get("modifier_hints") or {},
        "evidence_items": evidence_items,
        "rejected_candidate_count": len(retrieval_result.get("rejected_candidates") or []),
        "ambiguity_reason": retrieval_result.get("ambiguity_reason"),
        "followup_hints": list(retrieval_result.get("followup_hints") or []),
        "vector_search_policy": retrieval_result.get("vector_search_policy"),
        "manager_may_use_for": [
            "grounded_food_evidence",
            "followup_or_uncertainty_decision",
            "disambiguation",
        ],
        "manager_must_not_use_for": [
            "runtime_mutation",
            "creating_fooddb_truth",
            "inventing_source",
        ],
    }


def _compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "anchor_id": candidate.get("anchor_id"),
        "canonical_name": candidate.get("canonical_name"),
        "query_component": candidate.get("query_component"),
        "match_path": candidate.get("match_path"),
        "confidence": candidate.get("confidence"),
        "requires_manager_disambiguation": candidate.get("requires_manager_disambiguation"),
        "runtime_role": candidate.get("runtime_role"),
        "runtime_truth_allowed": candidate.get("runtime_truth_allowed"),
        "kcal_point": candidate.get("kcal_point"),
        "kcal_range": candidate.get("kcal_range"),
        "serving_basis": candidate.get("serving_basis"),
        "portion_basis": candidate.get("portion_basis"),
        "runtime_usage_boundary": candidate.get("runtime_usage_boundary"),
        "followup_hints": list(candidate.get("followup_hints") or []),
        "source_provenance": dict(candidate.get("source_provenance") or {}),
        "approval_metadata": dict(candidate.get("approval_metadata") or {}),
    }


def _is_compact_packet(packet: dict[str, Any]) -> bool:
    return (
        packet.get("raw_source_rows_included") is False
        and packet.get("candidate_only_records_included") is False
        and packet.get("full_fooddb_included") is False
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "FOODDB_PACKET_SMOKE_CASES",
    "FoodDBPacketSmokeCase",
    "build_fooddb_manager_packet_smoke",
]
