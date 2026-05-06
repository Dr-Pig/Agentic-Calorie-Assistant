from __future__ import annotations

from dataclasses import dataclass

from .retrieval_request import (
    FoodEvidenceRetrievalRequest,
    build_retrieval_request_from_intent_fixture,
    build_retrieval_request_from_raw_text_hint,
)
from .retrieval_intent import RetrievalIntent


@dataclass(frozen=True)
class RetrieverExecutionCase:
    case_id: str
    raw_query: str
    request: FoodEvidenceRetrievalRequest
    expected_primary_backend: str


def default_retriever_execution_cases() -> tuple[RetrieverExecutionCase, ...]:
    return (
        RetrieverExecutionCase(
            case_id="generic_boba_fooddb",
            raw_query="boba",
            expected_primary_backend="sqlite_fts_index",
            request=build_retrieval_request_from_intent_fixture(
                RetrievalIntent(
                    base_dish="bubble milk tea",
                    aliases=["boba"],
                    brand_hint=None,
                    size_hint=None,
                    modifier_hints=[],
                    listed_items=[],
                    retrieval_goal="generic_anchor_lookup",
                )
            ),
        ),
        RetrieverExecutionCase(
            case_id="exact_brand_websearch_candidate",
            raw_query="Milksha pearl black tea latte",
            expected_primary_backend="sqlite_fts_index",
            request=build_retrieval_request_from_intent_fixture(
                RetrievalIntent(
                    base_dish="pearl black tea latte",
                    aliases=["Milksha pearl black tea latte"],
                    brand_hint="Milksha",
                    size_hint=None,
                    modifier_hints=[],
                    listed_items=[],
                    retrieval_goal="exact_brand_lookup",
                )
            ),
        ),
        RetrieverExecutionCase(
            case_id="composition_clarification",
            raw_query="luwei",
            expected_primary_backend="ask_followup",
            request=build_retrieval_request_from_intent_fixture(
                RetrievalIntent(
                    base_dish="luwei",
                    aliases=["luwei"],
                    brand_hint=None,
                    size_hint=None,
                    modifier_hints=[],
                    listed_items=[],
                    retrieval_goal="composition_clarification",
                )
            ),
        ),
        RetrieverExecutionCase(
            case_id="raw_text_hint_does_not_execute_backend",
            raw_query="boba",
            expected_primary_backend="blocked_no_execution",
            request=build_retrieval_request_from_raw_text_hint("boba"),
        ),
    )


__all__ = [
    "RetrieverExecutionCase",
    "default_retriever_execution_cases",
]
