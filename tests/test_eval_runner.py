"""Tests for eval wave runner logic (mock provider, fixture loading, summary)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Fixture loading
# ---------------------------------------------------------------------------

def test_eval_fixture_loads_and_has_expected_shape() -> None:
    path = ROOT / "tests" / "fixtures" / "eval_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(cases, list)
    assert len(cases) >= 5
    for case in cases:
        assert "id" in case
        assert "bucket" in case
        assert "input_text" in case
        assert "should_follow_up" in case
        assert "expected_failed_layer" in case


def test_retrieval_fixture_loads_and_has_expected_shape() -> None:
    path = ROOT / "tests" / "fixtures" / "retrieval_sanity_cases.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(cases, list)
    assert len(cases) >= 6
    for case in cases:
        assert "id" in case
        assert "bucket" in case
        assert "query" in case


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_provider_returns_structured_answer() -> None:
    # Import inline to keep test module self-contained
    import sys
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from run_eval_wave import MockProvider

    provider = MockProvider()
    parsed, trace = await provider.complete_with_trace(
        system_prompt="test",
        user_payload={"user_input": "滷肉飯"},
        stage="primary_answer_pass_initial",
        max_tokens=1000,
    )
    assert isinstance(parsed, dict)
    assert parsed.get("title") == "滷肉飯"
    assert parsed.get("kcal_most_likely", 0) > 0
    assert trace["provider"] == "mock"


@pytest.mark.asyncio
async def test_mock_provider_handles_planner_stage() -> None:
    import sys
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from run_eval_wave import MockProvider

    provider = MockProvider()
    parsed, trace = await provider.complete_with_trace(
        system_prompt="test",
        user_payload={"raw_user_input": "起司蛋餅"},
        stage="planner_pass_initial",
        max_tokens=500,
    )
    assert parsed.get("intent") == "food_estimation"
    assert parsed.get("route") == "estimation"


# ---------------------------------------------------------------------------
# End-to-end mock eval (single case)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_eval_single_case_produces_trace_and_verdict() -> None:
    import sys
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from run_eval_wave import MockProvider, _run_eval_case

    case = {
        "id": "test-001",
        "bucket": "common_foods",
        "input_text": "起司蛋餅",
        "expected_route_family": None,
        "should_follow_up": False,
        "should_use_exact_truth": False,
        "expected_risk_family": [],
        "expected_failed_layer": None,
        "kcal_plausible_range": [250, 500],
    }
    provider = MockProvider()
    result = await _run_eval_case(case, provider=provider)

    assert result["id"] == "test-001"
    assert result["bucket"] == "common_foods"
    assert result["verdict"] in {"win", "neutral", "loss"}
    assert "checks" in result
    assert "actual" in result
    assert result["actual"]["estimated_kcal"] >= 0


# ---------------------------------------------------------------------------
# Summary builder
# ---------------------------------------------------------------------------

def test_eval_summary_aggregates_correctly() -> None:
    import sys
    scripts_dir = str(ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    from run_eval_wave import _build_eval_summary

    results = [
        {
            "id": "a", "bucket": "common_foods", "verdict": "win", "failed_layer": None,
            "checks": {"followup_not_expected_and_absent": True},
            "actual": {"retry_triggered": False, "best_answer_source": "initial"},
        },
        {
            "id": "b", "bucket": "common_foods", "verdict": "loss", "failed_layer": "layer3_primary_llm",
            "checks": {"followup_expected_and_present": False},
            "actual": {"retry_triggered": True, "best_answer_source": "retry"},
        },
        {
            "id": "c", "bucket": "exact_branded", "verdict": "win", "failed_layer": None,
            "checks": {"exact_truth_used": True, "followup_not_expected_and_absent": True},
            "actual": {"retry_triggered": False, "best_answer_source": "reference_card"},
        },
    ]
    summary = _build_eval_summary(results)

    assert summary["total_cases"] == 3
    assert summary["results"]["win"] == 2
    assert summary["results"]["loss"] == 1
    assert summary["layer_failure_rate"]["layer3_primary_llm"] == 1
    assert summary["bucket_results"]["common_foods"]["win"] == 1
    assert summary["bucket_results"]["common_foods"]["loss"] == 1
    assert summary["exact_truth_hit_rate"] == 1.0
    assert summary["retry_count"] == 1
    assert summary["rescue_count"] == 1
