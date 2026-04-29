from __future__ import annotations

from typing import Any

import pytest

from app.nutrition.application.exact_brand_web_canary import run_exact_brand_web_canary
from app.nutrition.application.retrieval_intent import build_retrieval_intent


class _FakeSearchPort:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self._hits = hits
        self.calls: list[dict[str, Any]] = []

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        self.calls.append({"query": query, "max_results": max_results})
        return list(self._hits)


class _FakeExtractPort:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.calls: list[dict[str, Any]] = []

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        self.calls.append({"urls": list(urls), "query": query})
        return list(self._rows)


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_returns_lane_result_when_extract_packet_is_accepted() -> None:
    intent = build_retrieval_intent("我喝了統一超級抹茶歐蕾")
    search_port = _FakeSearchPort(
        [
            {
                "title": "統一超級抹茶歐蕾",
                "url": "https://president.example/products/matcha-latte",
                "snippet": "官方商品頁",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "統一",
                "serving_basis": "per_cup",
                "raw_ref": "raw:search:001",
            }
        ]
    )
    extract_port = _FakeExtractPort(
        [
            {
                "url": "https://president.example/products/matcha-latte",
                "title": "統一超級抹茶歐蕾",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "統一",
                "raw_content": "每杯 400 kcal",
                "raw_ref": "raw:extract:001",
            }
        ]
    )

    outcome = await run_exact_brand_web_canary(
        raw_user_input="我喝了統一超級抹茶歐蕾",
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is not None
    assert outcome.trace["attempted"] is True
    assert outcome.trace["skip_reason"] is None
    assert outcome.trace["selected_search_packet_id"].startswith("pkt_web_search_")
    assert outcome.trace["accepted_extract_packet_id"].startswith("pkt_web_extract_")
    assert outcome.trace["search_attempt_count"] == 1
    assert outcome.trace["extract_attempt_count"] == 1
    assert outcome.result.manager_pass_2["item_results"][0]["exactness_posture"] == "exact"
    assert search_port.calls == [{"query": "統一超級抹茶歐蕾", "max_results": 5}]
    assert extract_port.calls == [
        {
            "urls": ["https://president.example/products/matcha-latte"],
            "query": "統一超級抹茶歐蕾",
        }
    ]


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_skips_non_exact_brand_inputs() -> None:
    search_port = _FakeSearchPort([])
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="我喝了一杯珍珠奶茶",
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is None
    assert outcome.trace["attempted"] is False
    assert outcome.trace["skip_reason"] == "retrieval_goal_not_exact_brand"
    assert search_port.calls == []
    assert extract_port.calls == []


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_returns_none_when_no_accepted_extract_packet_exists() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "統一超級抹茶歐蕾",
                "url": "https://president.example/products/matcha-latte",
                "snippet": "官方商品頁",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "統一",
                "serving_basis": "per_cup",
            }
        ]
    )
    extract_port = _FakeExtractPort(
        [
            {
                "url": "https://president.example/products/matcha-latte",
                "title": "統一超級抹茶歐蕾",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "統一",
                "raw_content": "每杯 400 kcal / 500 kcal",
            }
        ]
    )

    outcome = await run_exact_brand_web_canary(
        raw_user_input="我喝了統一超級抹茶歐蕾",
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is None
    assert outcome.trace["attempted"] is True
    assert outcome.trace["failure_reason"] == "no_accepted_web_extract_packet"
    assert outcome.trace["selected_search_packet_id"].startswith("pkt_web_search_")
    assert outcome.trace["accepted_extract_packet_id"] is None
