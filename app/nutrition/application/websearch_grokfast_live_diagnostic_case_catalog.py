from __future__ import annotations

import json
from typing import Any


REQUIRED_CASE_IDS = (
    "websearch_official_exact_candidate",
    "websearch_official_pdf_exact_candidate",
    "websearch_convenience_store_rice_ball",
    "websearch_chain_restaurant_menu_item",
    "websearch_wrong_brand_official",
    "websearch_wrong_size_candidate",
    "websearch_same_brand_wrong_flavor",
    "websearch_wrong_country_menu",
    "websearch_official_missing_nutrition",
    "websearch_third_party_weak_source",
    "websearch_modifier_mismatch",
)
REQUIRED_EXACT_CANDIDATE_CASE_COUNT = 4
REQUIRED_NEGATIVE_CASE_COUNT = 6
REQUIRED_IDENTITY_MISMATCH_CASE_COUNT = 4
REQUIRED_MISSING_NUTRITION_CASE_COUNT = 1
REQUIRED_WEAK_SOURCE_CASE_COUNT = 1
REQUIRED_MODIFIER_GUARD_CASE_COUNT = 1

_COMMON_FIELDS = [
    "case_id",
    "packet_id",
    "raw_user_input",
    "candidate_boundary",
    "source_url",
    "source_title",
    "source_quality",
    "identity_confidence",
    "serving_basis_candidate",
]
_NO_OVERCLAIM = [
    "runtime_ledger_mutation",
    "websearch_snippet_as_truth",
    "exact_card_created",
    "selected_extract_promoted_to_truth",
    "invented_nutrition_source",
    "candidate_used_as_item_result",
    "self_use_readiness_claimed",
]


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _case(
    case_id: str,
    user_utterance: str,
    family: str,
    expected_manager_posture: str,
    extra_fields: list[str],
    extra_must_not_happen: list[str],
    expected_candidate_boundary: str,
    why_needed: str,
    known_gap_covered: str,
    known_gap_not_covered: str,
) -> dict[str, Any]:
    return _json_safe(
        {
            "case_id": case_id,
            "user_utterance": user_utterance,
            "family": family,
            "expected_manager_posture": expected_manager_posture,
            "expected_packet_fields": [*_COMMON_FIELDS, *extra_fields],
            "expected_candidate_boundary": expected_candidate_boundary,
            "must_not_happen": [*_NO_OVERCLAIM, *extra_must_not_happen],
            "live_provider_invoked": False,
            "websearch_invoked": False,
            "ledger_mutation_allowed": False,
            "runtime_truth_allowed": False,
            "websearch_candidate_only": True,
            "snippet_truth_allowed": False,
            "exact_card_creation_allowed": False,
            "selected_extract_truth_allowed": False,
            "raw_content_allowed_in_manager_context": False,
            "why_needed": why_needed,
            "known_gap_covered": known_gap_covered,
            "known_gap_not_covered": known_gap_not_covered,
            "semantic_owner": "Manager LLM during later live diagnostic",
            "deterministic_role": "case_selection_guard_and_candidate_misuse_validator",
            "runtime_truth_changed": False,
            "mutation_changed": False,
            "manager_context_packet_changed": False,
            "packetizer_format_changed": False,
            "product_readiness_claimed": False,
        }
    )


