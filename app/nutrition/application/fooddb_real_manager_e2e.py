from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable

from app.nutrition.infrastructure.small_anchor_store_loader import load_small_anchor_seed_records

from .fooddb_grokfast_live_diagnostic_case_catalog import (
    build_fooddb_grokfast_live_diagnostic_cases,
)
from .fooddb_manager_packet_smoke import (
    FoodDBPacketSmokeCase,
    build_fooddb_manager_packet_smoke,
)
from .fooddb_retrieval_records import (
    IndexedFoodRecord,
    build_current_shell_retrieval_records_from_packet_ready_artifact,
)

_BEHAVIOR_BY_POSTURE = {
    "estimate_from_packet_with_uncertainty": "estimate_from_packet_with_uncertainty",
    "estimate_or_confirm_from_fuzzy_packet": "estimate_or_confirm_from_fuzzy_packet",
    "ask_followup_no_mutation": "ask_followup_no_mutation",
    "estimate_listed_components_only": "estimate_listed_components_only",
    "generic_range_estimate_with_followup_hints": "generic_range_estimate_with_followup_hints",
    "commit_exact_item_when_packet_supports_exactness": "use_exact_packet_macro_visible_without_mutation",
    "answer_only_no_mutation": "answer_only_no_mutation",
    "commit_without_macro_claims": "commit_without_macro_claims",
}

_CASE_FAMILY_BY_LIVE_FAMILY = {
    "modifier_guard": "common_commercial_drink",
    "fuzzy_alias": "common_commercial_drink",
    "bare_basket_followup": "composition_unknown_self_selected_basket",
    "listed_basket_components": "listed_ingredient_basket",
    "generic_anchor_modifier_guard": "common_commercial_meal",
    "exact_item_card": "exact_item_macro_present",
    "query_only_food_answer": "common_commercial_meal_macro_missing",
    "macro_visibility_hidden": "common_commercial_meal_macro_missing",
}

_RETRIEVAL_QUERY_OVERRIDE = {
    "food_query_no_mutation": "牛肉麵",
    "macro_missing_hidden": "蛋餅",
}


def _build_real_manager_e2e_cases() -> tuple[FoodDBPacketSmokeCase, ...]:
    cases: list[FoodDBPacketSmokeCase] = []
    for case in build_fooddb_grokfast_live_diagnostic_cases():
        case_id = str(case.get("case_id") or "")
        posture = str(case.get("expected_manager_posture") or "")
        family = str(case.get("family") or "")
        cases.append(
            FoodDBPacketSmokeCase(
                case_id=case_id,
                raw_input=str(case.get("utterance") or ""),
                expected_behavior=_BEHAVIOR_BY_POSTURE[posture],
                case_family=_CASE_FAMILY_BY_LIVE_FAMILY[family],
                retrieval_query_text=_RETRIEVAL_QUERY_OVERRIDE.get(case_id),
            )
        )
    return tuple(cases)


FOODDB_REAL_MANAGER_E2E_CASES = _build_real_manager_e2e_cases()


