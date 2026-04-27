from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

import httpx

from ..logger import logger
from ..runtime.agent.manager_branch_contract import (
    ManagerPass1BranchContractError,
    manager_pass1_decision_tool_arguments_schema_for_constraints,
    manager_pass1_schema_for_constraints,
    should_attempt_b1_common_commercial_meal_pass1_decision_transport,
    should_attempt_b1_generic_pass1_structured_output_transport,
    validate_manager_pass1_branch,
)
from ..runtime.contracts.trace import MANAGER_LOOP_STAGE
from ..text_integrity import corruption_summary, find_text_corruption


DEFAULT_BASE_URL = "https://space.ai-builders.com/backend/v1"
PLACEHOLDER_VALUES = {"", "replace-me", "https://api.example.com"}
MAX_PARSE_RETRIES = 1
DEFAULT_TIMEOUT_SECONDS = 30
MAX_TIMEOUT_SECONDS = 120

DEFAULT_STAGE_TEMPERATURES = {
    MANAGER_LOOP_STAGE: 0.0,
}
DECISION_TRANSPORT_TOOL_NAME = "manager_call_tools_decision"


class BuilderSpaceResponseError(RuntimeError):
    def __init__(self, message: str, *, trace: dict[str, Any]) -> None:
        super().__init__(message)
        self.trace = trace


class _BuilderSpaceParseError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        failure_family: str,
        failing_component: str,
        observed_value: Any = None,
        raw_content: str | None = None,
        parse_attempts: list[dict[str, Any]] | None = None,
        parse_contract_status: str | None = None,
        parse_recovery_used: bool = False,
        parse_recovery_strategy: str | None = None,
        parse_recovery_ambiguous: bool = False,
    ) -> None:
        super().__init__(message)
        self.failure_family = failure_family
        self.failing_component = failing_component
        self.observed_type = _observed_type_name(observed_value)
        self.value_excerpt, self.value_truncated = _value_excerpt(observed_value)
        self.raw_content_excerpt, self.raw_content_truncated = _value_excerpt(raw_content)
        self.parse_attempts = list(parse_attempts or [])
        self.parse_contract_status = parse_contract_status
        self.parse_recovery_used = parse_recovery_used
        self.parse_recovery_strategy = parse_recovery_strategy
        self.parse_recovery_ambiguous = parse_recovery_ambiguous


