from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.nutrition.application.fooddb_manager_packet_smoke import FOODDB_PACKET_SMOKE_CASES


_REPO_ROOT = Path(__file__).resolve().parents[3]
_CURRENT_SHELL_LIVE_MANIFEST = _REPO_ROOT / "docs" / "quality" / "accurate_intake_mvp_live_diagnostic_case_manifest.json"
REQUIRED_CASE_IDS = ("boba_large_half_sugar", "boba_typo", "bare_luwei", "listed_luwei_components", "chicken_bento_less_rice", "exact_item_official_label", "food_query_no_mutation", "macro_missing_hidden")
NON_CLAIMS = ("not_full_self_use_gate", "not_websearch_exact_card_gate", "not_final_response_quality_gate", "not_production_readiness", "not_private_self_use_approval", "not_kimi_activation", "not_runtime_mutation_gate")


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _case(
    *,
    case_id: str,
    utterance: str,
    family: str,
    canonical_manifest_case_id: str | None,
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
            "canonical_manifest_case_id": canonical_manifest_case_id,
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


def _manifest_utterance(case_id: str) -> str:
    manifest = json.loads(_CURRENT_SHELL_LIVE_MANIFEST.read_text(encoding="utf-8-sig"))
    by_id = {case["case_id"]: case for case in manifest["cases"]}
    turns = by_id[case_id]["turns"]
    return str(turns[0]["utterance_zh_tw"])


def build_fooddb_grokfast_live_diagnostic_cases() -> list[dict[str, Any]]:
    common_packet_fields = ["case_id", "packet_id", "raw_user_input", "manager_expected_behavior", "evidence_items", "followup_hints"]
    no_live_overclaim = ["self_use_readiness_claimed", "runtime_ledger_mutation", "invented_nutrition_source", "websearch_snippet_as_truth", "candidate_promoted_to_truth"]
    return [
        _case(
            case_id="boba_large_half_sugar",
            utterance=_smoke_utterance("boba_large_half_sugar"),
            family="modifier_guard",
            canonical_manifest_case_id="MVP-LIVE-006",
            expected_manager_posture="estimate_from_packet_with_uncertainty",
            expected_packet_fields=common_packet_fields + ["modifier_compatibility", "kcal_point", "kcal_range"],
            must_not_happen=[*no_live_overclaim, "size_or_sugar_kcal_adjusted_without_packet_adjustment"],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers P0 drink modifiers while preventing Manager-side calorie math.",
            known_gap_covered="drink_size_and_sugar_modifier_guard",
            known_gap_not_covered="full_drink_menu_exact_card_or_brand_specific_nutrition",
        ),
        _case(
            case_id="boba_typo",
            utterance=_smoke_utterance("boba_typo"),
            family="fuzzy_alias",
            canonical_manifest_case_id=None,
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
            canonical_manifest_case_id="MVP-LIVE-008",
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
            canonical_manifest_case_id="MVP-LIVE-009",
            expected_manager_posture="estimate_listed_components_only",
            expected_packet_fields=common_packet_fields + ["component_items", "runtime_usage_boundary", "kcal_range"],
            must_not_happen=[*no_live_overclaim, "unknown_component_calorie_invented", "basket_total_estimated_from_family_label"],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers listed basket fanout using only approved component anchors.",
            known_gap_covered="listed_luwei_component_estimation_boundary",
            known_gap_not_covered="missing_component_partial_estimate_policy_beyond_this_case",
        ),
        _case(
            case_id="chicken_bento_less_rice",
            utterance=_smoke_utterance("chicken_bento_less_rice"),
            family="generic_anchor_modifier_guard",
            canonical_manifest_case_id="MVP-LIVE-005",
            expected_manager_posture="generic_range_estimate_with_followup_hints",
            expected_packet_fields=common_packet_fields + ["variance_level", "modifier_compatibility"],
            must_not_happen=[*no_live_overclaim, "less_rice_kcal_adjusted_without_packet_adjustment", "generic_bento_presented_as_exact_truth"],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers generic meal range plus rice modifier guard.",
            known_gap_covered="generic_meal_modifier_guard_for_rice_portion",
            known_gap_not_covered="exact_restaurant_bento_or_full_composite_decomposition",
        ),
        _case(
            case_id="exact_item_official_label",
            utterance="統一巧克力牛乳 400ml",
            family="exact_item_card",
            canonical_manifest_case_id="MVP-LIVE-004",
            expected_manager_posture="commit_exact_item_when_packet_supports_exactness",
            expected_packet_fields=common_packet_fields + ["source_provenance", "kcal_point", "macro_fields", "runtime_usage_boundary"],
            must_not_happen=[*no_live_overclaim, "exact_item_claimed_without_supported_source", "macro_claimed_without_packet_macro_fields"],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers exact item logging with supported exactness and macro visibility.",
            known_gap_covered="exact_item_official_label_fooddb_path",
            known_gap_not_covered="brand resolution via live WebSearch fallback",
        ),
        _case(
            case_id="food_query_no_mutation",
            utterance=_manifest_utterance("MVP-LIVE-014"),
            family="query_only_food_answer",
            canonical_manifest_case_id="MVP-LIVE-014",
            expected_manager_posture="answer_only_no_mutation",
            expected_packet_fields=common_packet_fields + ["runtime_usage_boundary", "kcal_range"],
            must_not_happen=[*no_live_overclaim, "food_query_presented_as_logged", "food_query_triggered_ledger_mutation"],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers query-only food lookup without accidental meal logging.",
            known_gap_covered="food_answer_only_no_mutation_boundary",
            known_gap_not_covered="general nutrition coaching outside current shell",
        ),
        _case(
            case_id="macro_missing_hidden",
            utterance=_manifest_utterance("MVP-LIVE-017"),
            family="macro_visibility_hidden",
            canonical_manifest_case_id="MVP-LIVE-017",
            expected_manager_posture="commit_without_macro_claims",
            expected_packet_fields=common_packet_fields + ["kcal_point", "macro_visibility", "macro_guard_reason"],
            must_not_happen=[*no_live_overclaim, "invented_macro_claim", "macro_hidden_case_presented_as_macro_visible"],
            expected_runtime_evidence_in_packet=True,
            why_needed="Covers calorie logging when macro data is missing but must stay hidden.",
            known_gap_covered="macro_missing_hidden_no_invention_boundary",
            known_gap_not_covered="day-level macro completeness rollup beyond the packet seam",
        ),
    ]


__all__ = [
    "NON_CLAIMS",
    "REQUIRED_CASE_IDS",
    "build_fooddb_grokfast_live_diagnostic_cases",
]