def build_fooddb_real_manager_e2e(
    *,
    approved_packet_ready_artifact: dict[str, Any],
    semantic_small_anchor_records: Iterable[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    semantic_records = (
        load_small_anchor_seed_records()
        if semantic_small_anchor_records is None
        else list(semantic_small_anchor_records)
    )
    retrieval_records = build_current_shell_retrieval_records_from_packet_ready_artifact(
        approved_packet_ready_artifact,
        semantic_small_anchor_records=semantic_records,
    )
    smoke = build_fooddb_manager_packet_smoke(
        retrieval_records=retrieval_records,
        cases=FOODDB_REAL_MANAGER_E2E_CASES,
    )
    cases = [_case_with_grade(case) for case in smoke["cases"]]
    pass_count = sum(1 for case in cases if case["status"] == "pass")

    return {
        "artifact_type": "accurate_intake_fooddb_real_manager_e2e",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "claim_scope": "real_fooddb_packet_ready_manager_evidence_path",
        "pass_type": "offline_runtime",
        "status": "pass" if pass_count == len(cases) else "fail",
        "live_provider_used": False,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "manager_context_changed": False,
        "fooddb_truth_updated": False,
        "cases": cases,
        "summary": {
            "case_count": len(cases),
            "pass_count": pass_count,
            "fail_count": len(cases) - pass_count,
            "source_lane_counts": _source_lane_counts(retrieval_records),
            "packet_ready_item_count": approved_packet_ready_artifact.get("summary", {}).get(
                "packet_ready_item_count",
            ),
            "raw_source_rows_included": False,
            "candidate_only_records_included": False,
            "full_fooddb_included": False,
        },
        "non_claims": ["no_live_provider_call", "no_websearch_truth", "no_runtime_mutation", "no_product_readiness", "no_private_self_use_approval"],
    }


def _case_with_grade(case: dict[str, Any]) -> dict[str, Any]:
    packet = case["manager_evidence_packet"]
    evidence_items = packet.get("evidence_items") or []
    expected_behavior = str(case.get("manager_expected_behavior") or "")
    blockers = _case_blockers(expected_behavior, packet)
    return {
        **case,
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
        "final_response_basis": _final_response_basis(
            expected_behavior,
            evidence_items,
        ),
    }


def _case_blockers(expected_behavior: str, packet: dict[str, Any]) -> list[str]:
    evidence_items = packet.get("evidence_items") or []
    if expected_behavior == "ask_followup_no_mutation":
        blockers = []
        if packet.get("retrieval_boundary") != "bare_basket_ask_followup_no_estimate":
            blockers.append("bare_basket_not_followup_boundary")
        if evidence_items:
            blockers.append("bare_basket_returned_nutrition_evidence")
        if not packet.get("followup_hints"):
            blockers.append("bare_basket_missing_followup_hints")
        return blockers

    if not evidence_items:
        return ["case_missing_evidence_items"]
    if expected_behavior == "use_exact_packet_macro_visible_without_mutation":
        return _exact_item_blockers(evidence_items[0])
    if expected_behavior == "estimate_listed_components_only":
        return _macro_hidden_lane_blockers(evidence_items, expected_lane="listed_component")
    if expected_behavior in {
        "estimate_from_packet_with_uncertainty",
        "estimate_or_confirm_from_fuzzy_packet",
        "generic_range_estimate_with_followup_hints",
        "answer_only_no_mutation",
        "commit_without_macro_claims",
    }:
        return _macro_hidden_lane_blockers(evidence_items, expected_lane="generic_common_serving")
    return []


def _exact_item_blockers(item: dict[str, Any]) -> list[str]:
    blockers = []
    if item.get("source_lane") != "exact_item_card":
        blockers.append("exact_case_not_exact_item_card")
    if item.get("macro_visibility_status") != "visible":
        blockers.append("exact_case_macro_not_visible")
    for field in ("protein_g", "carbs_g", "fat_g"):
        if item.get(field) is None:
            blockers.append(f"exact_case_missing_{field}")
    return blockers


def _macro_hidden_lane_blockers(items: list[dict[str, Any]], *, expected_lane: str) -> list[str]:
    blockers = []
    for item in items:
        if item.get("source_lane") != expected_lane:
            blockers.append(f"unexpected_source_lane:{item.get('source_lane')}")
        if item.get("macro_visibility_status") != "hidden_missing_source":
            blockers.append(f"unexpected_macro_visibility:{item.get('macro_visibility_status')}")
        for field in ("protein_g", "carbs_g", "fat_g"):
            if item.get(field) is not None:
                blockers.append(f"hidden_macro_value_present:{field}")
    return blockers


def _final_response_basis(expected_behavior: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "basis_type": "allowed_facts_from_real_packet_ready_fooddb_evidence",
        "action_status": expected_behavior,
        "kcal_basis": [
            {
                "source_lane": item.get("source_lane"),
                "item_id": item.get("anchor_id"),
                "kcal_point": item.get("kcal_point"),
                "kcal_range": item.get("kcal_range"),
            }
            for item in items
        ],
        "macro_basis": _macro_basis(items),
        "packet_is_not_mutation_authority": True,
        "forbidden_claims": ["logged_status", "runtime_mutation", "fooddb_truth_created", "invented_macro", "invented_source_exactness"],
    }


def _macro_basis(items: list[dict[str, Any]]) -> dict[str, Any]:
    if len(items) != 1 or items[0].get("macro_visibility_status") != "visible":
        return {
            "macro_visibility_status": "hidden_missing_source" if items else "not_applicable",
            "allowed_macro_claims": {},
        }
    item = items[0]
    return {
        "macro_visibility_status": "visible",
        "allowed_macro_claims": {
            "protein_g": item.get("protein_g"),
            "carbs_g": item.get("carbs_g"),
            "fat_g": item.get("fat_g"),
        },
    }


def _source_lane_counts(records: tuple[IndexedFoodRecord, ...]) -> dict[str, int]:
    counts = {
        "exact_item_card": 0,
        "generic_common_serving": 0,
        "listed_component": 0,
        "basket_family_semantic_only": 0,
    }
    for record in records:
        if record.source_lane in counts:
            counts[record.source_lane] += 1
    return counts


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["FOODDB_REAL_MANAGER_E2E_CASES", "build_fooddb_real_manager_e2e"]
