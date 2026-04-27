from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.providers.builderspace_adapter import BuilderSpaceResponseError
import pytest

from scripts.run_wave1_phase_b_minimal_tool_loop_smoke import (
    _build_artifact_path,
    _resolve_targeted_smoke_cases,
    run_phase_b_minimal_tool_loop_smoke,
)


CASE_TEA_EGG = "\u6211\u5403\u4e86\u4e00\u9846\u8336\u8449\u86cb"
CASE_BUBBLE_TEA = "\u6211\u559d\u4e86\u4e00\u676f\u73cd\u73e0\u5976\u8336"
CASE_QUERY_BUBBLE_TEA = "\u73cd\u73e0\u5976\u8336\u5927\u6982\u591a\u5c11\u71b1\u91cf\uff1f"
CASE_BENTO = "\u6211\u5403\u4e86\u4e00\u500b\u4fbf\u7576"
CASE_LUWEI_UNKNOWN = "\u6211\u5403\u4e86\u6ef7\u5473"
CASE_LUWEI_LISTED = "\u6211\u5403\u4e86\u8c46\u5e72\u3001\u6d77\u5e36\u3001\u8ca2\u4e38\u7684\u6ef7\u5473"


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


class ProfileAwarePhaseBProvider(FakePhaseBProvider):
    def __init__(self) -> None:
        super().__init__()
        self.manager_model = "deepseek"
        self.manager_temperature = 0.0

    def readiness(self) -> dict[str, object]:
        return {
            "configured": True,
            "provider": "builderspace",
            "manager_model": self.manager_model,
        }

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        payload, trace = await super().complete_with_trace(**kwargs)
        trace = dict(trace)
        trace["model"] = self.manager_model
        trace["temperature"] = self.manager_temperature
        return payload, trace


class FailingPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise TimeoutError("simulated provider timeout")


class NonTimeoutFailingPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise ValueError("simulated non-timeout provider failure")


class Pass1MalformedPayloadPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        return ["call_tools", "lookup_generic_food"], self._trace(call_index=len(self.calls), kwargs=kwargs)


class Pass2MalformedPayloadPhaseBProvider(FakePhaseBProvider):
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
                    ],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return "final", self._trace(call_index=len(self.calls), kwargs=kwargs)


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


class AdapterParseAttributedErrorPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise BuilderSpaceResponseError(
            "BuilderSpace manager error at stage=intake_manager_round: RuntimeError: BuilderSpace did not return JSON.",
            trace={
                "stage": "intake_manager_round",
                "provider": "builderspace",
                "model": "deepseek",
                "base_url": "https://space.ai-builders.com/backend/v1",
                "timeout_seconds": 45,
                "failure_family": "non_json_model_output",
                "failing_component": "builderspace_adapter.extract_json_object",
                "raw_content_excerpt": "I am ready to help",
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "finish_reason": "length",
                "parse_contract_status": None,
                "parse_recovery_used": False,
                "parse_recovery_strategy": None,
                "parse_recovery_ambiguous": False,
                "structured_output_transport_attempted": True,
                "structured_output_transport_mode": "json_schema",
                "structured_output_transport_accepted": False,
                "structured_output_transport_fallback": "json_object",
                "fallback_reason": "provider_rejected_response_format",
                "structured_output_transport_constraint_snapshot": {
                    "phase_b1_manager_role": "pass_1_tool_request",
                    "phase_b1_pass1_mode": "natural_tool_selection_probe",
                    "phase_b1_case_family": "common_food_item",
                },
                "effective_response_format_type": "json_object",
                "transport_attempts": [],
                "parse_attempts": [
                    {
                        "attempt_index": 1,
                        "stage": "intake_manager_round",
                        "status": "failed",
                        "failure_family": "non_json_model_output",
                    }
                ],
            },
        )


class ToolCallDecisionBreachPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise BuilderSpaceResponseError(
            "BuilderSpace manager error at stage=intake_manager_round: RuntimeError: provider accepted tool transport but did not return tool calls.",
            trace={
                "stage": "intake_manager_round",
                "provider": "builderspace",
                "model": "deepseek",
                "base_url": "https://space.ai-builders.com/backend/v1",
                "timeout_seconds": 45,
                "failure_family": "tool_call_transport_contract_breach",
                "failing_component": "builderspace_adapter.extract_tool_call_decision",
                "structured_output_transport_attempted": False,
                "structured_output_transport_mode": None,
                "structured_output_transport_accepted": False,
                "structured_output_transport_fallback": None,
                "fallback_reason": None,
                "structured_output_transport_constraint_snapshot": None,
                "decision_transport_attempted": True,
                "decision_transport_mode": "tool_call_decision_transport",
                "decision_transport_accepted": True,
                "decision_transport_fallback": None,
                "decision_transport_fallback_reason": None,
                "decision_transport_contract_breach": True,
                "decision_transport_constraint_snapshot": {
                    "phase_b1_manager_role": "pass_1_tool_request",
                    "phase_b1_pass1_mode": "natural_tool_selection_probe",
                    "phase_b1_case_family": "common_commercial_meal",
                },
                "transport_attempts": [],
                "parse_attempts": [
                    {
                        "attempt_index": 1,
                        "stage": "intake_manager_round",
                        "status": "failed",
                        "failure_family": "tool_call_transport_contract_breach",
                    }
                ],
            },
        )


class TraceAsListPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], list[str]]:
        self.calls.append(dict(kwargs))
        return {"manager_action": "call_tools", "tool_calls": []}, ["bad-trace"]


class RequestPayloadAsStringPhaseBProvider(FakePhaseBProvider):
    def _trace(self, *, call_index: int, kwargs: dict[str, object]) -> dict[str, object]:
        trace = dict(super()._trace(call_index=call_index, kwargs=kwargs))
        trace["request_payload"] = "bad-request-payload"
        return trace


class TransportAttemptsAsStringPhaseBProvider(FakePhaseBProvider):
    def _trace(self, *, call_index: int, kwargs: dict[str, object]) -> dict[str, object]:
        trace = dict(super()._trace(call_index=call_index, kwargs=kwargs))
        trace["transport_attempts"] = "bad-transport-attempts"
        return trace


class ParseAttemptsAsStringPhaseBProvider(FakePhaseBProvider):
    def _trace(self, *, call_index: int, kwargs: dict[str, object]) -> dict[str, object]:
        trace = dict(super()._trace(call_index=call_index, kwargs=kwargs))
        trace["parse_attempts"] = "bad-parse-attempts"
        return trace


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


