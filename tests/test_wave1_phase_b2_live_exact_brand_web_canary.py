from __future__ import annotations

from typing import Any

import pytest

from app.nutrition.application.exact_brand_web_canary import run_exact_brand_web_canary
from app.nutrition.application.retrieval_semantic_decision import B2ManagerSemanticDecision


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


def _exact_brand_decision(
    *,
    base_dish: str = "Matcha Latte",
    aliases: list[str] | None = None,
    brand_hint: str = "Test Brand",
    size_hint: str | None = None,
) -> B2ManagerSemanticDecision:
    return B2ManagerSemanticDecision(
        base_dish=base_dish,
        aliases=list(aliases or [f"{brand_hint} {base_dish}"]),
        brand_hint=brand_hint,
        size_hint=size_hint,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="exact_brand_lookup",
        semantic_authority_source="synthetic_manager_structured_fixture",
    )


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_returns_lane_result_when_extract_packet_is_accepted() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "Test Brand Matcha Latte",
                "url": "https://brand.example/products/matcha-latte",
                "snippet": "deterministic official result",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "Test Brand",
                "serving_basis": "per_cup",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
                "raw_ref": "raw:search:001",
            }
        ]
    )
    extract_port = _FakeExtractPort(
        [
            {
                "url": "https://brand.example/products/matcha-latte",
                "title": "Test Brand Matcha Latte",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "Test Brand",
                "raw_content": "400 kcal",
                "raw_ref": "raw:extract:001",
            }
        ]
    )

    outcome = await run_exact_brand_web_canary(
        raw_user_input="I drank a Test Brand Matcha Latte",
        manager_decision=_exact_brand_decision(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is not None
    assert outcome.trace["attempted"] is True
    assert outcome.trace["skip_reason"] is None
    assert outcome.trace["semantic_authority_source"] == "synthetic_manager_structured_fixture"
    assert outcome.trace["raw_text_retrieval_hint_goal"] == "generic_anchor_lookup"
    assert outcome.trace["web_query"] == "Test BrandMatcha Latte"
    assert outcome.trace["provider_profile"]["search_port"] == "_FakeSearchPort"
    assert outcome.trace["selected_search_packet_id"].startswith("pkt_web_search_")
    assert outcome.trace["accepted_extract_packet_id"].startswith("pkt_web_extract_")
    candidate_trace = outcome.trace["candidate_traces"][0]
    assert candidate_trace["candidate_identity"] == "Test Brand Matcha Latte"
    assert candidate_trace["source_url"] == "https://brand.example/products/matcha-latte"
    assert candidate_trace["source_domain"] == "brand.example"
    assert candidate_trace["hard_recheck_verdict"] == "accepted_for_exact_recheck"
    assert outcome.trace["packet_consumption_trace"]["accepted_packets"][0]["accepted_usage"] == "exact"
    assert outcome.trace["synthesis_evidence_refs"] == [outcome.trace["accepted_extract_packet_id"]]
    assert outcome.result.manager_pass_2["item_results"][0]["exactness_posture"] == "exact"
    assert search_port.calls == [{"query": "Test BrandMatcha Latte", "max_results": 5}]
    assert extract_port.calls == [
        {
            "urls": ["https://brand.example/products/matcha-latte"],
            "query": "Test BrandMatcha Latte",
        }
    ]


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_uses_contextualized_query_without_changing_target_identity() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "Test Brand Mocha",
                "url": "https://brand.example/products/mocha",
                "snippet": "official mocha sibling",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "Test Brand",
                "serving_basis": "per_cup",
                "identity_confidence": "medium",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
            }
        ]
    )
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="I drank a Test Brand Matcha Latte",
        manager_decision=_exact_brand_decision(),
        contextualized_query="Test Brand Mocha",
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is None
    assert outcome.trace["web_query"] == "Test Brand Mocha"
    assert search_port.calls == [{"query": "Test Brand Mocha", "max_results": 5}]
    assert outcome.trace["candidate_traces"][0]["hard_recheck_verdict"] == "rejected_by_hard_recheck"
    assert outcome.trace["candidate_traces"][0]["rejected_risk"] in {"sibling_variant", "wrong_item"}
    assert outcome.trace["synthesis_evidence_refs"] == []


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_does_not_let_raw_multi_item_tokens_block_manager_exact_lane() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "Test Brand Matcha Latte",
                "url": "https://brand.example/products/matcha-latte",
                "snippet": "deterministic official result",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "Test Brand",
                "serving_basis": "per_cup",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
            }
        ]
    )
    extract_port = _FakeExtractPort(
        [
            {
                "url": "https://brand.example/products/matcha-latte",
                "title": "Test Brand Matcha Latte",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "Test Brand",
                "raw_content": "400 kcal",
            }
        ]
    )

    outcome = await run_exact_brand_web_canary(
        raw_user_input="Test Brand Matcha Latte + side salad",
        manager_decision=_exact_brand_decision(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is not None
    assert outcome.trace["attempted"] is True
    assert outcome.trace["skip_reason"] is None


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_skips_without_manager_owned_retrieval_intent() -> None:
    search_port = _FakeSearchPort([])
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="I drank a Test Brand Matcha Latte",
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is None
    assert outcome.trace["attempted"] is False
    assert outcome.trace["skip_reason"] == "manager_owned_retrieval_intent_required"
    assert outcome.trace["semantic_authority_source"] == "deterministic_raw_text_hint_only"
    assert search_port.calls == []
    assert extract_port.calls == []


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_skips_when_exact_db_hit_exists() -> None:
    search_port = _FakeSearchPort([])
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="I drank a Test Brand Matcha Latte",
        manager_decision=_exact_brand_decision(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        exact_db_hit_present=True,
    )

    assert outcome.result is None
    assert outcome.trace["attempted"] is False
    assert outcome.trace["skip_reason"] == "exact_db_hit"
    assert outcome.trace["exact_db_miss_confirmed"] is False


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_skips_non_exact_brand_manager_goal() -> None:
    search_port = _FakeSearchPort([])
    extract_port = _FakeExtractPort([])
    generic_decision = B2ManagerSemanticDecision(
        base_dish="Tea Egg",
        aliases=["Tea Egg"],
        brand_hint=None,
        size_hint=None,
        modifier_hints=[],
        listed_items=[],
        retrieval_goal="generic_anchor_lookup",
        semantic_authority_source="synthetic_manager_structured_fixture",
    )

    outcome = await run_exact_brand_web_canary(
        raw_user_input="I ate a tea egg",
        manager_decision=generic_decision,
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is None
    assert outcome.trace["attempted"] is False
    assert outcome.trace["skip_reason"] == "retrieval_goal_not_exact_brand"


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_returns_none_when_no_accepted_extract_packet_exists() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "Test Brand Matcha Latte",
                "url": "https://brand.example/products/matcha-latte",
                "snippet": "deterministic official result",
                "score": 0.92,
                "officialness": "official",
                "brand_detected": "Test Brand",
                "serving_basis": "per_cup",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
            }
        ]
    )
    extract_port = _FakeExtractPort(
        [
            {
                "url": "https://brand.example/products/matcha-latte",
                "title": "Test Brand Matcha Latte",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "Test Brand",
                "raw_content": "400 kcal / 500 kcal",
            }
        ]
    )

    outcome = await run_exact_brand_web_canary(
        raw_user_input="I drank a Test Brand Matcha Latte",
        manager_decision=_exact_brand_decision(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
    )

    assert outcome.result is None
    assert outcome.trace["attempted"] is True
    assert outcome.trace["failure_reason"] == "no_accepted_web_extract_packet"
    assert outcome.trace["accepted_extract_packet_id"] is None


@pytest.mark.asyncio
async def test_live_exact_brand_web_canary_keeps_rejected_web_candidates_out_of_synthesis_refs() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "Test Brand Cocoa Latte",
                "url": "https://brand.example/products/cocoa-latte",
                "snippet": "official sibling variant",
                "score": 0.9,
                "officialness": "official",
                "brand_detected": "Test Brand",
                "identity_confidence": "medium",
                "serving_basis": "per_cup",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
                "raw_ref": "raw:search:wrong-item",
            }
        ]
    )
    extract_port = _FakeExtractPort([])

    outcome = await run_exact_brand_web_canary(
        raw_user_input="I drank a Test Brand Matcha Latte",
        manager_decision=_exact_brand_decision(),
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
