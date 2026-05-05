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
    exact_top = top_candidate(exact)
    fuzzy_top = top_candidate(fuzzy)
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
    ]


def build_negative_cases(
    retrieval_records: tuple[IndexedFoodRecord, ...],
    *,
    websearch_pipeline: dict[str, Any],
) -> list[dict[str, Any]]:
    bare_basket = retrieve_fooddb_candidates("我吃滷味", retrieval_records=retrieval_records)
    exact_lane = build_exact_evidence_lane_policy_artifact()
    classifications = websearch_classifications(websearch_pipeline)
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
    ]