class ClarificationPass2CompletionPhaseBProvider(FakePhaseBProvider):
    def _trace(self, *, call_index: int, kwargs: dict[str, object]) -> dict[str, object]:
        trace = dict(super()._trace(call_index=call_index, kwargs=kwargs))
        trace["usage"] = {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
        return trace

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        message = str(user_payload["raw_user_input"])
        if round_index == 0 and message == CASE_LUWEI_UNKNOWN:
            return (
                {
                    "manager_action": "final",
                    "interaction_family": "food_logging",
                    "response_mode": "clarification",
                    "final_action": "request_clarification",
                    "operations": [],
                    "answer_contract": {"text": "Please list the specific items in the basket so I can estimate accurately."},
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        if round_index == 1 and message == CASE_LUWEI_UNKNOWN:
            return (
                {
                    "manager_action": "final",
                    "interaction_family": "food_logging",
                    "response_mode": "clarification",
                    "final_action": "request_clarification",
                    "operations": [],
                    "item_results": [
                        {
                            "food_name": "滷味",
                            "kcal_range": [300, 450],
                            "likely_kcal": 380,
                            "uncertainty": "high",
                            "evidence_used": ["should_not_be_promoted"],
                        }
                    ],
                    "answer_contract": {"text": "Please list the specific items in the basket so I can estimate accurately."},
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class MixedBranchSelfSelectedBasketPhaseBProvider(FakePhaseBProvider):
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
                        {"name": "search", "arguments": {"query": "滷味 熱量"}},
                        {"name": "extract", "arguments": {"urls": ["https://example.test/luwei"]}},
                    ],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class AdapterBranchViolationPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        raise BuilderSpaceResponseError(
            "BuilderSpace manager error at stage=intake_manager_round: ManagerPass1BranchContractError: conflicting fields",
            trace={
                "stage": "intake_manager_round",
                "provider": "builderspace",
                "model": "deepseek",
                "request_payload": kwargs.get("user_payload"),
                "transport_attempts": [],
                "parse_attempts": [],
                "request_failure_family": "manager_output_contract_violation",
                "failure_family": "manager_output_contract_violation",
                "failing_component": "manager_branch_contract.validate_manager_pass1_branch",
                "violation_family": "clarification_branch_conflicting_fields",
                "actual_shape": "call_tools.lookup_generic_food.response_mode=intake_result",
                "parsed_object": {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "滷味"}}],
                },
            },
        )


class LengthTruncatedJsonAttemptPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        raise BuilderSpaceResponseError(
            "BuilderSpace manager error at stage=intake_manager_round: _BuilderSpaceParseError: BuilderSpace did not return JSON.",
            trace={
                "stage": "intake_manager_round",
                "provider": "builderspace",
                "model": "deepseek",
                "base_url": "https://space.ai-builders.com/backend/v1",
                "timeout_seconds": 45,
                "failure_family": "non_json_model_output",
                "failing_component": "builderspace_adapter.extract_json_object",
                "raw_content_excerpt": "Let me finalize.\n```json\n{\n  \"manager_action\": \"final\",\n  \"intent\": \"estimate_calories\"",
                "finish_reason": "length",
                "parse_contract_status": None,
                "parse_recovery_used": False,
                "parse_recovery_strategy": None,
                "parse_recovery_ambiguous": False,
                "structured_output_transport_attempted": True,
                "structured_output_transport_mode": "json_schema",
                "structured_output_transport_accepted": False,
                "structured_output_transport_fallback": "json_object",
                "fallback_reason": "provider_rejected_response_format",
                "effective_response_format_type": "json_object",
                "transport_attempts": [],
                "parse_attempts": [
                    {
                        "attempt_index": 1,
                        "stage": "intake_manager_round",
                        "status": "failed",
                        "failure_family": "non_json_model_output",
                    }
                ],
            },
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


class GenericFamilySearchAliasPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        message = str(user_payload["raw_user_input"])
        if round_index == 0:
            if "豆干" in message and "海帶" in message and "貢丸" in message:
                tool_calls = [
                    {"name": "search", "arguments": {"query": "豆干 熱量"}},
                    {"name": "search", "arguments": {"query": "海帶 熱量"}},
                    {"name": "search", "arguments": {"query": "貢丸 熱量"}},
                ]
            elif "珍珠奶茶" in message:
                tool_calls = [{"name": "search", "arguments": {"query": "珍珠奶茶 熱量"}}]
            elif "便當" in message:
                tool_calls = [{"name": "search", "arguments": {"query": "便當 熱量"}}]
            else:
                tool_calls = [{"name": "search", "arguments": {"query": "茶葉蛋 熱量"}}]
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": tool_calls,
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class EchoInputLookupPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        message = str(user_payload["raw_user_input"])
        if round_index == 0:
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": message}}],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class AnswerContractBridgePhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        message = str(user_payload["raw_user_input"])
        if round_index == 0 and message == CASE_LUWEI_LISTED:
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": [
                        {"name": "lookup_generic_food", "arguments": {"food_name": "豆干"}},
                        {"name": "lookup_generic_food", "arguments": {"food_name": "海帶"}},
                        {"name": "lookup_generic_food", "arguments": {"food_name": "貢丸"}},
                    ],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        if round_index == 1 and message == CASE_LUWEI_LISTED:
            return (
                {
                    "manager_action": "final",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {
                        "items": [
                            {
                                "item_name": "豆干 (滷味)",
                                "item_results": {"kcal_range": [60, 100], "likely_kcal": 80, "uncertainty": "medium"},
                            },
                            {
                                "item_name": "海帶 (滷味)",
                                "item_results": {"kcal_range": [15, 45], "likely_kcal": 30, "uncertainty": "medium"},
                            },
                            {
                                "item_name": "貢丸 (滷味)",
                                "item_results": {"kcal_range": [60, 90], "likely_kcal": 75, "uncertainty": "low"},
                            },
                        ]
                    },
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class MealRootAnswerContractBridgePhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        message = str(user_payload["raw_user_input"])
        if round_index == 0 and message == CASE_BENTO:
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "便當"}}],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        if round_index == 1 and message == CASE_BENTO:
            return (
                {
                    "manager_action": "final",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "intent": "estimate_calories",
                    "workflow_effect": "complete",
                    "target_attachment": "generic_taiwanese_bento",
                    "operations": [],
                    "answer_contract": {
                        "item_results": [{"item_name": "便當", "item_quantity": 1, "item_unit": "個"}],
                        "kcal_range": [550, 960],
                        "likely_kcal": 750,
                        "uncertainty": "medium",
                        "evidence_used": ["generic_food_db:便當"],
                    },
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class DrinkRootAnswerContractOnlyPhaseBProvider(FakePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        round_index = user_payload["round_index"]
        message = str(user_payload["raw_user_input"])
        if round_index == 0 and message == CASE_QUERY_BUBBLE_TEA:
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "nutrition_info_query",
                    "response_mode": "info_answer",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": [{"name": "lookup_generic_food", "arguments": {"food_name": "珍珠奶茶"}}],
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        if round_index == 1 and message == CASE_QUERY_BUBBLE_TEA:
            return (
                {
                    "manager_action": "final",
                    "interaction_family": "nutrition_info_query",
                    "response_mode": "info_answer",
                    "intent": "query_food_calories",
                    "workflow_effect": "complete",
                    "target_attachment": "food_item",
                    "operations": [],
                    "answer_contract": {
                        "item_results": [{"item_name": "珍珠奶茶", "item_quantity": 1, "item_unit": "杯"}],
                        "kcal_range": [350, 450],
                        "likely_kcal": 400,
                        "uncertainty": "medium",
                        "evidence_used": ["generic_food_db:珍珠奶茶"],
                    },
                },
                self._trace(call_index=len(self.calls), kwargs=kwargs),
            )
        return await super().complete_with_trace(**kwargs)


class TopLevelItemResultsWinsPhaseBProvider(AnswerContractBridgePhaseBProvider):
    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        payload, trace = await super().complete_with_trace(**kwargs)
        user_payload = kwargs["user_payload"]
        if user_payload["round_index"] == 1 and str(user_payload["raw_user_input"]) == CASE_LUWEI_LISTED:
            payload = dict(payload)
            payload["item_results"] = [
                {
                    "food_name": "豆干",
                    "kcal_range": [55, 95],
                    "likely_kcal": 75,
                    "uncertainty": "low",
                    "evidence_used": ["top_level"],
                }
            ]
        return payload, trace


class TargetedTimeoutThenSuccessPhaseBProvider(FakePhaseBProvider):
    def __init__(self) -> None:
        super().__init__()
        self.fail_counts: dict[str, int] = {}

    async def complete_with_trace(self, **kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        self.calls.append(dict(kwargs))
        user_payload = kwargs["user_payload"]
        message = str(user_payload["raw_user_input"])
        round_index = user_payload["round_index"]
        if message == CASE_LUWEI_UNKNOWN:
            self.fail_counts[message] = self.fail_counts.get(message, 0) + 1
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
        if round_index == 0 and message == CASE_LUWEI_LISTED:
            return (
                {
                    "manager_action": "call_tools",
                    "interaction_family": "food_logging",
                    "response_mode": "intake_result",
                    "operations": [],
                    "answer_contract": {},
                    "tool_calls": [
                        {"name": "lookup_generic_food", "arguments": {"food_name": "豆干"}},
                        {"name": "lookup_generic_food", "arguments": {"food_name": "海帶"}},
                        {"name": "lookup_generic_food", "arguments": {"food_name": "貢丸"}},
                    ],
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
async def test_phase_b1_b1_004_natural_probe_runs_real_pass2_trace_without_semantic_reclassification(tmp_path: Path) -> None:
    provider = ClarificationPass2CompletionPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-004"],
    )

    trace = report["tool_loop_traces"][0]
    pass1 = trace["manager_pass_1"]
    pass2 = trace["manager_pass_2"]

    assert len(provider.calls) == 2
    assert provider.calls[0]["user_payload"]["round_index"] == 0
    assert provider.calls[1]["user_payload"]["round_index"] == 1
    assert provider.calls[1]["user_payload"]["tool_results"] == [
        {
            "tool_name": "packetize_food_evidence",
            "truth_level": "hint",
            "packetizer_outputs": trace["packetizer"]["outputs"],
        }
    ]

    assert pass1["decision_payload"]["manager_action"] == "final"
    assert pass1["decision_payload"]["final_action"] == "request_clarification"
    assert pass1["requested_read_tools"] == []

    assert pass2["started_at_utc"] is not None
    assert pass2["ended_at_utc"] is not None
    assert pass2["latency_ms"] is not None
    assert pass2["usage"] == {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
    assert pass2["provider_params"]["provider"] == "builderspace"
    assert pass2["provider_params"]["model"] == "deepseek"
    assert pass2["provider_params"]["request_id"] == "fake_req_2"
    assert pass2["provider_params"]["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass2["provider_params"]["provider_profile_route_mode"] == "default_build_loop"

    assert pass2["decision_payload"]["item_results"]
    assert pass2["item_results"] == []
    assert pass2["item_results_source"] == "none"
    assert pass2["item_results_bridge_shape"] is None
    assert pass2["item_results_bridge_parent_fallback_fields"] == []
    assert trace["runner_derived_item_results"] is False
    assert trace["mutation"] == {
        "mutation_attempted": False,
        "reason": "no_mutation_intent",
        "mutation_result": None,
    }
    assert trace["renderer"]["input"]["item_results"] == []


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
async def test_phase_b1_runtime_smoke_preserves_adapter_parse_attribution_in_provider_runtime(tmp_path: Path) -> None:
    provider = AdapterParseAttributedErrorPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    runtime = report["provider_runtime"]
    assert runtime["reason"] == "provider_runtime_error"
    assert runtime["failure_family"] == "non_json_model_output"
    assert runtime["failing_component"] == "builderspace_adapter.extract_json_object"
    assert runtime["raw_content_excerpt"] == "I am ready to help"
    assert runtime["status"] == "incomplete"
    assert runtime["incomplete_details"] == {"reason": "max_output_tokens"}
    assert runtime["finish_reason"] == "length"
    assert runtime["parse_recovery_used"] is False
    assert runtime["parse_recovery_ambiguous"] is False
    assert runtime["structured_output_transport_attempted"] is True
    assert runtime["structured_output_transport_mode"] == "json_schema"
    assert runtime["structured_output_transport_accepted"] is False
    assert runtime["structured_output_transport_fallback"] == "json_object"
    assert runtime["fallback_reason"] == "provider_rejected_response_format"
    assert runtime["structured_output_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_food_item"
    assert runtime["effective_response_format_type"] == "json_object"


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_marks_length_truncated_json_attempts_separately(tmp_path: Path) -> None:
    provider = LengthTruncatedJsonAttemptPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    runtime = report["provider_runtime"]
    assert runtime["reason"] == "provider_runtime_error"
    assert runtime["failure_family"] == "non_json_model_output"
    assert runtime["finish_reason"] == "length"
    assert runtime["length_truncated_before_json_completion"] is True
    assert runtime["truncation_failure_family"] == "incomplete_json_due_to_length"


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_preserves_decision_transport_breach_attribution(tmp_path: Path) -> None:
    provider = ToolCallDecisionBreachPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一個便當"],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    runtime = report["provider_runtime"]
    assert runtime["reason"] == "provider_runtime_error"
    assert runtime["failure_family"] == "tool_call_transport_contract_breach"
    assert runtime["failing_component"] == "builderspace_adapter.extract_tool_call_decision"
    assert runtime["decision_transport_attempted"] is True
    assert runtime["decision_transport_mode"] == "tool_call_decision_transport"
    assert runtime["decision_transport_accepted"] is True
    assert runtime["decision_transport_contract_breach"] is True
    assert runtime["decision_transport_fallback"] is None
    assert runtime["decision_transport_fallback_reason"] is None
    assert runtime["decision_transport_constraint_snapshot"]["phase_b1_case_family"] == "common_commercial_meal"


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
@pytest.mark.parametrize(
    ("provider_factory", "trace_field", "observed_type"),
    (
        (TraceAsListPhaseBProvider, "trace", "array"),
        (RequestPayloadAsStringPhaseBProvider, "request_payload", "string"),
        (TransportAttemptsAsStringPhaseBProvider, "transport_attempts", "string"),
        (ParseAttemptsAsStringPhaseBProvider, "parse_attempts", "string"),
    ),
)
async def test_phase_b1_runtime_smoke_provider_trace_shape_error_emits_provider_trace_blocker(
    tmp_path: Path,
    provider_factory: type[FakePhaseBProvider],
    trace_field: str,
    observed_type: str,
) -> None:
    provider = provider_factory()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    assert report.get("provider_runtime") is None
    blocker = report["provider_trace_blocker"]
    assert blocker["blocker"] is True
    assert blocker["reason"] == "provider_trace_shape_error"
    assert blocker["trace_field"] == trace_field
    assert blocker["observed_type"] == observed_type
    assert blocker["failing_component"] == "normalize_provider_trace"
    assert blocker["completed_trace_count"] == 0
    assert blocker["expected_case_count"] == 1
    assert isinstance(blocker["value_excerpt"], str)
    assert isinstance(blocker["value_truncated"], bool)
    assert report["tool_loop_traces"] == []


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_pass1_malformed_payload_is_runtime_blocker_not_provider_error(tmp_path: Path) -> None:
    provider = Pass1MalformedPayloadPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    assert report.get("provider_runtime") is None
    blocker = report["runtime_blocker"]
    assert blocker["blocker"] is True
    assert blocker["reason"] == "manager_payload_shape_error"
    assert blocker["stage"] == "pass_1_tool_request"
    assert blocker["round_index"] == 0
    assert blocker["decision_payload_type"] == "list"
    assert blocker["completed_trace_count"] == 0
    assert blocker["expected_case_count"] == 1
    assert report["tool_loop_traces"] == []


@pytest.mark.asyncio
async def test_phase_b1_runtime_smoke_pass2_malformed_payload_keeps_completed_trace_and_sets_runtime_blocker(tmp_path: Path) -> None:
    provider = Pass2MalformedPayloadPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=["我吃了一顆茶葉蛋"],
        output_dir=tmp_path,
        write_latest=False,
    )

    assert report.get("provider_runtime") is None
    blocker = report["runtime_blocker"]
    assert blocker["blocker"] is True
    assert blocker["reason"] == "manager_payload_shape_error"
    assert blocker["stage"] == "pass_2_synthesis"
    assert blocker["round_index"] == 1
    assert blocker["decision_payload_type"] == "str"
    assert blocker["completed_trace_count"] == 1
    assert blocker["expected_case_count"] == 1
    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_1"]["payload_shape_valid"] is True
    assert trace["manager_pass_2"]["payload_shape_valid"] is False
    assert trace["manager_pass_2"]["decision_payload_type"] == "str"


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
    assert "common food" in pass1_prompt.lower()
    assert "lookup_generic_food" in pass1_prompt
    assert "rather than a generic search alias or a web-evidence-only substitute" in pass1_prompt
    assert "For composition-unknown self-selected baskets" in pass1_prompt
    assert "clarify-style final decision" in pass1_prompt
    assert "missing item composition" in pass1_prompt
    assert "no fake-final delegation" in pass1_prompt
    assert "final_action='request_clarification'" in pass1_prompt
    assert "must not log_food or log_consumption" in pass1_prompt
    assert "For common_food_item, common_commercial_drink, and common_commercial_meal Pass 1 branches" in pass1_prompt
    assert "Output exactly one JSON object." in pass1_prompt
    assert "The first non-whitespace character of your response must be '{'." in pass1_prompt
    assert "Do not write prose preamble" in pass1_prompt
    assert "Do not use fenced code blocks" in pass1_prompt
    assert "Do not emit duplicated JSON objects" in pass1_prompt
    assert "Do not write final-synthesis narration" in pass1_prompt
    assert "Do not explain tool availability or tool failure in the output." in pass1_prompt
    assert "Do not echo policy or guidance text in the output." in pass1_prompt
    assert "This is still Pass 1, not Pass 2." in pass1_prompt
    assert "Do not produce item_results, likely_kcal, kcal_range, or final calorie claims." in pass1_prompt
    assert "Do not produce final logging, commit, or record_calories posture." in pass1_prompt
    assert "Do not summarize calories or evidence in prose." in pass1_prompt
    assert "must not return a final logging or commit decision before lookup_generic_food" in pass1_prompt
    assert "do not request any tools at all in Pass 1" in pass1_prompt
    assert "JSON example for common food logging" in pass1_prompt
    assert "JSON example for composition-unknown basket boundary" in pass1_prompt
    assert "lookup_generic_food" in pass1_prompt
    assert "Do not use unsupported aliases such as search, extract, web_search, or food_lookup" in pass1_prompt
    assert "If you choose a tool path, the tool name must be the canonical runtime name exactly." in pass1_prompt
    assert "Unsupported aliases are invalid tool choices and will be rejected by the runtime." in pass1_prompt
    assert "MUST return manager_action='call_tools'" not in pass1_prompt
    assert "Do not choose manager_action='final'" not in pass1_prompt
    assert "every food_logging or nutrition_info_query case must call at least one read tool" not in pass1_prompt
    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_1_common_food_item_anti_final_v1"
    assert pass1_provider_trace["phase_b1_task_payload_id"] == "phase_b1_pass_1_common_food_item_anti_final_v1"
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
async def test_phase_b1_natural_probe_b1_004_injects_case_family_constraint(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-004"],
    )

    constraints = provider.calls[0]["user_payload"]["constraints"]
    assert constraints["phase_b1_manager_role"] == "pass_1_tool_request"
    assert constraints["phase_b1_pass1_mode"] == "natural_tool_selection_probe"
    assert constraints["phase_b1_case_family"] == "composition_unknown_self_selected_basket"


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_b1_005_injects_case_family_constraint(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-005"],
    )

    constraints = provider.calls[0]["user_payload"]["constraints"]
    assert constraints["phase_b1_manager_role"] == "pass_1_tool_request"
    assert constraints["phase_b1_pass1_mode"] == "natural_tool_selection_probe"
    assert constraints["phase_b1_case_family"] == "listed_ingredient_basket"


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_b1_005_pass2_uses_compact_json_first_prompt_and_case_family(tmp_path: Path) -> None:
    provider = AnswerContractBridgePhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-005"],
    )

    pass2_prompt = str(provider.calls[1]["system_prompt"])
    constraints = provider.calls[1]["user_payload"]["constraints"]

    assert "listed-ingredient Pass 2 compact synthesis mode" in pass2_prompt
    assert "Output exactly one compact JSON object." in pass2_prompt
    assert "The first non-whitespace character of your response must be '{'." in pass2_prompt
    assert "Do not write narrative preamble" in pass2_prompt
    assert "Do not summarize packet evidence in prose before JSON." in pass2_prompt
    assert "include the active manager wrapper fields required by the current schema" in pass2_prompt
    assert "Compact JSON example:" in pass2_prompt
    assert "\"item_results\"" in pass2_prompt
    assert "\"intent\":\"estimate_calories\"" in pass2_prompt
    assert "\"workflow_effect\":\"complete\"" in pass2_prompt
    assert "\"evidence_posture\":\"packetized_generic_db\"" in pass2_prompt
    assert constraints["phase_b1_manager_role"] == "pass_2_synthesis"
    assert constraints["phase_b1_case_family"] == "listed_ingredient_basket"


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_b1_001_pass2_uses_compact_json_first_prompt(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-001"],
    )

    pass2_prompt = str(provider.calls[1]["system_prompt"])
    constraints = provider.calls[1]["user_payload"]["constraints"]

    assert "common-food-item Pass 2 compact synthesis mode" in pass2_prompt
    assert "Output exactly one compact JSON object." in pass2_prompt
    assert "The first non-whitespace character of your response must be '{'." in pass2_prompt
    assert "Do not write evidence essay" in pass2_prompt
    assert "Do not replay the runner payload envelope" in pass2_prompt
    assert "Prefer direct top-level item_results" in pass2_prompt
    assert "\"response_mode\":\"intake_result\"" in pass2_prompt
    assert "\"operations\":[]" in pass2_prompt
    assert "\"answer_contract\":{}" in pass2_prompt
    assert constraints["phase_b1_manager_role"] == "pass_2_synthesis"
    assert constraints["phase_b1_case_family"] == "common_food_item"
    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_2_common_food_item_compact_json_first_v1"


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_b1_002_pass2_preserves_required_wrapper_fields(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-002"],
    )

    pass2_prompt = str(provider.calls[1]["system_prompt"])
    constraints = provider.calls[1]["user_payload"]["constraints"]

    assert "common-commercial-drink Pass 2 compact synthesis mode" in pass2_prompt
    assert "Output exactly one compact JSON object." in pass2_prompt
    assert "You must retain response_mode." in pass2_prompt
    assert "You must retain operations=[]" in pass2_prompt
    assert "You must retain answer_contract." in pass2_prompt
    assert "Do not emit final synthesis while dropping required wrapper fields." in pass2_prompt
    assert "\"response_mode\":\"info_answer\"" in pass2_prompt
    assert "\"operations\":[]" in pass2_prompt
    assert "\"answer_contract\":{" in pass2_prompt
    assert constraints["phase_b1_manager_role"] == "pass_2_synthesis"
    assert constraints["phase_b1_case_family"] == "common_commercial_drink"
    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_2_common_commercial_drink_compact_json_first_v1"


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_b1_003_pass2_preserves_required_wrapper_fields(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-003"],
    )

    pass2_prompt = str(provider.calls[1]["system_prompt"])
    constraints = provider.calls[1]["user_payload"]["constraints"]

    assert "common-commercial-meal Pass 2 compact synthesis mode" in pass2_prompt
    assert "Output exactly one compact JSON object." in pass2_prompt
    assert "You must retain response_mode." in pass2_prompt
    assert "You must retain operations=[]" in pass2_prompt
    assert "You must retain answer_contract." in pass2_prompt
    assert "Do not emit final synthesis while dropping required wrapper fields." in pass2_prompt
    assert "\"response_mode\":\"intake_result\"" in pass2_prompt
    assert "\"operations\":[]" in pass2_prompt
    assert "\"answer_contract\":{" in pass2_prompt
    assert constraints["phase_b1_manager_role"] == "pass_2_synthesis"
    assert constraints["phase_b1_case_family"] == "common_commercial_meal"
    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_2_common_commercial_meal_compact_json_first_v1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_id", "expected_family"),
    (
        ("B1-001", "common_food_item"),
        ("B1-002", "common_commercial_drink"),
        ("B1-003", "common_commercial_meal"),
    ),
)
async def test_phase_b1_natural_probe_generic_cases_inject_case_family_constraint(
    tmp_path: Path,
    case_id: str,
    expected_family: str,
) -> None:
    provider = FinalOnlyPhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=[case_id],
    )

    constraints = provider.calls[0]["user_payload"]["constraints"]
    assert constraints["phase_b1_manager_role"] == "pass_1_tool_request"
    assert constraints["phase_b1_pass1_mode"] == "natural_tool_selection_probe"
    assert constraints["phase_b1_case_family"] == expected_family


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
async def test_phase_b1_natural_probe_generic_family_guidance_covers_drink_meal_and_listed_ingredients(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_BUBBLE_TEA],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    pass1_prompt = str(provider.calls[0]["system_prompt"])
    assert "common commercial drinks" in pass1_prompt
    assert "common commercial meals" in pass1_prompt
    assert "listed ingredients" in pass1_prompt
    assert "range and uncertainty" in pass1_prompt.lower()
    assert "item-level lookup_generic_food" in pass1_prompt
    assert "Mutation intent changes evidence threshold" in pass1_prompt
    assert "do not claim that tools are unavailable" in pass1_prompt
    assert "Do not treat lookup_generic_food as unavailable when it is listed among the available runtime tool names" in pass1_prompt
    assert "do not answer from model memory first" in pass1_prompt
    assert "do not ask the user to provide nutrition details instead of requesting lookup_generic_food" in pass1_prompt
    assert "logged common drinks and logged common meals still begin with lookup_generic_food" in pass1_prompt
    assert "one lookup_generic_food call per listed ingredient" in pass1_prompt
    assert "High-variance generic items still belong to the generic evidence path" in pass1_prompt
    assert "uncertainty comes from serving size, customization, recipe, sugar level, brand, or portion variation" in pass1_prompt
    assert "it does not come from a missing item list" in pass1_prompt
    assert "Do not collapse a high-variance generic item into a clarify-only boundary" in pass1_prompt
    assert "generic lookup would collapse unknown composition into fake evidence" in pass1_prompt
    assert "Do not treat a composition-unknown self-selected basket as a high-variance generic item." in pass1_prompt
    assert "must not request lookup_generic_food or retrieve_web_food_evidence" in pass1_prompt
    assert "If only the basket label is present, do not request lookup_generic_food for the basket label itself." in pass1_prompt
    assert "If listed ingredients are already present, do not ask a clarification question instead of item-level lookup." in pass1_prompt
    assert 'Do not collapse listed ingredients into lookup_generic_food("basket_name").' in pass1_prompt
    assert "A high-variance generic item still has known item identity and known generic category." in pass1_prompt
    assert "Do not start synthesis, summarize packet evidence, calculate calories, or write a final answer in Pass 1." in pass1_prompt
    assert "For listed ingredients already present, return only item-level tool intent in JSON rather than narrative evidence synthesis." in pass1_prompt
    assert "For composition-unknown self-selected baskets, keep the clarification text limited to asking for the missing item list." in pass1_prompt
    assert "For listed-ingredient baskets, do not use final_action='log_food' or final_action='log_consumption' in Pass 1." in pass1_prompt
    assert "For composition-unknown self-selected baskets, do not use response_mode='intake_result', workflow_effect='pass_to_next_round', or uncertainty_posture='high_variance_generic_item'." in pass1_prompt
    assert "For composition-unknown self-selected baskets without listed ingredients, manager_action must not be 'call_tools' in Pass 1." in pass1_prompt
    assert "For listed-ingredient baskets, manager_action must not be 'final' in Pass 1." in pass1_prompt
    assert "use the clarification-only JSON shape shown below" in pass1_prompt
    assert "{\"manager_action\":\"final\",\"interaction_family\":\"food_logging\",\"response_mode\":\"clarification\",\"final_action\":\"request_clarification\",\"operations\":[],\"answer_contract\":{\"text\":\"Please list the specific items in the basket so I can estimate accurately.\"}}" in pass1_prompt
    assert "Do not use intake/logging/high-variance fields in this clarification-only branch." in pass1_prompt
    assert "Compact JSON example for common_food_item:" in pass1_prompt
    assert "\"food_name\":\"茶葉蛋\"" in pass1_prompt
    assert "Compact JSON example for common_commercial_drink:" in pass1_prompt
    assert "\"food_name\":\"珍珠奶茶\"" in pass1_prompt
    assert "Compact JSON example for common_commercial_meal:" in pass1_prompt
    assert "\"food_name\":\"便當\"" in pass1_prompt


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_common_food_item_prompt_adds_anti_final_synthesis_contrast(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_TEA_EGG],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    pass1_prompt = str(provider.calls[0]["system_prompt"])
    constraints = provider.calls[0]["user_payload"]["constraints"]

    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_1_common_food_item_anti_final_v1"
    assert "Do not say \"I now have sufficient evidence\"" in pass1_prompt
    assert "Do not say \"Let me synthesize the final answer\"" in pass1_prompt
    assert "Bad pattern for common_food_item Pass 1" in pass1_prompt
    assert "Good pattern for common_food_item Pass 1" in pass1_prompt
    assert "\"manager_action\":\"call_tools\"" in pass1_prompt


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_common_commercial_meal_prompt_adds_anti_final_synthesis_contrast(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_BENTO],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    pass1_prompt = str(provider.calls[0]["system_prompt"])
    constraints = provider.calls[0]["user_payload"]["constraints"]

    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_1_common_commercial_meal_anti_final_v1"
    assert "Do not say \"I now have sufficient evidence\"" in pass1_prompt
    assert "Do not say \"Let me synthesize the final answer\"" in pass1_prompt
    assert "Bad pattern for common_commercial_meal Pass 1" in pass1_prompt
    assert "Good pattern for common_commercial_meal Pass 1" in pass1_prompt
    assert "\"food_name\":\"便當\"" in pass1_prompt


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_common_commercial_drink_keeps_generic_payload_id(tmp_path: Path) -> None:
    provider = FinalOnlyPhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_BUBBLE_TEA],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    constraints = provider.calls[0]["user_payload"]["constraints"]
    assert constraints["phase_b1_case_family"] == "common_commercial_drink"
    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_1_common_commercial_drink_anti_final_v1"


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_b1_006_pass1_uses_common_commercial_drink_family_and_payload_id(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-006"],
    )

    pass1_prompt = str(provider.calls[0]["system_prompt"])
    constraints = provider.calls[0]["user_payload"]["constraints"]

    assert constraints["phase_b1_manager_role"] == "pass_1_tool_request"
    assert constraints["phase_b1_pass1_mode"] == "natural_tool_selection_probe"
    assert constraints["phase_b1_case_family"] == "common_commercial_drink"
    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_1_common_commercial_drink_anti_final_v1"
    assert "common_commercial_drink anti-final-synthesis discipline." in pass1_prompt
    assert "For no-mutation calorie queries about a known common commercial drink" in pass1_prompt
    assert "\"interaction_family\":\"nutrition_info_query\"" in pass1_prompt
    assert "\"response_mode\":\"info_answer\"" in pass1_prompt


@pytest.mark.asyncio
async def test_phase_b1_natural_probe_b1_006_pass2_uses_common_commercial_drink_payload_and_case_family(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-006"],
    )

    pass2_prompt = str(provider.calls[1]["system_prompt"])
    constraints = provider.calls[1]["user_payload"]["constraints"]

    assert constraints["phase_b1_manager_role"] == "pass_2_synthesis"
    assert constraints["phase_b1_case_family"] == "common_commercial_drink"
    assert constraints["phase_b1_task_payload_id"] == "phase_b1_pass_2_common_commercial_drink_compact_json_first_v1"
    assert "common-commercial-drink Pass 2 compact synthesis mode" in pass2_prompt
    assert "\"response_mode\":\"info_answer\"" in pass2_prompt


@pytest.mark.asyncio
async def test_phase_b1_smoke_generic_family_search_aliases_are_blocked_without_normalization(tmp_path: Path) -> None:
    provider = GenericFamilySearchAliasPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_BUBBLE_TEA, CASE_BENTO, CASE_LUWEI_LISTED],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    traces = report["tool_loop_traces"]
    assert [trace["runtime_tool_router"]["requested_read_tools"] for trace in traces] == [
        ["search"],
        ["search"],
        ["search", "search", "search"],
    ]
    assert all(trace["runtime_tool_router"]["allowed_tools"] == [] for trace in traces)


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


def test_resolve_targeted_smoke_cases_dedups_and_preserves_order() -> None:
    resolved = _resolve_targeted_smoke_cases("B1-004,B1-005,B1-004")

    assert resolved["case_set"] == "targeted"
    assert resolved["requested_case_ids"] == ["B1-004", "B1-005"]
    assert resolved["smoke_cases"] == [CASE_LUWEI_UNKNOWN, CASE_LUWEI_LISTED]


def test_resolve_targeted_smoke_cases_rejects_invalid_case_ids() -> None:
    with pytest.raises(ValueError) as excinfo:
        _resolve_targeted_smoke_cases("B1-004,B1-999")

    text = str(excinfo.value)
    assert "B1-999" in text
    assert "B1-001" in text
    assert "B1-006" in text


def test_build_artifact_path_is_unique_for_same_second_targeted_runs(tmp_path: Path) -> None:
    requested_case_ids = ["B1-004", "B1-005"]

    path_one = _build_artifact_path(
        output_dir=tmp_path,
        pass1_mode="natural_tool_selection_probe",
        case_set="targeted",
        requested_case_ids=requested_case_ids,
    )
    path_two = _build_artifact_path(
        output_dir=tmp_path,
        pass1_mode="natural_tool_selection_probe",
        case_set="targeted",
        requested_case_ids=requested_case_ids,
    )

    assert path_one != path_two
    assert "natural-probe" in path_one.name
    assert "targeted" in path_one.name
    assert "B1-004-B1-005" in path_one.name


@pytest.mark.asyncio
async def test_phase_b1_smoke_targeted_cases_only_runs_requested_cases(tmp_path: Path) -> None:
    provider = EchoInputLookupPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-004", "B1-005"],
    )

    assert report["case_set"] == "targeted"
    assert report["requested_case_ids"] == ["B1-004", "B1-005"]
    assert report["core_smoke_cases_run"] == [CASE_LUWEI_UNKNOWN, CASE_LUWEI_LISTED]
    assert report["completed_case_count"] == 2
    assert report["expected_full_case_count"] == 6
    assert report["full_readiness_claimed"] is False
    assert report["runtime_latency"]["readiness_claim_scope"] == "diagnostic"
    assert [trace["input_message"] for trace in report["tool_loop_traces"]] == [CASE_LUWEI_UNKNOWN, CASE_LUWEI_LISTED]
    assert [str(call["user_payload"]["raw_user_input"]) for call in provider.calls if call["user_payload"]["round_index"] == 0] == [
        CASE_LUWEI_UNKNOWN,
        CASE_LUWEI_LISTED,
    ]


@pytest.mark.asyncio
async def test_phase_b1_smoke_targeted_case_timeout_does_not_hide_other_case_results(tmp_path: Path) -> None:
    provider = TargetedTimeoutThenSuccessPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-004", "B1-005"],
        _retry_backoff_seconds=0.0,
    )

    assert report["case_set"] == "targeted"
    assert report["requested_case_ids"] == ["B1-004", "B1-005"]
    assert report["completed_case_count"] == 1
    assert len(report["case_results"]) == 2
    timeout_case = report["case_results"][0]
    success_case = report["case_results"][1]
    assert timeout_case["case_id"] == "B1-004"
    assert timeout_case["case_execution_status"] == "provider_timeout"
    assert timeout_case["attempt_count"] == 2
    assert timeout_case["trace_present"] is False
    assert timeout_case["provider_runtime"]["reason"] == "provider_timeout"
    assert timeout_case["provider_runtime"]["timeout_layer"] == "adapter_http_timeout"
    assert success_case["case_id"] == "B1-005"
    assert success_case["case_execution_status"] == "completed"
    assert success_case["trace_present"] is True
    assert [trace["case_id"] for trace in report["tool_loop_traces"]] == ["B1-005"]


