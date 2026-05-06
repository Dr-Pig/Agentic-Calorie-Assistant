from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .exact_evidence_lane_projection import (
    build_exact_card_staging,
    build_websearch_case_summary,
)
from .exact_item_card_lookup import lookup_exact_item_card_candidates
from .retrieval_intent import RetrievalIntent
from .websearch_candidate_pipeline import WebSearchPipelineCase
from .websearch_candidate_pipeline_expansion_fixtures import (
    build_expanded_websearch_pipeline_cases,
)


class _LocalExactSeedStore:
    def load_small_anchor_records(self) -> list[dict[str, object]]:
        return []

    def load_exact_item_card_records(self) -> list[dict[str, object]]:
        return [
            {
                "item_id": "exact_test_food_large",
                "title": "Test Brand Food Large",
                "aliases": ["Test Brand Food Large"],
                "brand": "Test Brand",
                "serving_basis": "large serving",
                "kcal": 123,
            }
        ]


def build_exact_evidence_lane_policy_cases() -> list[dict[str, Any]]:
    return [
        _local_exact_seed_case(),
        _websearch_candidate_review_case(
            case_id="websearch_candidate_review_fallback",
            pipeline_case_id="pipeline_milksha_exact",
        ),
        _websearch_candidate_review_case(
            case_id="official_pdf_review_priority",
            pipeline_case_id="pipeline_official_pdf_priority",
        ),
        _websearch_candidate_review_case(
            case_id="large_size_review_priority",
            pipeline_case_id="pipeline_large_size_preferred",
        ),
        _websearch_candidate_review_case(
            case_id="modifier_match_review_priority",
            pipeline_case_id="pipeline_modifier_match_preferred",
        ),
        _no_exact_evidence_case(),
    ]


def _local_exact_seed_case() -> dict[str, Any]:
    intent = RetrievalIntent(
        base_dish="Food",
        aliases=["Test Brand Food Large"],
        brand_hint="Test Brand",
        size_hint="Large",
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
    )
    local_exact = lookup_exact_item_card_candidates(intent, evidence_store=_LocalExactSeedStore())
    lane = "local_exact_seed_support_only" if local_exact.candidates else "no_exact_evidence"
    return _case_payload(
        case_id="local_exact_seed_preferred",
        intent=intent,
        local_exact=local_exact,
        websearch_case=None,
        selected_lane=lane,
        evidence_signal="local_exact_seed_support_available" if local_exact.candidates else "no_exact_evidence_available",
    )


def _websearch_candidate_review_case(*, case_id: str, pipeline_case_id: str) -> dict[str, Any]:
    web_case = _websearch_case(pipeline_case_id)
    intent = web_case.intent
    local_exact = lookup_exact_item_card_candidates(intent)
    return _case_payload(
        case_id=case_id,
        intent=intent,
        local_exact=local_exact,
        websearch_case=web_case,
        selected_lane="websearch_candidate_review",
        evidence_signal="exact_card_candidate_review_available",
    )


def _no_exact_evidence_case() -> dict[str, Any]:
    web_case = _websearch_case("pipeline_all_candidates_blocked")
    intent = web_case.intent
    local_exact = lookup_exact_item_card_candidates(intent)
    return _case_payload(
        case_id="no_exact_evidence_available",
        intent=intent,
        local_exact=local_exact,
        websearch_case=web_case,
        selected_lane="no_exact_evidence",
        evidence_signal="no_exact_evidence_available",
    )


def _case_payload(
    *,
    case_id: str,
    intent: RetrievalIntent,
    local_exact: Any,
    websearch_case: WebSearchPipelineCase | None,
    selected_lane: str,
    evidence_signal: str,
) -> dict[str, Any]:
    local_candidates = [asdict(candidate) for candidate in local_exact.candidates]
    websearch_pipeline = build_websearch_case_summary(websearch_case)
    exact_card_staging = build_exact_card_staging(websearch_pipeline)
    return {
        "case_id": case_id,
        "intent": {
            "base_dish": intent.base_dish,
            "aliases": list(intent.aliases),
            "brand_hint": intent.brand_hint,
            "size_hint": intent.size_hint,
            "retrieval_goal": intent.retrieval_goal,
        },
        "runtime_truth_allowed": False,
        "packet_ready_truth_allowed": False,
        "runtime_mutation_allowed": False,
        "live_websearch_used": False,
        "local_exact": {
            "candidate_count": len(local_candidates),
            "defer_reason": local_exact.defer_reason,
            "candidates": local_candidates,
        },
        "websearch_pipeline": websearch_pipeline,
        "exact_card_staging": exact_card_staging,
        "lane_decision": {
            "selected_lane": selected_lane,
            "websearch_required": selected_lane == "websearch_candidate_review",
            "evidence_signal": evidence_signal,
        },
    }


def _websearch_case(case_id: str) -> WebSearchPipelineCase:
    cases = build_expanded_websearch_pipeline_cases(case_factory=WebSearchPipelineCase)
    by_id = {case.case_id: case for case in cases}
    try:
        return by_id[case_id]
    except KeyError as exc:
        raise ValueError(f"unknown exact evidence lane WebSearch case: {case_id}") from exc
