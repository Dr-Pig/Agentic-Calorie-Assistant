from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .retrieval_intent import RetrievalIntent, build_raw_text_retrieval_hint
from .retrieval_semantic_decision import (
    B2ManagerSemanticDecision,
    build_retrieval_intent_from_manager_decision,
)

RetrievalIntentSource = Literal[
    "manager_decision",
    "diagnostic_fixture",
    "raw_text_hint",
]


@dataclass(frozen=True)
class FoodEvidenceRetrievalRequest:
    intent: RetrievalIntent
    intent_source: RetrievalIntentSource
    semantic_authority_source: str
    runtime_execution_allowed: bool
    trace_role: str


def build_retrieval_request_from_manager_decision(
    decision: B2ManagerSemanticDecision,
) -> FoodEvidenceRetrievalRequest:
    return FoodEvidenceRetrievalRequest(
        intent=build_retrieval_intent_from_manager_decision(decision),
        intent_source="manager_decision",
        semantic_authority_source=str(decision.semantic_authority_source),
        runtime_execution_allowed=True,
        trace_role="manager_owned_runtime_request",
    )


def build_retrieval_request_from_intent_fixture(
    intent: RetrievalIntent,
) -> FoodEvidenceRetrievalRequest:
    return FoodEvidenceRetrievalRequest(
        intent=intent,
        intent_source="diagnostic_fixture",
        semantic_authority_source="synthetic_retrieval_fixture",
        runtime_execution_allowed=True,
        trace_role="fixture_runtime_request",
    )


def build_retrieval_request_from_raw_text_hint(
    raw_user_input: str,
) -> FoodEvidenceRetrievalRequest:
    return FoodEvidenceRetrievalRequest(
        intent=build_raw_text_retrieval_hint(raw_user_input),
        intent_source="raw_text_hint",
        semantic_authority_source="deterministic_raw_text_hint_only",
        runtime_execution_allowed=False,
        trace_role="diagnostic_raw_text_hint",
    )


__all__ = [
    "FoodEvidenceRetrievalRequest",
    "RetrievalIntentSource",
    "build_retrieval_request_from_intent_fixture",
    "build_retrieval_request_from_manager_decision",
    "build_retrieval_request_from_raw_text_hint",
]
