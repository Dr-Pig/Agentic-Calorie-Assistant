from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from scripts.run_manager_candidate_eval import _evaluate_case, MANAGER_CANDIDATE_EVAL_CASES, run_manager_candidate_eval


CASE_TEA_EGG = "我吃了一顆茶葉蛋"
CASE_BENTO = "我吃了一個便當"
CASE_LUWEI_UNKNOWN = "我吃了滷味"
CASE_LUWEI_LISTED = "我吃了豆干、海帶、貢丸的滷味"


class CandidateEvalFakeProvider:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.manager_model = "deepseek"
        self.manager_temperature = 0.0

    def readiness(self) -> dict[str, object]:
        return {
            "configured": True,
            "provider": "builderspace",
            "manager_model": self.manager_model,
        }

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = dict(kwargs["user_payload"])
        round_index = int(user_payload["round_index"])
        message = str(user_payload["raw_user_input"])
        if round_index == 0:
            if message == CASE_LUWEI_UNKNOWN:
                return (
                    {
                        "manager_action": "final",
                        "interaction_family": "food_logging",
                        "response_mode": "clarification",
                        "final_action": "request_clarification",
                        "operations": [],
                        "answer_contract": {"text": "Please list the specific items in the basket."},
                    },
                    self._trace(kwargs=kwargs),
                )
            food_name = "茶葉蛋" if message == CASE_TEA_EGG else "便當" if message == CASE_BENTO else "豆干"
            tool_calls = [{"name": "lookup_generic_food", "arguments": {"food_name": food_name}}]
            if message == CASE_LUWEI_LISTED:
                tool_calls = [
                    {"name": "lookup_generic_food", "arguments": {"food_name": "豆干"}},
                    {"name": "lookup_generic_food", "arguments": {"food_name": "海帶"}},
                    {"name": "lookup_generic_food", "arguments": {"food_name": "貢丸"}},
                ]
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": tool_calls,
                },
                self._trace(kwargs=kwargs),
            )

        item_results = [
            {
                "food_name": "茶葉蛋",
                "kcal_range": [70, 90],
                "likely_kcal": 80,
                "uncertainty": "low",
                "evidence_used": ["fixture_1"],
            }
        ]
        if message == CASE_BENTO:
            item_results = [
                {
                    "food_name": "便當",
                    "kcal_range": [650, 900],
                    "likely_kcal": 760,
                    "uncertainty": "medium",
                    "evidence_used": ["fixture_1"],
                }
            ]
        if message == CASE_LUWEI_LISTED:
            item_results = [
                {
                    "food_name": "豆干",
                    "kcal_range": [60, 100],
                    "likely_kcal": 80,
                    "uncertainty": "medium",
                    "evidence_used": ["fixture_a"],
                },
                {
                    "food_name": "海帶",
                    "kcal_range": [15, 45],
                    "likely_kcal": 30,
                    "uncertainty": "medium",
                    "evidence_used": ["fixture_b"],
                },
                {
                    "food_name": "貢丸",
                    "kcal_range": [60, 90],
                    "likely_kcal": 75,
                    "uncertainty": "low",
                    "evidence_used": ["fixture_c"],
                },
            ]
        return (
            {
                "manager_action": "final",
                "interaction_family": "food_logging",
                "response_mode": "intake_result",
                "item_results": item_results,
                "operations": [],
                "answer_contract": {"text": "ok"},
            },
            self._trace(kwargs=kwargs),
        )

    def _trace(self, *, kwargs: dict[str, object]) -> dict[str, object]:
        return {
            "provider": "builderspace",
            "model": self.manager_model,
            "temperature": self.manager_temperature,
            "max_tokens": kwargs.get("max_tokens"),
            "response_format": "json_schema",
            "timeout": None,
            "retry_policy": {"max_attempts": 1},
            "tool_choice": "none",
            "request_id": f"req_{len(self.calls)}",
            "raw_content": "{}",
            "parsed_object": {},
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 40,
                "total_tokens": 160,
            },
        }


def _test_output_dir() -> Path:
    path = Path("artifacts") / "test_manager_candidate_eval" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.mark.asyncio
