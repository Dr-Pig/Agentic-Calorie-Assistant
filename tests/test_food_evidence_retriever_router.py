from __future__ import annotations

from app.nutrition.application.food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan,
)
from app.nutrition.application.retrieval_intent import RetrievalIntent


def test_router_prefers_sqlite_fts_when_available_for_runtime_fooddb_lookup() -> None:
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="珍珠奶茶",
            aliases=["珍奶"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
        ),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=False,
        ),
    )

    assert plan.primary_backend == "sqlite_fts_index"
    assert plan.backend_sequence == ("sqlite_fts_index", "local_fooddb_index")
    assert plan.websearch_candidate_enabled is False
    assert plan.runtime_truth_source == "approved_fooddb_only"
    assert plan.mutation_allowed is True


def test_router_keeps_exact_brand_websearch_in_candidate_lane_only() -> None:
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="pearl black tea latte",
            aliases=["Milksha pearl black tea latte"],
            brand_hint="Milksha",
            size_hint="large",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        ),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=False,
            websearch_candidate_lane=True,
        ),
    )

    assert plan.primary_backend == "local_fooddb_index"
    assert plan.backend_sequence == ("local_fooddb_index", "websearch_candidate_lane")
    assert plan.websearch_candidate_enabled is True
    assert plan.websearch_runtime_truth_allowed is False
    assert plan.exact_candidate_requires_separate_promotion is True
    assert "no direct runtime truth from websearch" in plan.routing_reasons


def test_router_blocks_lookup_for_composition_clarification() -> None:
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="滷味",
            aliases=["滷味"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="composition_clarification",
        ),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=True,
            websearch_candidate_lane=True,
        ),
    )

    assert plan.primary_backend == "ask_followup"
    assert plan.backend_sequence == ()
    assert plan.read_only is False
    assert plan.mutation_allowed is False
    assert plan.routing_reasons == ("composition clarification requires follow-up before evidence lookup",)


def test_router_keeps_query_only_read_only_even_when_fooddb_lookup_is_allowed() -> None:
    plan = build_food_evidence_retriever_route_plan(
        RetrievalIntent(
            base_dish="珍珠奶茶",
            aliases=["珍珠奶茶"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="query_only_answer",
        ),
        availability=RetrieverBackendAvailability(
            local_fooddb_index=True,
            sqlite_fts_index=False,
            websearch_candidate_lane=False,
        ),
    )

    assert plan.primary_backend == "local_fooddb_index"
    assert plan.read_only is True
    assert plan.mutation_allowed is False
    assert plan.decides_logged_or_draft is False
