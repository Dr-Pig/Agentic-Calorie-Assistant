from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from app.nutrition.application.fooddb_manager_packet_smoke import FOODDB_PACKET_SMOKE_CASES


REQUIRED_CASE_IDS = (
    "boba_large_half_sugar",
    "boba_typo",
    "bare_luwei",
    "listed_luwei_components",
    "chicken_bento_less_rice",
)

NON_CLAIMS = (
    "not_full_self_use_gate",
    "not_websearch_exact_card_gate",
    "not_final_response_quality_gate",
    "not_production_readiness",
    "not_private_self_use_approval",
    "not_kimi_activation",
    "not_runtime_mutation_gate",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _case(
    *,
    case_id: str,
    utterance: str,
    family: str,
    expected_manager_posture: str,
    expected_packet_fields: list[str],
    must_not_happen: list[str],
    why_needed: str,
    known_gap_covered: str,
    known_gap_not_covered: str,
    expected_runtime_evidence_in_packet: bool,
) -> dict[str, Any]:
    return _json_safe(
        {
            "case_id": case_id,
            "utterance": utterance,
            "family": family,
            "expected_manager_posture": expected_manager_posture,
            "expected_packet_fields": expected_packet_fields,
            "must_not_happen": must_not_happen,
            "live_provider_invoked": False,
            "websearch_invoked": False,
            "ledger_mutation_allowed": False,
            "runtime_truth_allowed": False,
            "expected_runtime_evidence_in_packet": expected_runtime_evidence_in_packet,
            "why_needed": why_needed,
            "known_gap_covered": known_gap_covered,
            "known_gap_not_covered": known_gap_not_covered,
            "semantic_owner": "Manager LLM during later live diagnostic",
            "deterministic_role": "case_selection_guard_and_packet_misuse_validator",
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_changed": False,
            "product_readiness_claimed": False,
        }
    )


def _smoke_utterance(case_id: str) -> str:
    by_id = {case.case_id: case.raw_input for case in FOODDB_PACKET_SMOKE_CASES}
    return by_id[case_id]


def _cases() -> list[dict[str, Any]]:
    common_packet_fields = [
        "case_id",
        "packet_id",
        "raw_user_input",
        "manager_expected_behavior",
        "evidence_items",
        "followup_hints",
    ]
    no_live_overclaim = [
        "self_use_readiness_claimed",
        "runtime_ledger_mutation",
        "invented_nutrition_source",
        "websearch_snippet_as_truth",
        "candidate_promoted_to_truth",
    ]
    return [
        _case(
            case_id="boba_large_half_sugar",
            utterance=_smoke_utterance("boba_large_half_sugar"),
            family="modifier_guard",
            expected_manager_posture="estimate_from_packet_with_uncertainty",
            expected_packet_fields=common_packet_fields
            + ["modifier_compatibility", "kcal_point", "kcal_range"],
            must_not_happen=[
                *no_live_overclaim,
                "size_or_sugar_kcal_adjusted_without_packet_adjustment",
            ],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers P0 drink modifiers while preventing Manager-side calorie math.",
            known_gap_covered="drink_size_and_sugar_modifier_guard",
            known_gap_not_covered="full_drink_menu_exact_card_or_brand_specific_nutrition",
        ),
        _case(
            case_id="boba_typo",
            utterance=_smoke_utterance("boba_typo"),
            family="fuzzy_alias",
            expected_manager_posture="estimate_or_confirm_from_fuzzy_packet",
            expected_packet_fields=common_packet_fields + ["match_quality", "aliases", "kcal_range"],
            must_not_happen=[*no_live_overclaim, "typo_match_used_as_unqualified_exact_truth"],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers typo/fuzzy recall without allowing invented source truth.",
            known_gap_covered="common_typo_recall_for_boba_milk_tea",
            known_gap_not_covered="broad_ocr_or_phonetic_error_recovery",
        ),
        _case(
            case_id="bare_luwei",
            utterance=_smoke_utterance("bare_luwei"),
            family="bare_basket_followup",
            expected_manager_posture="ask_followup_no_mutation",
            expected_packet_fields=common_packet_fields + ["basket_family", "evidence_items_empty"],
            must_not_happen=[*no_live_overclaim, "bare_basket_estimated_as_whole_item"],
            expected_runtime_evidence_in_packet=False,
            why_needed="Covers composition-unknown basket behavior: ask, do not estimate.",
            known_gap_covered="bare_basket_no_estimate_boundary",
            known_gap_not_covered="all_possible_self_selected_basket_families",
        ),
        _case(
            case_id="listed_luwei_components",
            utterance=_smoke_utterance("listed_luwei_components"),
            family="listed_basket_components",
            expected_manager_posture="estimate_listed_components_only",
            expected_packet_fields=common_packet_fields
            + ["component_items", "runtime_usage_boundary", "kcal_range"],
            must_not_happen=[
                *no_live_overclaim,
                "unknown_component_calorie_invented",
                "basket_total_estimated_from_family_label",
            ],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers listed basket fanout using only approved component anchors.",
            known_gap_covered="listed_luwei_component_estimation_boundary",
            known_gap_not_covered="missing_component_partial_estimate_policy_beyond_this_case",
        ),
        _case(
            case_id="chicken_bento_less_rice",
            utterance=_smoke_utterance("chicken_bento_less_rice"),
            family="generic_anchor_modifier_guard",
            expected_manager_posture="generic_range_estimate_with_followup_hints",
            expected_packet_fields=common_packet_fields
            + ["variance_level", "modifier_compatibility"],
            must_not_happen=[
                *no_live_overclaim,
                "less_rice_kcal_adjusted_without_packet_adjustment",
                "generic_bento_presented_as_exact_truth",
            ],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers generic meal range plus rice modifier guard.",
            known_gap_covered="generic_meal_modifier_guard_for_rice_portion",
            known_gap_not_covered="exact_restaurant_bento_or_full_composite_decomposition",
        ),
    ]


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
    cases = _cases()
    blockers = _validate(cases)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "track": "FoodDB_WebSearch",
            "claim_scope": "fooddb_grokfast_packet_narrow_seam_case_selection_contract",
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
                "websearch_cases": 0,
                "exact_card_cases": 0,
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