def build_websearch_grokfast_live_diagnostic_cases() -> list[dict[str, Any]]:
    return [
        _case("websearch_official_exact_candidate", "Milksha pearl black tea latte calories", "exact_candidate_candidate_only", "answer_or_defer_with_candidate_review_only", ["officialness", "kcal_text_present"], ["official_candidate_marked_packet_ready"], "candidate_only_even_if_identity_and_kcal_text_match", "Covers the tempting happy path: an official near-exact source still remains candidate-only until a separate promotion lane approves it.", "official_exact_candidate_no_truth_shortcut", "brand_exact_card_runtime_promotion"),
        _case("websearch_official_pdf_exact_candidate", "Milksha pearl black tea latte nutrition PDF", "exact_candidate_candidate_only", "answer_or_defer_with_candidate_review_only", ["officialness", "source_class", "kcal_text_present"], ["official_pdf_candidate_marked_packet_ready"], "official_pdf_candidate_remains_candidate_only_until_review", "Covers the stronger official exact lane: even an official nutrition PDF still remains candidate-only and cannot short-circuit exact-card promotion.", "official_pdf_candidate_no_truth_shortcut", "official_pdf_extract_runtime_promotion"),
        _case("websearch_convenience_store_rice_ball", "7-Eleven salmon rice ball calories", "exact_candidate_candidate_only", "answer_or_defer_with_candidate_review_only", ["brand_detected", "officialness", "serving_basis_candidate"], ["packaged_candidate_promoted_without_review"], "convenience_store_exact_candidate_stays_review_only", "Covers a common convenience-store exact case so the live seam is not limited to one drink-family happy path.", "convenience_store_exact_candidate_review_lane", "runtime_exact_card_promotion_for_packaged_items"),
        _case("websearch_chain_restaurant_menu_item", "Matsuya gyudon large calories", "exact_candidate_candidate_only", "answer_or_defer_with_candidate_review_only", ["brand_detected", "officialness", "serving_basis_candidate"], ["chain_menu_candidate_used_as_runtime_truth"], "chain_menu_exact_candidate_stays_review_only", "Covers a chain-restaurant exact menu item so live diagnostics exercise a non-drink branded source without turning it into nutrition truth.", "chain_menu_exact_candidate_review_lane", "runtime_exact_card_promotion_for_chain_menu_items"),
        _case("websearch_wrong_brand_official", "Milksha pearl black tea latte calories", "negative_wrong_brand", "reject_or_ask_followup_no_mutation", ["brand_detected", "brand_mismatch_risk"], ["wrong_brand_presented_as_exact_match"], "wrong_brand_candidate_rejected_or_requires_followup", "Prevents official-looking but wrong-brand pages from becoming exact evidence.", "brand_mismatch_negative_case", "all_regional_brand_aliases"),
        _case("websearch_wrong_size_candidate", "Starbucks iced latte large calories", "negative_wrong_size", "ask_followup_or_reject_size_mismatch_no_mutation", ["size_hint", "size_mismatch_risk"], ["medium_size_used_for_large_exact_answer"], "wrong_size_candidate_rejected_or_requires_followup", "Prevents exact item shortcut when size or serving variant mismatches.", "size_variant_negative_case", "full_size_conversion_policy"),
        _case("websearch_same_brand_wrong_flavor", "Milksha pearl black tea latte calories", "negative_wrong_variant", "reject_or_ask_followup_no_mutation", ["brand_detected", "brand_mismatch_risk"], ["same_brand_wrong_flavor_presented_as_exact_match"], "same_brand_wrong_flavor_requires_followup_not_exact_match", "Prevents same-brand sibling variants from being treated as exact evidence just because the brand matches.", "same_brand_wrong_flavor_negative_case", "full_same_brand_variant_resolution"),
        _case("websearch_wrong_country_menu", "Milksha pearl black tea latte calories", "negative_wrong_country", "reject_or_ask_followup_no_mutation", ["brand_detected", "brand_mismatch_risk"], ["wrong_country_menu_presented_as_exact_match"], "wrong_country_menu_requires_followup_not_exact_match", "Prevents region-mismatched official pages from becoming exact evidence when the menu lineage is still ambiguous.", "wrong_country_menu_negative_case", "region_specific_variant_resolution"),
        _case("websearch_official_missing_nutrition", "Milksha pearl black tea latte calories", "negative_missing_nutrition", "request_better_source_or_defer_no_mutation", ["nutrition_fields_present"], ["kcal_invented_from_official_identity_only"], "official_identity_without_kcal_is_not_nutrition_truth", "Prevents identity-only official pages from being treated as nutrition evidence.", "official_missing_nutrition_negative_case", "live_page_extraction_quality"),
        _case("websearch_third_party_weak_source", "Milksha pearl black tea latte calories", "negative_weak_source", "reject_weak_source_or_answer_candidate_limitations", ["source_quality_label", "officialness"], ["third_party_snippet_as_exact_truth"], "third_party_weak_source_candidate_only", "Prevents low-quality calorie snippets from becoming evidence truth.", "weak_source_negative_case", "broad_web_source_trust_model"),
        _case("websearch_modifier_mismatch", "Milksha pearl black tea latte half sugar calories", "modifier_mismatch_guard", "ask_followup_or_keep_candidate_pending_no_mutation", ["modifier_hints", "customization_slots_present"], ["half_sugar_kcal_adjusted_without_packet_support"], "base_item_candidate_does_not_cover_modifier_variant", "Prevents Manager-side calorie math when WebSearch candidate lacks modifier evidence.", "websearch_modifier_mismatch_guard", "brand_menu_modifier_nutrition_extraction"),
    ]


__all__ = [
    "REQUIRED_CASE_IDS",
    "REQUIRED_EXACT_CANDIDATE_CASE_COUNT",
    "REQUIRED_NEGATIVE_CASE_COUNT",
    "REQUIRED_IDENTITY_MISMATCH_CASE_COUNT",
    "REQUIRED_MISSING_NUTRITION_CASE_COUNT",
    "REQUIRED_WEAK_SOURCE_CASE_COUNT",
    "REQUIRED_MODIFIER_GUARD_CASE_COUNT",
    "build_websearch_grokfast_live_diagnostic_cases",
]
