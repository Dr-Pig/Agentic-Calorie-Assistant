from __future__ import annotations

from app.nutrition.application.retrieval_intent import RetrievalIntent, build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates


def test_small_anchor_store_matches_generic_single_item_anchor() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u8336\u8449\u86cb"))

    assert result.defer_reason is None
    assert result.clarify_support is None
    assert result.retrieval_context == "logging_support"
    assert result.mutation_authority == "none"
    assert len(result.candidates) == 1

    candidate = result.candidates[0]
    assert candidate.canonical_name == "\u8336\u8449\u86cb"
    assert candidate.match_path == "canonical_name_exact"
    assert candidate.support_role == "lookup_support_only"
    assert candidate.source_posture == "generic_anchor_seed"
    assert candidate.truth_level == "anchor"


def test_small_anchor_store_matches_generic_anchor_from_natural_quantity_phrasing() -> None:
    tea_egg = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u4e00\u9846\u8336\u8449\u86cb"))
    boba = lookup_anchor_candidates(build_retrieval_intent("\u6211\u559d\u4e86\u4e00\u676f\u73cd\u73e0\u5976\u8336"))
    bento = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u4e00\u500b\u4fbf\u7576"))

    assert [candidate.canonical_name for candidate in tea_egg.candidates] == ["\u8336\u8449\u86cb"]
    assert [candidate.canonical_name for candidate in boba.candidates] == ["\u73cd\u73e0\u5976\u8336"]
    assert [candidate.canonical_name for candidate in bento.candidates] == ["\u96de\u817f\u4fbf\u7576"]


def test_small_anchor_store_returns_query_only_support_without_mutation_authority() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u73cd\u73e0\u5976\u8336\u591a\u5c11\u71b1\u91cf\uff1f"))

    assert result.defer_reason is None
    assert result.clarify_support is None
    assert result.retrieval_context == "query_only_support"
    assert result.mutation_authority == "none"
    assert [candidate.canonical_name for candidate in result.candidates] == ["\u73cd\u73e0\u5976\u8336"]


def test_small_anchor_store_returns_semantic_only_clarify_support_for_unlisted_luwei() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6211\u5403\u4e86\u6ef7\u5473"))

    assert result.candidates == ()
    assert result.defer_reason is None
    assert result.clarify_support is not None
    assert result.clarify_support.canonical_name == "\u6ef7\u5473"
    assert result.clarify_support.record_kind == "generic_semantic_only"
    assert result.clarify_support.clarify_required is True
    assert result.clarify_support.followup_hints == ("ask_listed_items", "ask_portion")
    assert result.retrieval_context == "logging_support"
    assert result.mutation_authority == "none"


def test_small_anchor_store_defers_exact_brand_lookup_to_b2_005() -> None:
    result = lookup_anchor_candidates(
        RetrievalIntent(
            base_dish="\u725b\u4e3c",
            aliases=[],
            brand_hint="\u677e\u5c4b",
            size_hint="\u7279\u76db",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
        )
    )

    assert result.candidates == ()
    assert result.defer_reason == "exact_brand_lookup_deferred_to_b2_005"


def test_small_anchor_store_resolves_single_listed_item_only() -> None:
    result = lookup_anchor_candidates(
        RetrievalIntent(
            base_dish="\u6ef7\u5473",
            aliases=[],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=["\u8c46\u5e72"],
            retrieval_goal="listed_item_lookup",
        )
    )

    assert result.defer_reason is None
    assert result.clarify_support is None
    assert [candidate.canonical_name for candidate in result.candidates] == ["\u8c46\u5e72"]


def test_small_anchor_store_defers_listed_item_fanout() -> None:
    result = lookup_anchor_candidates(
        RetrievalIntent(
            base_dish="\u6ef7\u5473",
            aliases=[],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=["\u8c46\u5e72", "\u6d77\u5e36", "\u8ca2\u4e38"],
            retrieval_goal="listed_item_lookup",
        )
    )

    assert result.candidates == ()
    assert result.defer_reason == "listed_item_fanout_deferred"


def test_small_anchor_store_returns_closed_enum_for_no_anchor_match() -> None:
    result = lookup_anchor_candidates(
        RetrievalIntent(
            base_dish="\u706b\u9f8d\u679c\u6c41",
            aliases=[],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
        )
    )

    assert result.candidates == ()
    assert result.clarify_support is None
    assert result.defer_reason == "no_anchor_match"


def test_small_anchor_store_returns_query_only_clarify_support_for_unlisted_luwei() -> None:
    result = lookup_anchor_candidates(build_retrieval_intent("\u6ef7\u5473\u591a\u5c11\u71b1\u91cf\uff1f"))

    assert result.candidates == ()
    assert result.defer_reason is None
    assert result.retrieval_context == "query_only_support"
    assert result.clarify_support is not None
    assert result.clarify_support.canonical_name == "\u6ef7\u5473"
