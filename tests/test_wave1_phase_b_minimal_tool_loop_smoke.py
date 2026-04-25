from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.providers.builderspace_adapter import BuilderSpaceResponseError
import pytest

from scripts.run_wave1_phase_b_minimal_tool_loop_smoke import run_phase_b_minimal_tool_loop_smoke


class FakePhaseBProvider:
    def __init__(self, *, pass2_forbidden: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self.pass2_forbidden = pass2_forbidden

    def readiness(self) -> dict[str, object]:
        return {
            "configured": True,
            "provider": "builderspace",
            "manager_model": "deepseek",
        }

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        if round_index == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "tool_calls": [
                        {"name": "lookup_generic_food", "arguments": {"food_name": "茶葉蛋"}},
                        {"name": "retrieve_web_food_evidence", "arguments": {"query": "茶葉蛋"}},
                    ],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        payload: dict[str, object] = {
            "manager_action": "final",
            "interaction_family": "food_logging",
            "response_mode": "intake_result",
            "item_results": [
                {
                    "food_name": "茶葉蛋",
                    "kcal_range": [70, 90],
                    "likely_kcal": 80,
                    "uncertainty": "low",
                    "evidence_used": ["packetized_generic_food_candidate"],
                }
            ],
            "operations": [
                {
                    "operation_type": "create_items",
                    "target_meal_ref": "new",
                    "target_item_ref": None,
                    "meal_time_context": {"local_date": "2026-04-25", "time_hint": None},
                    "items": [
                        {
                            "food_name": "茶葉蛋",
                            "ui_record_status": "logged",
                            "estimation_posture": "confident_estimate",
                            "ledger_status": "included",
                            "question_type": "none",
                            "refinement_open": False,
                        }
                    ],
                }
            ],
            "answer_contract": {"text": "ok"},
        }
        if self.pass2_forbidden:
            payload["mutation_result"] = {"ledger_item_ids": ["bad"]}
        return payload, self._trace(call_index=len(self.calls), kwargs=kwargs)

    def _trace(self, *, call_index: int, kwargs: dict[str, object]) -> dict[str, object]:
        return {
            "provider": "builderspace",
            "model": "deepseek",
            "temperature": None,
            "max_tokens": kwargs.get("max_tokens"),
            "response_format": "json_schema",
            "timeout": None,
            "retry_policy": {"max_attempts": 1},
            "tool_choice": "none",
            "request_id": f"fake_req_{call_index}",
            "raw_content": "{}",
            "parsed_object": {},
        }


class FailingPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise TimeoutError("simulated provider timeout")


class NonTimeoutFailingPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise ValueError("simulated non-timeout provider failure")


class WrappedReadTimeoutPhaseBProvider(FakePhaseBProvider):
    def readiness(self) -> dict[str, object]:
        readiness = dict(super().readiness())
        readiness.update(
            {
                "timeout_seconds": 45,
                "transport_retry_count": 0,
                "transport_retry_backoff_seconds": 0.75,
                "base_url": "https://space.ai-builders.com/backend/v1",
            }
        )
        return readiness

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise BuilderSpaceResponseError(
            "BuilderSpace manager error at stage=intake_manager_round: ReadTimeout: ",
            trace={
                "stage": "intake_manager_round",
                "provider": "builderspace",
                "model": "deepseek",
                "base_url": "https://space.ai-builders.com/backend/v1",
                "timeout_seconds": 45,
                "transport_attempts": [
                    {
                        "attempt_index": 1,
                        "stage": "intake_manager_round",
                        "model": "deepseek",
                        "error_type": "ReadTimeout",
                    }
                ],
            },
        )


class FinalOnlyPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        return (
            {
                "manager_action": "final",
                "interaction_family": "food_logging",
                "response_mode": "clarification",
                "operations": [
                    {
                        "operation_type": "create_items",
                        "target_meal_ref": "new",
                        "target_item_ref": None,
                        "meal_time_context": {"local_date": None, "time_hint": None},
                        "items": [
                            {
                                "food_name": "滷味",
                                "ui_record_status": "needs_info",
                                "estimation_posture": "unresolved",
                                "ledger_status": "excluded_pending_info",
                                "question_type": "blocking_pending",
                                "refinement_open": False,
                            }
                        ],
                    }
                ],
                "answer_contract": {},
            },
            self._trace(call_index=len(self.calls), kwargs=kwargs),
        )


class MissingRequestIdPhaseBProvider(FakePhaseBProvider):
    def _trace(self, *, call_index: int, kwargs: dict[str, object]) -> dict[str, object]:
        trace = dict(super()._trace(call_index=call_index, kwargs=kwargs))
        trace.pop("request_id")
        trace["request_payload"] = {
            "temperature": 0,
            "max_tokens": kwargs.get("max_tokens"),
            "response_format": {"type": "json_object"},
        }
        return trace


class SearchAliasPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        if round_index == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": [{"name": "search", "arguments": {"query": "茶葉蛋"}}],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class MixedCanonicalAndAliasPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        if round_index == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": [
                        {"name": "lookup_generic_food", "arguments": {"food_name": "茶葉蛋"}},
                        {"name": "search", "arguments": {"query": "茶葉蛋 熱量"}},
                    ],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class SlowPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        await asyncio.sleep(0.01)
        return await super().complete_with_trace(**kwargs)


class HangingPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        await asyncio.sleep(0.05)
        return await super().complete_with_trace(**kwargs)


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_calls_provider_exactly_twice_and_emits_trace(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    assert len(provider.calls) == 2
    trace = report["tool_loop_traces"][0]
    assert report["phase"] == "B-1"
    assert report["scope"] == "minimal_tool_loop_smoke"
    assert report["pass1_mode"] == "forced_tool_request_smoke"
    assert report["forced_tool_request_contract"] is True
    assert report["manager_tool_selection_claimed"] is False
    assert report["b2_evidence_runtime_started"] is False
    assert report["nutrition_accuracy_claimed"] is False
    assert trace["manager_pass_1"]["manager_role"] == "pass_1_tool_request"
    assert trace["pass1_mode"] == "forced_tool_request_smoke"
    assert trace["forced_tool_request_contract"] is True
    assert trace["manager_tool_selection_claimed"] is False
    assert trace["manager_pass_2"]["manager_role"] == "pass_2_synthesis"
    assert trace["manager_pass_1"]["prompt_hash"]
    assert trace["manager_pass_2"]["prompt_hash"]
    assert trace["manager_pass_1"]["latency_ms"] >= 0
    assert trace["manager_pass_2"]["latency_ms"] >= 0
    assert trace["case_latency_ms"] >= trace["manager_pass_1"]["latency_ms"] + trace["manager_pass_2"]["latency_ms"]
    assert report["runtime_latency"]["latency_budget_type"] == "b1_full_smoke_reporting_target"
    assert report["runtime_latency"]["not_user_runtime_budget"] is True
    assert report["runtime_latency"]["total_latency_ms"] >= trace["case_latency_ms"]
    assert provider.calls[1]["user_payload"]["tool_results"][0]["packetizer_outputs"]
    assert "raw_stub_output" not in provider.calls[1]["user_payload"]["tool_results"][0]
    assert trace["packetizer"]["outputs"][0]["fixture_id"]
    assert trace["packetizer"]["outputs"][0]["fixture_hash"]
    assert trace["packetizer"]["outputs"][0]["fixture_only"] is True
    assert trace["packetizer"]["outputs"][0]["generated_by"] == "deterministic_fixture"


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_blocks_luwei_estimate_tools(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了滷味"],
        output_dir=tmp_path,
        write_latest=False,
    )

    router = report["tool_loop_traces"][0]["runtime_tool_router"]
    assert "lookup_generic_food" in router["blocked_tools"]
    assert "retrieve_web_food_evidence" in router["blocked_tools"]
    assert router["block_reasons"][0]["rule"] == "self_selected_basket_without_ingredients_blocks_estimate_tools"


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_no_mutation_query_has_explicit_no_mutation_trace(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["珍珠奶茶大概多少熱量？"],
        output_dir=tmp_path,
        write_latest=False,
    )

    mutation = report["tool_loop_traces"][0]["mutation"]
    assert mutation == {
        "mutation_attempted": False,
        "reason": "no_mutation_intent",
        "mutation_result": None,
    }


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_pass2_forbidden_mutation_fields_are_traced(tmp_path: Path) -> None:
    provider = FakePhaseBProvider(pass2_forbidden=True)

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    assert "mutation_result" in report["tool_loop_traces"][0]["manager_pass_2"]["forbidden_mutation_fields_present"]


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_provider_error_emits_diagnostic_artifact(tmp_path: Path) -> None:
    provider = FailingPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    assert report["provider_runtime"]["blocker"] is True
    assert report["provider_runtime"]["reason"] == "provider_timeout"
    assert report["provider_runtime"]["error_type"] == "TimeoutError"
    assert report["tool_loop_traces"] == []


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_wrapped_read_timeout_has_timeout_diagnostics(tmp_path: Path) -> None:
    provider = WrappedReadTimeoutPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
        provider_timeout_ms=240000,
    )

    runtime = report["provider_runtime"]
    assert runtime["blocker"] is True
    assert runtime["reason"] == "provider_timeout"
    assert runtime["error_type"] == "BuilderSpaceResponseError"
    assert runtime["provider"] == "builderspace"
    assert runtime["model"] == "deepseek"
    assert runtime["stage"] == "intake_manager_round"
    assert runtime["adapter_timeout_seconds"] == 45
    assert runtime["outer_provider_timeout_ms"] == 240000
    assert runtime["timeout_layer"] == "adapter_http_timeout"
    assert runtime["attempt_count"] == 1
    assert runtime["retry_count"] == 0
    assert runtime["completed_trace_count"] == 0
    assert runtime["expected_case_count"] == 1
    assert runtime["base_url"] == "https://space.ai-builders.com/backend/v1"
    assert report["tool_loop_traces"] == []


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_non_timeout_error_is_not_labeled_timeout(tmp_path: Path) -> None:
    provider = NonTimeoutFailingPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    runtime = report["provider_runtime"]
    assert runtime["reason"] == "provider_runtime_error"
    assert runtime["error_type"] == "ValueError"
    assert runtime["timeout_layer"] is None


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_records_positive_latency_for_slow_provider(tmp_path: Path) -> None:
    provider = SlowPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_1"]["latency_ms"] > 0
    assert trace["manager_pass_2"]["latency_ms"] > 0
    assert report["runtime_latency"]["total_latency_ms"] > 0


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_provider_timeout_is_artifactized(tmp_path: Path) -> None:
    provider = HangingPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
        provider_timeout_ms=1,
    )

    assert report["provider_runtime"]["blocker"] is True
    assert report["provider_runtime"]["reason"] == "provider_timeout"
    assert report["provider_runtime"]["timeout_ms"] == 1
    assert report["provider_runtime"]["outer_provider_timeout_ms"] == 1
    assert report["provider_runtime"]["timeout_layer"] == "outer_provider_timeout"
    assert report["provider_runtime"]["completed_trace_count"] == 0
    assert report["provider_runtime"]["expected_case_count"] == 1
    assert report["runtime_latency"]["completed_trace_count"] == 0
    assert report["tool_loop_traces"] == []


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_records_self_selected_block_when_manager_skips_tools(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了滷味"],
        output_dir=tmp_path,
        write_latest=False,
    )

    router = report["tool_loop_traces"][0]["runtime_tool_router"]
    assert router["manager_requested_tools"] == []
    assert "lookup_generic_food" in router["blocked_tools"]
    assert "retrieve_web_food_evidence" in router["blocked_tools"]
    assert router["block_reasons"][0]["rule"] == "self_selected_basket_without_ingredients_blocks_estimate_tools"


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_normalizes_missing_provider_request_id(tmp_path: Path) -> None:
    provider = MissingRequestIdPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    params = report["tool_loop_traces"][0]["manager_pass_2"]["provider_params"]
    assert params["provider"] == "builderspace"
    assert params["model"] == "deepseek"
    assert params["request_id"].startswith("phase_b1_pass_2_synthesis_")
    assert params["temperature"] == 0
    assert params["response_format"]


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_pass1_prompt_prioritizes_tool_request_mode(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    pass1_prompt = str(provider.calls[0]["system_prompt"])
    assert pass1_prompt.startswith("Phase B-1 Pass 1 HARD CONTRACT")
    assert "MUST return manager_action='call_tools'" in pass1_prompt
    assert "Do not choose manager_action='final' in Pass 1" in pass1_prompt
    assert "JSON example for tea egg" in pass1_prompt
    assert "lookup_generic_food" in pass1_prompt
    assert "If ready, return manager_action='final'" not in pass1_prompt


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_does_not_inject_hard_call_tools_prompt(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    pass1_prompt = str(provider.calls[0]["system_prompt"])
    trace = report["tool_loop_traces"][0]
    constraints = provider.calls[0]["user_payload"]["constraints"]
    pass1_provider_trace = trace["manager_pass_1"]

    assert pass1_prompt.startswith("Phase B-1 natural-probe tool selection guidance")
    assert "Phase B-1 natural-probe tool selection guidance" in pass1_prompt
    assert "evidence-needed scenarios" in pass1_prompt
    assert "manager_action='call_tools'" in pass1_prompt
    assert "tool_calls" in pass1_prompt
    assert "operations=[]" in pass1_prompt
    assert "answer_contract={}" in pass1_prompt
    assert "lookup_generic_food" in pass1_prompt
    assert "Do not use generic aliases such as search or web_search" in pass1_prompt
    assert "MUST return manager_action='call_tools'" not in pass1_prompt
    assert "Do not choose manager_action='final'" not in pass1_prompt
    assert "every food_logging or nutrition_info_query case must call at least one read tool" not in pass1_prompt
    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_1_natural_tool_selection_guidance_v1"
    assert pass1_provider_trace["phase_b1_task_payload_id"] == "phase_b1_pass_1_natural_tool_selection_guidance_v1"
    assert pass1_provider_trace["phase_b1_task_payload_hash"]
    assert report["pass1_mode"] == "natural_tool_selection_probe"
    assert report["forced_tool_request_contract"] is False
    assert report["manager_tool_selection_claimed"] is True


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_does_not_add_tool_calls_when_manager_skips(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    trace = report["tool_loop_traces"][0]
    assert trace["runtime_tool_router"]["manager_requested_tools"] == []
    assert trace["read_tool_executions"] == []
    assert trace["packetizer"]["outputs"] == []


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_does_not_fallback_item_results_from_packets(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    trace = report["tool_loop_traces"][0]
    assert trace["runner_derived_item_results"] is False


@pytest.mark.asyncio
async def test_phase_b1_smoke_blocks_search_alias_without_execution_or_packet(tmp_path: Path) -> None:
    provider = SearchAliasPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    trace = report["tool_loop_traces"][0]
    router = trace["runtime_tool_router"]
    assert router["requested_read_tools"] == ["search"]
    assert router["allowed_tools"] == []
    assert router["filtered_tool_plan"] == []
    assert router["blocked_tools"] == ["search"]
    assert router["available_read_tools"] == [
        "lookup_generic_food",
        "retrieve_web_food_evidence",
        "load_taiwan_food_semantics_skill",
    ]
    assert router["canonical_tool_catalog_hash"]
    assert router["block_reasons"] == [
        {
            "tool_name": "search",
            "reason": "unsupported_read_tool_name",
            "supported_tools": [
                "lookup_generic_food",
                "retrieve_web_food_evidence",
                "load_taiwan_food_semantics_skill",
            ],
            "normalization_attempted": False,
        }
    ]
    assert trace["read_tool_executions"] == []
    assert trace["packetizer"]["outputs"] == []


@pytest.mark.asyncio
async def test_phase_b1_smoke_allows_canonical_lookup_generic_food(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    trace = report["tool_loop_traces"][0]
    router = trace["runtime_tool_router"]
    assert "lookup_generic_food" in router["allowed_tools"]
    assert "unsupported_read_tool_name" not in str(router["block_reasons"])
    assert any(item["tool_name"] == "lookup_generic_food" for item in trace["read_tool_executions"])
    assert any(packet["packet_type"] == "GenericFoodDbPacket" for packet in trace["packetizer"]["outputs"])


@pytest.mark.asyncio
async def test_phase_b1_smoke_mixed_canonical_and_alias_only_executes_canonical_tool(tmp_path: Path) -> None:
    provider = MixedCanonicalAndAliasPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    trace = report["tool_loop_traces"][0]
    router = trace["runtime_tool_router"]
    assert router["requested_read_tools"] == ["lookup_generic_food", "search"]
    assert router["allowed_tools"] == ["lookup_generic_food"]
    assert router["blocked_tools"] == ["search"]
    assert [item["tool_name"] for item in trace["read_tool_executions"]] == ["lookup_generic_food"]
    assert [packet["packet_type"] for packet in trace["packetizer"]["outputs"]] == ["GenericFoodDbPacket"]
    assert "search" not in json.dumps(trace["packetizer"]["outputs"], ensure_ascii=False)
