from __future__ import annotations

from dataclasses import dataclass

from .food_evidence_retriever_router import RetrievalIntentSource
from .retrieval_intent import RetrievalIntent


@dataclass(frozen=True)
class RetrieverExecutionCase:
    case_id: str
    raw_query: str
    intent: RetrievalIntent
    expected_primary_backend: str
    intent_source: RetrievalIntentSource = "manager_decision"


def default_retriever_execution_cases() -> tuple[RetrieverExecutionCase, ...]:
    return (
        RetrieverExecutionCase(
            case_id="generic_boba_fooddb",
            raw_query="boba",
            expected_primary_backend="sqlite_fts_index",
            intent=RetrievalIntent(
                base_dish="bubble milk tea",
                aliases=["boba"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
            ),
        ),
        RetrieverExecutionCase(
            case_id="exact_brand_websearch_candidate",
            raw_query="Milksha pearl black tea latte",
            expected_primary_backend="sqlite_fts_index",
            intent=RetrievalIntent(
                base_dish="pearl black tea latte",
                aliases=["Milksha pearl black tea latte"],
                brand_hint="Milksha",
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="exact_brand_lookup",
            ),
        ),
        RetrieverExecutionCase(
            case_id="composition_clarification",
            raw_query="luwei",
            expected_primary_backend="ask_followup",
            intent=RetrievalIntent(
                base_dish="luwei",
                aliases=["luwei"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="composition_clarification",
            ),
        ),
        RetrieverExecutionCase(
            case_id="raw_text_hint_does_not_execute_backend",
            raw_query="boba",
            expected_primary_backend="blocked_no_execution",
            intent_source="raw_text_hint",
            intent=RetrievalIntent(
                base_dish="bubble milk tea",
                aliases=["boba"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
            ),
        ),
    )


__all__ = [
    "RetrieverExecutionCase",
    "default_retriever_execution_cases",
]
