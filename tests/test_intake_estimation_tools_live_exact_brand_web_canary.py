from __future__ import annotations

import sys
import types
from typing import Any

import pytest

_conversation_state_summaries = types.ModuleType("app.runtime.application.conversation_state_summaries")
_conversation_state_summaries.build_archive_records = lambda *args, **kwargs: []
_conversation_state_summaries.build_pending_followup_state = lambda *args, **kwargs: {}
_conversation_state_summaries.build_recent_turn_summary = lambda *args, **kwargs: {}
_conversation_state_summaries.build_session_transcript_records = lambda *args, **kwargs: []
_conversation_state_summaries.build_session_summary = lambda *args, **kwargs: {}
_conversation_state_summaries.extract_current_session_preferences = lambda *args, **kwargs: {}
sys.modules.setdefault(
    "app.runtime.application.conversation_state_summaries",
    _conversation_state_summaries,
)

from app.composition.intake_estimation_tools import estimate_nutrition_tool  # noqa: E402
import app.nutrition.application.estimate_artifacts as estimate_artifacts_module  # noqa: E402
from app.nutrition.application.retrieval_semantic_decision import B2ManagerSemanticDecision  # noqa: E402


class _ProviderStub:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "provider_stub", "configured": False}


class _ConfiguredProviderStub:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "provider_stub", "configured": True}


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


@pytest.fixture(autouse=True)
def _stub_runtime_context_loader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        estimate_artifacts_module,
        "load_request_runtime_context",
        lambda **_: types.SimpleNamespace(
            user=None,
            latest_log=None,
            conversation_state=None,
            incoming_user_message_id=None,
            context_str="",
            manager_llm=None,
        ),
    )


