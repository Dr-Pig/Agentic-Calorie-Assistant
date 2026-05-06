from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from .websearch_grokfast_live_diagnostic_case_catalog import (
    REQUIRED_CASE_IDS,
    REQUIRED_EXACT_CANDIDATE_CASE_COUNT,
    REQUIRED_IDENTITY_MISMATCH_CASE_COUNT,
    REQUIRED_MISSING_NUTRITION_CASE_COUNT,
    REQUIRED_MODIFIER_GUARD_CASE_COUNT,
    REQUIRED_NEGATIVE_CASE_COUNT,
    REQUIRED_WEAK_SOURCE_CASE_COUNT,
    build_websearch_grokfast_live_diagnostic_cases,
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


def _validate(cases: list[dict[str, Any]]) -> list[str]:
    blockers: list[str] = []
    case_ids = [str(case.get("case_id") or "") for case in cases]
    if case_ids != list(REQUIRED_CASE_IDS):
        blockers.append("required_case_order_mismatch")

    required_families = {
        "exact_candidate_candidate_only",
        "negative_wrong_brand",
        "negative_wrong_size",
        "negative_wrong_variant",
        "negative_wrong_country",
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
    cases = build_websearch_grokfast_live_diagnostic_cases()
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
                    1
                    for case in cases
                    if case["family"]
                    in {
                        "negative_wrong_brand",
                        "negative_wrong_size",
                        "negative_wrong_variant",
                        "negative_wrong_country",
                    }
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
                    "large_size_preferred",
                    "modifier_same_candidate",
                ],
                "negative_mismatch": [
                    "serving_size_not_listed",
                    "size_unknown_requires_followup",
                ],
                "source_quality": [
                    "brand_page_without_nutrition",
                    "third_party_blog_snippet",
                    "all_candidates_blocked_source_policy",
                ],
            },
            "cases": cases,
        }
    )


__all__ = [
    "REQUIRED_CASE_IDS",
    "REQUIRED_EXACT_CANDIDATE_CASE_COUNT",
    "REQUIRED_NEGATIVE_CASE_COUNT",
    "REQUIRED_IDENTITY_MISMATCH_CASE_COUNT",
    "REQUIRED_MISSING_NUTRITION_CASE_COUNT",
    "REQUIRED_WEAK_SOURCE_CASE_COUNT",
    "REQUIRED_MODIFIER_GUARD_CASE_COUNT",
    "build_websearch_grokfast_live_diagnostic_case_matrix_artifact",
]
