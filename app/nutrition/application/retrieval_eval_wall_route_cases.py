from __future__ import annotations

from typing import Any

from .food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan,
)
from .retrieval_eval_wall_case_utils import status
from .retrieval_intent import RetrievalIntent


def build_source_selection_cases() -> list[dict[str, Any]]:
    default_availability = RetrieverBackendAvailability(
        local_fooddb_index=True,
        sqlite_fts_index=True,
        websearch_candidate_lane=True,
    )
    websearch_disabled = RetrieverBackendAvailability(
        local_fooddb_index=True,
        sqlite_fts_index=True,
        websearch_candidate_lane=False,
    )
    cases: list[dict[str, Any]] = [
        {
            "case_id": "generic_fooddb_prefers_sqlite_then_local",
            "intent": RetrievalIntent(
                base_dish="bubble milk tea",
                aliases=["boba"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
            ),
            "expected_sequence": ("sqlite_fts_index", "local_fooddb_index"),
        },
        {
            "case_id": "exact_brand_keeps_websearch_candidate_only",
            "intent": RetrievalIntent(
                base_dish="pearl black tea latte",
                aliases=["Milksha pearl black tea latte"],
                brand_hint="Milksha",
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="exact_brand_lookup",
            ),
            "expected_sequence": (
                "sqlite_fts_index",
                "local_fooddb_index",
                "websearch_candidate_lane",
            ),
            "expected_websearch_candidate_enabled": True,
        },
        {
            "case_id": "composition_clarification_asks_followup",
            "intent": RetrievalIntent(
                base_dish="luwei",
                aliases=["luwei"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="composition_clarification",
            ),
            "expected_sequence": (),
            "intent_source": "manager_decision",
            "expected_primary_backend": "ask_followup",
        },
        {
            "case_id": "raw_text_hint_does_not_execute_backend",
            "intent": RetrievalIntent(
                base_dish="bubble milk tea",
                aliases=["boba"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
            ),
            "expected_sequence": (),
            "intent_source": "raw_text_hint",
            "expected_primary_backend": "blocked_no_execution",
        },
        {
            "case_id": "listed_basket_components_stay_fooddb_only",
            "intent": RetrievalIntent(
                base_dish="luwei",
                aliases=["luwei"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=["dried tofu", "kelp", "meatball"],
                retrieval_goal="listed_item_lookup",
            ),
            "expected_sequence": ("sqlite_fts_index", "local_fooddb_index"),
            "expected_websearch_candidate_enabled": False,
        },
        {
            "case_id": "query_only_route_is_read_only",
            "intent": RetrievalIntent(
                base_dish="today total",
                aliases=[],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="query_only_answer",
            ),
            "expected_sequence": ("sqlite_fts_index", "local_fooddb_index"),
            "expected_read_only": True,
            "expected_mutation_allowed": False,
        },
        {
            "case_id": "exact_brand_without_websearch_keeps_fooddb_only",
            "intent": RetrievalIntent(
                base_dish="pearl black tea latte",
                aliases=["Milksha pearl black tea latte"],
                brand_hint="Milksha",
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="exact_brand_lookup",
            ),
            "expected_sequence": ("sqlite_fts_index", "local_fooddb_index"),
            "availability": websearch_disabled,
            "expected_websearch_candidate_enabled": False,
        },
    ]
    results: list[dict[str, Any]] = []
    for item in cases:
        intent = item["intent"]
        intent_source = item.get("intent_source") or "manager_decision"
        plan = build_food_evidence_retriever_route_plan(
            intent,
            availability=item.get("availability") or default_availability,
            intent_source=intent_source,
        )
        expected_primary_backend = _expected_primary_backend(item)
        checks = {
            "expected_backend_sequence": plan.backend_sequence == item["expected_sequence"],
            "expected_primary_backend": plan.primary_backend == expected_primary_backend,
            "expected_read_only": plan.read_only is item.get("expected_read_only", plan.read_only),
            "expected_mutation_allowed": plan.mutation_allowed
            is item.get("expected_mutation_allowed", plan.mutation_allowed),
            "expected_websearch_candidate_enabled": plan.websearch_candidate_enabled
            is item.get(
                "expected_websearch_candidate_enabled",
                plan.websearch_candidate_enabled,
            ),
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
                "case_id": item["case_id"],
                "stage": "source_selection",
                "status": status(checks),
                "checks": checks,
                "primary_backend": plan.primary_backend,
                "backend_sequence": list(plan.backend_sequence),
                "retrieval_intent_source": plan.retrieval_intent_source,
                "manager_owned_intent_required": plan.manager_owned_intent_required,
                "raw_text_hint_executed": plan.raw_text_hint_executed,
                "read_only": plan.read_only,
                "mutation_allowed": plan.mutation_allowed,
                "websearch_candidate_enabled": plan.websearch_candidate_enabled,
                "runtime_truth_source": plan.runtime_truth_source,
                "routing_reasons": list(plan.routing_reasons),
            }
        )
    return results


def _expected_primary_backend(item: dict[str, Any]) -> str:
    explicit = item.get("expected_primary_backend")
    if explicit is not None:
        return str(explicit)
    expected_sequence = item.get("expected_sequence") or ()
    if not expected_sequence:
        return "__missing_expected_primary_backend_for_empty_sequence__"
    return str(expected_sequence[0])
