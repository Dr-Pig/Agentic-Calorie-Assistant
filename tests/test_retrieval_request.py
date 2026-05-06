from __future__ import annotations

from app.nutrition.application.retrieval_intent import RetrievalIntent
from app.nutrition.application.retrieval_request import (
    build_retrieval_request_from_intent_fixture,
    build_retrieval_request_from_manager_decision,
    build_retrieval_request_from_raw_text_hint,
)
from app.nutrition.application.retrieval_semantic_decision import (
    B2ManagerSemanticDecision,
)


def test_manager_decision_request_is_runtime_executable() -> None:
    request = build_retrieval_request_from_manager_decision(
        B2ManagerSemanticDecision(
            base_dish="茶葉蛋",
            aliases=["茶葉蛋"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        )
    )

    assert request.intent_source == "manager_decision"
    assert request.semantic_authority_source == "synthetic_manager_structured_fixture"
    assert request.runtime_execution_allowed is True
    assert request.trace_role == "manager_owned_runtime_request"
    assert request.intent.base_dish == "茶葉蛋"


def test_fixture_request_is_explicitly_diagnostic_only_authority() -> None:
    request = build_retrieval_request_from_intent_fixture(
        RetrievalIntent(
            base_dish="bubble milk tea",
            aliases=["boba"],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
        )
    )

    assert request.intent_source == "diagnostic_fixture"
    assert request.semantic_authority_source == "synthetic_retrieval_fixture"
    assert request.runtime_execution_allowed is True
    assert request.trace_role == "fixture_runtime_request"


def test_raw_text_hint_request_cannot_authorize_runtime_execution() -> None:
    request = build_retrieval_request_from_raw_text_hint("星巴克冰拿鐵大杯")

    assert request.intent_source == "raw_text_hint"
    assert request.semantic_authority_source == "deterministic_raw_text_hint_only"
    assert request.runtime_execution_allowed is False
    assert request.trace_role == "diagnostic_raw_text_hint"
    assert request.intent.brand_hint == "星巴克"
    assert request.intent.retrieval_goal == "exact_brand_lookup"
