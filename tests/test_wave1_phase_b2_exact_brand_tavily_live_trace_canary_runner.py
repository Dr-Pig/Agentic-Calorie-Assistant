from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from scripts.run_wave1_phase_b2_exact_brand_tavily_live_trace_canary import (
    DEFAULT_CASE_IDS,
    build_missing_token_report,
    run_tavily_live_trace_canary,
)


class _FakeSearchPort:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self._hits = hits

    def readiness(self) -> dict[str, Any]:
        return {"provider": "tavily", "configured": True, "timeout_seconds": 15}

    async def search_hits(self, *, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        return list(self._hits)


class _FakeExtractPort:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def readiness(self) -> dict[str, Any]:
        return {"provider": "tavily", "configured": True, "timeout_seconds": 15}

    async def extract_rows(self, *, urls: list[str], query: str) -> list[dict[str, Any]]:
        return list(self._rows)


def test_missing_token_report_is_not_live_and_never_claims_readiness() -> None:
    report = build_missing_token_report(case_ids=DEFAULT_CASE_IDS)

    assert report["provider_mode"] == "not_invoked"
    assert report["live_invoked"] is False
    assert report["failure_family"] == "missing_tavily_api_key"
    assert report["readiness_claimed"] is False


@pytest.mark.asyncio
async def test_runner_writes_live_trace_report_without_secret_or_readiness_claim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-secret")
    search_port = _FakeSearchPort(
        [
            {
                "title": "星巴克 那堤",
                "url": "https://www.starbucks.com.tw/products/drinks/product.jspx?id=1",
                "snippet": "大杯 熱量(大卡) 295",
                "score": 0.95,
                "officialness": "official",
                "brand_detected": "starbucks",
                "serving_basis": "per_cup",
                "identity_confidence": "medium",
            }
        ]
    )
    extract_port = _FakeExtractPort(
        [
            {
                "url": "https://www.starbucks.com.tw/products/drinks/product.jspx?id=1",
                "title": "那堤",
                "source_type": "official",
                "officialness": "official",
                "serving_basis": "per_cup",
                "brand_detected": "starbucks",
                "raw_content": "大杯 熱量(大卡) 295",
            }
        ]
    )

    path = await run_tavily_live_trace_canary(
        case_ids=("starbucks_latte_positive",),
        output_dir=tmp_path,
        search_port=search_port,
        extract_port=extract_port,
    )

    text = path.read_text(encoding="utf-8")
    assert "tvly-test-secret" not in text
    assert "api_key" not in text
    report = __import__("json").loads(text)
    assert report["provider_mode"] == "live"
    assert report["live_invoked"] is True
    assert report["readiness_claimed"] is False
    assert report["cases"][0]["trace"]["provider_profile"]["provider"] == "tavily"
    assert report["cases"][0]["trace"]["provider_profile"]["search_port"] == "_FakeSearchPort"
