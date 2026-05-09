from __future__ import annotations

EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES = {
    "exact_item_card": {
        "source_lane": "exact_item_card",
        "item_id": "exact_unified_chocolate_milk_400ml",
        "kcal_point": 300,
        "kcal_range": [300, 300],
        "macro_visibility_status": "visible",
        "macro_state": "visible",
        "protein_text": "12",
        "carbs_text": "48",
        "fat_text": "6",
        "macro_guard_reason_text": "",
        "packet_is_not_mutation_authority": True,
    },
    "generic_common_serving": {
        "source_lane": "generic_common_serving",
        "item_id": "generic_meal_chicken_bento",
        "kcal_point": 780,
        "kcal_range": [650, 900],
        "macro_visibility_status": "hidden_missing_source",
        "macro_state": "guarded",
        "protein_text": "--",
        "carbs_text": "--",
        "fat_text": "--",
        "macro_guard_reason_text": "hidden_missing_source",
        "packet_is_not_mutation_authority": True,
    },
    "listed_component": {
        "source_lane": "listed_component",
        "item_id": "listed_item_tofu_dried",
        "kcal_point": 95,
        "kcal_range": [70, 120],
        "macro_visibility_status": "hidden_missing_source",
        "macro_state": "guarded",
        "protein_text": "--",
        "carbs_text": "--",
        "fat_text": "--",
        "macro_guard_reason_text": "hidden_missing_source",
        "packet_is_not_mutation_authority": True,
    },
}

FOODDB_TRIAD_SAME_TRUTH_REQUIRED_NON_CLAIMS = (
    "live_llm_invoked",
    "web_tavily_used",
    "fooddb_truth_updated",
    "real_fooddb_pass_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "frontend_semantic_owner",
    "frontend_calculates_macro_values",
    "assistant_text_macro_parsed",
)


def _object_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def fooddb_triad_same_truth_blockers(
    group_id: str,
    payload: dict[str, object],
) -> list[str]:
    blockers: list[str] = []
    if payload.get("fooddb_triad_same_truth_browser_checked") is not True:
        blockers.append(f"{group_id}.fooddb_triad_same_truth_browser_checked_not_true")
    cases = _object_dict(payload.get("fooddb_triad_same_truth_cases"))
    for lane, expected in EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES.items():
        actual = _object_dict(cases.get(lane))
        if not actual:
            blockers.append(f"{group_id}.fooddb_triad_same_truth_case_missing:{lane}")
            continue
        for field, expected_value in expected.items():
            if actual.get(field) != expected_value:
                blockers.append(f"{group_id}.fooddb_triad_same_truth_case_mismatch:{lane}:{field}")
    non_claims = _object_dict(payload.get("fooddb_triad_same_truth_non_claims"))
    for flag in FOODDB_TRIAD_SAME_TRUTH_REQUIRED_NON_CLAIMS:
        if non_claims.get(flag) is not False:
            blockers.append(f"{group_id}.fooddb_triad_same_truth_non_claim_overclaim:{flag}")
    return blockers


def fooddb_triad_same_truth_checked(payload: dict[str, object]) -> bool:
    return not fooddb_triad_same_truth_blockers("product_pages_browser_smoke", payload)
