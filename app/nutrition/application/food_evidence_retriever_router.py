from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .retrieval_intent import RetrievalIntent
from .retrieval_request import FoodEvidenceRetrievalRequest, RetrievalIntentSource

RetrieverBackend = Literal[
    "ask_followup",
    "blocked_no_execution",
    "local_fooddb_index",
    "sqlite_fts_index",
    "supabase_index",
    "websearch_candidate_lane",
]


@dataclass(frozen=True)
class RetrieverBackendAvailability:
    local_fooddb_index: bool
    sqlite_fts_index: bool
    websearch_candidate_lane: bool
    supabase_index: bool = False


@dataclass(frozen=True)
class FoodEvidenceRetrieverRoutePlan:
    primary_backend: RetrieverBackend
    backend_sequence: tuple[RetrieverBackend, ...]
    retrieval_intent_source: RetrievalIntentSource
    manager_owned_intent_required: bool
    raw_text_hint_executed: bool
    read_only: bool
    mutation_allowed: bool
    decides_logged_or_draft: Literal[False]
    runtime_truth_source: str
    websearch_candidate_enabled: bool
    websearch_runtime_truth_allowed: bool
    exact_candidate_requires_separate_promotion: bool
    routing_reasons: tuple[str, ...]


def build_food_evidence_retriever_route_plan(
    intent: RetrievalIntent,
    *,
    availability: RetrieverBackendAvailability,
    intent_source: RetrievalIntentSource = "manager_decision",
) -> FoodEvidenceRetrieverRoutePlan:
    return build_food_evidence_retriever_route_plan_for_request(
        FoodEvidenceRetrievalRequest(
            intent=intent,
            intent_source=intent_source,
            semantic_authority_source=(
                "deterministic_raw_text_hint_only"
                if intent_source == "raw_text_hint"
                else "synthetic_retrieval_fixture"
                if intent_source == "diagnostic_fixture"
                else "manager_owned_runtime_request"
            ),
            runtime_execution_allowed=intent_source != "raw_text_hint",
            trace_role=(
                "diagnostic_raw_text_hint"
                if intent_source == "raw_text_hint"
                else "fixture_runtime_request"
                if intent_source == "diagnostic_fixture"
                else "manager_owned_runtime_request"
            ),
        ),
        availability=availability,
    )


def build_food_evidence_retriever_route_plan_for_request(
    request: FoodEvidenceRetrievalRequest,
    *,
    availability: RetrieverBackendAvailability,
) -> FoodEvidenceRetrieverRoutePlan:
    intent = request.intent
    intent_source = request.intent_source
    read_only = intent.retrieval_goal == "query_only_answer"

    if not request.runtime_execution_allowed:
        return FoodEvidenceRetrieverRoutePlan(
            primary_backend="blocked_no_execution",
            backend_sequence=(),
            retrieval_intent_source=intent_source,
            manager_owned_intent_required=True,
            raw_text_hint_executed=False,
            read_only=True,
            mutation_allowed=False,
            decides_logged_or_draft=False,
            runtime_truth_source="manager_owned_retrieval_intent_required",
            websearch_candidate_enabled=False,
            websearch_runtime_truth_allowed=False,
            exact_candidate_requires_separate_promotion=True,
            routing_reasons=(
                "raw-text retrieval hint is diagnostic/candidate-recall only",
                "manager-owned retrieval intent is required before evidence backend execution",
            ),
        )

    if intent.retrieval_goal == "composition_clarification":
        return FoodEvidenceRetrieverRoutePlan(
            primary_backend="ask_followup",
            backend_sequence=(),
            retrieval_intent_source=intent_source,
            manager_owned_intent_required=True,
            raw_text_hint_executed=False,
            read_only=read_only,
            mutation_allowed=False,
            decides_logged_or_draft=False,
            runtime_truth_source="no_lookup_until_clarified",
            websearch_candidate_enabled=False,
            websearch_runtime_truth_allowed=False,
            exact_candidate_requires_separate_promotion=True,
            routing_reasons=("composition clarification requires follow-up before evidence lookup",),
        )

    primary_fooddb_backend: RetrieverBackend
    if availability.sqlite_fts_index:
        primary_fooddb_backend = "sqlite_fts_index"
    elif availability.supabase_index:
        primary_fooddb_backend = "supabase_index"
    else:
        primary_fooddb_backend = "local_fooddb_index"
    backend_sequence: list[RetrieverBackend] = []
    routing_reasons: list[str] = []

    if primary_fooddb_backend == "sqlite_fts_index":
        backend_sequence.append("sqlite_fts_index")
        if availability.supabase_index:
            backend_sequence.append("supabase_index")
        backend_sequence.append("local_fooddb_index")
        routing_reasons.append("prefer adapter-compatible SQLite FTS when available")
    elif primary_fooddb_backend == "supabase_index":
        backend_sequence.extend(("supabase_index", "local_fooddb_index"))
        routing_reasons.append("use Supabase index only through FoodEvidenceIndexPort")
    else:
        backend_sequence.append("local_fooddb_index")
        routing_reasons.append("local FoodDB index is the current runtime baseline")

    websearch_candidate_enabled = False
    if intent.retrieval_goal == "exact_brand_lookup" and availability.websearch_candidate_lane:
        backend_sequence.append("websearch_candidate_lane")
        websearch_candidate_enabled = True
        routing_reasons.append("no direct runtime truth from websearch")

    if intent.retrieval_goal == "listed_item_lookup":
        routing_reasons.append("listed basket stays on approved FoodDB component anchors only")
    elif intent.retrieval_goal == "query_only_answer":
        routing_reasons.append("query-only lookup remains read-only")
    else:
        routing_reasons.append("runtime truth remains limited to approved FoodDB evidence")

    return FoodEvidenceRetrieverRoutePlan(
        primary_backend=backend_sequence[0],
        backend_sequence=tuple(backend_sequence),
        retrieval_intent_source=intent_source,
        manager_owned_intent_required=True,
        raw_text_hint_executed=False,
        read_only=read_only,
        mutation_allowed=not read_only,
        decides_logged_or_draft=False,
        runtime_truth_source="approved_fooddb_only",
        websearch_candidate_enabled=websearch_candidate_enabled,
        websearch_runtime_truth_allowed=False,
        exact_candidate_requires_separate_promotion=True,
        routing_reasons=tuple(routing_reasons),
    )


__all__ = [
    "FoodEvidenceRetrieverRoutePlan",
    "RetrieverBackend",
    "RetrieverBackendAvailability",
    "RetrievalIntentSource",
    "build_food_evidence_retriever_route_plan",
    "build_food_evidence_retriever_route_plan_for_request",
]
