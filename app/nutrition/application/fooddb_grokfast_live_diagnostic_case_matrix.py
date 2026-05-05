from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .fooddb_manager_packet_smoke import FOODDB_PACKET_SMOKE_CASES


ARTIFACT_TYPE = "accurate_intake_fooddb_grokfast_packet_live_diagnostic_case_matrix_v1"
NEXT_REQUIRED_SLICE = "fooddb_modifier_seam_guard_repair"

EXPECTED_PACKET_FIELDS = (
    "packet_type",
    "case_id",
    "accepted_candidates",
    "rejected_candidates",
    "ambiguity_reason",
    "followup_hints",
    "confidence",
    "runtime_boundary",
)

NON_CLAIMS = (
    "not_full_self_use_gate",
    "not_websearch_exact_card_gate",
    "not_final_response_quality_gate",
    "not_production_readiness",
    "not_private_self_use_approval",
    "no_live_provider_call",
    "no_live_websearch_call",
    "no_runtime_truth_promotion",
    "no_runtime_mutation",
    "no_manager_context_change",
    "no_packetizer_format_change",
)

_BASE_MUST_NOT_HAPPEN = (
    "invent_nutrition_source",
    "intake_ledger_mutation",
    "claim_self_use_readiness",
    "treat_candidate_as_truth",
)

_CASE_POLICY: dict[str, dict[str, Any]] = {
    "boba_large_half_sugar": {
        "family": "modifier_guard",
        "expected_runtime_evidence_in_packet": True,
        "must_not_happen": (
            *_BASE_MUST_NOT_HAPPEN,
            "unsupported_modifier_kcal_adjustment",
            "treat_size_or_sugar_as_exact_without_packet_adjustment",
        ),
        "why_needed": "Checks the drink modifier seam before a live manager call can see FoodDB packets.",
        "known_gap_covered": (
            "drink_base_alias",
            "p0_size_modifier_guard",
            "p0_sugar_modifier_guard",
        ),
        "known_gap_not_covered": (
            "full_drink_modifier_calorie_model",
            "brand_menu_exact_card",
            "final_response_quality",
        ),
    },
    "boba_typo": {
        "family": "alias_typo_recall",
        "expected_runtime_evidence_in_packet": True,
        "must_not_happen": (
            *_BASE_MUST_NOT_HAPPEN,
            "typo_match_as_exact_truth",
            "invent_source_for_fuzzy_candidate",
        ),
        "why_needed": "Checks typo/fuzzy recall without letting lexical similarity become final evidence truth.",
        "known_gap_covered": ("cjk_typo_recall", "alias_fuzzy_packet_boundary"),
        "known_gap_not_covered": (
            "broad_typo_eval_wall",
            "semantic_vector_recall",
            "exact_variant_disambiguation",
        ),
    },
    "bare_luwei": {
        "family": "bare_basket_followup",
        "expected_runtime_evidence_in_packet": False,
        "must_not_happen": (
            *_BASE_MUST_NOT_HAPPEN,
            "estimate_bare_basket",
            "select_default_components",
        ),
        "why_needed": "Checks that a bare self-selected basket asks follow-up and never mutates from family detection alone.",
        "known_gap_covered": ("bare_basket_followup", "no_default_component_invention"),
        "known_gap_not_covered": (
            "listed_basket_component_quantity",
            "basket_exact_vendor_menu",
        ),
    },
    "listed_luwei_components": {
        "family": "listed_basket_components",
        "expected_runtime_evidence_in_packet": True,
        "must_not_happen": (
            *_BASE_MUST_NOT_HAPPEN,
            "estimate_unapproved_component",
            "turn_listed_components_into_whole_basket_anchor",
        ),
        "why_needed": "Checks listed basket fanout while keeping unknown or unapproved components out of runtime truth.",
        "known_gap_covered": (
            "listed_basket_component_path",
            "approved_component_only_boundary",
        ),
        "known_gap_not_covered": (
            "component_quantity_resolution",
            "all_luwei_components_coverage",
        ),
    },
    "chicken_bento_less_rice": {
        "family": "generic_meal_modifier_guard",
        "expected_runtime_evidence_in_packet": True,
        "must_not_happen": (
            *_BASE_MUST_NOT_HAPPEN,
            "exact_bento_claim",
            "unsupported_modifier_kcal_adjustment",
            "silently_rewrite_less_rice_to_exact_portion",
        ),
        "why_needed": "Checks generic meal evidence plus rice modifier posture without converting a bento range into an exact card.",
        "known_gap_covered": (
            "generic_meal_range_anchor",
            "p0_rice_modifier_guard",
        ),
        "known_gap_not_covered": (
            "fried_vs_braised_chicken_disambiguation",
            "side_dish_breakdown",
            "exact_restaurant_card",
        ),
    },
}


