from __future__ import annotations

import pytest

from app.nutrition.application.retrieval_semantic_decision import (
    B2ManagerSemanticDecision,
    build_retrieval_intent_from_manager_decision,
)
from app.nutrition.application.retrieval_intent import build_retrieval_intent


def test_retrieval_intent_marks_composition_unknown_luwei_as_clarification() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u6ef7\u5473")

    assert intent.base_dish == "\u6ef7\u5473"
    assert intent.listed_items == []
    assert intent.retrieval_goal == "composition_clarification"


def test_retrieval_intent_extracts_listed_items_from_luwei_basket() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38\u7684\u6ef7\u5473")

    assert intent.base_dish == "\u6ef7\u5473"
    assert intent.listed_items == ["\u8c46\u5e72", "\u6d77\u5e36", "\u8ca2\u4e38"]
    assert intent.retrieval_goal == "listed_item_lookup"


def test_retrieval_intent_marks_brand_and_size_logging_case_as_exact_brand_lookup() -> None:
    intent = build_retrieval_intent("\u6211\u5403\u4e86\u677e\u5c4b\u7279\u76db\u725b\u4e3c")

    assert intent.brand_hint == "\u677e\u5c4b"
    assert intent.size_hint == "\u7279\u76db"
    assert intent.base_dish == "\u725b\u4e3c"
    assert intent.retrieval_goal == "exact_brand_lookup"


def test_retrieval_intent_marks_brand_query_case_as_query_only_answer() -> None:
    intent = build_retrieval_intent("\u7d71\u4e00\u5de7\u514b\u529b\u725b\u4e73 400ml\u591a\u5c11\u71b1\u91cf\uff1f")

    assert intent.brand_hint == "\u7d71\u4e00"
    assert intent.size_hint == "400ml"
    assert intent.base_dish == "\u5de7\u514b\u529b\u725b\u4e73"
    assert intent.retrieval_goal == "query_only_answer"


def test_retrieval_intent_keeps_luwei_query_as_query_only_answer() -> None:
    intent = build_retrieval_intent("\u6ef7\u5473\u591a\u5c11\u71b1\u91cf\uff1f")

    assert intent.base_dish == "\u6ef7\u5473"
    assert intent.retrieval_goal == "query_only_answer"


def test_retrieval_intent_marks_generic_item_as_generic_anchor_lookup() -> None:
    intent = build_retrieval_intent("\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336")

    assert intent.base_dish == "\u73cd\u73e0\u5976\u8336"
    assert intent.brand_hint is None
    assert intent.retrieval_goal == "generic_anchor_lookup"


def test_retrieval_intent_marks_approved_self_selected_baskets_as_clarification() -> None:
    hotpot = build_retrieval_intent("\u6211\u5403\u4e86\u9ebb\u8fa3\u71d9")
    salty_basket = build_retrieval_intent("\u6211\u8cb7\u4e86\u9e7d\u9165\u96de")

    assert hotpot.base_dish == "\u9ebb\u8fa3\u71d9"
    assert hotpot.retrieval_goal == "composition_clarification"

    assert salty_basket.base_dish == "\u9e7d\u9165\u96de"
    assert salty_basket.retrieval_goal == "composition_clarification"


def test_retrieval_intent_resolves_salt_crispy_chicken_listed_basket() -> None:
    intent = build_retrieval_intent(
        "\u6211\u5403\u4e86\u9e7d\u9165\u96de\uff0c\u6709\u751c\u4e0d\u8fa3\u3001\u7c73\u8840\u3001\u56db\u5b63\u8c46"
    )

    assert intent.base_dish == "\u9e7d\u9165\u96de"
    assert intent.listed_items == ["\u751c\u4e0d\u8fa3", "\u7c73\u8840", "\u56db\u5b63\u8c46"]
    assert intent.retrieval_goal == "listed_item_lookup"


