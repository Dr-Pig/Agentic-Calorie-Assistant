from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.nutrition.application.fooddb_grokfast_live_diagnostic_case_catalog import (
    NON_CLAIMS,
    REQUIRED_CASE_IDS,
    build_fooddb_grokfast_live_diagnostic_cases,
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _validate(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    case_ids = [str(case.get("case_id") or "") for case in cases]
    if case_ids != list(REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")

    required_families = {
        "modifier_guard",
        "fuzzy_alias",
        "bare_basket_followup",
        "listed_basket_components",
        "generic_anchor_modifier_guard",
        "exact_item_card",
        "query_only_food_answer",
        "macro_visibility_hidden",
    }
    families = {str(case.get("family") or "") for case in cases}
    for family in sorted(required_families - families):
        blockers.append(f"missing_family.{family}")

    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        if not case.get("utterance"):
            blockers.append(f"{case_id}.utterance_missing")
        if not case.get("family"):
            blockers.append(f"{case_id}.family_missing")
        if not case.get("expected_manager_posture"):
            blockers.append(f"{case_id}.expected_manager_posture_missing")
        canonical_manifest_case_id = case.get("canonical_manifest_case_id")
        if canonical_manifest_case_id is not None and not str(canonical_manifest_case_id).startswith(
            "MVP-LIVE-"
        ):
            blockers.append(f"{case_id}.canonical_manifest_case_id_invalid")
        expected_fields = case.get("expected_packet_fields")
        if not isinstance(expected_fields, list) or "evidence_items" not in expected_fields:
            blockers.append(f"{case_id}.expected_packet_fields_missing_evidence_items")
        must_not_happen = case.get("must_not_happen")
        if not isinstance(must_not_happen, list) or "invented_nutrition_source" not in must_not_happen:
            blockers.append(f"{case_id}.invented_source_guard_missing")
        if case.get("live_provider_invoked") is not False:
            blockers.append(f"{case_id}.live_provider_invoked")
        if case.get("websearch_invoked") is not False:
            blockers.append(f"{case_id}.websearch_invoked")
        if case.get("ledger_mutation_allowed") is not False:
            blockers.append(f"{case_id}.ledger_mutation_allowed")
        if case.get("runtime_truth_allowed") is not False:
            blockers.append(f"{case_id}.runtime_truth_allowed")
        if case.get("runtime_truth_changed") is not False:
            blockers.append(f"{case_id}.runtime_truth_changed")
        if case.get("mutation_changed") is not False:
            blockers.append(f"{case_id}.mutation_changed")
        if case.get("manager_context_packet_changed") is not False:
            blockers.append(f"{case_id}.manager_context_packet_changed")
        if case.get("product_readiness_claimed") is not False:
            blockers.append(f"{case_id}.product_readiness_claimed")
        if case.get("family") == "bare_basket_followup":
            if case.get("expected_runtime_evidence_in_packet") is not False:
                blockers.append(f"{case_id}.bare_basket_runtime_evidence_expected")
            if case.get("expected_manager_posture") != "ask_followup_no_mutation":
                blockers.append(f"{case_id}.bare_basket_posture_not_followup")
        elif case.get("expected_runtime_evidence_in_packet") is not True:
            blockers.append(f"{case_id}.runtime_evidence_expectation_missing")
    return blockers


def build_fooddb_grokfast_live_diagnostic_case_matrix_artifact() -> dict[str, Any]:
    cases = build_fooddb_grokfast_live_diagnostic_cases()
    blockers = _validate(cases)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "track": "FoodDB_WebSearch",
            "claim_scope": "fooddb_grokfast_packet_live_case_subset_contract",
            "classification": "live_diagnostic_plan_only",
            "diagnostic_only": True,
            "plan_only": True,
            "local_only": True,
            "live_llm_invoked": False,
            "live_provider_invoked": False,
            "websearch_invoked": False,
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_changed": False,
            "shared_contract_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "case_count": len(cases),
                "modifier_guard_cases": sum(
                    1 for case in cases if "modifier" in str(case.get("family") or "")
                ),
                "bare_basket_cases": sum(
                    1 for case in cases if case.get("family") == "bare_basket_followup"
                ),
                "listed_basket_cases": sum(
                    1 for case in cases if case.get("family") == "listed_basket_components"
                ),
                "expected_runtime_evidence_packet_cases": sum(
                    1 for case in cases if case["expected_runtime_evidence_in_packet"]
                ),
                "query_only_cases": sum(
                    1 for case in cases if case.get("family") == "query_only_food_answer"
                ),
                "macro_hidden_cases": sum(
                    1 for case in cases if case.get("family") == "macro_visibility_hidden"
                ),
                "canonical_manifest_linked_case_count": sum(
                    1 for case in cases if case.get("canonical_manifest_case_id")
                ),
                "fooddb_specific_edge_case_count": sum(
                    1 for case in cases if not case.get("canonical_manifest_case_id")
                ),
                "websearch_cases": 0,
                "exact_card_cases": sum(
                    1 for case in cases if case.get("family") == "exact_item_card"
                ),
            },
            "non_claims": list(NON_CLAIMS),
            "later_expansion_candidates": {
                "generic_anchor": ["tea_egg", "beef_noodle_soup"],
                "exact_card_websearch": [
                    "wrong_brand",
                    "wrong_size",
                    "official_page_missing_nutrition",
                ],
                "additional_modifiers": ["zero_sugar", "medium_cup", "extra_boba"],
            },
            "cases": cases,
        }
    )


__all__ = [
    "REQUIRED_CASE_IDS",
    "build_fooddb_grokfast_live_diagnostic_case_matrix_artifact",
]
