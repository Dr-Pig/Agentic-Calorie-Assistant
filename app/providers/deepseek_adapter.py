from __future__ import annotations

import os
from typing import Any

import httpx

from ..runtime.agent.manager_branch_contract import (
    manager_pass1_decision_tool_arguments_schema_for_constraints,
    should_attempt_b1_common_commercial_meal_pass1_decision_transport,
)
from ..runtime.contracts.trace import MANAGER_LOOP_STAGE
from .deepseek_config import check_encoding_safety, format_user_message
from .deepseek_parsing import extract_json_object, extract_text_content
from .deepseek_runtime_contract import (
    response_format_request_for_stage,
    response_schema_for_stage,
    validate_manager_payload,
)
from .deepseek_session import complete_deepseek_with_trace


DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
class DeepSeekResponseError(RuntimeError):
    def __init__(self, message: str, *, trace: dict[str, Any]) -> None:
        super().__init__(message)
        self.trace = trace


class DeepSeekAdapter:
    """Single-manager adapter for DeepSeek chat completions."""

    def __init__(self) -> None:
        self.base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.token = os.getenv("DEEPSEEK_API_KEY", "")
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.timeout_seconds = min(int(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "15")), 15)
        self.transport_retry_count = max(0, int(os.getenv("DEEPSEEK_TRANSPORT_RETRY_COUNT", "2")))
        self.transport_retry_backoff_seconds = float(os.getenv("DEEPSEEK_TRANSPORT_RETRY_BACKOFF_SECONDS", "1.0"))
        self.temperature = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.0"))

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "deepseek",
            "configured": bool(self.token),
            "manager_model": self.model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "transport_retry_count": self.transport_retry_count,
            "transport_retry_backoff_seconds": self.transport_retry_backoff_seconds,
            "stage_models": {
                MANAGER_LOOP_STAGE: self.model,
            },
            "stage_temperatures": {
                MANAGER_LOOP_STAGE: self.temperature,
            },
        }

    async def complete_with_trace(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = 2000,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self.token:
            raise RuntimeError("DeepSeek API Key is missing. Please set DEEPSEEK_API_KEY.")

        formatted_user_message = format_user_message(stage, user_payload)
        check_encoding_safety(formatted_user_message)
        constraints = dict(user_payload.get("constraints") or {})

        response_format, transport_meta = response_format_request_for_stage(stage, constraints=constraints)
        request_payload: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_user_message},
            ],
            "response_format": response_format,
        }
        if max_tokens is not None:
            request_payload["max_tokens"] = max_tokens

        return await complete_deepseek_with_trace(
            base_url=self.base_url,
            token=self.token,
            timeout_seconds=self.timeout_seconds,
            transport_retry_count=self.transport_retry_count,
            transport_retry_backoff_seconds=self.transport_retry_backoff_seconds,
            model=self.model,
            stage=stage,
            temperature=self.temperature,
            request_payload=request_payload,
            transport_meta=transport_meta,
            validate_manager_payload=lambda current_stage, payload, **_: validate_manager_payload(current_stage, payload, constraints=constraints),
            async_client_factory=httpx.AsyncClient,
            build_error=lambda **kwargs: DeepSeekResponseError(
                f"DeepSeek manager error at stage={stage}: {type(kwargs['exc']).__name__}: {kwargs['exc']}",
                trace={
                    "stage": stage,
                    "provider": "deepseek",
                    "model": self.model,
                    "request_payload": kwargs["request_payload"],
                    "transport_attempts": kwargs["transport_attempts"],
                    "parse_attempts": kwargs["parse_attempts"],
                    "request_failure_family": getattr(kwargs["exc"], "failure_family", "empty_content" if "empty" in str(kwargs["exc"]).lower() else "malformed_json"),
                    "failure_family": getattr(kwargs["exc"], "failure_family", "empty_content" if "empty" in str(kwargs["exc"]).lower() else "malformed_json"),
                    "failing_component": getattr(kwargs["exc"], "failing_component", "deepseek_adapter.complete_with_trace"),
                    "violation_family": getattr(kwargs["exc"], "violation_family", None),
                    "actual_shape": getattr(kwargs["exc"], "actual_shape", None),
                    "parsed_object": getattr(kwargs["exc"], "observed_value", None),
                    "value_excerpt": getattr(kwargs["exc"], "value_excerpt", None),
                    "value_truncated": getattr(kwargs["exc"], "value_truncated", None),
                    "structured_output_transport_attempted": kwargs["transport_meta"]["structured_output_transport_attempted"],
                    "structured_output_transport_mode": kwargs["transport_meta"]["structured_output_transport_mode"],
                    "structured_output_transport_accepted": kwargs["transport_meta"]["structured_output_transport_accepted"],
                    "structured_output_transport_fallback": kwargs["transport_meta"]["structured_output_transport_fallback"],
                    "fallback_reason": kwargs["transport_meta"]["fallback_reason"],
                    "structured_output_transport_constraint_snapshot": kwargs["transport_meta"]["structured_output_transport_constraint_snapshot"],
                    "effective_response_format_type": request_payload["response_format"].get("type"),
                },
            ),
        )

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = 2000,
    ) -> dict[str, Any]:
        parsed, _ = await self.complete_with_trace(
            system_prompt=system_prompt,
            user_payload=user_payload,
            stage=stage,
            max_tokens=max_tokens,
        )
        return parsed

    def _response_schema_for_stage(self, stage: str, constraints: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return response_schema_for_stage(stage, constraints)

    def _response_format_request_for_stage(
        self,
        stage: str,
        *,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return response_format_request_for_stage(stage, constraints=constraints)

    def _decision_transport_request_for_stage(
        self,
        stage: str,
        *,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        constraint_snapshot = {
            "phase_b1_manager_role": str((constraints or {}).get("phase_b1_manager_role") or ""),
            "phase_b1_pass1_mode": str((constraints or {}).get("phase_b1_pass1_mode") or ""),
            "phase_b1_case_family": str((constraints or {}).get("phase_b1_case_family") or ""),
        }
        meta = {
            "decision_transport_attempted": False,
            "decision_transport_mode": None,
            "decision_transport_accepted": False,
            "decision_transport_fallback": None,
            "decision_transport_fallback_reason": None,
            "decision_transport_contract_breach": False,
            "decision_transport_constraint_snapshot": constraint_snapshot,
        }
        if stage != MANAGER_LOOP_STAGE or not should_attempt_b1_common_commercial_meal_pass1_decision_transport(constraints):
            return None, meta
        schema = manager_pass1_decision_tool_arguments_schema_for_constraints(self._response_schema_for_stage(stage), constraints)
        meta["decision_transport_attempted"] = True
        meta["decision_transport_mode"] = "tool_call_decision_transport"
        return (
            {
                "mode": "tool_call_decision_transport",
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": "manager_call_tools_decision",
                            "description": "Return the manager call-tools decision as structured arguments.",
                            "parameters": schema,
                        },
                    }
                ],
                "tool_choice": {"type": "function", "function": {"name": "manager_call_tools_decision"}},
            },
            meta,
        )

    def _validate_manager_payload(
        self,
        stage: str,
        payload: dict[str, Any],
        *,
        constraints: dict[str, Any] | None = None,
    ) -> None:
        validate_manager_payload(stage, payload, constraints=constraints)

    def _extract_text_content(self, data: dict[str, Any]) -> str:
        return extract_text_content(data)

    def _extract_json_object(self, content: str) -> dict[str, Any]:
        return extract_json_object(content)
