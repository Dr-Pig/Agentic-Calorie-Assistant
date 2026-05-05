from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .exact_evidence_lane_policy import build_exact_evidence_lane_policy_artifact
from .food_evidence_packet_builder import (
    build_food_evidence_recall_packet,
    is_compact_food_evidence_packet,
)
from .food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan,
)
from .fooddb_retrieval_policy import IndexedFoodRecord, retrieve_fooddb_candidates
from .retrieval_intent import RetrievalIntent
from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic


def build_retrieval_eval_wall(
    *,
    retrieval_records: tuple[IndexedFoodRecord, ...],
    websearch_pipeline_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    websearch_pipeline = websearch_pipeline_artifact or build_websearch_candidate_pipeline_diagnostic()
    source_selection_cases = _source_selection_cases()
    ranking_cases = _ranking_cases(retrieval_records)
    grounding_cases = _grounding_cases(retrieval_records, websearch_pipeline=websearch_pipeline)
    negative_cases = _negative_cases(retrieval_records, websearch_pipeline=websearch_pipeline)
    all_cases = [*source_selection_cases, *ranking_cases, *grounding_cases, *negative_cases]
    fail_count = sum(1 for case in all_cases if case["status"] != "pass")
    return {
        "artifact_type": "accurate_intake_retrieval_eval_wall_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_retrieval_eval_wall_only",
        "claim_scope": "retrieval_source_ranking_grounding_negative_eval",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "best_practice_basis": {
            "trace_level_eval": "separate source selection, ranking, grounding, and negative cases",
            "retrieval_first": "typed retrieval packet before manager synthesis",
            "tool_loop_boundary": "retrieval tools provide data only; manager/runtime guard own later synthesis and mutation",
        },
        "source_selection_cases": source_selection_cases,
        "ranking_cases": ranking_cases,
        "grounding_cases": grounding_cases,
        "negative_cases": negative_cases,
        "summary": {
            "case_count": len(all_cases),
            "source_selection_case_count": len(source_selection_cases),
            "ranking_case_count": len(ranking_cases),
            "grounding_case_count": len(grounding_cases),
            "negative_case_count": len(negative_cases),
            "pass_count": sum(1 for case in all_cases if case["status"] == "pass"),
            "fail_count": fail_count,
            "websearch_runtime_truth_allowed_count": _websearch_runtime_truth_allowed_count(
                websearch_pipeline
            ),
            "next_required_slice": (
                "inspect_retrieval_eval_wall_failures"
                if fail_count
                else "grokfast_fooddb_packet_live_diagnostic"
            ),
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_readiness_claim",
        ],
    }


def _source_selection_cases() -> list[dict[str, Any]]:
    availability = RetrieverBackendAvailability(
        local_fooddb_index=True,
        sqlite_fts_index=True,
        websearch_candidate_lane=True,
    )
    cases = [
        (
            "generic_fooddb_prefers_sqlite_then_local",
            RetrievalIntent(
                base_dish="bubble milk tea",
                aliases=["boba"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
            ),
            ("sqlite_fts_index", "local_fooddb_index"),
        ),
        (
            "exact_brand_keeps_websearch_candidate_only",
            RetrievalIntent(
                base_dish="pearl black tea latte",
                aliases=["Milksha pearl black tea latte"],
                brand_hint="Milksha",
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="exact_brand_lookup",
            ),
            ("sqlite_fts_index", "local_fooddb_index", "websearch_candidate_lane"),
        ),
        (
            "composition_clarification_asks_followup",
            RetrievalIntent(
                base_dish="luwei",
                aliases=["luwei"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="composition_clarification",
            ),
            (),
            "manager_decision",
        ),
        (
            "raw_text_hint_does_not_execute_backend",
            RetrievalIntent(
                base_dish="bubble milk tea",
                aliases=["boba"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
            ),
            (),
            "raw_text_hint",
        ),
    ]
    results: list[dict[str, Any]] = []
    for item in cases:
        case_id, intent, expected_sequence, *source = item
        intent_source = source[0] if source else "manager_decision"
        plan = build_food_evidence_retriever_route_plan(
            intent,
            availability=availability,
            intent_source=intent_source,
        )
        checks = {
            "expected_backend_sequence": plan.backend_sequence == expected_sequence,
            "does_not_decide_logged_or_draft": plan.decides_logged_or_draft is False,
            "websearch_not_runtime_truth": plan.websearch_runtime_truth_allowed is False,
            "raw_text_hint_not_executed": plan.raw_text_hint_executed is False,
            "raw_text_hint_no_interaction_route": (
                plan.retrieval_intent_source != "raw_text_hint"
                or plan.primary_backend == "blocked_no_execution"
            ),
        }
        results.append(
            {
                "case_id": case_id,
                "stage": "source_selection",
                "status": _status(checks),
                "checks": checks,
                "primary_backend": plan.primary_backend,
                "backend_sequence": list(plan.backend_sequence),
                "retrieval_intent_source": plan.retrieval_intent_source,
                "manager_owned_intent_required": plan.manager_owned_intent_required,
                "raw_text_hint_executed": plan.raw_text_hint_executed,
                "runtime_truth_source": plan.runtime_truth_source,
                "routing_reasons": list(plan.routing_reasons),
            }
        )
    return results


def _ranking_cases(retrieval_records: tuple[IndexedFoodRecord, ...]) -> list[dict[str, Any]]:
    exact = retrieve_fooddb_candidates("large boba", retrieval_records=retrieval_records)
    fuzzy = retrieve_fooddb_candidates("boba milk teaa", retrieval_records=retrieval_records)
    exact_top = _top_candidate(exact)
    fuzzy_top = _top_candidate(fuzzy)
    return [
        {
            "case_id": "alias_exact_ranking_prefers_runtime_anchor",
            "stage": "ranking",
            "status": _status(
                {
                    "top_candidate_is_boba_anchor": exact_top.get("anchor_id")
                    == "custom_drink_boba_milk_tea",
                    "runtime_truth_boost_present": "runtime_truth_allowed"
                    in exact_top.get("ranking_reasons", []),
                    "modifier_compatibility_ranked": "modifier_compatible:cup_size"
                    in exact_top.get("ranking_reasons", []),
                }
            ),
            "top_candidate": _ranking_projection(exact_top),
        },
        {
            "case_id": "fuzzy_candidate_requires_manager_disambiguation",
            "stage": "ranking",
            "status": _status(
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
            "top_candidate": _ranking_projection(fuzzy_top),
        },
    ]


def _grounding_cases(
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
    websearch_classifications = _websearch_classifications(websearch_pipeline)
    return [
        {
            "case_id": "fooddb_packet_is_compact_and_read_only",
            "stage": "grounding",
            "status": _status(
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
            "status": _status(
                {
                    "websearch_runtime_truth_count_zero": _websearch_runtime_truth_allowed_count(
                        websearch_pipeline
                    )
                    == 0,
                    "candidate_classifications_present": bool(websearch_classifications),
                    "extract_candidates_still_not_runtime": all(
                        item.get("runtime_truth_allowed") is False
                        for item in websearch_classifications
                    ),
                }
            ),
            "classification_counts": dict(
                websearch_pipeline.get("summary", {}).get("classification_counts") or {}
            ),
        },
    ]


def _negative_cases(
    retrieval_records: tuple[IndexedFoodRecord, ...],
    *,
    websearch_pipeline: dict[str, Any],
) -> list[dict[str, Any]]:
    bare_basket = retrieve_fooddb_candidates("\u6211\u5403\u6ef7\u5473", retrieval_records=retrieval_records)
    exact_lane = build_exact_evidence_lane_policy_artifact()
    classifications = _websearch_classifications(websearch_pipeline)
    return [
        {
            "case_id": "bare_basket_does_not_estimate",
            "stage": "negative",
            "status": _status(
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
            "status": _status(
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
                        item.get("runtime_truth_allowed") is False
                        for item in classifications
                    ),
                }
            ),
            "exact_card_staging_candidate_count": exact_lane["summary"][
                "exact_card_staging_candidate_count"
            ],
        },
    ]


def _top_candidate(retrieval_result: dict[str, Any]) -> dict[str, Any]:
    candidates = retrieval_result.get("accepted_candidates") or []
    return dict(candidates[0]) if candidates else {}


def _ranking_projection(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "anchor_id": candidate.get("anchor_id"),
        "match_path": candidate.get("match_path"),
        "match_score": candidate.get("match_score"),
        "confidence": candidate.get("confidence"),
        "requires_manager_disambiguation": candidate.get("requires_manager_disambiguation"),
        "runtime_truth_allowed": candidate.get("runtime_truth_allowed"),
        "ranking_reasons": list(candidate.get("ranking_reasons") or []),
    }


def _websearch_classifications(websearch_pipeline: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        classification
        for case in websearch_pipeline.get("cases") or []
        for classification in case.get("candidate_classifications") or []
        if isinstance(classification, dict)
    ]


def _websearch_runtime_truth_allowed_count(websearch_pipeline: dict[str, Any]) -> int:
    return sum(
        1
        for classification in _websearch_classifications(websearch_pipeline)
        if classification.get("runtime_truth_allowed") is True
    )


def _status(checks: dict[str, bool]) -> str:
    return "pass" if checks and all(checks.values()) else "fail"


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_retrieval_eval_wall"]
