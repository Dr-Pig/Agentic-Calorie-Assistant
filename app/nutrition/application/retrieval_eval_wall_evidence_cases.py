from __future__ import annotations

from typing import Any

from .exact_evidence_lane_policy import build_exact_evidence_lane_policy_artifact
from .food_evidence_packet_builder import (
    build_food_evidence_recall_packet,
    is_compact_food_evidence_packet,
)
from .fooddb_retrieval_policy import IndexedFoodRecord, retrieve_fooddb_candidates
from .retrieval_eval_wall_case_utils import (
    ranking_projection,
    status,
    top_candidate,
    websearch_classifications,
    websearch_runtime_truth_allowed_count,
)


def build_ranking_cases(retrieval_records: tuple[IndexedFoodRecord, ...]) -> list[dict[str, Any]]:
    exact = retrieve_fooddb_candidates("large boba", retrieval_records=retrieval_records)
    fuzzy = retrieve_fooddb_candidates("boba milk teaa", retrieval_records=retrieval_records)
    stable_single = retrieve_fooddb_candidates("\u8336\u8449\u86cb", retrieval_records=retrieval_records)
    listed_component = retrieve_fooddb_candidates("\u6d77\u5e36", retrieval_records=retrieval_records)
    generic_meal = retrieve_fooddb_candidates(
        "\u96de\u817f\u4fbf\u7576\u5c11\u98ef",
        retrieval_records=retrieval_records,
    )
    exact_top = top_candidate(exact)
    fuzzy_top = top_candidate(fuzzy)
    stable_single_top = top_candidate(stable_single)
    listed_component_top = top_candidate(listed_component)
    generic_meal_top = top_candidate(generic_meal)
    return [
        {
            "case_id": "alias_exact_ranking_prefers_runtime_anchor",
            "stage": "ranking",
            "status": status(
                {
                    "top_candidate_is_boba_anchor": exact_top.get("anchor_id")
                    == "custom_drink_boba_milk_tea",
                    "runtime_truth_boost_present": "runtime_truth_allowed"
                    in exact_top.get("ranking_reasons", []),
                    "modifier_compatibility_ranked": "modifier_compatible:cup_size"
                    in exact_top.get("ranking_reasons", []),
                }
            ),
            "top_candidate": ranking_projection(exact_top),
        },
        {
            "case_id": "fuzzy_candidate_requires_manager_disambiguation",
            "stage": "ranking",
            "status": status(
                {
                    "top_candidate_is_boba_anchor": fuzzy_top.get("anchor_id")
                    == "custom_drink_boba_milk_tea",
                    "fuzzy_path_used": str(fuzzy_top.get("match_path") or "").startswith("fuzzy"),
                    "manager_disambiguation_required": fuzzy_top.get(
                        "requires_manager_disambiguation"
                    )
                    is True,
                }
            ),
            "top_candidate": ranking_projection(fuzzy_top),
        },
        {
            "case_id": "stable_generic_anchor_uses_approved_common_serving",
            "stage": "ranking",
            "status": status(
                {
                    "top_candidate_is_tea_egg": stable_single_top.get("anchor_id")
                    == "single_item_tea_egg",
                    "high_confidence_exact_match": stable_single_top.get("confidence") == "high",
                    "serving_basis_present": stable_single_top.get("serving_basis")
                    == "common_serving",
                    "no_disambiguation_needed": stable_single_top.get(
                        "requires_manager_disambiguation"
                    )
                    is False,
                }
            ),
            "top_candidate": ranking_projection(stable_single_top),
        },
        {
            "case_id": "listed_component_ranking_prefers_approved_anchor",
            "stage": "ranking",
            "status": status(
                {
                    "top_candidate_is_kelp_anchor": listed_component_top.get("anchor_id")
                    == "listed_item_kelp",
                    "runtime_usage_boundary_is_listed_component": listed_component_top.get(
                        "runtime_usage_boundary"
                    )
                    == "listed_component_only",
                    "runtime_truth_boost_present": "runtime_truth_allowed"
                    in listed_component_top.get("ranking_reasons", []),
                }
            ),
            "top_candidate": ranking_projection(listed_component_top),
        },
        {
            "case_id": "generic_meal_modifier_keeps_range_and_followup",
            "stage": "ranking",
            "status": status(
                {
                    "top_candidate_is_chicken_bento": generic_meal_top.get("anchor_id")
                    == "generic_meal_chicken_bento",
                    "modifier_compatible_via_normalized_equivalent": (
                        generic_meal_top.get("modifier_compatibility") or {}
                    ).get("rice_portion")
                    == "compatible_via_normalized_equivalent",
                    "generic_range_not_exact": generic_meal_top.get("runtime_usage_boundary")
                    == "generic_range_estimate_only_not_exact",
                    "followup_hints_preserved": bool(generic_meal_top.get("followup_hints")),
                    "kcal_range_present": bool(generic_meal_top.get("kcal_range")),
                }
            ),
            "top_candidate": ranking_projection(generic_meal_top),
        },
    ]


