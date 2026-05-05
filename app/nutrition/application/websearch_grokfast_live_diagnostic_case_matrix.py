from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any


REQUIRED_CASE_IDS = (
    "websearch_official_exact_candidate",
    "websearch_wrong_brand_official",
    "websearch_wrong_size_candidate",
    "websearch_official_missing_nutrition",
    "websearch_third_party_weak_source",
    "websearch_modifier_mismatch",
)

NON_CLAIMS = (
    "not_full_self_use_gate",
    "not_fooddb_generic_anchor_gate",
    "not_websearch_runtime_truth_gate",
    "not_exact_card_promotion_gate",
    "not_final_response_quality_gate",
    "not_production_readiness",
    "not_private_self_use_approval",
    "not_kimi_activation",
    "not_runtime_mutation_gate",
    "not_live_websearch_execution",
)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _case(
    *,
    case_id: str,
    user_utterance: str,
    family: str,
    expected_manager_posture: str,
    expected_packet_fields: list[str],
    must_not_happen: list[str],
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
            "expected_packet_fields": expected_packet_fields,
            "expected_candidate_boundary": expected_candidate_boundary,
            "must_not_happen": must_not_happen,
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


def _cases() -> list[dict[str, Any]]:
    common_fields = [
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
    no_overclaim = [
        "runtime_ledger_mutation",
        "websearch_snippet_as_truth",
        "exact_card_created",
        "selected_extract_promoted_to_truth",
        "invented_nutrition_source",
        "candidate_used_as_item_result",
        "self_use_readiness_claimed",
    ]
    return [
        _case(
            case_id="websearch_official_exact_candidate",
            user_utterance="Milksha pearl black tea latte calories",
            family="exact_candidate_candidate_only",
            expected_manager_posture="answer_or_defer_with_candidate_review_only",
            expected_packet_fields=common_fields + ["officialness", "kcal_text_present"],
            expected_candidate_boundary="candidate_only_even_if_identity_and_kcal_text_match",
            must_not_happen=[*no_overclaim, "official_candidate_marked_packet_ready"],
            why_needed=(
                "Covers the tempting happy path: an official near-exact source still "
                "remains candidate-only until a separate promotion lane approves it."
            ),
            known_gap_covered="official_exact_candidate_no_truth_shortcut",
            known_gap_not_covered="brand_exact_card_runtime_promotion",
        ),
        _case(
            case_id="websearch_wrong_brand_official",
            user_utterance="Milksha pearl black tea latte calories",
            family="negative_wrong_brand",
            expected_manager_posture="reject_or_ask_followup_no_mutation",
            expected_packet_fields=common_fields + ["brand_detected", "brand_mismatch_risk"],
            expected_candidate_boundary="wrong_brand_candidate_rejected_or_requires_followup",
            must_not_happen=[*no_overclaim, "wrong_brand_presented_as_exact_match"],
            why_needed="Prevents official-looking but wrong-brand pages from becoming exact evidence.",
            known_gap_covered="brand_mismatch_negative_case",
            known_gap_not_covered="all_regional_brand_aliases",
        ),
        _case(
            case_id="websearch_wrong_size_candidate",
            user_utterance="Starbucks iced latte large calories",
            family="negative_wrong_size",
            expected_manager_posture="ask_followup_or_reject_size_mismatch_no_mutation",
            expected_packet_fields=common_fields + ["size_hint", "size_mismatch_risk"],
            expected_candidate_boundary="wrong_size_candidate_rejected_or_requires_followup",
            must_not_happen=[*no_overclaim, "medium_size_used_for_large_exact_answer"],
            why_needed="Prevents exact item shortcut when size or serving variant mismatches.",
            known_gap_covered="size_variant_negative_case",
            known_gap_not_covered="full_size_conversion_policy",
        ),
        _case(
            case_id="websearch_official_missing_nutrition",
            user_utterance="Milksha pearl black tea latte calories",
            family="negative_missing_nutrition",
            expected_manager_posture="request_better_source_or_defer_no_mutation",
            expected_packet_fields=common_fields + ["nutrition_fields_present"],
            expected_candidate_boundary="official_identity_without_kcal_is_not_nutrition_truth",
            must_not_happen=[*no_overclaim, "kcal_invented_from_official_identity_only"],
            why_needed="Prevents identity-only official pages from being treated as nutrition evidence.",
            known_gap_covered="official_missing_nutrition_negative_case",
            known_gap_not_covered="live_page_extraction_quality",
        ),
        _case(
            case_id="websearch_third_party_weak_source",
            user_utterance="Milksha pearl black tea latte calories",
            family="negative_weak_source",
            expected_manager_posture="reject_weak_source_or_answer_candidate_limitations",
            expected_packet_fields=common_fields + ["source_quality_label", "officialness"],
            expected_candidate_boundary="third_party_weak_source_candidate_only",
            must_not_happen=[*no_overclaim, "third_party_snippet_as_exact_truth"],
            why_needed="Prevents low-quality calorie snippets from becoming evidence truth.",
            known_gap_covered="weak_source_negative_case",
            known_gap_not_covered="broad_web_source_trust_model",
        ),
        _case(
            case_id="websearch_modifier_mismatch",
            user_utterance="Milksha pearl black tea latte half sugar calories",
            family="modifier_mismatch_guard",
            expected_manager_posture="ask_followup_or_keep_candidate_pending_no_mutation",
            expected_packet_fields=common_fields + ["modifier_hints", "customization_slots_present"],
            expected_candidate_boundary="base_item_candidate_does_not_cover_modifier_variant",
            must_not_happen=[*no_overclaim, "half_sugar_kcal_adjusted_without_packet_support"],
            why_needed="Prevents Manager-side calorie math when WebSearch candidate lacks modifier evidence.",
            known_gap_covered="websearch_modifier_mismatch_guard",
            known_gap_not_covered="brand_menu_modifier_nutrition_extraction",
        ),
    ]


def _validate(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    case_ids = [str(case.get("case_id") or "") for case in cases]
    if case_ids != list(REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")

    required_families = {
        "exact_candidate_candidate_only",
        "negative_wrong_brand",
        "negative_wrong_size",
        "negative_missing_nutrition",
        "negative_weak_source",
        "modifier_mismatch_guard",
    }
    families = {str(case.get("family") or "") for case in cases}
    for family in sorted(required_families - families):
        blockers.append(f"missing_family.{family}")

    for case in cases:
        case_id = str(case.get("case_id") or "unknown")
        if not case.get("user_utterance"):
            blockers.append(f"{case_id}.user_utterance_missing")
        if not case.get("expected_manager_posture"):
            blockers.append(f"{case_id}.expected_manager_posture_missing")
        expected_fields = case.get("expected_packet_fields")
        if not isinstance(expected_fields, list) or "candidate_boundary" not in expected_fields:
            blockers.append(f"{case_id}.expected_packet_fields_missing_candidate_boundary")
        must_not_happen = case.get("must_not_happen")
        if not isinstance(must_not_happen, list) or "websearch_snippet_as_truth" not in must_not_happen:
            blockers.append(f"{case_id}.snippet_truth_guard_missing")
        for key in (
            "live_provider_invoked",
            "websearch_invoked",
            "ledger_mutation_allowed",
            "runtime_truth_allowed",
            "snippet_truth_allowed",
            "exact_card_creation_allowed",
            "selected_extract_truth_allowed",
            "raw_content_allowed_in_manager_context",
            "runtime_truth_changed",
            "mutation_changed",
            "manager_context_packet_changed",
            "packetizer_format_changed",
            "product_readiness_claimed",
        ):
            if case.get(key) is not False:
                blockers.append(f"{case_id}.{key}")
        if case.get("websearch_candidate_only") is not True:
            blockers.append(f"{case_id}.websearch_candidate_only_not_true")
        if case.get("family", "").startswith("negative_"):
            posture = str(case.get("expected_manager_posture") or "")
            if not any(token in posture for token in ("reject", "ask_followup", "request_better_source")):
                blockers.append(f"{case_id}.negative_case_posture_not_reject_or_followup")
        if case.get("family") == "modifier_mismatch_guard":
            if "half_sugar_kcal_adjusted_without_packet_support" not in must_not_happen:
                blockers.append(f"{case_id}.modifier_math_guard_missing")
    return blockers


def build_websearch_grokfast_live_diagnostic_case_matrix_artifact() -> dict[str, Any]:
    cases = _cases()
    blockers = _validate(cases)
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix",
            "status": "pass" if not blockers else "fail",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "track": "FoodDB_WebSearch",
            "claim_scope": "websearch_grokfast_packet_narrow_seam_case_selection_contract",
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
            "packetizer_format_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "blockers": blockers,
            "summary": {
                "case_count": len(cases),
                "exact_candidate_cases": sum(
                    1 for case in cases if case["family"] == "exact_candidate_candidate_only"
                ),
                "negative_case_count": sum(
                    1 for case in cases if str(case["family"]).startswith("negative_")
                ),
                "identity_mismatch_case_count": sum(
                    1 for case in cases if case["family"] in {"negative_wrong_brand", "negative_wrong_size"}
                ),
                "missing_nutrition_case_count": sum(
                    1 for case in cases if case["family"] == "negative_missing_nutrition"
                ),
                "weak_source_case_count": sum(
                    1 for case in cases if case["family"] == "negative_weak_source"
                ),
                "modifier_guard_cases": sum(
                    1 for case in cases if case["family"] == "modifier_mismatch_guard"
                ),
                "runtime_truth_allowed_cases": 0,
                "websearch_invoked_cases": 0,
                "live_provider_invoked_cases": 0,
            },
            "non_claims": list(NON_CLAIMS),
            "later_expansion_candidates": {
                "official_brand_positive": [
                    "convenience_store_rice_ball",
                    "chain_restaurant_menu_item",
                ],
                "negative_mismatch": [
                    "wrong_flavor",
                    "wrong_country_menu",
                    "serving_size_not_listed",
                ],
                "source_quality": [
                    "official_pdf_with_nutrition_table",
                    "brand_page_without_nutrition",
                    "third_party_blog_snippet",
                ],
            },
            "cases": cases,
        }
    )


__all__ = [
    "REQUIRED_CASE_IDS",
    "build_websearch_grokfast_live_diagnostic_case_matrix_artifact",
]
