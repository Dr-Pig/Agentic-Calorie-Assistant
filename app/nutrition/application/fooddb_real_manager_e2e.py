from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterable

from app.nutrition.infrastructure.small_anchor_store_loader import load_small_anchor_seed_records

from .fooddb_manager_packet_smoke import (
    FoodDBPacketSmokeCase,
    build_fooddb_manager_packet_smoke,
)
from .fooddb_retrieval_records import (
    IndexedFoodRecord,
    build_current_shell_retrieval_records_from_packet_ready_artifact,
)

FOODDB_REAL_MANAGER_E2E_CASES: tuple[FoodDBPacketSmokeCase, ...] = tuple(
    FoodDBPacketSmokeCase(*item)
    for item in (
        (
            "exact_macro_visible_chocolate_milk",
            "\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73 400ml",
            "use_exact_packet_macro_visible_without_mutation",
            "exact_item_macro_present",
        ),
        (
            "generic_macro_hidden_boba",
            "\u5927\u676f\u534a\u7cd6\u73cd\u5976",
            "estimate_range_with_macro_hidden",
            "generic_common_drink_macro_missing",
        ),
        (
            "listed_luwei_components",
            "\u6ef7\u5473\u6709\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",
            "estimate_listed_components_only",
            "listed_ingredient_basket_macro_missing",
        ),
        (
            "bare_luwei_followup_only",
            "\u6211\u5403\u6ef7\u5473",
            "ask_followup_no_mutation",
            "composition_unknown_self_selected_basket",
        ),
        (
            "generic_bento_macro_hidden_less_rice",
            "\u96de\u817f\u4fbf\u7576\u5c11\u98ef",
            "generic_range_estimate_with_followup_hints",
            "common_commercial_meal_macro_missing",
        ),
    )
)


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
    blockers = _case_blockers(case["case_id"], packet)
    return {
        **case,
        "status": "pass" if not blockers else "fail",
        "blockers": blockers,
        "final_response_basis": _final_response_basis(
            case["manager_expected_behavior"],
            evidence_items,
        ),
    }


def _case_blockers(case_id: str, packet: dict[str, Any]) -> list[str]:
    evidence_items = packet.get("evidence_items") or []
    if case_id == "bare_luwei_followup_only":
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
    if case_id.startswith("exact_"):
        return _exact_item_blockers(evidence_items[0])
    if case_id.startswith("generic_"):
        return _macro_hidden_lane_blockers(evidence_items, expected_lane="generic_common_serving")
    if case_id.startswith("listed_"):
        return _macro_hidden_lane_blockers(evidence_items, expected_lane="listed_component")
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