@pytest.mark.asyncio
async def test_phase_b1_smoke_targeted_non_retryable_runtime_blocker_is_not_retried(tmp_path: Path) -> None:
    provider = Pass1MalformedPayloadPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        requested_case_ids=["B1-004"],
        _retry_backoff_seconds=0.0,
    )

    assert len(report["case_results"]) == 1
    case_result = report["case_results"][0]
    assert case_result["case_execution_status"] == "runtime_blocker"
    assert case_result["attempt_count"] == 1
    assert case_result["trace_present"] is False


@pytest.mark.asyncio
async def test_phase_b1_smoke_targeted_b1_004_mixed_branch_contract_violation_keeps_partial_trace(tmp_path: Path) -> None:
    provider = MixedBranchSelfSelectedBasketPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-004"],
        _retry_backoff_seconds=0.0,
    )

    assert len(report["case_results"]) == 1
    case_result = report["case_results"][0]
    assert case_result["case_execution_status"] == "runtime_blocker"
    assert case_result["attempt_count"] == 1
    assert case_result["trace_present"] is True
    assert case_result["runtime_blocker"]["reason"] == "manager_output_contract_violation"
    assert case_result["runtime_blocker"]["stage"] == "pass_1_tool_request"
    assert case_result["runtime_blocker"]["violation_family"] == "clarification_branch_conflicting_fields"
    assert case_result["runtime_blocker"]["actual_shape"] == "call_tools.search.extract.response_mode=intake_result"
    assert [trace["case_id"] for trace in report["tool_loop_traces"]] == ["B1-004"]
    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_1"]["decision_payload"]["manager_action"] == "call_tools"
    assert trace["manager_pass_1"]["requested_read_tools"] == ["search", "extract"]
    assert trace["runtime_tool_router"]["requested_read_tools"] == ["search", "extract"]
    assert "lookup_generic_food" in trace["runtime_tool_router"]["blocked_tools"]
    assert "retrieve_web_food_evidence" in trace["runtime_tool_router"]["blocked_tools"]


