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
    assert outcome.trace["readiness_claimed"] is False
    assert outcome.trace["skip_reason"] is None
    assert outcome.trace["web_query"] == "統一超級抹茶歐蕾"
    assert outcome.trace["provider_profile"]["search_port"] == "_FakeSearchPort"
    assert outcome.trace["selected_search_packet_id"].startswith("pkt_web_search_")
    assert outcome.trace["accepted_extract_packet_id"].startswith("pkt_web_extract_")
    assert outcome.trace["candidate_traces"] == [
        {
            "packet_id": outcome.trace["selected_search_packet_id"],
            "candidate_identity": "統一超級抹茶歐蕾",
            "source_url": "https://president.example/products/matcha-latte",
            "source_domain": "president.example",
            "source_title": "統一超級抹茶歐蕾",
            "source_snippet": "官方商品頁",
            "hard_recheck_verdict": "accepted_for_exact_recheck",
            "accepted_usage": None,
            "rejected_risk": None,
        }
    ]
    assert outcome.trace["packet_consumption_trace"]["accepted_packets"][0]["accepted_usage"] == "exact"
    assert outcome.trace["packet_consumption_trace"]["rejected_candidates"] == []
    assert outcome.trace["synthesis_evidence_refs"] == [outcome.trace["accepted_extract_packet_id"]]
    assert outcome.trace["truth_boundary"] == {
        "trace_only": True,
        "runtime_web_diagnostic_enabled": True,
        "web_candidate_truth_authority": False,
        "accepted_extract_packet_truth_authority": False,
        "requires_packetizer_hard_recheck_consumption": True,
        "requires_synthesis_verifier": True,
        "runtime_web_activation_recommended": False,
    }
    accepted_packet_ids = {
        packet["packet_id"] for packet in outcome.trace["packet_consumption_trace"]["accepted_packets"]
    }
    assert set(outcome.trace["synthesis_evidence_refs"]).issubset(accepted_packet_ids)
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
async def test_live_exact_brand_web_canary_uses_contextualized_query_without_changing_target_identity() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "星巴克 大杯 摩卡",
                "url": "https://www.starbucks.com.tw/products/drinks/mocha",
                "snippet": "官方商品頁",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "星巴克",
                "serving_basis": "per_cup",
                "identity_confidence": "medium",
            }
        ]
    )
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="我喝了星巴克大杯那堤",
        contextualized_query="星巴克大杯摩卡",
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is None
    assert outcome.trace["web_query"] == "星巴克大杯摩卡"
    assert search_port.calls == [{"query": "星巴克大杯摩卡", "max_results": 5}]
    assert outcome.trace["candidate_traces"][0]["hard_recheck_verdict"] == "rejected_by_hard_recheck"
    assert outcome.trace["candidate_traces"][0]["rejected_risk"] in {"sibling_variant", "wrong_item"}
    assert outcome.trace["synthesis_evidence_refs"] == []


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_skips_when_exact_db_hit_exists() -> None:
    search_port = _FakeSearchPort([])
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="我吃了松屋特盛牛丼",
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        exact_db_hit_present=True,
    )

    assert outcome.result is None
    assert outcome.trace["attempted"] is False
    assert outcome.trace["skip_reason"] == "exact_db_hit"
    assert outcome.trace["exact_db_miss_confirmed"] is False
    assert search_port.calls == []
    assert extract_port.calls == []


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
async def test_live_exact_brand_web_canary_skips_self_selected_basket_without_search() -> None:
    search_port = _FakeSearchPort([])
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="我吃了滷味",
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


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_keeps_rejected_web_candidates_out_of_synthesis_refs() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "統一 超級可可歐蕾",
                "url": "https://president.example/products/cocoa-latte",
                "snippet": "同品牌相近品項",
                "score": 0.9,
                "officialness": "official",
                "brand_detected": "統一",
                "identity_confidence": "medium",
                "serving_basis": "per_cup",
                "raw_ref": "raw:search:wrong-item",
            }
        ]
    )
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="我喝了統一超級抹茶歐蕾",
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is None
    assert outcome.trace["failure_reason"] == "selected_extract_policy_blocked"
    assert outcome.trace["candidate_traces"][0]["hard_recheck_verdict"] == "rejected_by_hard_recheck"
    assert outcome.trace["candidate_traces"][0]["rejected_risk"] in {"sibling_variant", "wrong_item"}
    assert outcome.trace["synthesis_evidence_refs"] == []
    assert outcome.trace["rejected_web_candidates_used_as_evidence"] is False