async def test_manager_candidate_eval_uses_distinct_scope_and_not_b1_readiness() -> None:
    provider = CandidateEvalFakeProvider()
    output_dir = _test_output_dir()
    report = await run_manager_candidate_eval(
        provider=provider,
        candidate_profile_id="builderspace-kimi-k2.5-candidate",
        output_dir=output_dir,
        write_latest=False,
    )

    assert report["scope"] == "manager_candidate_eval"
    assert report["not_b1_readiness_evidence"] is True
    assert report["candidate_model"] == "kimi-k2.5"
    assert report["provider_profile_id"] == "builderspace-kimi-k2.5-candidate"
    assert report["provider_profile_role"] == "manager_candidate_primary"
    assert report["manager_candidate_status"] == "hypothesis_only"
    assert report["production_selected"] is False
    assert report["selection_status"] == "not_decided"
    assert report["evaluation_dimensions"] == [
        "tool_call_decision_obedience",
        "pass1_pass2_boundary_obedience",
        "multi_context_state_handling",
        "memory_summarization_posture",
        "no_fake_semantic_green",
    ]
    assert report["usage"] == {
        "prompt_tokens": 840,
        "completion_tokens": 280,
        "total_tokens": 1120,
    }
    assert isinstance(report["latency_ms"], int)
    assert report["latency_ms"] >= 0
    assert len(report["cases"]) == 4
    assert len(report["tool_loop_traces"]) == 4
    assert Path(report["artifact_path"]).exists()

    for case in report["cases"]:
        assert set(case).issuperset(
            {
                "case_id",
                "dimension",
                "transport_obeyed",
                "schema_valid",
                "boundary_obeyed",
                "context_stable",
                "memory_posture_acceptable",
                "semantic_honesty_preserved",
                "fake_green_detected",
                "failure_family",
                "trace_pointer",
                "usage",
                "latency_ms",
            }
        )


@pytest.mark.asyncio
async def test_manager_candidate_eval_can_select_gemini_candidate_and_preserves_honesty_case() -> None:
    provider = CandidateEvalFakeProvider()
    output_dir = _test_output_dir()
    report = await run_manager_candidate_eval(
        provider=provider,
        candidate_profile_id="builderspace-gemini-3-flash-preview-candidate",
        output_dir=output_dir,
        write_latest=False,
        case_ids=["MC-004"],
    )

    assert report["candidate_model"] == "gemini-3-flash-preview"
    assert report["provider_profile_role"] == "manager_candidate_secondary"
    assert report["manager_candidate_status"] == "hypothesis_only"
    assert report["selection_status"] == "not_decided"
    assert report["usage"] == {
        "prompt_tokens": 120,
        "completion_tokens": 40,
        "total_tokens": 160,
    }
    assert isinstance(report["latency_ms"], int)
    assert report["latency_ms"] >= 0
    assert len(report["cases"]) == 1
    case = report["cases"][0]
    assert case["case_id"] == "MC-004"
    assert case["fake_green_detected"] is False
    assert case["semantic_honesty_preserved"] is True
    assert case["failure_family"] == "none"


def test_manager_candidate_eval_matrix_doc_exists_and_mentions_not_readiness_evidence() -> None:
    text = Path(
        "docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md"
    ).read_text(encoding="utf-8-sig")

    assert "not B-1 readiness evidence" in text
    assert "kimi-k2.5" in text
    assert "gemini-3-flash-preview" in text


def test_manager_candidate_eval_handles_unreadable_case_without_trace() -> None:
    case_report = _evaluate_case(
        case=MANAGER_CANDIDATE_EVAL_CASES["MC-001"],
        case_result={
            "case_execution_status": "provider_runtime_error",
            "provider_runtime": {"reason": "provider_runtime_error", "raw_content_excerpt": "timeout"},
            "trace_index": 0,
            "case_latency_ms": 1234,
        },
        trace=None,
    )

    assert case_report["failure_family"] == "provider_runtime_error"
    assert case_report["transport_obeyed"] is False
    assert case_report["semantic_honesty_preserved"] is True
    assert case_report["trace_pointer"] is None