def build_grounding_cases(
    retrieval_records: tuple[IndexedFoodRecord, ...],
    *,
    websearch_pipeline: dict[str, Any],
) -> list[dict[str, Any]]:
    retrieval = retrieve_fooddb_candidates("large boba", retrieval_records=retrieval_records)
    packet = build_food_evidence_recall_packet(
        packet_id="retrieval-eval-wall:boba",
        raw_user_input="large boba",
        retrieval_result=retrieval,
    )
    listed_retrieval = retrieve_fooddb_candidates(
        "\u6ef7\u5473\u6709\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38",
        retrieval_records=retrieval_records, listed_components=["\u8c46\u5e72", "\u6d77\u5e36", "\u8ca2\u4e38"],
    )
    listed_packet = build_food_evidence_recall_packet(
        packet_id="retrieval-eval-wall:listed-luwei",
        raw_user_input="listed luwei components",
        retrieval_result=listed_retrieval,
        manager_expected_behavior="estimate_listed_components_only",
    )
    classifications = websearch_classifications(websearch_pipeline)
    return [
        {
            "case_id": "fooddb_packet_is_compact_and_read_only",
            "stage": "grounding",
            "status": status(
                {
                    "compact_packet": is_compact_food_evidence_packet(packet),
                    "truth_selection_forbidden": packet["truth_selection_forbidden"] is True,
                    "runtime_mutation_forbidden": packet["runtime_mutation_allowed"] is False,
                    "raw_rows_excluded": packet["raw_source_rows_included"] is False,
                }
            ),
            "packet_projection": {
                "packet_type": packet["packet_type"],
                "evidence_item_count": len(packet["evidence_items"]),
                "rejected_candidate_count": packet["rejected_candidate_count"],
                "manager_may_use_for": list(packet["manager_may_use_for"]),
                "manager_must_not_use_for": list(packet["manager_must_not_use_for"]),
            },
        },
        {
            "case_id": "websearch_candidates_remain_candidate_only",
            "stage": "grounding",
            "status": status(
                {
                    "websearch_runtime_truth_count_zero": websearch_runtime_truth_allowed_count(
                        websearch_pipeline
                    )
                    == 0,
                    "candidate_classifications_present": bool(classifications),
                    "extract_candidates_still_not_runtime": all(
                        item.get("runtime_truth_allowed") is False
                        for item in classifications
                    ),
                }
            ),
            "classification_counts": dict(
                websearch_pipeline.get("summary", {}).get("classification_counts") or {}
            ),
        },
        {
            "case_id": "listed_component_packet_keeps_component_boundary",
            "stage": "grounding",
            "status": status(
                {
                    "compact_packet": is_compact_food_evidence_packet(listed_packet),
                    "listed_boundary": listed_packet["retrieval_boundary"]
                    == "listed_basket_component_recall",
                    "three_component_items": len(listed_packet["evidence_items"]) == 3,
                    "all_items_listed_component_only": all(
                        item.get("runtime_usage_boundary") == "listed_component_only"
                        for item in listed_packet["evidence_items"]
                    ),
                    "no_raw_rows": listed_packet["raw_source_rows_included"] is False,
                    "no_runtime_mutation": listed_packet["runtime_mutation_allowed"] is False,
                }
            ),
            "packet_projection": {
                "packet_type": listed_packet["packet_type"],
                "evidence_item_count": len(listed_packet["evidence_items"]),
                "retrieval_boundary": listed_packet["retrieval_boundary"],
                "anchor_ids": [
                    item.get("anchor_id") for item in listed_packet["evidence_items"]
                ],
                "runtime_usage_boundaries": sorted(
                    {
                        str(item.get("runtime_usage_boundary") or "")
                        for item in listed_packet["evidence_items"]
                    }
                ),
                "manager_must_not_use_for": list(listed_packet["manager_must_not_use_for"]),
            },
        },
    ]


