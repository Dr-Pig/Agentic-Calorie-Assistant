from __future__ import annotations

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


def test_retrieval_intent_strips_simple_quantity_prefixes_for_generic_anchor_cases() -> None:
    tea_egg = build_retrieval_intent("\u6211\u5403\u4e86\u4e00\u9846\u8336\u8449\u86cb")
    boba = build_retrieval_intent("\u6211\u559d\u4e86\u4e00\u676f\u73cd\u73e0\u5976\u8336")
    bento = build_retrieval_intent("\u6211\u5403\u4e86\u4e00\u500b\u4fbf\u7576")

    assert tea_egg.base_dish == "\u8336\u8449\u86cb"
    assert tea_egg.aliases == ["\u8336\u8449\u86cb"]
    assert tea_egg.retrieval_goal == "generic_anchor_lookup"

    assert boba.base_dish == "\u73cd\u73e0\u5976\u8336"
    assert boba.aliases == ["\u73cd\u73e0\u5976\u8336"]
    assert boba.retrieval_goal == "generic_anchor_lookup"

    assert bento.base_dish == "\u4fbf\u7576"
    assert bento.aliases == ["\u4fbf\u7576"]
    assert bento.retrieval_goal == "generic_anchor_lookup"