@pytest.mark.asyncio
async def test_exact_db_hit_bypasses_live_exact_brand_canary() -> None:
    search_port = _FakeSearchPort([])
    extract_port = _FakeExtractPort([])

    artifact = await estimate_nutrition_tool(
        None,
        user_external_id="user-1",
        raw_user_input="我吃了松屋特盛牛丼",
        request_id="req-1",
        local_date="2026-04-29",
        provider=_ProviderStub(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="特盛牛丼",
            aliases=[],
            brand_hint="松屋",
            size_hint="特盛",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
    )

    assert artifact.payload.best_estimate_mode == "exact_item"
    assert artifact.payload.trace_contract["web_runtime_trace"]["attempted"] is False
    assert artifact.payload.trace_contract["web_runtime_trace"]["skip_reason"] == "exact_db_hit"
    assert search_port.calls == []
    assert extract_port.calls == []


@pytest.mark.asyncio
async def test_exact_db_hit_bypasses_live_exact_brand_canary_for_prefixed_starbucks_sentence() -> None:
    search_port = _FakeSearchPort([])
    extract_port = _FakeExtractPort([])

    artifact = await estimate_nutrition_tool(
        None,
        user_external_id="user-1b",
        raw_user_input="\u6211\u559d\u4e86\u661f\u5df4\u514b\u51b0\u90a3\u5802\u5927\u676f",
        request_id="req-1b",
        local_date="2026-04-29",
        provider=_ProviderStub(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="\u51b0\u90a3\u5802",
            aliases=[],
            brand_hint="\u661f\u5df4\u514b",
            size_hint="\u5927\u676f",
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
    )

    assert artifact.payload.best_estimate_mode == "exact_item"
    assert artifact.payload.estimated_kcal == 154
    assert artifact.payload.trace_contract["web_runtime_trace"]["attempted"] is False
    assert artifact.payload.trace_contract["web_runtime_trace"]["skip_reason"] == "exact_db_hit"
    assert search_port.calls == []
    assert extract_port.calls == []


@pytest.mark.asyncio
async def test_exact_brand_canary_success_builds_turn_web_evidence_artifact() -> None:
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
                "url": "https://president.example/products/matcha-latte",
                "title": "統一超級抹茶歐蕾",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "統一",
                "raw_content": "每杯 400 kcal",
            }
        ]
    )

    artifact = await estimate_nutrition_tool(
        None,
        user_external_id="user-2",
        raw_user_input="我喝了統一超級抹茶歐蕾",
        request_id="req-2",
        local_date="2026-04-29",
        provider=_ProviderStub(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="超級抹茶歐蕾",
            aliases=[],
            brand_hint="統一",
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
    )

    assert artifact.payload.best_estimate_mode == "exact_item"
    assert artifact.payload.estimated_kcal == 400
    assert artifact.payload.best_answer_source == "turn_web_evidence_packet"
    assert artifact.payload.trace_contract["canonical_write_decision"] == {
        "can_write_canonical": True,
        "source": "turn_web_evidence_packet",
        "failure_family": None,
    }
    assert artifact.payload.trace_contract["shadow_stub"] is False
    assert artifact.payload.trace_contract.get("evidence_unavailable") is not True
    assert artifact.payload.trace_contract["websearch_evidence_used"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["attempted"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["source_admissibility_status"] == "accepted"
    assert artifact.payload.trace_contract["web_runtime_trace"]["selected_extract_present"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["turn_web_evidence_packet_present"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["turn_web_evidence_may_support_commit"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["permanent_fooddb_promotion_allowed"] is False
    assert artifact.payload.trace_contract["web_runtime_trace"]["selected_search_packet_id"].startswith("pkt_web_search_")
    assert artifact.payload.trace_contract["web_runtime_trace"]["accepted_extract_packet_id"].startswith("pkt_web_extract_")
    assert search_port.calls == [{"query": "統一超級抹茶歐蕾", "max_results": 5}]
    assert extract_port.calls == [
        {
            "urls": ["https://president.example/products/matcha-latte"],
            "query": "統一超級抹茶歐蕾",
        }
    ]


@pytest.mark.asyncio
async def test_exact_brand_canary_query_does_not_duplicate_brand_when_base_already_contains_brand() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "Matsuya beef set nutrition",
                "url": "https://matsuya.example/beef-set",
                "snippet": "Official Matsuya beef set nutrition.",
                "score": 0.96,
                "officialness": "official",
                "brand_detected": "Matsuya",
                "serving_basis": "per_set",
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
                "url": "https://matsuya.example/beef-set",
                "title": "Matsuya beef set nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_set",
                "brand_detected": "Matsuya",
                "raw_content": "Matsuya beef set 720 kcal.",
            }
        ]
    )

    await estimate_nutrition_tool(
        None,
        user_external_id="user-brand-dedupe",
        raw_user_input="Matsuya beef set",
        request_id="req-brand-dedupe",
        local_date="2026-04-29",
        provider=_ProviderStub(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="Matsuya beef set",
            aliases=[],
            brand_hint="Matsuya",
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
    )

    assert search_port.calls == [{"query": "Matsuya beef set", "max_results": 5}]
    assert extract_port.calls == [
        {
            "urls": ["https://matsuya.example/beef-set"],
            "query": "Matsuya beef set",
        }
    ]


@pytest.mark.asyncio
async def test_exact_brand_canary_accepts_known_cross_language_brand_family() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "\u677e\u5c4b \u725b\u71d2\u8089\u5b9a\u98df Matsuya gyu yakiniku teishoku nutrition",
                "url": "https://matsuya.example/gyu-yakiniku-teishoku",
                "snippet": "Official Matsuya menu page.",
                "score": 0.95,
                "officialness": "official",
                "source_class": "brand_menu_page",
                "brand_detected": "Matsuya",
                "serving_basis": "per_set",
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
                "url": "https://matsuya.example/gyu-yakiniku-teishoku",
                "title": "\u677e\u5c4b \u725b\u71d2\u8089\u5b9a\u98df Matsuya gyu yakiniku teishoku nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_set",
                "brand_detected": "Matsuya",
                "raw_content": "\u677e\u5c4b \u725b\u71d2\u8089\u5b9a\u98df 720 kcal per set.",
            }
        ]
    )

    artifact = await estimate_nutrition_tool(
        None,
        user_external_id="user-cross-brand",
        raw_user_input="\u6211\u665a\u9910\u5403\u4e86\u677e\u5c4b\u725b\u71d2\u8089\u5b9a\u98df",
        request_id="req-cross-brand",
        local_date="2026-04-29",
        provider=_ProviderStub(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="\u725b\u71d2\u8089\u5b9a\u98df",
            aliases=[],
            brand_hint="\u677e\u5c4b",
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
    )

    web_trace = artifact.payload.trace_contract["web_runtime_trace"]
    assert artifact.payload.best_answer_source == "turn_web_evidence_packet"
    assert artifact.payload.estimated_kcal == 720
    assert web_trace["source_admissibility_status"] == "accepted"
    assert web_trace["turn_web_evidence_packet_present"] is True


@pytest.mark.asyncio
async def test_listed_item_web_evidence_builds_component_artifact_from_manager_owned_items() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "McDonalds Big Mac nutrition",
                "url": "https://mcdonalds.example/big-mac",
                "snippet": "Official Big Mac nutrition.",
                "score": 0.95,
                "officialness": "official",
                "brand_detected": "McDonalds",
                "serving_basis": "per_item",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
            },
            {
                "title": "McDonalds medium fries nutrition",
                "url": "https://mcdonalds.example/medium-fries",
                "snippet": "Official medium fries nutrition.",
                "score": 0.94,
                "officialness": "official",
                "brand_detected": "McDonalds",
                "serving_basis": "per_item",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
            },
            {
                "title": "McDonalds medium Coke nutrition",
                "url": "https://mcdonalds.example/medium-coke",
                "snippet": "Official medium Coke nutrition.",
                "score": 0.93,
                "officialness": "official",
                "brand_detected": "McDonalds",
                "serving_basis": "per_item",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
            },
        ]
    )
    extract_port = _FakeExtractPort(
        [
            {
                "url": "https://mcdonalds.example/big-mac",
                "title": "McDonalds Big Mac nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_item",
                "brand_detected": "McDonalds",
                "raw_content": "Big Mac 560 kcal.",
            },
            {
                "url": "https://mcdonalds.example/medium-fries",
                "title": "McDonalds medium fries nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_item",
                "brand_detected": "McDonalds",
                "raw_content": "Medium fries 320 kcal.",
            },
            {
                "url": "https://mcdonalds.example/medium-coke",
                "title": "McDonalds medium Coke nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_item",
                "brand_detected": "McDonalds",
                "raw_content": "Medium Coke 210 kcal.",
            },
        ]
    )

    artifact = await estimate_nutrition_tool(
        None,
        user_external_id="user-web-components",
        raw_user_input="mcdonalds combo",
        request_id="req-web-components",
        local_date="2026-04-29",
        provider=_ProviderStub(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="McDonalds combo",
            aliases=[],
            brand_hint="McDonalds",
            size_hint="medium fries medium Coke",
            modifier_hints=[],
            listed_items=["Big Mac", "medium fries", "medium Coke"],
            retrieval_goal="listed_item_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
    )

    web_trace = artifact.payload.trace_contract["web_runtime_trace"]
    assert artifact.payload.best_estimate_mode == "anchored_component"
    assert artifact.payload.estimated_kcal == 1090
    assert [item.name for item in artifact.payload.component_estimates] == [
        "McDonalds Big Mac nutrition",
        "McDonalds medium fries nutrition",
        "McDonalds medium Coke nutrition",
    ]
    assert web_trace["attempted"] is True
    assert web_trace["retrieval_goal"] == "listed_item_lookup"
    assert web_trace["component_level_evidence_present"] is True
    assert web_trace["all_listed_components_have_sources"] is True
    assert web_trace["turn_web_evidence_packet_present"] is True
    assert web_trace["turn_web_evidence_may_support_commit"] is True
    assert web_trace["permanent_fooddb_promotion_allowed"] is False
    assert len(search_port.calls) == 3
    assert len(extract_port.calls) == 3


@pytest.mark.asyncio
async def test_listed_item_web_evidence_requires_all_manager_listed_components() -> None:
    search_port = _FakeSearchPort(
        [
            {
                "title": "McDonalds Big Mac nutrition",
                "url": "https://mcdonalds.example/big-mac",
                "snippet": "Official Big Mac nutrition.",
                "score": 0.95,
                "officialness": "official",
                "brand_detected": "McDonalds",
                "serving_basis": "per_item",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
            },
            {
                "title": "McDonalds medium Coke nutrition",
                "url": "https://mcdonalds.example/medium-coke",
                "snippet": "Official medium Coke nutrition.",
                "score": 0.93,
                "officialness": "official",
                "brand_detected": "McDonalds",
                "serving_basis": "per_item",
                "identity_confidence": "high",
                "license_status": "public_menu_page",
                "robots_status": "allowed",
                "nutrition_fields_present": ["kcal"],
            },
        ]
    )
    extract_port = _FakeExtractPort(
        [
            {
                "url": "https://mcdonalds.example/big-mac",
                "title": "McDonalds Big Mac nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_item",
                "brand_detected": "McDonalds",
                "raw_content": "Big Mac 560 kcal.",
            },
            {
                "url": "https://mcdonalds.example/medium-coke",
                "title": "McDonalds medium Coke nutrition",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_item",
                "brand_detected": "McDonalds",
                "raw_content": "Medium Coke 210 kcal.",
            },
        ]
    )

    artifact = await estimate_nutrition_tool(
        None,
        user_external_id="user-web-partial-components",
        raw_user_input="mcdonalds combo",
        request_id="req-web-partial-components",
        local_date="2026-04-29",
        provider=_ProviderStub(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="McDonalds combo",
            aliases=[],
            brand_hint="McDonalds",
            size_hint="medium fries medium Coke",
            modifier_hints=[],
            listed_items=["Big Mac", "medium fries", "medium Coke"],
            retrieval_goal="listed_item_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
    )

    web_trace = artifact.payload.trace_contract["web_runtime_trace"]
    assert artifact.payload.best_estimate_mode is None
    assert artifact.payload.estimated_kcal == 0
    assert artifact.payload.trace_contract["canonical_write_decision"]["can_write_canonical"] is False
    assert web_trace["component_level_evidence_present"] is False
    assert web_trace["all_listed_components_have_sources"] is False
    assert web_trace["turn_web_evidence_packet_present"] is False


@pytest.mark.asyncio
async def test_exact_brand_canary_failure_records_failure_without_shadow_fallback() -> None:
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
                "url": "https://president.example/products/matcha-latte",
                "title": "統一超級抹茶歐蕾",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "unknown",
                "brand_detected": "統一",
                "raw_content": "400 kcal",
            }
        ]
    )

    artifact = await estimate_nutrition_tool(
        None,
        user_external_id="user-3",
        raw_user_input="我喝了統一超級抹茶歐蕾",
        request_id="req-3",
        local_date="2026-04-29",
        provider=_ProviderStub(),
        search_port=search_port,
        extract_port=extract_port,
        allow_search=True,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="超級抹茶歐蕾",
            aliases=[],
            brand_hint="統一",
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
            semantic_authority_source="synthetic_manager_structured_fixture",
        ),
    )

    assert artifact.payload.best_estimate_mode is None
    assert artifact.payload.estimated_kcal == 0
    assert artifact.payload.trace_contract["shadow_stub"] is False
    assert artifact.payload.trace_contract["evidence_unavailable"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["attempted"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["failure_reason"] == "no_accepted_web_extract_packet"


@pytest.mark.asyncio
async def test_missing_runtime_evidence_returns_unavailable_packet_not_shadow_fallback() -> None:
    artifact = await estimate_nutrition_tool(
        None,
        user_external_id="user-no-fallback",
        raw_user_input="unanchored breakfast combo abcxyz",
        request_id="req-no-fallback",
        local_date="2026-04-29",
        provider=_ConfiguredProviderStub(),
        search_port=_FakeSearchPort([]),
        extract_port=_FakeExtractPort([]),
        allow_search=False,
        manager_semantic_decision=B2ManagerSemanticDecision(
            base_dish="unanchored breakfast combo abcxyz",
            aliases=[],
            brand_hint=None,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="generic_anchor_lookup",
            semantic_authority_source="live_manager_structured_output",
        ),
    )

    trace_contract = artifact.payload.trace_contract
    assert artifact.payload.estimated_kcal == 0
    assert artifact.payload.component_estimates == []
    assert artifact.payload.reply_text == ""
    assert trace_contract["shadow_stub"] is False
    assert trace_contract["evidence_unavailable"] is True
    assert trace_contract["canonical_write_decision"] == {
        "can_write_canonical": False,
        "source": "evidence_unavailable",
        "failure_family": "nutrition_evidence_unavailable",
        "blockers": ["no_approved_runtime_evidence"],
    }
    assert trace_contract["response_mode_hint"] == "clarify_first"