@pytest.mark.asyncio
async def test_phase_b1_smoke_targeted_provider_side_branch_violation_becomes_runtime_blocker(tmp_path: Path) -> None:
    provider = AdapterBranchViolationPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-004"],
        _retry_backoff_seconds=0.0,
    )

    case_result = report["case_results"][0]
    assert case_result["case_execution_status"] == "runtime_blocker"
    assert case_result["trace_present"] is True
    assert case_result["runtime_blocker"]["reason"] == "manager_output_contract_violation"
    assert case_result["runtime_blocker"]["violation_family"] == "clarification_branch_conflicting_fields"
    assert report.get("provider_runtime") is None
    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_1"]["decision_payload"]["manager_action"] == "call_tools"
    assert trace["manager_pass_1"]["requested_read_tools"] == ["lookup_generic_food"]


@pytest.mark.asyncio
async def test_phase_b1_b1_005_answer_contract_bridge_populates_canonical_item_results(tmp_path: Path) -> None:
    provider = AnswerContractBridgePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-005"],
    )

    trace = report["tool_loop_traces"][0]
    item_results = trace["manager_pass_2"]["item_results"]
    assert trace["manager_pass_2"]["item_results_source"] == "answer_contract_bridge"
    assert trace["runner_derived_item_results"] is False
    assert [item["food_name"] for item in item_results] == ["豆干", "海帶", "貢丸"]
    assert item_results[0]["evidence_used"] == ["B1-005_lookup_generic_food_75f53b5e47261724"]
    assert item_results[1]["evidence_used"] == ["B1-005_lookup_generic_food_0bbbc312b28c6fa5"]
    assert item_results[2]["evidence_used"] == ["B1-005_lookup_generic_food_7c6553e85a47ba2c"]