def build_fooddb_grokfast_live_diagnostic_case_matrix() -> dict[str, Any]:
    cases = [_case_matrix_row(case) for case in FOODDB_PACKET_SMOKE_CASES]
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "live_diagnostic_plan_only",
        "claim_scope": "fooddb_grokfast_packet_narrow_seam_case_matrix",
        "live_provider_invoked": False,
        "live_websearch_invoked": False,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "full_self_use_gate": False,
        "websearch_exact_card_gate": False,
        "final_response_quality_gate": False,
        "production_readiness": False,
        "next_required_slice": NEXT_REQUIRED_SLICE,
        "cases": cases,
        "summary": _summary(cases),
        "later_expansion_candidates": {
            "generic_anchor": ["\u8336\u8449\u86cb", "\u725b\u8089\u9eb5"],
            "exact_card_websearch": [
                "wrong_brand",
                "wrong_size",
                "official_missing_nutrition",
            ],
            "additional_modifiers": [
                "\u7121\u7cd6",
                "\u5c0f\u676f/\u4e2d\u676f/\u5927\u676f",
                "\u52a0\u73cd\u73e0/\u53bb\u73cd\u73e0",
            ],
        },
        "non_claims": list(NON_CLAIMS),
        "best_practice_basis": {
            "trace_level_eval": "case matrix defines observable seam expectations before provider trace grading",
            "tool_loop_boundary": "FoodDB/WebSearch packets provide data only; manager behavior is checked later",
            "structured_output_boundary": "case rows state expected packet fields without changing manager schema",
        },
    }


def _case_matrix_row(case: Any) -> dict[str, Any]:
    policy = _CASE_POLICY[case.case_id]
    return {
        "case_id": case.case_id,
        "user_utterance": case.raw_input,
        "family": policy["family"],
        "expected_manager_posture": case.expected_behavior,
        "expected_packet_fields": list(EXPECTED_PACKET_FIELDS),
        "must_not_happen": list(policy["must_not_happen"]),
        "live_provider_invoked": False,
        "websearch_invoked": False,
        "ledger_mutation_allowed": False,
        "runtime_truth_allowed": False,
        "expected_runtime_evidence_in_packet": bool(
            policy["expected_runtime_evidence_in_packet"]
        ),
        "why_needed": policy["why_needed"],
        "known_gap_covered": list(policy["known_gap_covered"]),
        "known_gap_not_covered": list(policy["known_gap_not_covered"]),
    }


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    families: dict[str, int] = {}
    for case in cases:
        family = str(case["family"])
        families[family] = families.get(family, 0) + 1
    return {
        "case_count": len(cases),
        "case_ids": [case["case_id"] for case in cases],
        "families": families,
        "live_provider_case_count": sum(1 for case in cases if case["live_provider_invoked"]),
        "websearch_case_count": sum(1 for case in cases if case["websearch_invoked"]),
        "ledger_mutation_allowed_case_count": sum(
            1 for case in cases if case["ledger_mutation_allowed"]
        ),
        "runtime_truth_allowed_case_count": sum(
            1 for case in cases if case["runtime_truth_allowed"]
        ),
        "expected_runtime_evidence_in_packet_case_count": sum(
            1 for case in cases if case["expected_runtime_evidence_in_packet"]
        ),
        "narrow_live_diagnostic_ready_after_preflight": True,
        "full_self_use_gate": False,
        "websearch_exact_card_gate": False,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "ARTIFACT_TYPE",
    "NEXT_REQUIRED_SLICE",
    "build_fooddb_grokfast_live_diagnostic_case_matrix",
]
