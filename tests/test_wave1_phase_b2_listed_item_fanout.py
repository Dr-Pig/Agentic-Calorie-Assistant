from __future__ import annotations

from app.nutrition.application.retrieval_intent import build_retrieval_intent
from app.nutrition.application.small_anchor_store import lookup_anchor_candidates

from app.nutrition.application.listed_item_fanout import fanout_listed_item_anchor_lookups


def test_listed_item_fanout_resolves_each_listed_item_independently() -> None:
    intent = build_retrieval_intent("我吃了豆干、海帶、貢丸的滷味")

    fanout = fanout_listed_item_anchor_lookups(intent)

    assert [entry.listed_item for entry in fanout] == ["豆干", "海帶", "貢丸"]
    assert [entry.sub_intent.listed_items for entry in fanout] == [["豆干"], ["海帶"], ["貢丸"]]
    assert [entry.lookup_result.defer_reason for entry in fanout] == [None, None, None]
    assert [entry.lookup_result.candidates[0].canonical_name for entry in fanout] == ["豆干", "海帶", "貢丸"]


def test_listed_item_fanout_keeps_partial_failure_trace_visible() -> None:
    intent = build_retrieval_intent("我吃了豆干、海帶、火龍果汁的滷味")

    fanout = fanout_listed_item_anchor_lookups(intent)

    assert [entry.listed_item for entry in fanout] == ["豆干", "海帶", "火龍果汁"]
    assert fanout[0].lookup_result.defer_reason is None
    assert fanout[1].lookup_result.defer_reason is None
    assert fanout[2].lookup_result.defer_reason == "no_anchor_match"
    assert fanout[2].lookup_result.candidates == ()
    assert fanout[2].lookup_result.clarify_support is None


def test_multi_item_listed_lookup_api_stays_deferred_while_fanout_helper_owns_orchestration() -> None:
    intent = build_retrieval_intent("我吃了豆干、海帶、貢丸的滷味")

    lookup_result = lookup_anchor_candidates(intent)

    assert lookup_result.defer_reason == "listed_item_fanout_deferred"
    assert lookup_result.candidates == ()