@pytest.mark.asyncio
async def test_phase_b1_b1_003_meal_root_answer_contract_bridge_populates_canonical_item_results(tmp_path: Path) -> None:
    provider = MealRootAnswerContractBridgePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-003"],
    )

    trace = report["tool_loop_traces"][0]
    item_results = trace["manager_pass_2"]["item_results"]
    assert trace["manager_pass_2"]["item_results_source"] == "answer_contract_bridge"
    assert trace["runner_derived_item_results"] is False
    assert trace["manager_pass_2"]["item_results_bridge_shape"] == "answer_contract.item_results"
    assert set(trace["manager_pass_2"]["item_results_bridge_parent_fallback_fields"]) == {
        "evidence_used",
        "kcal_range",
        "likely_kcal",
        "uncertainty",
    }
    assert item_results == [
        {
            "food_name": "便當",
            "kcal_range": [550, 960],
            "likely_kcal": 750,
            "uncertainty": "medium",
            "evidence_used": ["generic_food_db:便當"],
        }
    ]


@pytest.mark.asyncio
async def test_phase_b1_answer_contract_item_results_bridge_is_locked_outside_meal_branch(tmp_path: Path) -> None:
    provider = DrinkRootAnswerContractOnlyPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-006"],
    )

    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_2"]["item_results_source"] == "none"
    assert trace["manager_pass_2"]["item_results"] == []
    assert trace["manager_pass_2"]["item_results_bridge_shape"] is None
    assert trace["manager_pass_2"]["item_results_bridge_parent_fallback_fields"] == []