def build_negative_cases(
    retrieval_records: tuple[IndexedFoodRecord, ...],
    *,
    websearch_pipeline: dict[str, Any],
) -> list[dict[str, Any]]:
    bare_basket = retrieve_fooddb_candidates("\u6211\u5403\u6ef7\u5473", retrieval_records=retrieval_records)
    listed_unknown = retrieve_fooddb_candidates(
        "\u6ef7\u5473\u6709\u8c46\u5e72\u3001\u672a\u77e5\u4e38",
        retrieval_records=retrieval_records, listed_components=["\u8c46\u5e72", "\u672a\u77e5\u4e38"],
    )
    exact_lane = build_exact_evidence_lane_policy_artifact()
    classifications = websearch_classifications(websearch_pipeline)
    risky_websearch_classes = {
        "near_exact_wrong_size_candidate",
        "blocked_source_policy_candidate",
        "weak_or_unusable_candidate",
    }
    return [
        {
            "case_id": "bare_basket_does_not_estimate",
            "stage": "negative",
            "status": status(
                {
                    "boundary_is_followup": bare_basket["retrieval_boundary"]
                    == "bare_basket_ask_followup_no_estimate",
                    "no_accepted_candidates": bare_basket["accepted_candidates"] == [],
                    "followup_hints_present": bool(bare_basket["followup_hints"]),
                }
            ),
            "retrieval_boundary": bare_basket["retrieval_boundary"],
        },
        {
            "case_id": "exact_candidates_do_not_mutate",
            "stage": "negative",
            "status": status(
                {
                    "exact_lane_runtime_mutation_forbidden": exact_lane[
                        "runtime_mutation_allowed"
                    ]
                    is False,
                    "all_exact_card_staging_candidates_non_runtime": all(
                        candidate.get("runtime_truth_allowed") is False
                        for case in exact_lane["cases"]
                        for candidate in case["exact_card_staging"]["candidates"]
                    ),
                    "websearch_candidates_non_runtime": all(
                        item.get("runtime_truth_allowed") is False for item in classifications
                    ),
                }
            ),
            "exact_card_staging_candidate_count": exact_lane["summary"][
                "exact_card_staging_candidate_count"
            ],
        },
        {
            "case_id": "listed_unknown_component_stays_partial_gap",
            "stage": "negative",
            "status": status(
                {
                    "listed_boundary": listed_unknown["retrieval_boundary"]
                    == "listed_basket_component_recall",
                    "known_component_retained": [
                        item.get("anchor_id") for item in listed_unknown["accepted_candidates"]
                    ]
                    == ["listed_item_tofu_dried"],
                    "unknown_component_rejected": bool(listed_unknown["rejected_candidates"]),
                    "rejected_not_invented": all(
                        item.get("reason") == "no_runtime_anchor_match"
                        for item in listed_unknown["rejected_candidates"]
                    ),
                }
            ),
            "accepted_anchor_ids": [
                item.get("anchor_id") for item in listed_unknown["accepted_candidates"]
            ],
            "rejected_candidates": list(listed_unknown["rejected_candidates"]),
        },
        {
            "case_id": "websearch_mismatch_candidates_do_not_ground_truth",
            "stage": "negative",
            "status": status(
                {
                    "risky_classes_present": bool(
                        {
                            item.get("candidate_class")
                            for item in classifications
                            if item.get("candidate_class") in risky_websearch_classes
                        }
                    ),
                    "risky_classes_non_runtime": all(
                        item.get("runtime_truth_allowed") is False
                        for item in classifications
                        if item.get("candidate_class") in risky_websearch_classes
                    ),
                    "no_websearch_runtime_truth": websearch_runtime_truth_allowed_count(
                        websearch_pipeline
                    )
                    == 0,
                }
            ),
            "risky_class_counts": {
                class_name: sum(
                    1
                    for item in classifications
                    if item.get("candidate_class") == class_name
                )
                for class_name in sorted(risky_websearch_classes)
            },
        },
    ]
