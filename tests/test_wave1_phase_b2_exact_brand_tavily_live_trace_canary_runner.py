from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from scripts.run_wave1_phase_b2_exact_brand_tavily_live_trace_canary import (
    DEFAULT_CASE_IDS,
    build_missing_token_report,
    _load_local_env,
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
    assert report["failure_family"] == "environment_or_provider_blocker"
    assert report["failure_detail"] == "missing_tavily_api_key"
    assert report["readiness_claimed"] is False


def test_tavily_runner_loads_ignored_local_env_without_overwriting_session_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("TAVILY_API_KEY=tvly-test-secret\n", encoding="utf-8")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    _load_local_env(env_path)

    assert os.environ["TAVILY_API_KEY"] == "tvly-test-secret"

    monkeypatch.setenv("TAVILY_API_KEY", "session-secret")
    _load_local_env(env_path)

    assert os.environ["TAVILY_API_KEY"] == "session-secret"


def test_tavily_runner_loads_windows_utf8_bom_local_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("TAVILY_API_KEY=tvly-test-secret\n", encoding="utf-8-sig")
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    _load_local_env(env_path)

    assert os.environ["TAVILY_API_KEY"] == "tvly-test-secret"


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
    assert report["runtime_web_diagnostic_enabled"] is True
    assert report["readiness_claimed"] is False
    assert report["runtime_web_activation_recommended"] is False
    assert report["decision_pack_options"] == [
        "no_live_search_seam",
        "trace_only_canary_continues",
        "narrow_exact_brand_web_seam",
        "defer_web_and_continue_B2_local",
    ]
    assert report["readiness_claim"]["allowed_next_stage"] == "live_search_seam_decision_pack"
    assert report["cases"][0]["trace"]["provider_profile"]["provider"] == "tavily"
    assert report["cases"][0]["trace"]["provider_profile"]["search_port"] == "_FakeSearchPort"
    assert report["cases"][0]["runtime_web_diagnostic_enabled"] is True
    assert report["cases"][0]["trace"]["truth_boundary"]["runtime_web_diagnostic_enabled"] is True
    assert report["cases"][0]["verdict_category"] == "diagnostic_observation"
    assert report["cases"][0]["failure_family"] is None
    assert report["cases"][0]["runtime_web_activation_recommended"] is False