@pytest.mark.asyncio
async def test_phase_b1_b1_005_top_level_item_results_take_precedence_over_bridge(tmp_path: Path) -> None:
    provider = TopLevelItemResultsWinsPhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-005"],
    )

    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_2"]["item_results_source"] == "manager_pass_2_payload"
    assert trace["runner_derived_item_results"] is False
    assert trace["manager_pass_2"]["item_results"] == [
        {
            "food_name": "豆干",
            "kcal_range": [55, 95],
            "likely_kcal": 75,
            "uncertainty": "low",
            "evidence_used": ["top_level"],
        }
    ]


@pytest.mark.asyncio
async def test_phase_b1_smoke_full_run_claims_full_readiness_scope(tmp_path: Path) -> None:
    provider = FakePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_TEA_EGG],
        output_dir=tmp_path,
        write_latest=False,
    )

    assert report["case_set"] == "full"
    assert report["requested_case_ids"] == ["B1-001"]
    assert report["completed_case_count"] == 1
    assert report["expected_full_case_count"] == 6
    assert report["full_readiness_claimed"] is True
    assert report["runtime_latency"]["readiness_claim_scope"] == "full_actual_smoke"


def test_phase_b1_provider_profile_registry_exposes_build_loop_probe_candidate_and_manual_roles() -> None:
    from scripts.run_wave1_phase_b_minimal_tool_loop_smoke import PHASE_B1_PROVIDER_PROFILES

    deepseek = PHASE_B1_PROVIDER_PROFILES["builderspace-deepseek-default"]
    grok = PHASE_B1_PROVIDER_PROFILES["builderspace-grok-4-fast-b1003-probe"]
    grok_b1005 = PHASE_B1_PROVIDER_PROFILES["builderspace-grok-4-fast-b1005-probe"]
    grok_b1006 = PHASE_B1_PROVIDER_PROFILES["builderspace-grok-4-fast-b1006-probe"]
    kimi = PHASE_B1_PROVIDER_PROFILES["builderspace-kimi-k2.5-candidate"]
    gemini = PHASE_B1_PROVIDER_PROFILES["builderspace-gemini-3-flash-preview-candidate"]
    gpt5 = PHASE_B1_PROVIDER_PROFILES["builderspace-gpt-5-manual"]

    assert deepseek["model"] == "deepseek"
    assert deepseek["provider_profile_role"] == "default_build_loop"
    assert deepseek["cost_tier"] == "low"
    assert deepseek["default_for_build_loop"] is True
    assert deepseek["documented_reasoning_status"] == "not_documented"
    assert deepseek["artifact_tool_call_reliability"] == "B1-003_failed"
    assert deepseek["production_selected"] is False

    assert grok["model"] == "grok-4-fast"
    assert grok["provider_profile_role"] == "low_cost_transport_probe"
    assert grok["cost_tier"] == "low"
    assert grok["manual_only"] is False
    assert grok["artifact_tool_call_reliability"] == "B1-003_passed"
    assert grok["production_selected"] is False

    assert grok_b1005["model"] == "grok-4-fast"
    assert grok_b1005["provider_profile_role"] == "low_cost_transport_probe"
    assert grok_b1005["cost_tier"] == "low"
    assert grok_b1005["manual_only"] is False
    assert grok_b1005["artifact_tool_call_reliability"] == "B1-005_passed"
    assert grok_b1005["branch_scope"] == "listed_ingredient_basket"
    assert grok_b1005["manager_role_scope"] == "pass_1_tool_request"
    assert grok_b1005["production_selected"] is False

    assert grok_b1006["model"] == "grok-4-fast"
    assert grok_b1006["provider_profile_role"] == "low_cost_transport_probe"
    assert grok_b1006["cost_tier"] == "low"
    assert grok_b1006["manual_only"] is False
    assert grok_b1006["artifact_tool_call_reliability"] == "B1-006_passed"
    assert grok_b1006["branch_scope"] == "common_commercial_drink"
    assert grok_b1006["manager_role_scope"] == "pass_1_tool_request"
    assert grok_b1006["production_selected"] is False

    assert kimi["model"] == "kimi-k2.5"
    assert kimi["provider_profile_role"] == "manager_candidate_primary"
    assert kimi["manager_candidate_status"] == "hypothesis_only"
    assert kimi["production_selected"] is False
    assert kimi["manual_only"] is False
    assert kimi["default_for_build_loop"] is False

    assert gemini["model"] == "gemini-3-flash-preview"
    assert gemini["provider_profile_role"] == "manager_candidate_secondary"
    assert gemini["manager_candidate_status"] == "hypothesis_only"
    assert gemini["production_selected"] is False
    assert gemini["manual_only"] is False
    assert gemini["default_for_build_loop"] is False

    assert gpt5["model"] == "gpt-5"
    assert gpt5["provider_profile_role"] == "expensive_manual_baseline"
    assert gpt5["manual_only"] is True
    assert gpt5["allow_expensive_model_probe"] is False
    assert gpt5["production_selected"] is False