class BuilderSpaceAdapter:
    def __init__(self, *, manager_model_override: str | None = None, role_label: str = "manager") -> None:
        self.base_url = os.getenv("AI_BUILDER_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
        self.token = os.getenv("AI_BUILDER_TOKEN", "")
        self.manager_model = manager_model_override or os.getenv("BUILDERSPACE_MANAGER_MODEL", "deepseek")
        self.role_label = role_label
        self.configured_timeout_env = os.getenv("AI_BUILDER_TIMEOUT_SECONDS")
        self.timeout_seconds, self.timeout_was_clamped = self._effective_timeout_seconds(self.configured_timeout_env)
        self.transport_retry_count = max(0, int(os.getenv("AI_BUILDER_TRANSPORT_RETRY_COUNT", "2")))
        self.transport_retry_backoff_seconds = float(os.getenv("AI_BUILDER_TRANSPORT_RETRY_BACKOFF_SECONDS", "0.75"))
        self.manager_temperature = float(
            os.getenv("BUILDERSPACE_MANAGER_TEMPERATURE", str(DEFAULT_STAGE_TEMPERATURES[MANAGER_LOOP_STAGE]))
        )

    def readiness(self) -> dict[str, Any]:
        return {
            "provider": "builderspace",
            "configured": self._is_configured(),
            "manager_model": self.manager_model,
            "base_url": self.base_url,
            "timeout_seconds": self.timeout_seconds,
            "configured_timeout_env": self.configured_timeout_env,
            "default_timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
            "max_timeout_seconds": MAX_TIMEOUT_SECONDS,
            "timeout_was_clamped": self.timeout_was_clamped,
            "transport_retry_count": self.transport_retry_count,
            "transport_retry_backoff_seconds": self.transport_retry_backoff_seconds,
            "role": self.role_label,
            "stage_temperatures": {
                MANAGER_LOOP_STAGE: self.manager_temperature,
            },
            "stage_models": {
                MANAGER_LOOP_STAGE: self.manager_model,
            },
        }

    async def complete_with_trace(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = 1800,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not self._is_configured():
            raise RuntimeError("BuilderSpace is not configured.")

        model = self._model_for_stage(stage)
        formatted_user_message = self._format_user_message(stage, user_payload)
        self._check_encoding_safety(formatted_user_message)
        constraints = dict(user_payload.get("constraints") or {})

        decision_transport_request, decision_transport_meta = self._decision_transport_request_for_stage(
            stage, constraints=constraints
        )
        response_format, transport_meta = self._response_format_request_for_stage(stage, constraints=constraints)
        base_request_payload: dict[str, Any] = {
            "model": model,
            "temperature": self._temperature_for_stage(stage),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": formatted_user_message},
            ],
        }
        if max_tokens is not None:
            base_request_payload["max_tokens"] = max_tokens
        fallback_reason: str | None = None
        effective_response_format_type = response_format.get("type")

        transport_attempts: list[dict[str, Any]] = []
        parse_attempts: list[dict[str, Any]] = []
        last_error: Exception | None = None
        parse_retry_budget = MAX_PARSE_RETRIES
        response: httpx.Response | _FakeResponse | None = None
        data: dict[str, Any] | None = None

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                for attempt_index in range(1, self.transport_retry_count + 2):
                    attempt_trace = {
                        "attempt_index": attempt_index,
                        "base_url": self.base_url,
                        "endpoint": f"{self.base_url}/chat/completions",
                        "model": model,
                        "stage": stage,
                    }
                    if decision_transport_request is not None:
                        request_payload = dict(base_request_payload)
                        request_payload["tools"] = decision_transport_request["tools"]
                        request_payload["tool_choice"] = decision_transport_request["tool_choice"]
                        attempt_trace["decision_transport_mode"] = decision_transport_request["mode"]
                        try:
                            response = await client.post(
                                f"{self.base_url}/chat/completions",
                                params={"debug": "true"},
                                headers={
                                    "Authorization": f"Bearer {self.token}",
                                    "Content-Type": "application/json",
                                },
                                json=request_payload,
                            )
                            attempt_trace["http_status"] = response.status_code
                            response.raise_for_status()
                            data = response.json()
                            if not isinstance(data, dict):
                                raise _BuilderSpaceParseError(
                                    "BuilderSpace response JSON must be an object.",
                                    failure_family="response_json_shape_error",
                                    failing_component="builderspace_adapter.response_json",
                                    observed_value=data,
                                )
                            parsed = self._extract_tool_call_decision(data)
                            decision_transport_meta["decision_transport_accepted"] = True
                            decision_transport_meta["decision_transport_contract_breach"] = False
                            self._validate_manager_payload(stage, parsed, constraints=constraints)
                            attempt_trace["status"] = "success"
                            transport_attempts.append(attempt_trace)
                            trace = {
                                "stage": stage,
                                "provider": "builderspace",
                                "model": model,
                                "request_payload": request_payload,
                                "raw_content": None,
                                "raw_response_excerpt": response.text[:1200],
                                "parsed_object": parsed,
                                "status": data.get("status"),
                                "incomplete_details": data.get("incomplete_details"),
                                "usage": data.get("usage"),
                                "transport_attempts": transport_attempts,
                                "parse_attempts": parse_attempts,
                                "finish_reason": self._extract_finish_reason(data),
                                "response_status": response.status_code,
                                "parse_contract_status": None,
                                "parse_recovery_used": False,
                                "parse_recovery_strategy": None,
                                "parse_recovery_ambiguous": False,
                                "raw_content_excerpt": None,
                                "request_failure_family": None,
                                "structured_output_transport_attempted": transport_meta["structured_output_transport_attempted"],
                                "structured_output_transport_mode": transport_meta["structured_output_transport_mode"],
                                "structured_output_transport_accepted": transport_meta["structured_output_transport_accepted"],
                                "structured_output_transport_fallback": transport_meta["structured_output_transport_fallback"],
                                "fallback_reason": transport_meta["fallback_reason"],
                                "structured_output_transport_constraint_snapshot": transport_meta["structured_output_transport_constraint_snapshot"],
                                "effective_response_format_type": None,
                                "decision_transport_attempted": decision_transport_meta["decision_transport_attempted"],
                                "decision_transport_mode": decision_transport_meta["decision_transport_mode"],
                                "decision_transport_accepted": decision_transport_meta["decision_transport_accepted"],
                                "decision_transport_fallback": decision_transport_meta["decision_transport_fallback"],
                                "decision_transport_fallback_reason": decision_transport_meta["decision_transport_fallback_reason"],
                                "decision_transport_contract_breach": decision_transport_meta["decision_transport_contract_breach"],
                                "decision_transport_constraint_snapshot": decision_transport_meta["decision_transport_constraint_snapshot"],
                            }
                            return parsed, trace
                        except httpx.HTTPStatusError as exc:
                            if self._is_tool_call_transport_rejection(exc):
                                decision_transport_meta["decision_transport_accepted"] = False
                                decision_transport_meta["decision_transport_fallback"] = "json_schema"
                                decision_transport_meta["decision_transport_fallback_reason"] = (
                                    "provider_rejected_tool_call_transport"
                                )
                                decision_transport_request = None
                            else:
                                raise
                        except _BuilderSpaceParseError:
                            decision_transport_meta["decision_transport_accepted"] = True
                            decision_transport_meta["decision_transport_contract_breach"] = True
                            raise
                    response_format_attempts = [response_format]
                    if transport_meta["structured_output_transport_attempted"]:
                        response_format_attempts.append({"type": "json_object"})
                    try:
                        for format_index, current_response_format in enumerate(response_format_attempts, start=1):
                            request_payload = dict(base_request_payload)
                            request_payload["response_format"] = current_response_format
                            attempt_trace["response_format_type"] = current_response_format.get("type")
                            attempt_trace["response_format_attempt_index"] = format_index
                            response = await client.post(
                                f"{self.base_url}/chat/completions",
                                params={"debug": "true"},
                                headers={
                                    "Authorization": f"Bearer {self.token}",
                                    "Content-Type": "application/json",
                                },
                                json=request_payload,
                            )
                            attempt_trace["http_status"] = response.status_code
                            try:
                                response.raise_for_status()
                            except httpx.HTTPStatusError as exc:
                                if (
                                    current_response_format.get("type") == "json_schema"
                                    and self._is_structured_output_transport_rejection(exc)
                                    and format_index < len(response_format_attempts)
                                ):
                                    fallback_reason = "provider_rejected_response_format"
                                    transport_meta["structured_output_transport_accepted"] = False
                                    transport_meta["structured_output_transport_fallback"] = "json_object"
                                    transport_meta["fallback_reason"] = fallback_reason
                                    continue
                                raise
                            effective_response_format_type = current_response_format.get("type")
                            transport_meta["structured_output_transport_accepted"] = current_response_format.get("type") == "json_schema"
                            break
                        try:
                            data = response.json()
                        except Exception as exc:
                            raise _BuilderSpaceParseError(
                                "BuilderSpace response body is not a JSON object.",
                                failure_family="response_json_shape_error",
                                failing_component="builderspace_adapter.response_json",
                                observed_value=response.text,
                                parse_attempts=[
                                    {
                                        "attempt_index": attempt_index,
                                        "stage": stage,
                                        "parser": "response_json",
                                        "status": "failed",
                                        "failure_family": "response_json_shape_error",
                                    }
                                ],
                            ) from exc
                        if not isinstance(data, dict):
                            raise _BuilderSpaceParseError(
                                "BuilderSpace response JSON must be an object.",
                                failure_family="response_json_shape_error",
                                failing_component="builderspace_adapter.response_json",
                                observed_value=data,
                                parse_attempts=[
                                    {
                                        "attempt_index": attempt_index,
                                        "stage": stage,
                                        "parser": "response_json",
                                        "status": "failed",
                                        "failure_family": "response_json_shape_error",
                                    }
                                ],
                            )
                        raw_content = self._extract_text_content(data)
                        try:
                            parsed, parse_meta = self._extract_json_object(raw_content)
                        except Exception as exc:  # parse failure is retriable once
                            parse_attempt = {
                                "attempt_index": attempt_index,
                                "stage": stage,
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                                "raw_content_excerpt": raw_content[:600],
                                "failure_family": getattr(exc, "failure_family", "malformed_json"),
                            }
                            if isinstance(exc, _BuilderSpaceParseError):
                                parse_attempt["parse_recovery_used"] = exc.parse_recovery_used
                                parse_attempt["parse_recovery_strategy"] = exc.parse_recovery_strategy
                                parse_attempt["parse_recovery_ambiguous"] = exc.parse_recovery_ambiguous
                            parse_attempts.append(parse_attempt)
                            last_error = exc
                            if parse_retry_budget > 0:
                                parse_retry_budget -= 1
                                continue
                            raise
                        if not parsed:
                            exc = RuntimeError("empty parsed manager payload")
                            parse_attempts.append(
                                {
                                    "attempt_index": attempt_index,
                                    "stage": stage,
                                    "error_type": type(exc).__name__,
                                    "error": str(exc),
                                    "failure_family": "empty_content",
                                }
                            )
                            last_error = exc
                            if parse_retry_budget > 0:
                                parse_retry_budget -= 1
                                continue
                            raise exc
                        try:
                            self._validate_manager_payload(stage, parsed, constraints=constraints)
                        except ManagerPass1BranchContractError:
                            raise
                        except Exception as exc:
                            parse_attempts.append(
                                {
                                    "attempt_index": attempt_index,
                                    "stage": stage,
                                    "error_type": type(exc).__name__,
                                    "error": str(exc),
                                    "failure_family": getattr(exc, "failure_family", "malformed_json"),
                                }
                            )
                            last_error = exc
                            if parse_retry_budget > 0:
                                parse_retry_budget -= 1
                                continue
                            raise
                        attempt_trace["status"] = "success"
                        transport_attempts.append(attempt_trace)
                        trace = {
                            "stage": stage,
                            "provider": "builderspace",
                            "model": model,
                            "request_payload": request_payload,
                            "raw_content": raw_content,
                            "raw_response_excerpt": response.text[:1200],
                            "parsed_object": parsed,
                            "status": data.get("status"),
                            "incomplete_details": data.get("incomplete_details"),
                            "usage": data.get("usage"),
                            "transport_attempts": transport_attempts,
                            "parse_attempts": parse_attempts + list(parse_meta.get("parse_attempts") or []),
                            "finish_reason": self._extract_finish_reason(data),
                            "response_status": response.status_code,
                            "parse_contract_status": parse_meta.get("parse_contract_status"),
                            "parse_recovery_used": parse_meta.get("parse_recovery_used"),
                            "parse_recovery_strategy": parse_meta.get("parse_recovery_strategy"),
                            "parse_recovery_ambiguous": parse_meta.get("parse_recovery_ambiguous"),
                            "raw_content_excerpt": parse_meta.get("raw_content_excerpt"),
                            "request_failure_family": None,
                            "structured_output_transport_attempted": transport_meta["structured_output_transport_attempted"],
                            "structured_output_transport_mode": transport_meta["structured_output_transport_mode"],
                            "structured_output_transport_accepted": transport_meta["structured_output_transport_accepted"],
                            "structured_output_transport_fallback": transport_meta["structured_output_transport_fallback"],
                            "fallback_reason": transport_meta["fallback_reason"],
                            "structured_output_transport_constraint_snapshot": transport_meta["structured_output_transport_constraint_snapshot"],
                            "effective_response_format_type": effective_response_format_type,
                            "decision_transport_attempted": decision_transport_meta["decision_transport_attempted"],
                            "decision_transport_mode": decision_transport_meta["decision_transport_mode"],
                            "decision_transport_accepted": decision_transport_meta["decision_transport_accepted"],
                            "decision_transport_fallback": decision_transport_meta["decision_transport_fallback"],
                            "decision_transport_fallback_reason": decision_transport_meta["decision_transport_fallback_reason"],
                            "decision_transport_contract_breach": decision_transport_meta["decision_transport_contract_breach"],
                            "decision_transport_constraint_snapshot": decision_transport_meta["decision_transport_constraint_snapshot"],
                        }
                        return parsed, trace
                    except Exception as exc:
                        last_error = exc
                        attempt_trace["error_type"] = type(exc).__name__
                        attempt_trace["error"] = str(exc)
                        transport_attempts.append(attempt_trace)
                        if attempt_index < self.transport_retry_count + 1:
                            await asyncio.sleep(self.transport_retry_backoff_seconds * attempt_index)
                raise last_error or RuntimeError("BuilderSpace transport failed without a captured exception.")
        except Exception as exc:
            failure_family = getattr(exc, "failure_family", None)
            failing_component = getattr(exc, "failing_component", "builderspace_adapter.complete_with_trace")
            message = f"BuilderSpace manager error at stage={stage}: {type(exc).__name__}: {exc}"
            raise BuilderSpaceResponseError(
                message,
                trace={
                    "stage": stage,
                    "provider": "builderspace",
                    "model": model,
                    "request_payload": request_payload,
                    "transport_attempts": transport_attempts,
                    "parse_attempts": list(parse_attempts) + list(getattr(exc, "parse_attempts", []) or []),
                    "base_url": self.base_url,
                    "timeout_seconds": self.timeout_seconds,
                    "request_failure_family": failure_family,
                    "failure_family": failure_family,
                    "failing_component": failing_component,
                    "violation_family": getattr(exc, "violation_family", None),
                    "actual_shape": getattr(exc, "actual_shape", None),
                    "parsed_object": getattr(exc, "observed_value", None),
                    "observed_type": getattr(exc, "observed_type", None),
                    "value_excerpt": getattr(exc, "value_excerpt", None),
                    "value_truncated": getattr(exc, "value_truncated", None),
                    "raw_content_excerpt": getattr(exc, "raw_content_excerpt", None),
                    "raw_content_truncated": getattr(exc, "raw_content_truncated", None),
                    "raw_response_excerpt": response.text[:1200] if response is not None else None,
                    "response_status": response.status_code if response is not None else None,
                    "status": data.get("status") if isinstance(data, dict) else None,
                    "incomplete_details": data.get("incomplete_details") if isinstance(data, dict) else None,
                    "usage": data.get("usage") if isinstance(data, dict) else None,
                    "finish_reason": self._extract_finish_reason(data) if isinstance(data, dict) else None,
                    "parse_contract_status": getattr(exc, "parse_contract_status", None),
                    "parse_recovery_used": getattr(exc, "parse_recovery_used", False),
                    "parse_recovery_strategy": getattr(exc, "parse_recovery_strategy", None),
                    "parse_recovery_ambiguous": getattr(exc, "parse_recovery_ambiguous", False),
                    "structured_output_transport_attempted": transport_meta["structured_output_transport_attempted"],
                    "structured_output_transport_mode": transport_meta["structured_output_transport_mode"],
                    "structured_output_transport_accepted": transport_meta["structured_output_transport_accepted"],
                    "structured_output_transport_fallback": transport_meta["structured_output_transport_fallback"],
                    "fallback_reason": transport_meta["fallback_reason"] or fallback_reason,
                    "structured_output_transport_constraint_snapshot": transport_meta["structured_output_transport_constraint_snapshot"],
                    "decision_transport_attempted": decision_transport_meta["decision_transport_attempted"],
                    "decision_transport_mode": decision_transport_meta["decision_transport_mode"],
                    "decision_transport_accepted": decision_transport_meta["decision_transport_accepted"],
                    "decision_transport_fallback": decision_transport_meta["decision_transport_fallback"],
                    "decision_transport_fallback_reason": decision_transport_meta["decision_transport_fallback_reason"],
                    "decision_transport_contract_breach": decision_transport_meta["decision_transport_contract_breach"],
                    "decision_transport_constraint_snapshot": decision_transport_meta["decision_transport_constraint_snapshot"],
                    "effective_response_format_type": effective_response_format_type,
                },
            ) from exc

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_payload: dict[str, Any],
        stage: str,
        max_tokens: int | None = 1800,
    ) -> dict[str, Any]:
        parsed, _ = await self.complete_with_trace(
            system_prompt=system_prompt,
            user_payload=user_payload,
            stage=stage,
            max_tokens=max_tokens,
        )
        return parsed

    def _extract_text_content(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise _BuilderSpaceParseError(
                "BuilderSpace returned invalid choices envelope.",
                failure_family="choices_shape_error",
                failing_component="builderspace_adapter.extract_choices",
                observed_value=choices,
            )
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise _BuilderSpaceParseError(
                "BuilderSpace first choice must be an object.",
                failure_family="choices_shape_error",
                failing_component="builderspace_adapter.extract_choices",
                observed_value=first_choice,
            )
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise _BuilderSpaceParseError(
                "BuilderSpace message must be an object.",
                failure_family="message_shape_error",
                failing_component="builderspace_adapter.extract_message",
                observed_value=message,
            )
        content = message.get("content")
        if isinstance(content, list):
            texts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    raise _BuilderSpaceParseError(
                        "BuilderSpace content list must contain object parts only.",
                        failure_family="content_shape_error",
                        failing_component="builderspace_adapter.extract_text_content",
                        observed_value=item,
                    )
                texts.append(str(item.get("text") or ""))
            content = "\n".join(texts).strip()
        elif content is not None and not isinstance(content, str):
            raise _BuilderSpaceParseError(
                "BuilderSpace content must be a string or a list of text parts.",
                failure_family="content_shape_error",
                failing_component="builderspace_adapter.extract_text_content",
                observed_value=content,
            )
        content = str(content or "").strip()
        if not content:
            raise _BuilderSpaceParseError(
                "BuilderSpace returned empty content.",
                failure_family="non_json_model_output",
                failing_component="builderspace_adapter.extract_text_content",
                observed_value=content,
                raw_content=content,
            )
        return content

    def _extract_finish_reason(self, data: dict[str, Any] | None) -> str | None:
        if not isinstance(data, dict):
            return None
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return None
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None
        finish_reason = first_choice.get("finish_reason")
        return finish_reason if isinstance(finish_reason, str) else None

    def _extract_json_object(self, content: str) -> tuple[dict[str, Any], dict[str, Any]]:
        raw_text = content.strip().replace("\ufeff", "")
        parse_attempts: list[dict[str, Any]] = []
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            parse_attempts.append(
                {
                    "parser": "strict_json",
                    "status": "failed",
                    "failure_family": "malformed_json",
                    "error_type": type(exc).__name__,
                }
            )
        else:
            if isinstance(parsed, dict):
                parse_attempts.append(
                    {
                        "parser": "strict_json",
                        "status": "success",
                        "parse_contract_status": "strict_json",
                    }
                )
                return parsed, {
                    "parse_contract_status": "strict_json",
                    "parse_recovery_used": False,
                    "parse_recovery_strategy": None,
                    "parse_recovery_ambiguous": False,
                    "parse_attempts": parse_attempts,
                    "raw_content_excerpt": raw_text[:1200],
                    "finish_reason": None,
                }
            raise _BuilderSpaceParseError(
                "BuilderSpace strict JSON content must be an object.",
                failure_family="malformed_json",
                failing_component="builderspace_adapter.extract_json_object",
                observed_value=parsed,
                raw_content=raw_text,
                parse_attempts=parse_attempts,
            )

        fenced = re.findall(r"```(?:json)?\s*(.*?)```", raw_text, flags=re.DOTALL | re.IGNORECASE)
        fenced_candidates: list[dict[str, Any]] = []
        for chunk in fenced:
            chunk_text = chunk.strip()
            if not chunk_text:
                continue
            try:
                parsed = json.loads(chunk_text)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                fenced_candidates.append(parsed)
        if len(fenced_candidates) == 1:
            parse_attempts.append(
                {
                    "parser": "fenced_json",
                    "status": "recovered",
                    "parse_contract_status": "fenced_json_recovered",
                }
            )
            return fenced_candidates[0], {
                "parse_contract_status": "fenced_json_recovered",
                "parse_recovery_used": True,
                "parse_recovery_strategy": "fenced_json",
                "parse_recovery_ambiguous": False,
                "parse_attempts": parse_attempts,
                "raw_content_excerpt": raw_text[:1200],
                "finish_reason": None,
            }
        if len(fenced_candidates) > 1:
            raise _BuilderSpaceParseError(
                "BuilderSpace fenced JSON recovery is ambiguous.",
                failure_family="malformed_json",
                failing_component="builderspace_adapter.extract_json_object",
                observed_value=raw_text,
                raw_content=raw_text,
                parse_attempts=parse_attempts,
                parse_recovery_used=True,
                parse_recovery_strategy="fenced_json",
                parse_recovery_ambiguous=True,
            )

        open_fenced_candidates = self._extract_open_fenced_json_candidates(raw_text)
        if len(open_fenced_candidates) == 1:
            parse_attempts.append(
                {
                    "parser": "open_fenced_json_marker",
                    "status": "recovered",
                    "parse_contract_status": "open_fenced_json_recovered",
                }
            )
            return open_fenced_candidates[0], {
                "parse_contract_status": "open_fenced_json_recovered",
                "parse_recovery_used": True,
                "parse_recovery_strategy": "open_fenced_json_marker",
                "parse_recovery_ambiguous": False,
                "parse_attempts": parse_attempts,
                "raw_content_excerpt": raw_text[:1200],
                "finish_reason": None,
            }
        if len(open_fenced_candidates) > 1:
            raise _BuilderSpaceParseError(
                "BuilderSpace open fenced JSON recovery is ambiguous.",
                failure_family="malformed_json",
                failing_component="builderspace_adapter.extract_json_object",
                observed_value=raw_text,
                raw_content=raw_text,
                parse_attempts=parse_attempts,
                parse_recovery_used=True,
                parse_recovery_strategy="open_fenced_json_marker",
                parse_recovery_ambiguous=True,
            )

        candidates = self._extract_json_candidates(raw_text)
        if len(candidates) == 1:
            parse_attempts.append(
                {
                    "parser": "last_valid_json_object",
                    "status": "recovered",
                    "parse_contract_status": "prose_json_recovered",
                }
            )
            return candidates[0], {
                "parse_contract_status": "prose_json_recovered",
                "parse_recovery_used": True,
                "parse_recovery_strategy": "last_valid_json_object",
                "parse_recovery_ambiguous": False,
                "parse_attempts": parse_attempts,
                "raw_content_excerpt": raw_text[:1200],
                "finish_reason": None,
            }
        if len(candidates) > 1:
            raise _BuilderSpaceParseError(
                "BuilderSpace prose JSON recovery is ambiguous.",
                failure_family="malformed_json",
                failing_component="builderspace_adapter.extract_json_object",
                observed_value=raw_text,
                raw_content=raw_text,
                parse_attempts=parse_attempts,
                parse_recovery_used=True,
                parse_recovery_strategy="last_valid_json_object",
                parse_recovery_ambiguous=True,
            )
        raise _BuilderSpaceParseError(
            "BuilderSpace did not return JSON.",
            failure_family="non_json_model_output",
            failing_component="builderspace_adapter.extract_json_object",
            observed_value=raw_text,
            raw_content=raw_text,
            parse_attempts=parse_attempts,
        )

    def _extract_json_candidates(self, content: str) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        stack = 0
        start_index: int | None = None
        for index, char in enumerate(content):
            if char == "{":
                if stack == 0:
                    start_index = index
                stack += 1
            elif char == "}":
                if stack > 0:
                    stack -= 1
                    if stack == 0 and start_index is not None:
                        chunk = content[start_index : index + 1]
                        try:
                            parsed = json.loads(chunk)
                        except json.JSONDecodeError:
                            start_index = None
                            continue
                        if isinstance(parsed, dict):
                            candidates.append(parsed)
                        start_index = None
        return candidates

    def _extract_open_fenced_json_candidates(self, content: str) -> list[dict[str, Any]]:
        marker = re.compile(r"```(?:json)?\s*", flags=re.IGNORECASE)
        matches = list(marker.finditer(content))
        if len(matches) != 1:
            return []
        suffix = content[matches[0].end() :]
        if "```" in suffix:
            return []
        return self._extract_json_candidates(suffix)

    def _sanitize_content(self, content: str) -> str:
        text = content.strip().replace("\ufeff", "")
        fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced:
            text = "\n".join(chunk.strip() for chunk in fenced if chunk.strip())
        return text

    def _format_user_message(self, stage: str, user_payload: dict[str, Any]) -> str:
        payload = _jsonable(user_payload)
        return json.dumps({"stage": stage, "payload": payload}, ensure_ascii=False)

    def _check_encoding_safety(self, content: str) -> None:
        findings = find_text_corruption(content)
        if findings:
            summary = corruption_summary(findings)
            raise RuntimeError(
                f"Encoding Gate Failure (Layer 1): text corruption detected before serialization: {summary}"
            )

    def _model_for_stage(self, stage: str) -> str:
        return self.manager_model

    def _temperature_for_stage(self, stage: str) -> float:
        return self.manager_temperature

    def _manager_loop_schema(self, constraints: dict[str, Any] | None = None) -> dict[str, Any]:
        base_schema = {
            "type": "object",
            "properties": {
                "manager_action": {"type": "string", "enum": ["call_tools", "final"]},
                "interaction_family": {"type": "string"},
                "response_mode": {"type": "string"},
                "intent": {"type": "string"},
                "intent_type": {"type": "string"},
                "workflow_effect": {"type": "string"},
                "target_attachment": {"type": "object"},
                "exactness": {"type": "string"},
                "confidence": {"type": "string"},
                "evidence_posture": {"type": "string"},
                "repair_ack": {"type": "boolean"},
                "response_summary": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "pending_followup": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                "tool_calls": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "arguments": {"type": "object"},
                        },
                        "required": ["name"],
                        "additionalProperties": False,
                    },
                },
                "final_action": {"type": "string"},
                "operations": {"type": "array"},
                "answer_contract": {"type": "object"},
                "uncertainty_posture": {"type": "string"},
                "evidence_honesty_posture": {"type": "string"},
            },
            "required": [
                "manager_action",
                "intent",
                "workflow_effect",
                "target_attachment",
                "exactness",
                "confidence",
                "evidence_posture",
                "repair_ack",
            ],
            "additionalProperties": False,
        }
        return manager_pass1_schema_for_constraints(base_schema, constraints)

    def _response_schema_for_stage(self, stage: str, constraints: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if stage == MANAGER_LOOP_STAGE:
            return self._manager_loop_schema(constraints)
        return None

    def _response_format_request_for_stage(
        self,
        stage: str,
        *,
        constraints: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        constraint_snapshot = {
            "phase_b1_manager_role": str((constraints or {}).get("phase_b1_manager_role") or ""),
            "phase_b1_pass1_mode": str((constraints or {}).get("phase_b1_pass1_mode") or ""),
            "phase_b1_case_family": str((constraints or {}).get("phase_b1_case_family") or ""),
        }
        if stage == MANAGER_LOOP_STAGE and should_attempt_b1_generic_pass1_structured_output_transport(constraints):
            schema = self._response_schema_for_stage(stage, constraints)
            return (
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "phase_b1_generic_pass1_call_tools",
                        "strict": True,
                        "schema": schema,
                    },
                },
                {
                    "structured_output_transport_attempted": True,
                    "structured_output_transport_mode": "json_schema",
                    "structured_output_transport_accepted": None,
                    "structured_output_transport_fallback": None,
                    "fallback_reason": None,
                    "structured_output_transport_constraint_snapshot": constraint_snapshot,
                },
            )
        return (
            {"type": "json_object"},
            {
                "structured_output_transport_attempted": False,
                "structured_output_transport_mode": "json_object",
                "structured_output_transport_accepted": False,
                "structured_output_transport_fallback": None,
                "fallback_reason": None,
                "structured_output_transport_constraint_snapshot": constraint_snapshot,
            },
        )

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
        schema = manager_pass1_decision_tool_arguments_schema_for_constraints(self._manager_loop_schema(), constraints)
        meta["decision_transport_attempted"] = True
        meta["decision_transport_mode"] = "tool_call_decision_transport"
        return (
            {
                "mode": "tool_call_decision_transport",
                "tools": [
                    {
                        "type": "function",
                        "function": {
                            "name": DECISION_TRANSPORT_TOOL_NAME,
                            "description": "Return the manager call-tools decision as structured arguments.",
                            "parameters": schema,
                        },
                    }
                ],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": DECISION_TRANSPORT_TOOL_NAME},
                },
            },
            meta,
        )

    def _is_structured_output_transport_rejection(self, exc: httpx.HTTPStatusError) -> bool:
        response = exc.response
        if response is None or response.status_code not in {400, 404, 415, 422}:
            return False
        text = (response.text or "").lower()
        return any(marker in text for marker in ("response_format", "json_schema", "strict", "unsupported"))

    def _is_tool_call_transport_rejection(self, exc: httpx.HTTPStatusError) -> bool:
        response = exc.response
        if response is None or response.status_code not in {400, 404, 415, 422}:
            return False
        text = (response.text or "").lower()
        return any(marker in text for marker in ("tool_choice", "tools", "function", "unsupported"))

    def _extract_tool_call_decision(self, data: dict[str, Any]) -> dict[str, Any]:
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise _BuilderSpaceParseError(
                "BuilderSpace returned no tool-call choices.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=choices,
            )
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise _BuilderSpaceParseError(
                "BuilderSpace tool-call choice must be an object.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=first_choice,
            )
        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise _BuilderSpaceParseError(
                "BuilderSpace tool-call message must be an object.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=message,
            )
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list) or not tool_calls:
            raise _BuilderSpaceParseError(
                "BuilderSpace did not return the synthetic decision tool call.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=message.get("content"),
            )
        if len(tool_calls) != 1:
            raise _BuilderSpaceParseError(
                "BuilderSpace returned multiple synthetic decision tool calls.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=tool_calls,
            )
        tool_call = tool_calls[0]
        function = tool_call.get("function") if isinstance(tool_call, dict) else None
        if not isinstance(function, dict) or function.get("name") != DECISION_TRANSPORT_TOOL_NAME:
            raise _BuilderSpaceParseError(
                "BuilderSpace returned an unexpected synthetic decision tool call.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=tool_call,
            )
        arguments = function.get("arguments")
        if not isinstance(arguments, str):
            raise _BuilderSpaceParseError(
                "BuilderSpace synthetic decision tool arguments must be a JSON string.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=arguments,
            )
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise _BuilderSpaceParseError(
                "BuilderSpace synthetic decision tool arguments were not valid JSON.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=arguments,
            ) from exc
        if not isinstance(parsed, dict):
            raise _BuilderSpaceParseError(
                "BuilderSpace synthetic decision tool arguments must decode to an object.",
                failure_family="tool_call_transport_contract_breach",
                failing_component="builderspace_adapter.extract_tool_call_decision",
                observed_value=parsed,
            )
        return parsed

    def _validate_manager_payload(
        self,
        stage: str,
        payload: dict[str, Any],
        *,
        constraints: dict[str, Any] | None = None,
    ) -> None:
        schema = self._response_schema_for_stage(stage, constraints)
        if schema is None:
            return
        required = set(schema.get("required") or [])
        missing = sorted(key for key in required if key not in payload)
        if missing:
            raise RuntimeError(f"manager payload missing required fields for {stage}: {missing}")
        if schema.get("additionalProperties") is False:
            allowed = set((schema.get("properties") or {}).keys())
            unknown = sorted(key for key in payload.keys() if key not in allowed)
            if unknown:
                raise RuntimeError(f"manager payload has unknown fields for {stage}: {unknown}")
        if stage == MANAGER_LOOP_STAGE:
            validate_manager_pass1_branch(payload, constraints)

    def _is_configured(self) -> bool:
        return (
            self._has_real_value(self.base_url)
            and self._has_real_value(self.token)
            and self._has_real_value(self.manager_model)
        )

    def _has_real_value(self, value: str) -> bool:
        normalized = value.strip()
        if not normalized:
            return False
        if normalized in PLACEHOLDER_VALUES:
            return False
        if normalized.endswith("example.com"):
            return False
        return True

    def _effective_timeout_seconds(self, raw_value: str | None) -> tuple[int, bool]:
        if raw_value in (None, ""):
            return DEFAULT_TIMEOUT_SECONDS, False
        try:
            parsed = int(str(raw_value).strip())
        except (TypeError, ValueError):
            return DEFAULT_TIMEOUT_SECONDS, False
        if parsed <= 0:
            return DEFAULT_TIMEOUT_SECONDS, False
        if parsed > MAX_TIMEOUT_SECONDS:
            return MAX_TIMEOUT_SECONDS, True
        return parsed, False


def _observed_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, tuple):
        return "tuple"
    return "unknown"


def _value_excerpt(value: Any, *, max_chars: int = 1200) -> tuple[str | None, bool]:
    if value is None:
        return None, False
    rendered = value if isinstance(value, str) else json.dumps(_jsonable(value), ensure_ascii=False, default=str)
    if len(rendered) <= max_chars:
        return rendered, False
    return rendered[:max_chars], True


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
