from __future__ import annotations

import sys
import types
from typing import Any

import pytest

_conversation_state_summaries = types.ModuleType("app.runtime.application.conversation_state_summaries")
_conversation_state_summaries.build_archive_records = lambda *args, **kwargs: []
_conversation_state_summaries.build_pending_followup_state = lambda *args, **kwargs: None
_conversation_state_summaries.build_recent_turn_summary = lambda *args, **kwargs: {}
_conversation_state_summaries.build_session_transcript_records = lambda *args, **kwargs: []
_conversation_state_summaries.build_session_summary = lambda *args, **kwargs: {}
_conversation_state_summaries.extract_current_session_preferences = lambda *args, **kwargs: {}
sys.modules.setdefault(
    "app.runtime.application.conversation_state_summaries",
    _conversation_state_summaries,
)

from app.composition.intake_estimation_tools import estimate_nutrition_tool
import app.nutrition.application.estimate_artifacts as estimate_artifacts_module


class _ProviderStub:
    def readiness(self) -> dict[str, Any]:
        return {"provider": "provider_stub", "configured": False}


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
    )

    assert artifact.payload.best_estimate_mode == "exact_item"
    assert artifact.payload.trace_contract["web_runtime_trace"]["attempted"] is False
    assert artifact.payload.trace_contract["web_runtime_trace"]["skip_reason"] == "exact_db_hit"
    assert search_port.calls == []
    assert extract_port.calls == []


@pytest.mark.asyncio
async def test_exact_brand_canary_success_keeps_user_facing_fallback_unchanged_but_records_trace() -> None:
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
    )

    assert artifact.payload.best_estimate_mode is None
    assert artifact.payload.trace_contract["web_runtime_trace"]["attempted"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["selected_search_packet_id"].startswith("pkt_web_search_")
    assert artifact.payload.trace_contract["web_runtime_trace"]["accepted_extract_packet_id"].startswith("pkt_web_extract_")
    assert artifact.payload.estimated_kcal > 0
    assert search_port.calls == [{"query": "統一超級抹茶歐蕾", "max_results": 5}]
    assert extract_port.calls == [
        {
            "urls": ["https://president.example/products/matcha-latte"],
            "query": "統一超級抹茶歐蕾",
        }
    ]


@pytest.mark.asyncio
async def test_exact_brand_canary_failure_keeps_fallback_and_records_failure_reason() -> None:
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
    )

    assert artifact.payload.best_estimate_mode is None
    assert artifact.payload.trace_contract["web_runtime_trace"]["attempted"] is True
    assert artifact.payload.trace_contract["web_runtime_trace"]["failure_reason"] == "no_accepted_web_extract_packet"
    assert artifact.payload.estimated_kcal > 0