@pytest.mark.asyncio
async def test_phase_b1_targeted_b1003_can_select_grok_fast_profile_and_trace_attribution(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-003"],
        provider_profile_id="builderspace-grok-4-fast-b1003-probe",
    )

    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_id"] == "builderspace-grok-4-fast-b1003-probe"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_model"] == "grok-4-fast"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_cost_tier"] == "low"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_manual_only"] is False
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_role"] == "low_cost_transport_probe"
    assert trace["manager_pass_1"]["provider_params"]["manager_candidate_status"] == "not_applicable"
    assert trace["manager_pass_1"]["provider_params"]["documented_reasoning_status"] == "documented"
    assert trace["manager_pass_1"]["provider_params"]["documented_tool_call_support"] == "documented_at_endpoint_surface"
    assert trace["manager_pass_1"]["provider_params"]["production_selected"] is False
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_transport_mode"] == "tool_call_decision_transport"
    assert trace["manager_pass_1"]["provider_params"]["allow_expensive_model_probe"] is False
    assert trace["manager_pass_1"]["provider_params"]["artifact_tool_call_reliability"] == "B1-003_passed"
    assert trace["manager_pass_1"]["provider_params"]["model"] == "grok-4-fast"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_route_mode"] == "explicit_targeted_override"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_route_reason"] == "requested_targeted_profile_override"
    assert trace["manager_pass_1"]["provider_params"]["profile_routing_rule_id"] == "phase_b1_targeted_profile_override_v1"
    assert trace["manager_pass_1"]["provider_params"]["profile_routing_scope"] == "b1_local_diagnostic"
    assert trace["manager_pass_1"]["provider_params"]["profile_routing_artifact_basis"] is None
    assert trace["manager_pass_2"]["provider_params"]["provider_profile_id"] == "builderspace-deepseek-default"
    assert trace["manager_pass_2"]["provider_params"]["provider_profile_route_mode"] == "default_build_loop"


@pytest.mark.asyncio
async def test_phase_b1_full_smoke_does_not_silently_switch_to_grok_profile(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_TEA_EGG],
        output_dir=tmp_path,
        write_latest=False,
        provider_profile_id="builderspace-grok-4-fast-b1003-probe",
    )

    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_id"] == "builderspace-deepseek-default"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_model"] == "deepseek"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_role"] == "default_build_loop"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_route_mode"] == "default_build_loop"


@pytest.mark.asyncio
async def test_phase_b1_full_smoke_auto_routes_b1003_pass1_to_grok_but_keeps_pass2_on_deepseek(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_BENTO],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    pass2_params = trace["manager_pass_2"]["provider_params"]

    assert pass1_params["provider_profile_id"] == "builderspace-grok-4-fast-b1003-probe"
    assert pass1_params["provider_profile_model"] == "grok-4-fast"
    assert pass1_params["provider_profile_role"] == "low_cost_transport_probe"
    assert pass1_params["model"] == "grok-4-fast"
    assert pass1_params["provider_profile_route_mode"] == "auto_branch_route"
    assert pass1_params["provider_profile_route_reason"] == "known_deepseek_b1003_pass1_transport_breach"
    assert pass1_params["profile_routing_rule_id"] == "phase_b1_full_smoke_b1003_pass1_grok_route_v1"
    assert pass1_params["profile_routing_scope"] == "b1_local_diagnostic"
    assert pass1_params["profile_routing_artifact_basis"] == {
        "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T155117.987328Z_natural-probe_targeted_B1-003_4ab12d.json",
        "observed_result": "B1-003_pass1_grok_legal_decision",
        "prior_default_failure": "B1-003_pass1_deepseek_tool_call_transport_contract_breach",
    }

    assert pass2_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass2_params["provider_profile_model"] == "deepseek"
    assert pass2_params["provider_profile_role"] == "default_build_loop"
    assert pass2_params["model"] == "deepseek"
    assert pass2_params["provider_profile_route_mode"] == "default_build_loop"
    assert pass2_params["provider_profile_route_reason"] == "no_branch_specific_override"
    assert pass2_params["profile_routing_rule_id"] == "phase_b1_default_build_loop_v1"
    assert pass2_params["profile_routing_scope"] == "b1_local_diagnostic"
    assert pass2_params["profile_routing_artifact_basis"] is None


