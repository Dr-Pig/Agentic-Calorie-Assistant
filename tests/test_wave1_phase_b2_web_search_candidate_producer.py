from __future__ import annotations

from typing import Any

import pytest

from app.nutrition.application.web_search_candidate_producer import (
    collect_web_search_candidates,
    produce_web_search_candidates,
)


_TRUTH_FIELDS = {
    "kcal_range",
    "likely_kcal",
    "exactness_posture",
    "final_truth",
    "primary_source",
    "match_type",
    "sibling_variant_risk",
}


class _FakeWebSearchPort:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self._hits = list(hits)
        self.calls: list[dict[str, Any]] = []

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "max_results": max_results})
        return list(self._hits)


def _assert_candidate_only(candidate: dict[str, Any]) -> None:
    assert candidate["source_type"] == "web_search"
    assert _TRUTH_FIELDS.isdisjoint(candidate)


@pytest.mark.asyncio
async def test_collect_web_search_candidates_normalizes_provider_agnostic_hits() -> None:
    port = _FakeWebSearchPort(
        [
            {
                "url": "https://www.milksha.com.tw/menu/drink",
                "domain": "www.milksha.com.tw",
                "title": "\u8ff7\u5ba2\u590f \u73cd\u73e0\u7d05\u8336\u62ff\u9435",
                "snippet": "\u4e2d\u676f \u3001 \u73cd\u73e0 \u3001 \u7d05\u8336 \u62ff\u9435",
                "score": 0.93,
                "officialness": "official",
                "source_quality_label": "high",
                "brand_detected": "\u8ff7\u5ba2\u590f",
                "channel_detected": "handmade_foodservice",
                "serving_basis": "per_cup",
                "nutrition_fields_present": ["kcal"],
                "customization_slots_present": ["size", "sugar"],
                "identity_confidence": "medium",
                "applicability_confidence": "medium",
                "applicability_notes": "menu page",
                "raw_ref": "raw/tavily/milksha_1.json#0",
            }
        ]
    )

    candidates = await collect_web_search_candidates(
        search_port=port,
        query="\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        identity_target="\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        max_results=3,
    )

    assert port.calls == [{"query": "\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435", "max_results": 3}]
    assert len(candidates) == 1
    candidate = candidates[0]
    _assert_candidate_only(candidate)
    assert candidate["candidate_id"]
    assert candidate["source_url"] == "https://www.milksha.com.tw/menu/drink"
    assert candidate["source_domain"] == "www.milksha.com.tw"
    assert candidate["source_title"] == "\u8ff7\u5ba2\u590f \u73cd\u73e0\u7d05\u8336\u62ff\u9435"
    assert candidate["query"] == "\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435"
    assert candidate["officialness_hint"] == "official"
    assert candidate["source_quality_hint"] == "high"
    assert candidate["brand_detected"] == "\u8ff7\u5ba2\u590f"
    assert candidate["serving_basis_candidate"] == "per_cup"
    assert candidate["nutrition_fields_present"] == ["kcal"]
    assert candidate["customization_slots_present"] == ["size", "sugar"]
    assert candidate["raw_ref"] == "raw/tavily/milksha_1.json#0"


def test_produce_web_search_candidates_keeps_official_wrong_item_as_candidate_only() -> None:
    candidates = produce_web_search_candidates(
        query="\u53ef\u53ef\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        identity_target="\u53ef\u53ef\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        raw_hits=[
            {
                "url": "https://www.coco-tea.com/menu/pearl-black-tea-latte",
                "title": "\u53ef\u53ef \u73cd\u73e0\u5976\u8336",
                "snippet": "\u5b98\u65b9\u83dc\u55ae",
                "officialness": "official",
                "source_quality_hint": "medium",
                "identity_confidence": "low",
                "applicability_notes": "official result but likely wrong item",
                "raw_ref": "raw/tavily/coco_wrong_item.json#0",
            }
        ],
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    _assert_candidate_only(candidate)
    assert candidate["officialness_hint"] == "official"
    assert candidate["identity_confidence"] == "low"
    assert candidate["applicability_notes"] == "official result but likely wrong item"


def test_produce_web_search_candidates_keeps_sibling_candidate_as_candidate_only() -> None:
    candidates = produce_web_search_candidates(
        query="\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        identity_target="\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        raw_hits=[
            {
                "url": "https://www.milksha.com.tw/menu/pearl-black-tea",
                "title": "\u8ff7\u5ba2\u590f \u73cd\u73e0\u7d05\u8336",
                "snippet": "\u76f8\u8fd1\u54c1\u9805",
                "officialness": "official",
                "identity_confidence": "medium",
                "applicability_confidence": "low",
                "raw_ref": "raw/tavily/milksha_sibling.json#0",
            }
        ],
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    _assert_candidate_only(candidate)
    assert candidate["identity_confidence"] == "medium"
    assert candidate["applicability_confidence"] == "low"


def test_produce_web_search_candidates_returns_empty_list_for_empty_hits() -> None:
    candidates = produce_web_search_candidates(
        query="\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        identity_target="\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        raw_hits=[],
    )

    assert candidates == []


def test_produce_web_search_candidates_degrades_safely_on_malformed_optional_fields() -> None:
    candidates = produce_web_search_candidates(
        query="\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        identity_target="\u8ff7\u5ba2\u590f\u73cd\u73e0\u7d05\u8336\u62ff\u9435",
        raw_hits=[
            {
                "url": "https://example.com/result",
                "title": 123,
                "snippet": None,
                "score": "bad-score",
                "officialness": 42,
                "source_quality_label": None,
                "serving_basis": 9,
                "nutrition_fields_present": "kcal",
                "customization_slots_present": None,
                "identity_confidence": 0.9,
                "applicability_confidence": {},
                "applicability_notes": ["not", "text"],
                "raw_ref": None,
            }
        ],
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    _assert_candidate_only(candidate)
    assert candidate["source_title"] == ""
    assert candidate["snippet"] == ""
    assert candidate["score"] is None
    assert candidate["officialness_hint"] == "unknown"
    assert candidate["source_quality_hint"] == "unknown"
    assert candidate["serving_basis_candidate"] == "unknown"
    assert candidate["nutrition_fields_present"] == []
    assert candidate["customization_slots_present"] == []
    assert candidate["identity_confidence"] == "unknown"
    assert candidate["applicability_confidence"] == "unknown"
    assert candidate["applicability_notes"] == ""
    assert candidate["raw_ref"]
