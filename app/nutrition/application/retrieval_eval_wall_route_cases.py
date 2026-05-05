from __future__ import annotations

from typing import Any

from .food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan,
)
from .retrieval_eval_wall_case_utils import status
from .retrieval_intent import RetrievalIntent


def build_source_selection_cases() -> list[dict[str, Any]]:
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
                "status": status(checks),
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