@pytest.mark.asyncio
async def test_phase_b1_targeted_b1003_without_explicit_profile_remains_deepseek_diagnostic_path(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-003"],
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    assert pass1_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass1_params["provider_profile_model"] == "deepseek"
    assert pass1_params["provider_profile_role"] == "default_build_loop"
    assert pass1_params["model"] == "deepseek"
    assert pass1_params["provider_profile_route_mode"] == "default_build_loop"
    assert pass1_params["provider_profile_route_reason"] == "no_branch_specific_override"


@pytest.mark.asyncio
async def test_phase_b1_targeted_b1006_can_select_grok_fast_probe_profile_and_trace_attribution(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-006"],
        provider_profile_id="builderspace-grok-4-fast-b1006-probe",
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    pass2_params = trace["manager_pass_2"]["provider_params"]

    assert pass1_params["provider_profile_id"] == "builderspace-grok-4-fast-b1006-probe"
    assert pass1_params["provider_profile_model"] == "grok-4-fast"
    assert pass1_params["provider_profile_role"] == "low_cost_transport_probe"
    assert pass1_params["provider_profile_cost_tier"] == "low"
    assert pass1_params["artifact_tool_call_reliability"] == "B1-006_passed"
    assert pass1_params["model"] == "grok-4-fast"
    assert pass1_params["provider_profile_route_mode"] == "explicit_targeted_override"
    assert pass1_params["provider_profile_route_reason"] == "requested_targeted_profile_override"
    assert pass1_params["profile_routing_rule_id"] == "phase_b1_targeted_profile_override_v1"
    assert pass1_params["profile_routing_scope"] == "b1_local_diagnostic"
    assert pass2_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass2_params["provider_profile_route_mode"] == "default_build_loop"


@pytest.mark.asyncio
async def test_phase_b1_targeted_b1005_can_select_grok_fast_probe_profile_and_trace_attribution(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-005"],
        provider_profile_id="builderspace-grok-4-fast-b1005-probe",
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    pass2_params = trace["manager_pass_2"]["provider_params"]

    assert pass1_params["provider_profile_id"] == "builderspace-grok-4-fast-b1005-probe"
    assert pass1_params["provider_profile_model"] == "grok-4-fast"
    assert pass1_params["provider_profile_role"] == "low_cost_transport_probe"
    assert pass1_params["provider_profile_cost_tier"] == "low"
    assert pass1_params["artifact_tool_call_reliability"] == "B1-005_passed"
    assert pass1_params["model"] == "grok-4-fast"
    assert pass1_params["provider_profile_route_mode"] == "explicit_targeted_override"
    assert pass1_params["provider_profile_route_reason"] == "requested_targeted_profile_override"
    assert pass1_params["profile_routing_rule_id"] == "phase_b1_targeted_profile_override_v1"
    assert pass1_params["profile_routing_scope"] == "b1_local_diagnostic"
    assert pass2_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass2_params["provider_profile_route_mode"] == "default_build_loop"


@pytest.mark.asyncio
async def test_phase_b1_targeted_b1005_without_explicit_profile_remains_deepseek_diagnostic_path(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-005"],
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    assert pass1_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass1_params["provider_profile_model"] == "deepseek"
    assert pass1_params["provider_profile_role"] == "default_build_loop"
    assert pass1_params["model"] == "deepseek"
    assert pass1_params["provider_profile_route_mode"] == "default_build_loop"
    assert pass1_params["provider_profile_route_reason"] == "no_branch_specific_override"


@pytest.mark.asyncio
async def test_phase_b1_targeted_b1005_probe_does_not_apply_to_other_targeted_cases(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-002"],
        provider_profile_id="builderspace-grok-4-fast-b1005-probe",
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    assert pass1_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass1_params["provider_profile_model"] == "deepseek"
    assert pass1_params["provider_profile_route_mode"] == "default_build_loop"


@pytest.mark.asyncio
async def test_phase_b1_full_smoke_auto_routes_b1005_pass1_to_grok_but_keeps_pass2_on_deepseek(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_LUWEI_LISTED],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    pass2_params = trace["manager_pass_2"]["provider_params"]
    assert pass1_params["provider_profile_id"] == "builderspace-grok-4-fast-b1005-probe"
    assert pass1_params["provider_profile_model"] == "grok-4-fast"
    assert pass1_params["provider_profile_role"] == "low_cost_transport_probe"
    assert pass1_params["artifact_tool_call_reliability"] == "B1-005_passed"
    assert pass1_params["model"] == "grok-4-fast"
    assert pass1_params["provider_profile_route_mode"] == "auto_branch_route"
    assert pass1_params["provider_profile_route_reason"] == "known_deepseek_b1005_pass1_tool_policy_mismatch"
    assert pass1_params["profile_routing_rule_id"] == "phase_b1_full_smoke_b1005_pass1_grok_route_v1"
    assert pass1_params["profile_routing_scope"] == "b1_local_diagnostic"
    assert pass1_params["profile_routing_artifact_basis"] == {
        "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T180042.469158Z_natural-probe_targeted_B1-005_b176c8.json",
        "observed_result": "B1-005_pass1_grok_item_level_lookup_generic_food",
        "prior_default_failure": "B1-005_pass1_deepseek_search_tool_policy_mismatch",
    }
    assert pass2_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass2_params["provider_profile_model"] == "deepseek"
    assert pass2_params["provider_profile_role"] == "default_build_loop"
    assert pass2_params["model"] == "deepseek"
    assert pass2_params["provider_profile_route_mode"] == "default_build_loop"
    assert pass2_params["provider_profile_route_reason"] == "no_branch_specific_override"


@pytest.mark.asyncio
async def test_phase_b1_targeted_b1006_without_explicit_profile_remains_deepseek_diagnostic_path(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-006"],
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    assert pass1_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass1_params["provider_profile_model"] == "deepseek"
    assert pass1_params["provider_profile_role"] == "default_build_loop"
    assert pass1_params["model"] == "deepseek"
    assert pass1_params["provider_profile_route_mode"] == "default_build_loop"
    assert pass1_params["provider_profile_route_reason"] == "no_branch_specific_override"


@pytest.mark.asyncio
async def test_phase_b1_targeted_b1006_probe_does_not_apply_to_other_targeted_cases(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
        requested_case_ids=["B1-002"],
        provider_profile_id="builderspace-grok-4-fast-b1006-probe",
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    assert pass1_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass1_params["provider_profile_model"] == "deepseek"
    assert pass1_params["provider_profile_route_mode"] == "default_build_loop"


@pytest.mark.asyncio
async def test_phase_b1_full_smoke_auto_routes_b1006_pass1_to_grok_but_keeps_pass2_on_deepseek(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_QUERY_BUBBLE_TEA],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    pass2_params = trace["manager_pass_2"]["provider_params"]

    assert pass1_params["provider_profile_id"] == "builderspace-grok-4-fast-b1006-probe"
    assert pass1_params["provider_profile_model"] == "grok-4-fast"
    assert pass1_params["provider_profile_role"] == "low_cost_transport_probe"
    assert pass1_params["artifact_tool_call_reliability"] == "B1-006_passed"
    assert pass1_params["model"] == "grok-4-fast"
    assert pass1_params["provider_profile_route_mode"] == "auto_branch_route"
    assert pass1_params["provider_profile_route_reason"] == "known_deepseek_b1006_pass1_non_json_output"
    assert pass1_params["profile_routing_rule_id"] == "phase_b1_full_smoke_b1006_pass1_grok_route_v1"
    assert pass1_params["profile_routing_scope"] == "b1_local_diagnostic"
    assert pass1_params["profile_routing_artifact_basis"] == {
        "artifact_path": "artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T172310.969052Z_natural-probe_targeted_B1-006_242ece.json",
        "observed_result": "B1-006_pass1_grok_legal_decision",
        "prior_default_failure": "B1-006_pass1_deepseek_non_json_model_output",
    }

    assert pass2_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass2_params["provider_profile_model"] == "deepseek"
    assert pass2_params["provider_profile_role"] == "default_build_loop"
    assert pass2_params["model"] == "deepseek"
    assert pass2_params["provider_profile_route_mode"] == "default_build_loop"
    assert pass2_params["provider_profile_route_reason"] == "no_branch_specific_override"


@pytest.mark.asyncio
async def test_phase_b1_full_smoke_b1002_remains_deepseek_when_b1006_route_exists(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_BUBBLE_TEA],
        output_dir=tmp_path,
        write_latest=False,
        mode="natural-probe",
    )

    trace = report["tool_loop_traces"][0]
    pass1_params = trace["manager_pass_1"]["provider_params"]
    assert pass1_params["provider_profile_id"] == "builderspace-deepseek-default"
    assert pass1_params["provider_profile_model"] == "deepseek"
    assert pass1_params["provider_profile_route_mode"] == "default_build_loop"


@pytest.mark.asyncio
async def test_phase_b1_candidate_profiles_do_not_become_routine_smoke_defaults(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    report = await run_phase_b_minimal_tool_loop_smoke(
        provider=provider,
        smoke_cases=[CASE_TEA_EGG],
        output_dir=tmp_path,
        write_latest=False,
        provider_profile_id="builderspace-kimi-k2.5-candidate",
    )

    trace = report["tool_loop_traces"][0]
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_id"] == "builderspace-deepseek-default"
    assert trace["manager_pass_1"]["provider_params"]["provider_profile_model"] == "deepseek"


@pytest.mark.asyncio
async def test_phase_b1_expensive_profile_is_disabled_by_default(tmp_path: Path) -> None:
    provider = ProfileAwarePhaseBProvider()

    with pytest.raises(ValueError, match="expensive provider profile"):
        await run_phase_b_minimal_tool_loop_smoke(
            provider=provider,
            output_dir=tmp_path,
            write_latest=False,
            mode="natural-probe",
            requested_case_ids=["B1-003"],
            provider_profile_id="builderspace-gpt-5-manual",
        )