def test_retrieval_intent_strips_simple_quantity_prefixes_for_generic_anchor_cases() -> None:
    tea_egg = build_retrieval_intent("\u6211\u5403\u4e86\u4e00\u9846\u8336\u8449\u86cb")
    boba = build_retrieval_intent("\u6211\u559d\u4e86\u4e00\u676f\u73cd\u73e0\u5976\u8336")
    bento = build_retrieval_intent("\u6211\u5403\u4e86\u4e00\u500b\u4fbf\u7576")
    salty_item = build_retrieval_intent("\u6211\u5403\u4e86\u4e00\u4efd\u9e7d\u9165\u96de")

    assert tea_egg.base_dish == "\u8336\u8449\u86cb"
    assert tea_egg.aliases == ["\u8336\u8449\u86cb"]
    assert tea_egg.retrieval_goal == "generic_anchor_lookup"

    assert boba.base_dish == "\u73cd\u73e0\u5976\u8336"
    assert boba.aliases == ["\u73cd\u73e0\u5976\u8336"]
    assert boba.retrieval_goal == "generic_anchor_lookup"

    assert bento.base_dish == "\u4fbf\u7576"
    assert bento.aliases == ["\u4fbf\u7576"]
    assert bento.retrieval_goal == "generic_anchor_lookup"

    assert salty_item.base_dish == "\u9e7d\u9165\u96de"
    assert salty_item.aliases == ["\u9e7d\u9165\u96de"]
    assert salty_item.retrieval_goal == "generic_anchor_lookup"


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        (
            B2ManagerSemanticDecision(
                base_dish="\u8336\u8449\u86cb",
                aliases=["\u8336\u8449\u86cb"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
                semantic_authority_source="synthetic_manager_structured_fixture",
            ),
            {
                "base_dish": "\u8336\u8449\u86cb",
                "aliases": ["\u8336\u8449\u86cb"],
                "brand_hint": None,
                "size_hint": None,
                "listed_items": [],
                "retrieval_goal": "generic_anchor_lookup",
            },
        ),
        (
            B2ManagerSemanticDecision(
                base_dish="\u73cd\u73e0\u5976\u8336",
                aliases=["\u73cd\u73e0\u5976\u8336"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
                semantic_authority_source="synthetic_manager_structured_fixture",
            ),
            {
                "base_dish": "\u73cd\u73e0\u5976\u8336",
                "aliases": ["\u73cd\u73e0\u5976\u8336"],
                "brand_hint": None,
                "size_hint": None,
                "listed_items": [],
                "retrieval_goal": "generic_anchor_lookup",
            },
        ),
        (
            B2ManagerSemanticDecision(
                base_dish="\u6ef7\u5473",
                aliases=["\u6ef7\u5473"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="composition_clarification",
                semantic_authority_source="synthetic_manager_structured_fixture",
            ),
            {
                "base_dish": "\u6ef7\u5473",
                "aliases": ["\u6ef7\u5473"],
                "brand_hint": None,
                "size_hint": None,
                "listed_items": [],
                "retrieval_goal": "composition_clarification",
            },
        ),
        (
            B2ManagerSemanticDecision(
                base_dish="\u6ef7\u5473",
                aliases=["\u6ef7\u5473"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=["\u8c46\u5e72", "\u6d77\u5e36", "\u8ca2\u4e38"],
                retrieval_goal="listed_item_lookup",
                semantic_authority_source="synthetic_manager_structured_fixture",
            ),
            {
                "base_dish": "\u6ef7\u5473",
                "aliases": ["\u6ef7\u5473"],
                "brand_hint": None,
                "size_hint": None,
                "listed_items": ["\u8c46\u5e72", "\u6d77\u5e36", "\u8ca2\u4e38"],
                "retrieval_goal": "listed_item_lookup",
            },
        ),
        (
            B2ManagerSemanticDecision(
                base_dish="\u725b\u4e3c",
                aliases=["\u677e\u5c4b\u7279\u76db\u725b\u4e3c"],
                brand_hint="\u677e\u5c4b",
                size_hint="\u7279\u76db",
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="exact_brand_lookup",
                semantic_authority_source="synthetic_manager_structured_fixture",
            ),
            {
                "base_dish": "\u725b\u4e3c",
                "aliases": ["\u677e\u5c4b\u7279\u76db\u725b\u4e3c"],
                "brand_hint": "\u677e\u5c4b",
                "size_hint": "\u7279\u76db",
                "listed_items": [],
                "retrieval_goal": "exact_brand_lookup",
            },
        ),
        (
            B2ManagerSemanticDecision(
                base_dish="\u73cd\u73e0\u5976\u8336",
                aliases=["\u73cd\u73e0\u5976\u8336"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="query_only_answer",
                semantic_authority_source="synthetic_manager_structured_fixture",
            ),
            {
                "base_dish": "\u73cd\u73e0\u5976\u8336",
                "aliases": ["\u73cd\u73e0\u5976\u8336"],
                "brand_hint": None,
                "size_hint": None,
                "listed_items": [],
                "retrieval_goal": "query_only_answer",
            },
        ),
    ],
)
def test_manager_semantic_decision_maps_to_retrieval_intent_without_raw_text(
    decision: B2ManagerSemanticDecision,
    expected: dict[str, object],
) -> None:
    intent = build_retrieval_intent_from_manager_decision(decision)

    assert intent.base_dish == expected["base_dish"]
    assert intent.aliases == expected["aliases"]
    assert intent.brand_hint == expected["brand_hint"]
    assert intent.size_hint == expected["size_hint"]
    assert intent.listed_items == expected["listed_items"]
    assert intent.retrieval_goal == expected["retrieval_goal"]


def test_manager_semantic_decision_rejects_non_manager_authority() -> None:
    decision = B2ManagerSemanticDecision(
        base_dish="\u8336\u8449\u86cb",
        aliases=["\u8336\u8449\u86cb"],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="generic_anchor_lookup",
        semantic_authority_source="deterministic_validator",
    )

    with pytest.raises(ValueError, match="semantic_authority_source"):
        build_retrieval_intent_from_manager_decision(decision)


def test_manager_semantic_decision_accepts_manager_tool_arguments_authority() -> None:
    decision = B2ManagerSemanticDecision(
        base_dish="\u9435\u677f\u9eb5",
        aliases=[],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=["\u9435\u677f\u9eb5", "\u8377\u5305\u86cb"],
        retrieval_goal="listed_item_lookup",
        semantic_authority_source="manager_tool_arguments",
    )

    intent = build_retrieval_intent_from_manager_decision(decision)

    assert intent.base_dish == "\u9435\u677f\u9eb5"
    assert intent.listed_items == ["\u9435\u677f\u9eb5", "\u8377\u5305\u86cb"]
    assert intent.retrieval_goal == "listed_item_lookup"


def test_manager_semantic_decision_rejects_unknown_retrieval_goal() -> None:
    decision = B2ManagerSemanticDecision(
        base_dish="\u8336\u8449\u86cb",
        aliases=["\u8336\u8449\u86cb"],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="raw_text_guess",
        semantic_authority_source="synthetic_manager_structured_fixture",
    )

    with pytest.raises(ValueError, match="retrieval_goal"):
        build_retrieval_intent_from_manager_decision(decision)
